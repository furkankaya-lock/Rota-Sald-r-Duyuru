import re
import logging
from urllib.parse import urljoin

from .base import get_soup_with_session

logger = logging.getLogger(__name__)

BASE_URL = "https://personeltemin.msb.gov.tr"
HOME_URL = f"{BASE_URL}/"

DATE_RE = re.compile(r"(\d{2}\.\d{2}\.\d{4})")
MIN_TITLE_LEN = 8

# Ana sayfadaki iki bölümün başlık metinleri (ekran görüntüsünden doğrulandı)
SECTION_HEADINGS = {
    "duyuru": "GÜNCEL DUYURULAR",
    "temin": "GÜNCEL TEMİNLER",
}


def scrape_home() -> dict:
    """
    MSB Personel Temin ana sayfasını (personeltemin.msb.gov.tr) tek seferde tarar;
    hem 'Güncel Duyurular' hem 'Güncel Teminler' bloklarını aynı sayfadan çıkarır.

    NOT: /AnaSayfa/Duyurular ve /AnaSayfa/Teminler alt adresleri doğrudan HTTP
    isteğiyle 404 döndürüyor (muhtemelen JS ile açılan client-side route ya da
    bot koruması). Bu yüzden gerçek tarayıcıda da görülen ana sayfa taranıyor.

    Dönüş: {"duyuru": [...], "temin": [...]}
    Her öğe: {"id": url, "title": str, "url": str, "date": "DD.MM.YYYY"}
    """
    soup = get_soup_with_session(HOME_URL, warmup_url=HOME_URL)
    if soup is None:
        logger.warning("MSB ana sayfası alınamadı.")
        return {"duyuru": [], "temin": []}

    result = {}
    for key, heading_text in SECTION_HEADINGS.items():
        container = _find_section_container(soup, heading_text)
        items = _extract_items_from_container(container, BASE_URL) if container else []
        if not items:
            logger.warning(
                f"[MSB-{key}] hiç sonuç bulunamadı; sayfa yapısı beklenenden farklı olabilir."
            )
        result[key] = items
    return result


def _find_section_container(soup, heading_text):
    """Verilen başlık metnini TAM olarak içeren en küçük etiketi bulur,
    sonra o bölümü saran (renkli/çerçeveli) kutuya ulaşmak için birkaç
    seviye yukarı çıkar."""
    heading_lower = heading_text.strip().lower()
    for tag in soup.find_all(True):
        text = tag.get_text(strip=True)
        if text.lower() == heading_lower:
            container = tag
            for _ in range(3):
                if container.parent is None:
                    break
                container = container.parent
            return container
    return None


def _extract_items_from_container(container, base_url):
    if container is None:
        return []

    results = []
    seen = set()
    for a in container.find_all("a", href=True):
        href = a["href"].strip()
        if href.startswith("#") or href.startswith("javascript"):
            continue
        text = a.get_text(strip=True)
        if len(text) < MIN_TITLE_LEN:
            continue
        full_url = urljoin(base_url, href)
        if full_url in seen:
            continue
        date_str = _find_nearby_date(a)
        seen.add(full_url)
        results.append({
            "id": full_url,
            "title": text,
            "url": full_url,
            "date": date_str or "",
        })

    if results:
        return results

    # Fallback: bağlantı (<a>) bulunamadıysa, kalın/başlık metinlerle
    # tarihleri sıraya göre eşleştirmeyi dene (link olmasa bile en azından
    # yeni duyuru geldiğini haber verebilmek için).
    return _extract_items_textual(container, base_url)


def _extract_items_textual(container, base_url):
    results = []
    pending_title = None
    for node in container.descendants:
        if isinstance(node, str):
            text = node.strip()
            if not text:
                continue
            match = DATE_RE.search(text)
            if match and pending_title:
                results.append({
                    "id": pending_title,
                    "title": pending_title,
                    "url": base_url,
                    "date": match.group(1),
                })
                pending_title = None
        else:
            if getattr(node, "name", None) in ("strong", "b", "h1", "h2", "h3", "h4", "h5"):
                t = node.get_text(strip=True)
                if len(t) >= MIN_TITLE_LEN:
                    pending_title = t
    return results


def _find_nearby_date(anchor_tag):
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
