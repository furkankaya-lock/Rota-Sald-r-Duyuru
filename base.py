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
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
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


def fetch_html_with_session(url: str, warmup_url: str = None, timeout: int = 20, max_retries: int = 3) -> Optional[str]:
    """
    Bazı siteler direkt/referrer'sız isteklere karşı korumalı olabiliyor.
    Önce ana sayfaya (warmup_url) gidip çerez/cookie alan, sonra asıl sayfayı
    o oturumla ve Referer header'ıyla çeken bir versiyon.
    """
    session = requests.Session()
    session.headers.update(DEFAULT_HEADERS)

    if warmup_url:
        try:
            session.get(warmup_url, timeout=timeout)
        except requests.RequestException as e:
            logger.warning(f"Warmup isteği başarısız ({warmup_url}): {e}")

    extra_headers = {"Referer": warmup_url} if warmup_url else {}

    for attempt in range(1, max_retries + 1):
        try:
            resp = session.get(url, headers=extra_headers, timeout=timeout)
            resp.raise_for_status()
            resp.encoding = resp.apparent_encoding or resp.encoding or "utf-8"
            return resp.text
        except requests.RequestException as e:
            logger.warning(f"[{url}] fetch hatası (deneme {attempt}/{max_retries}): {e}")
            time.sleep(2 * attempt)

    logger.error(f"[{url}] sayfa alınamadı, tüm denemeler başarısız.")
    return None


def get_soup_with_session(url: str, warmup_url: str = None) -> Optional[BeautifulSoup]:
    html = fetch_html_with_session(url, warmup_url)
    if html is None:
        return None
    return BeautifulSoup(html, "html.parser")
