import re
import logging
from urllib.parse import urljoin

from .base import get_soup

logger = logging.getLogger(__name__)

BASE_URL = "https://www.jandarma.gov.tr"
LIST_URL = f"{BASE_URL}/duyurular"

TR_MONTHS = ["Oca", "Şub", "Mar", "Nis", "May", "Haz", "Tem", "Ağu", "Eyl", "Eki", "Kas", "Ara"]
MONTH_PATTERN = "|".join(TR_MONTHS)

DAY_RE = re.compile(r"^\d{1,2}$")
MONTH_RE = re.compile(rf"^({MONTH_PATTERN})$")
MIN_TITLE_LEN = 12


def scrape() -> list:
    """
    Jandarma /duyurular sayfasını tarar.
    Sayfa yapısı: her duyuru bir 'gün' + 'ay (kısaltma)' rozeti + başlık linkinden oluşuyor.
    Bunları DOM sırasına göre (state machine) eşliyoruz, böylece hangi tarihin
    hangi başlığa ait olduğunu karıştırma riski en aza iner.

    Dönüş: [{"id": url, "title": str, "url": str, "date": "27 Ağu"}, ...]
    En güncel duyuru listenin başında olacak şekilde sıralanır (sitedeki sırayla aynı).
    """
    soup = get_soup(LIST_URL)
    if soup is None:
        return []

    results = []
    seen_urls = set()
    pending_day = None
    pending_month = None

    for node in soup.descendants:
        if isinstance(node, str):
            text = node.strip()
            if not text:
                continue
            if DAY_RE.match(text):
                pending_day = text
            elif MONTH_RE.match(text):
                pending_month = text
        else:
            if getattr(node, "name", None) == "a" and node.get("href"):
                href = node["href"].strip()
                if href.startswith("#") or href.startswith("javascript"):
                    continue
                text = node.get_text(strip=True)
                if len(text) < MIN_TITLE_LEN:
                    continue
                full_url = urljoin(BASE_URL, href)
                if not full_url.startswith(BASE_URL) or full_url in seen_urls:
                    continue
                if pending_day and pending_month:
                    results.append({
                        "id": full_url,
                        "title": text,
                        "url": full_url,
                        "date": f"{pending_day} {pending_month}",
                    })
                    seen_urls.add(full_url)
                    pending_day = None
                    pending_month = None

    if not results:
        logger.warning("Jandarma sayfasında hiç duyuru bulunamadı; site yapısı değişmiş olabilir.")

    return results
