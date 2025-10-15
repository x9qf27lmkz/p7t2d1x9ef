"""Seed the sale table with contract payloads from the Seoul API."""
from __future__ import annotations

import logging
import os
from decimal import Decimal, InvalidOperation
from typing import Sequence

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.db.database import SessionLocal
from app.models.sale import Sale
from app.utils.normalize import (
    clean_lot_jibun,
    mwon_to_krw,
    norm_text,
    stable_bigint_id,
    yyyymmdd_to_date,
)
from app.utils.seoul_api import fetch_pages, probe_service

LOGGER = logging.getLogger(__name__)
SERVICE_CANDIDATES = ("tbLnOpendataRtmsV", "RealEstateSales", "tbLnOpendataRltm")


def _to_decimal(value: object) -> Decimal | None:
    if value in (None, ""):
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return None


def _lot_from(row: dict) -> str | None:
    main = row.get("MNO")
    sub = row.get("SNO")
    if main in (None, ""):
        return None
    lot = str(main)
    if sub not in (None, "", "0"):
        lot = f"{lot}-{sub}"
    return clean_lot_jibun(lot)


def _coords(row: dict) -> tuple[Decimal | None, Decimal | None]:
    lat = _to_decimal(row.get("LAT") or row.get("Y") or row.get("WGS84_Y"))
    lng = _to_decimal(row.get("LNG") or row.get("X") or row.get("WGS84_X"))
    return lat, lng


def _transform_row(row: dict) -> dict:
    raw = dict(row)
    contract_date = yyyymmdd_to_date(row.get("CTRT_YMD") or row.get("CTRT_DAY"))
    area = _to_decimal(row.get("ARCH_AREA") or row.get("RENT_AREA"))
    price = mwon_to_krw(row.get("THING_AMT") or row.get("SUM_AMT"))
    lat, lng = _coords(row)

    return {
        "id": stable_bigint_id(raw),
        "raw": raw,
        "contract_date": contract_date,
        "price_krw": price,
        "area_m2": area,
        "gu_key": norm_text(row.get("CGG_NM") or row.get("SGG_NM")),
        "dong_key": norm_text(row.get("STDG_NM") or row.get("EMD_ADDR")),
        "name_key": norm_text(row.get("BLDG_NM") or row.get("APT_NM")),
        "lot_key": _lot_from(row),
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
            insert(Sale)
            .values(**values)
            .on_conflict_do_update(index_elements=[Sale.id], set_=update_values)
        )
        session.execute(stmt)


def run(service_name: str | None = None, *, api_key: str | None = None) -> None:
    """Fetch the sale dataset and upsert it into the database."""

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
            LOGGER.info("sale batch %s committed", batch_count)


if __name__ == "__main__":  # pragma: no cover - manual script
    logging.basicConfig(level=logging.INFO)
    run()
