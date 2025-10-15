"""Seed the rent table with lease payloads from the Seoul API."""
from __future__ import annotations

import logging
from decimal import Decimal, InvalidOperation
from typing import Sequence

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.db.database import SessionLocal
from app.models.rent import Rent
from app.utils.normalize import normalize_lot, normalize_text, parse_yyyymmdd, stable_bigint_id
from app.utils.seoul_api import iter_rows

LOGGER = logging.getLogger(__name__)
SERVICE_NAME = "tbLnOpendataRlstM"


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
    return normalize_lot(lot)


def _transform_row(row: dict) -> dict:
    contract_date = parse_yyyymmdd(row.get("CTRT_DAY") or row.get("CTRT_YMD"))
    area = _to_decimal(row.get("RENT_AREA") or row.get("ARCH_AREA"))

    deposit = None
    deposit_raw = row.get("GRFE") or row.get("DEPOSIT")
    if deposit_raw not in (None, ""):
        try:
            deposit = int(Decimal(str(deposit_raw)) * Decimal("10000"))
        except (InvalidOperation, TypeError, ValueError):
            deposit = None

    rent = None
    rent_raw = row.get("RTFE") or row.get("MONTHLY_RENT")
    if rent_raw not in (None, ""):
        try:
            rent = int(Decimal(str(rent_raw)) * Decimal("10000"))
        except (InvalidOperation, TypeError, ValueError):
            rent = None

    return {
        "id": stable_bigint_id(row),
        "raw": row,
        "contract_date": contract_date,
        "deposit_krw": deposit,
        "rent_krw": rent,
        "area_m2": area,
        "gu_key": normalize_text(row.get("CGG_NM") or row.get("SGG_NM")),
        "dong_key": normalize_text(row.get("STDG_NM") or row.get("EMD_ADDR")),
        "name_key": normalize_text(row.get("BLDG_NM") or row.get("APT_NM")),
        "lot_key": _lot_from(row),
        "lat": _to_decimal(row.get("LAT") or row.get("Y")),
        "lng": _to_decimal(row.get("LNG") or row.get("X")),
    }


def _upsert_rows(session: Session, rows: Sequence[dict]) -> None:
    if not rows:
        return
    for payload in rows:
        values = _transform_row(payload)
        update_values = values.copy()
        update_values.pop("id", None)
        stmt = (
            insert(Rent)
            .values(**values)
            .on_conflict_do_update(index_elements=[Rent.id], set_=update_values)
        )
        session.execute(stmt)


def run(service_name: str = SERVICE_NAME) -> None:
    """Fetch the rent dataset and upsert it into the database."""

    with SessionLocal() as session:
        batch_count = 0
        for batch in iter_rows(service_name):
            _upsert_rows(session, batch)
            session.commit()
            batch_count += 1
            LOGGER.info("rent batch %s committed", batch_count)


if __name__ == "__main__":  # pragma: no cover - manual script
    logging.basicConfig(level=logging.INFO)
    run()
