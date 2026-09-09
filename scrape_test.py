"""
Deploy etmeden ONCE calistir: python scrape_test.py

Telegram'a HICBIR mesaj GONDERMEZ, sadece her kaynaktan neler bulundugunu
ekrana yazdirir. Bir kaynak "SONUC YOK" derse, o sitenin HTML yapisi
scraper'in bekledigi kaliptan farklidir; bu ciktiyi Claude'a gosterip
scraper'i guncelletebilirsin.
"""
from scrapers import jandarma, msb


def show(name, items):
    print(f"\n=== {name} ===")
    if not items:
        print("SONUC YOK - selector/parse mantigi bu site icin calismiyor olabilir.")
        return
    for item in items[:5]:
        print(f"- [{item['date']}] {item['title']}")
        print(f"  {item['url']}")
    print(f"(toplam {len(items)} kayit bulundu, ilk 5 tanesi gosterildi)")


if __name__ == "__main__":
    show("JANDARMA", jandarma.scrape())
    show("MSB - DUYURULAR", msb.scrape("https://personeltemin.msb.gov.tr/AnaSayfa/Duyurular", "MSB-Duyuru"))
    show("MSB - TEMINLER", msb.scrape("https://personeltemin.msb.gov.tr/AnaSayfa/Teminler", "MSB-Temin"))
