import re
import logging
from urllib.parse import urljoin

from .base import get_soup_with_session

logger = logging.getLogger(__name__)

BASE_URL = "https://personeltemin.msb.gov.tr"
HOME_URL = f"{BASE_URL}/"

# Duyuru/temin kartları <a href="..."> DEĞİL, şu şekilde çalışıyor:
# <div onclick="javascript: window.location.href='/AnaSayfa/DuyuruDetay/?id=...';" class="item cal">
# Bu yüzden linki onclick içinden regex ile çıkarıyoruz.
ONCLICK_HREF_RE = re.compile(r"window\.location\.href\s*=\s*'([^']+)'")
DATE_RE = re.compile(r"^\d{2}\.\d{2}\.\d{4}$")


def scrape_home() -> dict:
    """
    MSB Personel Temin ana sayfasını (personeltemin.msb.gov.tr) tarar.

    Gerçek HTML yapısı (görüntülenen sayfa kaynağından doğrulandı):
      - Temin kartı:  <div class="item cal" onclick="...">
                         <div class="home-first-block--item">
                           <h3>BAŞLIK</h3> ... <p class="date">DD.MM.YYYY</p>
                         </div>
                       </div>
      - Duyuru kartı: <div class="item cal" onclick="...">
                         <div class="home-first-calendar--item">
                           ...
                           <div class="item--exp">
                             <h3>BAŞLIK</h3>
                             <p class="date">DD.MM.YYYY</p>
                           </div>
                         </div>
                       </div>

    "home-first-block--item" sınıfı temin kartlarını, "home-first-calendar--item"
    sınıfı duyuru kartlarını ayırt etmek için kullanılıyor.

    Dönüş: {"duyuru": [...], "temin": [...]}
    """
    soup = get_soup_with_session(HOME_URL, warmup_url=HOME_URL)
    if soup is None:
        logger.warning("MSB ana sayfası alınamadı.")
        return {"duyuru": [], "temin": []}

    result = {"duyuru": [], "temin": []}
    seen_urls = set()

    for card in soup.find_all("div", class_="cal"):
        onclick = card.get("onclick", "")
        match = ONCLICK_HREF_RE.search(onclick)
        if not match:
            continue

        href = match.group(1).strip()
        full_url = urljoin(BASE_URL, href)
        if full_url in seen_urls:
            continue

        h3 = card.find("h3")
        title = h3.get_text(strip=True) if h3 else ""

        date_str = ""
        for date_tag in card.find_all("p", class_="date"):
            candidate = date_tag.get_text(strip=True)
            if DATE_RE.match(candidate):
                date_str = candidate
                break

        if not title or not date_str:
            continue

        if card.find(class_="home-first-block--item"):
            category = "temin"
        elif card.find(class_="home-first-calendar--item"):
            category = "duyuru"
        else:
            continue

        seen_urls.add(full_url)
        result[category].append({
            "id": full_url,
            "title": title,
            "url": full_url,
            "date": date_str,
        })

    for key in result:
        if not result[key]:
            logger.warning(
                f"[MSB-{key}] hiç sonuç bulunamadı; sayfa yapısı beklenenden farklı olabilir."
            )

    return result
