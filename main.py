import logging
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer

import config
from storage import Storage
from telegram_notifier import TelegramNotifier
from scrapers import jandarma, msb

logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("main")

# Jandarma tek sayfa, tek kaynak.
JANDARMA_SOURCE = {"key": "jandarma", "label": "Jandarma"}

# MSB'de iki kategori ("duyuru", "temin") AYNI ana sayfadan tek istekle
# çıkarılıyor (bkz. scrapers/msb.py). Bu yüzden ayrı ele alınıyor.
MSB_SOURCES = {
    "duyuru": {"key": "msb_duyuru", "label": "MSB"},
    "temin": {"key": "msb_temin", "label": "MSB"},
}


def run_health_server():
    """
    Bazı barındırma platformları (Railway dahil, servis 'web' tipinde yapılandırılırsa)
    bir HTTP portunun açık olmasını bekleyebilir. Zararsız, minik bir health endpoint.
    """
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"OK")

        def log_message(self, *_args):
            pass  # http.server'in kendi log satirlarini bastir

    try:
        server = HTTPServer(("0.0.0.0", config.PORT), Handler)
        server.serve_forever()
    except Exception as e:
        logger.warning(f"Health server başlatılamadı (kritik değil): {e}")


def _process_items(key: str, label: str, items: list, storage: Storage, notifier: TelegramNotifier):
    """Tek bir kaynağın (jandarma / msb_duyuru / msb_temin) sonuçlarını işler:
    ilk çalıştırmada baseline atar, sonrasında sadece yeni olanları bildirir."""
    if not items:
        return

    is_first_run = not storage.has_any(key)

    if is_first_run:
        # İlk çalıştırma: spam olmaması için sadece en güncel duyuruyu bildir,
        # geri kalan mevcut duyuruları sessizce "görüldü" say.
        latest = items[0]
        notifier.send_announcement(latest["title"], label, latest["url"], latest["date"])
        for item in items:
            storage.mark_seen(key, item["id"], item["title"], item["url"])
        logger.info(f"[{key}] ilk çalıştırma: {len(items)} kayıt baseline olarak işaretlendi.")
        return

    new_items = [item for item in items if not storage.is_seen(key, item["id"])]

    # Eskiden yeniye doğru gönder (kronolojik sırayla kanala düşsün diye)
    for item in reversed(new_items):
        success = notifier.send_announcement(item["title"], label, item["url"], item["date"])
        if success:
            storage.mark_seen(key, item["id"], item["title"], item["url"])
            logger.info(f"[{key}] yeni duyuru gönderildi: {item['title'][:60]}")
        else:
            logger.error(f"[{key}] gönderilemedi, sonraki turda tekrar denenecek: {item['title'][:60]}")
        time.sleep(1)  # Telegram flood limitine takılmamak için


def check_all_sources(storage: Storage, notifier: TelegramNotifier):
    # --- Jandarma ---
    try:
        jandarma_items = jandarma.scrape()
    except Exception as e:
        logger.exception(f"[jandarma] tarama sırasında beklenmeyen hata: {e}")
        jandarma_items = []
    _process_items(JANDARMA_SOURCE["key"], JANDARMA_SOURCE["label"], jandarma_items, storage, notifier)

    # --- MSB (tek istekle iki kategori) ---
    try:
        msb_result = msb.scrape_home()
    except Exception as e:
        logger.exception(f"[msb] tarama sırasında beklenmeyen hata: {e}")
        msb_result = {"duyuru": [], "temin": []}

    for category, source_info in MSB_SOURCES.items():
        items = msb_result.get(category, [])
        _process_items(source_info["key"], source_info["label"], items, storage, notifier)


def main():
    config.validate_config()

    threading.Thread(target=run_health_server, daemon=True).start()

    storage = Storage(database_url=config.DATABASE_URL, sqlite_path=config.SQLITE_PATH)
    notifier = TelegramNotifier(config.TELEGRAM_BOT_TOKEN, config.TELEGRAM_CHANNEL_ID)

    logger.info(f"Bot başlatıldı. Kontrol aralığı: {config.CHECK_INTERVAL_MINUTES} dakika")

    while True:
        try:
            check_all_sources(storage, notifier)
        except Exception as e:
            logger.exception(f"Ana döngüde beklenmeyen hata: {e}")
        time.sleep(config.CHECK_INTERVAL_MINUTES * 60)


if __name__ == "__main__":
    main()
