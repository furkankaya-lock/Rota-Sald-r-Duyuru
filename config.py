import os

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHANNEL_ID = os.getenv("TELEGRAM_CHANNEL_ID", "")
CHECK_INTERVAL_MINUTES = int(os.getenv("CHECK_INTERVAL_MINUTES", "45"))
DATABASE_URL = os.getenv("DATABASE_URL", "")  # dolu ise Postgres, boş ise SQLite kullanılır
SQLITE_PATH = os.getenv("SQLITE_PATH", "bot_data.db")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
PORT = int(os.getenv("PORT", "8080"))

REQUIRED_VARS = ["TELEGRAM_BOT_TOKEN", "TELEGRAM_CHANNEL_ID"]


def validate_config():
    missing = [v for v in REQUIRED_VARS if not os.getenv(v)]
    if missing:
        raise RuntimeError(
            f"Eksik ortam değişkenleri: {', '.join(missing)}. "
            f"Railway 'Variables' sekmesinden veya yerelde .env dosyasından ekleyin."
        )
