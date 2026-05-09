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


def _normalize_channel(name: str) -> str:
    name = name.strip()
    name = name.removeprefix("https://t.me/").removeprefix("http://t.me/")
    name = name.removeprefix("t.me/").removeprefix("@")
    return name.split("/", 1)[0].split("?", 1)[0]


def _fetch_channel_html(channel: str) -> str | None:
    url = f"https://t.me/s/{channel}"
    try:
        resp = requests.get(url, headers=DEFAULT_HEADERS, timeout=REQUEST_TIMEOUT)
    except requests.RequestException as e:
        logger.warning("tg: %s — ошибка сети: %s", url, e)
        return None
    if resp.status_code != 200:
        logger.warning("tg: %s — HTTP %s", url, resp.status_code)
        return None
    return resp.text


def _extract_messages(html: str) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    nodes = soup.select(".tgme_widget_message_text")
    out: list[str] = []
    for node in nodes:
        text = node.get_text(" ", strip=True)
        if text:
            out.append(text)
    return out


def scrape_telegram_public(channels: Iterable[str]) -> list[str]:
    texts: list[str] = []
    for raw in channels:
        channel = _normalize_channel(raw)
        if not channel:
            continue
        html = _fetch_channel_html(channel)
        if html is None:
            continue
        msgs = _extract_messages(html)
        if not msgs:
            logger.warning(
                "tg: %s — превью пустое (канал приватный или нет публичного web-preview)",
                channel,
            )
            time.sleep(DELAY_BETWEEN_REQUESTS_SEC)
            continue
        logger.info("tg: %s — %d сообщений", channel, len(msgs))
        texts.extend(msgs)
        time.sleep(DELAY_BETWEEN_REQUESTS_SEC)
    return texts
