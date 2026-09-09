import logging
import time
from typing import Optional

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


def fetch_html(url: str, timeout: int = 20, max_retries: int = 3) -> Optional[str]:
    for attempt in range(1, max_retries + 1):
        try:
            resp = requests.get(url, headers=DEFAULT_HEADERS, timeout=timeout)
            resp.raise_for_status()
            resp.encoding = resp.apparent_encoding or resp.encoding or "utf-8"
            return resp.text
        except requests.RequestException as e:
            logger.warning(f"[{url}] fetch hatası (deneme {attempt}/{max_retries}): {e}")
            time.sleep(2 * attempt)
    logger.error(f"[{url}] sayfa alınamadı, tüm denemeler başarısız.")
    return None


def get_soup(url: str) -> Optional[BeautifulSoup]:
    html = fetch_html(url)
    if html is None:
        return None
    return BeautifulSoup(html, "html.parser")
