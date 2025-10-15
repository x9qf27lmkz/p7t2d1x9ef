"""Seed the aptinfo table with raw payloads from the Seoul API."""
from __future__ import annotations

import logging
from decimal import Decimal, InvalidOperation
from typing import Sequence

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.db.database import SessionLocal
from app.models.aptinfo import AptInfo
from app.utils.normalize import normalize_lot, normalize_text, parse_yyyymmdd, stable_bigint_id
from app.utils.seoul_api import iter_rows

LOGGER = logging.getLogger(__name__)
SERVICE_NAME = "AptInfo"


def _to_decimal(value: object) -> Decimal | None:
    if value in (None, ""):
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return None


def _transform_row(row: dict) -> dict:
    return {
        "id": stable_bigint_id(row),
        "raw": row,
        "approval_date": parse_yyyymmdd(row.get("USE_APRV_YMD")),
        "gu_key": normalize_text(row.get("SGG_ADDR")),
        "dong_key": normalize_text(row.get("EMD_ADDR")),
        "name_key": normalize_text(row.get("APT_NM")),
        "lot_key": normalize_lot(row.get("APT_STDG_ADDR")),
        "lat": _to_decimal(row.get("Y")),
        "lng": _to_decimal(row.get("X")),
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


def run(service_name: str = SERVICE_NAME) -> None:
    """Fetch the apt info dataset and upsert it into the database."""

    with SessionLocal() as session:
        batch_count = 0
        for batch in iter_rows(service_name):
            _upsert_rows(session, batch)
            session.commit()
            batch_count += 1
            LOGGER.info("aptinfo batch %s committed", batch_count)


if __name__ == "__main__":  # pragma: no cover - manual script
    logging.basicConfig(level=logging.INFO)
    run()
