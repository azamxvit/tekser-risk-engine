from __future__ import annotations

import logging
import time
from typing import Iterable

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "ru-RU,ru;q=0.9,kk;q=0.8,en;q=0.7",
}
REQUEST_TIMEOUT = 15
DELAY_BETWEEN_REQUESTS_SEC = 1.0


def _fetch(url: str) -> str | None:
    try:
        resp = requests.get(url, headers=DEFAULT_HEADERS, timeout=REQUEST_TIMEOUT)
    except requests.RequestException as e:
        logger.warning("web: %s — ошибка сети: %s", url, e)
        return None
    if resp.status_code != 200:
        logger.warning("web: %s — HTTP %s", url, resp.status_code)
        return None
    return resp.text


def _visible_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    return soup.get_text(" ", strip=True)


def scrape_web_pages(
    urls: Iterable[str],
    pages_per_url: int = 1,
) -> list[str]:
    texts: list[str] = []
    for url in urls:
        if "{page}" in url:
            for page in range(1, max(1, pages_per_url) + 1):
                full_url = url.replace("{page}", str(page))
                html = _fetch(full_url)
                if html:
                    text = _visible_text(html)
                    if text:
                        logger.info("web: %s — %d симв.", full_url, len(text))
                        texts.append(text)
                time.sleep(DELAY_BETWEEN_REQUESTS_SEC)
        else:
            html = _fetch(url)
            if html:
                text = _visible_text(html)
                if text:
                    logger.info("web: %s — %d симв.", url, len(text))
                    texts.append(text)
            time.sleep(DELAY_BETWEEN_REQUESTS_SEC)
    return texts
