import os
import json
import base64
import logging
from collections.abc import Iterable, Mapping
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from supabase import create_client, Client

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(dotenv_path=_PROJECT_ROOT / ".env", override=True)
load_dotenv()

SUPABASE_URL = (os.environ.get("SUPABASE_URL") or "").strip()
SUPABASE_SERVICE_ROLE_KEY = (
    (os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or "").strip().lstrip("\ufeff")
)

WRITE_REPORTS = os.environ.get("WRITE_REPORTS", "").strip().lower() in {
    "1", "true", "yes", "on",
}


def _env_bool(name: str, default: bool = True) -> bool:
    raw = (os.environ.get(name) or "").strip().lower()
    if raw == "":
        return default
    if raw in {"0", "false", "no", "off"}:
        return False
    return raw in {"1", "true", "yes", "on"}


DAILY_REPORT_DEDUP = _env_bool("DAILY_REPORT_DEDUP", True)

if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
    raise ValueError(
        "Missing Supabase credentials in .env (SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)"
    )

logger = logging.getLogger(__name__)

REPORT_DESCRIPTION_MAX_LEN = 4000
DEFAULT_BATCH_SIZE = 500
SELECT_CHUNK_SIZE = 200

_FRAUD_TYPE_PRIORITY: dict[Any, int] = {
    "fake_police": 5,
    "bank_fraud": 4,
    "investment": 3,
    "spam": 2,
    "other": 1,
    None: 0,
    "": 0,
}


def _decode_jwt_role(key: str) -> str | None:
    if not key.startswith("eyJ"):
        return None
    try:
        payload_b64 = key.split(".")[1]
        pad = "=" * (-len(payload_b64) % 4)
        raw = base64.urlsafe_b64decode((payload_b64 + pad).encode("ascii"))
        return json.loads(raw.decode("utf-8")).get("role")
    except (ValueError, IndexError, json.JSONDecodeError, UnicodeDecodeError):
        return None


def _assert_service_role(key: str) -> None:
    if key.startswith("sb_publishable_"):
        raise ValueError(
            "SUPABASE_SERVICE_ROLE_KEY содержит publishable-ключ. "
            "Возьмите secret service_role в Supabase → Project Settings → API."
        )
    role = _decode_jwt_role(key)
    if role == "anon":
        raise ValueError(
            "SUPABASE_SERVICE_ROLE_KEY содержит anon-ключ. PostgREST применит RLS, "
            "INSERT/UPSERT в phone_numbers будет падать. Нужен service_role."
        )
    if role is not None and role != "service_role":
        logger.warning("Неожиданная роль в JWT: %s. Ожидался service_role.", role)


_assert_service_role(SUPABASE_SERVICE_ROLE_KEY)
supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)


def _is_valid_kz_e164(number: str) -> bool:
    return (
        isinstance(number, str)
        and len(number) == 12
        and number.startswith("+7")
        and number[1:].isdigit()
    )


def _fraud_type_rank(value: Any) -> int:
    return _FRAUD_TYPE_PRIORITY.get(value, 0)


def _stronger_fraud_type(a: str | None, b: str | None) -> str | None:
    return a if _fraud_type_rank(a) >= _fraud_type_rank(b) else b


def _parse_iso(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    return None


def _aggregate_records(
    records: Iterable[Mapping[str, Any]],
) -> dict[str, dict[str, Any]]:
    by_number: dict[str, dict[str, Any]] = {}
    for r in records:
        number = (r.get("number") or "").strip()
        if not _is_valid_kz_e164(number):
            continue
        ft = r.get("fraud_type") or None
        observed_at = r.get("observed_at") or datetime.now(timezone.utc)
        if observed_at.tzinfo is None:
            observed_at = observed_at.replace(tzinfo=timezone.utc)
        count = max(1, int(r.get("count", 1)))
        prev = by_number.get(number)
        if prev is None:
            by_number[number] = {
                "number": number,
                "fraud_type": ft,
                "report_count": count,
                "last_reported": observed_at,
            }
        else:
            prev["report_count"] += count
            prev["fraud_type"] = _stronger_fraud_type(prev["fraud_type"], ft)
            if observed_at > prev["last_reported"]:
                prev["last_reported"] = observed_at
    return by_number


def _fetch_existing(numbers: list[str]) -> dict[str, dict[str, Any]]:
    existing: dict[str, dict[str, Any]] = {}
    for i in range(0, len(numbers), SELECT_CHUNK_SIZE):
        chunk = numbers[i:i + SELECT_CHUNK_SIZE]
        resp = (
            supabase.table("phone_numbers")
            .select("number, report_count, last_reported, fraud_type")
            .in_("number", chunk)
            .execute()
        )
        for row in resp.data or []:
            existing[row["number"]] = row
    return existing


def upsert_phone_numbers(
    records: Iterable[Mapping[str, Any]],
    batch_size: int = DEFAULT_BATCH_SIZE,
) -> dict[str, int]:
    records_list = list(records)
    aggregated = _aggregate_records(records_list)
    if not aggregated:
        return {"received": len(records_list), "unique": 0, "upserted": 0, "dedup_skipped": 0}

    numbers = list(aggregated.keys())
    existing = _fetch_existing(numbers)
    run_day_utc = datetime.now(timezone.utc).date()

    rows: list[dict[str, Any]] = []
    dedup_skipped = 0
    for number, agg in aggregated.items():
        prev = existing.get(number) or {}
        prev_count = int(prev.get("report_count") or 0)
        prev_last = _parse_iso(prev.get("last_reported"))
        new_last: datetime = agg["last_reported"]
        candidates = [d for d in (prev_last, new_last) if d is not None]
        last_reported = max(candidates) if candidates else new_last
        increment = int(agg["report_count"])
        if (
            DAILY_REPORT_DEDUP
            and prev_last is not None
            and prev_last.astimezone(timezone.utc).date() == run_day_utc
        ):
            dedup_skipped += increment
            increment = 0
        rows.append({
            "number": number,
            "report_count": prev_count + increment,
            "last_reported": last_reported.isoformat(),
            "fraud_type": _stronger_fraud_type(prev.get("fraud_type"), agg["fraud_type"]),
        })

    upserted = 0
    for i in range(0, len(rows), batch_size):
        batch = rows[i:i + batch_size]
        try:
            supabase.table("phone_numbers").upsert(batch, on_conflict="number").execute()
            upserted += len(batch)
        except Exception as e:
            logger.error("phone_numbers upsert batch failed (size=%d): %s", len(batch), e)

    return {
        "received": len(records_list),
        "unique": len(aggregated),
        "upserted": upserted,
        "dedup_skipped": dedup_skipped,
    }


def insert_reports(records: Iterable[Mapping[str, Any]]) -> int:
    if not WRITE_REPORTS:
        return 0
    rows: list[dict[str, Any]] = []
    for r in records:
        number = (r.get("phone_number") or r.get("number") or "").strip()
        if not _is_valid_kz_e164(number):
            continue
        desc = (r.get("description") or "")[:REPORT_DESCRIPTION_MAX_LEN] or None
        rows.append({
            "phone_number": number,
            "fraud_type": r.get("fraud_type"),
            "description": desc,
            "region": r.get("region"),
        })
    if not rows:
        return 0

    inserted = 0
    for i in range(0, len(rows), DEFAULT_BATCH_SIZE):
        batch = rows[i:i + DEFAULT_BATCH_SIZE]
        try:
            supabase.table("reports").insert(batch).execute()
            inserted += len(batch)
        except Exception as e:
            logger.error("reports insert batch failed (size=%d): %s", len(batch), e)
    return inserted
