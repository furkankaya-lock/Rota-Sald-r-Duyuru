# Telegram Duyuru Botu (MSB & Jandarma)

Jandarma ve MSB Personel Temin sitelerindeki yeni duyuruları/temin ilanlarını
45 dakikada bir kontrol edip Telegram kanalına otomatik mesaj atan bot.

## Takip Edilen Kaynaklar

| Kaynak | URL |
|---|---|
| Jandarma | https://www.jandarma.gov.tr/duyurular |
| MSB - Güncel Duyurular | https://personeltemin.msb.gov.tr/AnaSayfa/Duyurular |
| MSB - Güncel Teminler | https://personeltemin.msb.gov.tr/AnaSayfa/Teminler |

## Mesaj Formatı

```
🚨 Yeni Duyuru!
📌 Başlık: ...
🌐 Site: MSB / Jandarma
🔗 Link: ...
🕒 Tarih: ...
```

## ÖNEMLİ - Deploy Etmeden Önce Mutlaka Yapılması Gereken

Bu sitelerin HTML yapısı manuel incelenerek (ekran görüntüsü üzerinden) taklit
edildi, canlı test edilemedi çünkü siteler otomatik erişim araçlarını
robots.txt ile kısıtlıyor. **Deploy etmeden önce mutlaka yerelde çalıştır:**

```bash
pip install -r requirements.txt
python scrape_test.py
```

Her üç kaynak için de birkaç kayıt basıyorsa sorun yok, deploy edebilirsin.
Bir kaynak "SONUC YOK" diyorsa, o sitenin HTML yapısı beklenenden farklıdır —
konsol çıktısını (ve mümkünse sayfanın HTML kaynağını) paylaş, scraper'ı
güncelleriz.

## Kurulum (Yerel)

1. Python 3.11+ kur
2. Bağımlılıkları kur:
   ```bash
   pip install -r requirements.txt
   ```
3. `.env.example` dosyasını `.env` olarak kopyala, kendi bilgilerini gir:
   ```bash
   cp .env.example .env
   ```
4. Test et:
   ```bash
   python scrape_test.py
   ```
5. Botu çalıştır:
   ```bash
   python main.py
   ```

## Railway'e Deploy

1. Bu klasörü GitHub reposuna yükle.
2. Railway'de "New Project" → "Deploy from GitHub repo" ile bu repoyu seç.
   `Dockerfile` otomatik algılanır.
3. Railway'in **Variables** sekmesinden şu değişkenleri ekle:
   - `TELEGRAM_BOT_TOKEN`
   - `TELEGRAM_CHANNEL_ID`
   - `CHECK_INTERVAL_MINUTES` (opsiyonel, varsayılan 45)
4. **Önerilen:** Railway'de "New" → "Database" → "PostgreSQL" ekle. Railway
   otomatik olarak `DATABASE_URL` değişkenini servise bağlar (Variable
   Reference ile). Bu, redeploy'larda "hangi duyurular gönderildi" bilgisinin
   silinmesini engeller. Postgres eklemezsen bot SQLite dosyasına yazar ama bu
   dosya her redeploy'da sıfırlanabilir ve bot eski duyuruları tekrar atabilir.
5. Deploy sonrası logları kontrol et: "Bot başlatıldı" ve "ilk çalıştırma"
   satırlarını görmen lazım, kanalına da 3 kaynaktan birer "baseline" mesajı
   düşer.

## Davranış Kuralları

- **İlk çalıştırma:** Her kaynağın sadece en güncel duyurusu gönderilir
  (geçmiş duyurularla kanalı doldurmamak için), geri kalanlar sessizce
  "görüldü" işaretlenir.
- **Sonraki taramalar:** Sadece daha önce görülmemiş duyurular gönderilir.
  Aynı duyuru bir daha asla tekrar gönderilmez.
- **Kontrol sıklığı:** `CHECK_INTERVAL_MINUTES` ile ayarlanır (varsayılan 45).
- **Hata toleransı:** Bir kaynak tarama sırasında hata verirse (site geçici
  kapalı, yapı değişmiş vb.) diğer kaynaklar etkilenmez, bot çökmez, bir
  sonraki turda tekrar dener.

## Proje Yapısı

```
telegram-duyuru-bot/
├── main.py                  # Zamanlayıcı döngü + orkestrasyon
├── config.py                 # Ortam değişkenleri
├── storage.py                 # SQLite/Postgres görülen-duyuru takibi
├── telegram_notifier.py       # Telegram'a mesaj gönderme
├── scrapers/
│   ├── base.py                # Ortak HTTP fetch fonksiyonları
│   ├── jandarma.py            # Jandarma scraper
│   └── msb.py                  # MSB Duyurular + Teminler scraper
├── scrape_test.py             # Deploy öncesi doğrulama scripti
├── requirements.txt
├── Dockerfile
├── .env.example
└── .gitignore
```

## Sorun Giderme

- **Bot mesaj atmıyor:** Botun kanala **admin** olarak eklendiğinden emin ol.
  `TELEGRAM_CHANNEL_ID` kanal kullanıcı adıysa `@` ile başlamalı.
- **"SONUC YOK" hatası:** İlgili sitenin HTML yapısı değişmiş demektir,
  `scrape_test.py` çıktısını paylaş, scraper güncellenir.
- **Aynı duyuru tekrar tekrar geliyor:** `DATABASE_URL` ayarlı değilse ve
  Railway container'ı yeniden başlatıldıysa SQLite dosyası sıfırlanmış
  olabilir — Postgres ekle (yukarıdaki adım 4).
