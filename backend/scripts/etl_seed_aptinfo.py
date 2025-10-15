"""Seed the aptinfo table with raw payloads from the Seoul API."""
from __future__ import annotations

import logging
import os
from decimal import Decimal, InvalidOperation
from typing import Sequence

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.db.database import SessionLocal
from app.models.aptinfo import AptInfo
from app.utils.normalize import (
    clean_lot_jibun,
    norm_text,
    stable_bigint_id,
    yyyymmdd_to_date,
)
from app.utils.seoul_api import fetch_pages, probe_service

LOGGER = logging.getLogger(__name__)
SERVICE_CANDIDATES = ("AptInfo", "OpenAptInfo", "ApartmentInfo")


def _to_decimal(value: object) -> Decimal | None:
    if value in (None, ""):
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return None


def _coords(row: dict) -> tuple[Decimal | None, Decimal | None]:
    lat = _to_decimal(
        row.get("WGS84_Y") or row.get("Y") or row.get("LAT") or row.get("YCRD")
    )
    lng = _to_decimal(
        row.get("WGS84_X") or row.get("X") or row.get("LNG") or row.get("XCRD")
    )
    return lat, lng


def _transform_row(row: dict) -> dict:
    raw = dict(row)
    approval_date = yyyymmdd_to_date(
        row.get("USE_APRV_YMD") or row.get("CMPX_APRV_DAY")
    )
    year = approval_date.year if approval_date else None
    lat, lng = _coords(row)
    return {
        "id": stable_bigint_id(raw),
        "raw": raw,
        "approval_date": approval_date,
        "year_approved": year,
        "gu_key": norm_text(row.get("SGG_ADDR")),
        "dong_key": norm_text(row.get("EMD_ADDR")),
        "name_key": norm_text(row.get("APT_NM")),
        "lot_key": clean_lot_jibun(row.get("APT_STDG_ADDR")),
        "lat": lat,
        "lng": lng,
    }


def _upsert_rows(session: Session, rows: Sequence[dict]) -> None:
    if not rows:
        return
    for payload in rows:
        values = _transform_row(payload)
        update_values = values.copy()
        update_values.pop("id", None)
        stmt = (
            insert(AptInfo)
            .values(**values)
            .on_conflict_do_update(index_elements=[AptInfo.id], set_=update_values)
        )
        session.execute(stmt)


def run(service_name: str | None = None, *, api_key: str | None = None) -> None:
    """Fetch the apt info dataset and upsert it into the database."""

    key = api_key or os.getenv("SEOUL_API_KEY")
    if not key:
        raise RuntimeError("SEOUL_API_KEY not set")

    service = service_name or probe_service(key, SERVICE_CANDIDATES)

    with SessionLocal() as session:
        batch_count = 0
        for batch in fetch_pages(key, service):
            _upsert_rows(session, batch)
            session.commit()
            batch_count += 1
            LOGGER.info("aptinfo batch %s committed", batch_count)


if __name__ == "__main__":  # pragma: no cover - manual script
    logging.basicConfig(level=logging.INFO)
    run()
