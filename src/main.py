import logging
import os
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

from core.classifier import get_scam_type
from core.extractor import extract_kz_phones
from db.supabase_client import (
    WRITE_REPORTS,
    insert_reports,
    upsert_phone_numbers,
)
from scrapers.tg_scraper import scrape_telegram_public
from scrapers.web_scraper import scrape_web_pages

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(dotenv_path=_PROJECT_ROOT / ".env", override=True)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def _csv_env(name: str) -> list[str]:
    raw = os.environ.get(name, "") or ""
    return [x.strip() for x in raw.split(",") if x.strip()]


def _int_env(name: str, default: int) -> int:
    raw = (os.environ.get(name) or "").strip()
    if not raw:
        return default
    try:
        return max(1, int(raw))
    except ValueError:
        logger.warning("%s=%r — не число, использую %d", name, raw, default)
        return default


def collect_texts() -> list[str]:
    texts: list[str] = []

    web_urls = _csv_env("SCRAPER_URLS")
    pages = _int_env("SCRAPER_PAGES", 1)
    if web_urls:
        logger.info("web: %d URL(ов), pages_per_url=%d", len(web_urls), pages)
        texts.extend(scrape_web_pages(web_urls, pages_per_url=pages))
    else:
        logger.info("web: SCRAPER_URLS пуст — пропускаю")

    tg_channels = _csv_env("TG_PUBLIC_CHANNELS")
    if tg_channels:
        logger.info("tg: %d канал(ов)", len(tg_channels))
        texts.extend(scrape_telegram_public(tg_channels))
    else:
        logger.info("tg: TG_PUBLIC_CHANNELS пуст — пропускаю")

    return texts


def texts_to_records(texts: list[str]) -> tuple[list[dict], list[dict]]:
    now = datetime.now(timezone.utc)
    phone_records: list[dict] = []
    report_records: list[dict] = []

    for text in texts:
        fraud_type = get_scam_type(text)
        for phone in extract_kz_phones(text):
            phone_records.append(
                {
                    "number": phone,
                    "fraud_type": fraud_type,
                    "observed_at": now,
                    "count": 1,
                }
            )
            if WRITE_REPORTS:
                report_records.append(
                    {
                        "phone_number": phone,
                        "fraud_type": fraud_type,
                        "description": text[:1000],
                    }
                )
    return phone_records, report_records


def run_etl_pipeline() -> None:
    logger.info("Tekser ETL: старт (write_reports=%s)", WRITE_REPORTS)

    texts = collect_texts()
    logger.info("Собрано текстов: %d", len(texts))

    if not texts:
        logger.warning(
            "Нет источников. Заполните SCRAPER_URLS и/или TG_PUBLIC_CHANNELS в .env."
        )
        return

    phone_records, report_records = texts_to_records(texts)

    stats = upsert_phone_numbers(phone_records)
    logger.info(
        "phone_numbers: received=%d unique=%d upserted=%d dedup_skipped=%d",
        stats["received"],
        stats["unique"],
        stats["upserted"],
        stats.get("dedup_skipped", 0),
    )

    if WRITE_REPORTS:
        inserted = insert_reports(report_records)
        logger.info("reports: inserted=%d", inserted)

    logger.info("Tekser ETL: готово")


if __name__ == "__main__":
    run_etl_pipeline()
