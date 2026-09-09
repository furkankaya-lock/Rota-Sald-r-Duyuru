import re
import logging
from urllib.parse import urljoin

from .base import get_soup

logger = logging.getLogger(__name__)

BASE_URL = "https://personeltemin.msb.gov.tr"

# Detay sayfalarına giden linkleri yakalamak için genel bir desen.
# (örn: /AnaSayfa/DuyuruDetay/?id=..., /AnaSayfa/TeminDetay/?id=...)
DETAIL_HREF_RE = re.compile(r"(duyurudetay|temindetay|detay)", re.IGNORECASE)
DATE_RE = re.compile(r"(\d{2}\.\d{2}\.\d{4})")
MIN_TITLE_LEN = 8


def scrape(url: str, source_label: str = "MSB") -> list:
    """
    MSB Personel Temin sitesindeki bir liste sayfasını (Duyurular veya Teminler) tarar.

    Dönüş: [{"id": url, "title": str, "url": str, "date": "08.09.2026"}, ...]
    """
    soup = get_soup(url)
    if soup is None:
        return []

    results = []
    seen_urls = set()

    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if not DETAIL_HREF_RE.search(href):
            continue

        full_url = urljoin(BASE_URL, href)
        if full_url in seen_urls:
            continue

        title = a.get_text(strip=True)
        if len(title) < MIN_TITLE_LEN:
            heading = a.find_next(["h1", "h2", "h3", "h4", "strong", "b"])
            if heading:
                title = heading.get_text(strip=True)

        date_str = _find_nearby_date(a)

        if not title or not date_str:
            continue

        seen_urls.add(full_url)
        results.append({
            "id": full_url,
            "title": title,
            "url": full_url,
            "date": date_str,
        })

    if not results:
        logger.warning(f"[{source_label}] hiç sonuç bulunamadı; sayfa yapısı beklenenden farklı olabilir.")

    return results


def _find_nearby_date(anchor_tag):
    """Anchor'ın bulunduğu kartın metninde DD.MM.YYYY formatlı tarihi arar."""
    container = anchor_tag
    for _ in range(3):
        if container is None:
            break
        text = container.get_text(" ", strip=True)
        match = DATE_RE.search(text)
        if match:
            return match.group(1)
        container = container.parent
    return None
