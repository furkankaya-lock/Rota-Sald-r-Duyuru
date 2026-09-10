import re
import logging
from urllib.parse import urljoin

from .base import get_soup_with_session

logger = logging.getLogger(__name__)

BASE_URL = "https://personeltemin.msb.gov.tr"
HOME_URL = f"{BASE_URL}/"

DATE_RE = re.compile(r"(\d{2}\.\d{2}\.\d{4})")
MIN_TITLE_LEN = 8
MAX_NODE_DISTANCE = 60  # tarih ile link arasında izin verilen maksimum DOM mesafesi

SECTION_MARKERS = {
    "GÜNCEL DUYURULAR": "duyuru",
    "GÜNCEL TEMİNLER": "temin",
}


def scrape_home() -> dict:
    """
    MSB Personel Temin ana sayfasını tarar; 'Güncel Duyurular' ve 'Güncel Teminler'
    bloklarını aynı sayfadan çıkarır.

    Yöntem: Sayfadaki her DD.MM.YYYY tarihini, DOM sırasında ona EN YAKIN olan
    (öncesinde ya da sonrasında fark etmez) <a> etiketiyle eşleştirir. Bu sayede
    hangi kutunun tam olarak nerede başlayıp bittiğini tahmin etmeye gerek kalmaz
    ve menü/giriş linkleri gibi yanında tarih olmayan öğeler otomatik elenir.
    Hangi bölüme (duyuru/temin) ait olduğu, o tarihten önce görülen en son
    "GÜNCEL DUYURULAR" / "GÜNCEL TEMİNLER" başlığına bakılarak belirlenir.

    Dönüş: {"duyuru": [...], "temin": [...]}
    """
    soup = get_soup_with_session(HOME_URL, warmup_url=HOME_URL)
    if soup is None:
        logger.warning("MSB ana sayfası alınamadı.")
        return {"duyuru": [], "temin": []}

    flat_nodes = list(soup.descendants)

    section_positions = []  # [(index, "duyuru"|"temin")]
    date_positions = []     # [(index, "DD.MM.YYYY")]
    anchor_positions = []   # [(index, <a> tag)]

    for idx, node in enumerate(flat_nodes):
        if isinstance(node, str):
            text = node.strip()
            if not text:
                continue
            upper = text.upper()
            matched_section = None
            for marker, key in SECTION_MARKERS.items():
                if marker in upper:
                    matched_section = key
                    break
            if matched_section:
                section_positions.append((idx, matched_section))
                continue
            date_match = DATE_RE.search(text)
            if date_match:
                date_positions.append((idx, date_match.group(1)))
        else:
            if getattr(node, "name", None) == "a" and node.get("href"):
                href = node["href"].strip()
                if href.startswith("#") or href.startswith("javascript"):
                    continue
                text = node.get_text(strip=True)
                if len(text) >= MIN_TITLE_LEN:
                    anchor_positions.append((idx, node))

    def section_for(idx: int):
        current = None
        for pos, key in section_positions:
            if pos <= idx:
                current = key
            else:
                break
        return current

    result = {"duyuru": [], "temin": []}
    seen_urls = set()

    for date_idx, date_str in date_positions:
        best_anchor = None
        best_dist = None
        for anchor_idx, anchor_tag in anchor_positions:
            dist = abs(anchor_idx - date_idx)
            if dist > MAX_NODE_DISTANCE:
                continue
            if best_dist is None or dist < best_dist:
                best_anchor = anchor_tag
                best_dist = dist

        if best_anchor is None:
            continue

        section = section_for(date_idx)
        if section is None:
            continue

        href = best_anchor["href"].strip()
        full_url = urljoin(BASE_URL, href)
        if full_url in seen_urls:
            continue
        seen_urls.add(full_url)

        result[section].append({
            "id": full_url,
            "title": _extract_title(best_anchor),
            "url": full_url,
            "date": date_str,
        })

    for key in result:
        if not result[key]:
            logger.warning(
                f"[MSB-{key}] hiç sonuç bulunamadı; sayfa yapısı beklenenden farklı olabilir."
            )

    return result


def _extract_title(anchor_tag) -> str:
    """
    <a> etiketi başlık+açıklama+tarih gibi birden fazla şeyi birlikte
    sarmalıyorsa, sadece asıl başlık kısmını (varsa) almaya çalışır.
    """
    heading = anchor_tag.find(["h1", "h2", "h3", "h4", "h5", "strong", "b"])
    if heading:
        text = heading.get_text(strip=True)
        if len(text) >= MIN_TITLE_LEN:
            return text

    full_text = anchor_tag.get_text(strip=True)
    # Tarih deseniyle karşılaşınca kes (başlığın hemen ardından tarih geliyorsa)
    date_match = DATE_RE.search(full_text)
    if date_match:
        full_text = full_text[:date_match.start()].strip()
    return full_text
