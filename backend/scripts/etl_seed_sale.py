# backend/scripts/etl_seed_sale.py
# -*- coding: utf-8 -*-
from __future__ import annotations
"""
(기존 주석 동일)
"""

import os
import time
import logging
from decimal import Decimal, InvalidOperation
from typing import Iterable, Sequence, Dict, Tuple, List

# 👇 dotenv 추가
from dotenv import load_dotenv
load_dotenv(dotenv_path=os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"), override=False)

from sqlalchemy import func, text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.db.db_connection import SessionLocal
from app.models.sale import Sale
from app.utils.normalize import (
    clean_lot_jibun,
    mwon_to_krw,
    norm_text,
    stable_bigint_id,
    yyyymmdd_to_date,
)
from app.utils.seoul_tail_scanner import (
    get_last_page_index,
    find_anchor_page_reverse,
    _fetch_page_once,
)

LOGGER = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def _none_if_blank(v: object) -> str | None:
    if v is None:
        return None
    s = str(v).strip()
    return s if s != "" else None

def _to_int(v: object) -> int | None:
    s = _none_if_blank(v)
    if s is None:
        return None
    try:
        return int(s)
    except (ValueError, TypeError):
        try:
            return int(Decimal(s))
        except Exception:
            return None

def _to_decimal(v: object) -> Decimal | None:
    s = _none_if_blank(v)
    if s is None:
        return None
    try:
        return Decimal(s)
    except (InvalidOperation, ValueError, TypeError):
        return None

def _lot_from(row: dict) -> str | None:
    main, sub = _none_if_blank(row.get("MNO")), _none_if_blank(row.get("SNO"))
    if main is None or main == "0":
        return None
    lot = main
    if sub and sub != "0":
        lot = f"{lot}-{sub}"
    return clean_lot_jibun(lot)

def _transform_row(row: dict) -> dict:
    raw = dict(row)
    return {
        "id": stable_bigint_id(raw),

        "rcpt_yr": _to_int(row.get("RCPT_YR")),
        "cgg_cd": _to_int(row.get("CGG_CD")),
        "cgg_nm": _none_if_blank(row.get("CGG_NM")),
        "stdg_cd": _to_int(row.get("STDG_CD")),
        "stdg_nm": _none_if_blank(row.get("STDG_NM")),
        "lotno_se": _to_int(row.get("LOTNO_SE")),
        "lotno_se_nm": _none_if_blank(row.get("LOTNO_SE_NM")),
        "mno": _none_if_blank(row.get("MNO")),
        "sno": _none_if_blank(row.get("SNO")),
        "bldg_nm": _none_if_blank(row.get("BLDG_NM")),
        "ctrt_day": yyyymmdd_to_date(_none_if_blank(row.get("CTRT_DAY"))),
        "thing_amt": mwon_to_krw(_none_if_blank(row.get("THING_AMT"))),
        "arch_area": _to_decimal(row.get("ARCH_AREA")),
        "land_area": _to_decimal(row.get("LAND_AREA")),
        "flr": _none_if_blank(row.get("FLR")),
        "rght_se": _none_if_blank(row.get("RGHT_SE")),
        "rtrcn_day": _none_if_blank(row.get("RTRCN_DAY")),
        "arch_yr": _to_int(row.get("ARCH_YR")),
        "bldg_usg": _none_if_blank(row.get("BLDG_USG")),
        "dclr_se": _none_if_blank(row.get("DCLR_SE")),
        "opbiz_restagnt_sgg_nm": _none_if_blank(row.get("OPBIZ_RESTAGNT_SGG_NM")),

        "gu_key": norm_text(row.get("CGG_NM")),
        "dong_key": norm_text(row.get("STDG_NM")),
        "name_key": norm_text(row.get("BLDG_NM")),
        "lot_key": _lot_from(row),
        "lat": None,
        "lng": None,

        "raw": raw,
    }

def _iter_chunks(it: Iterable[dict], n: int) -> Iterable[List[dict]]:
    buf: List[dict] = []
    for x in it:
        buf.append(x)
        if len(buf) >= n:
            yield buf
            buf = []
    if buf:
        yield buf

def _upsert_rows(session: Session, rows: Sequence[dict], *, chunk_size: int) -> None:
    if not rows:
        return

    for part in _iter_chunks(rows, chunk_size):
        transformed = [_transform_row(r) for r in part]

        dedup_by_id: Dict[int, dict] = {}
        for t in transformed:
            dedup_by_id[t["id"]] = t
        payload = list(dedup_by_id.values())
        if not payload:
            continue

        stmt = insert(Sale).values(payload)

        update_map = {
            col.name: getattr(stmt.excluded, col.name)
            for col in Sale.__table__.columns
            if col.name not in ("id", "created_at", "updated_at")
        }
        update_map["updated_at"] = func.now()

        session.execute(
            stmt.on_conflict_do_update(
                index_elements=[Sale.id],
                set_=update_map,
            ),
            execution_options={"synchronize_session": False},
        )

def _get_anchor_latest_sale(session: Session) -> Tuple[int | None, str | None]:
    row = session.execute(
        text("SELECT id, created_at FROM sale ORDER BY created_at DESC LIMIT 1")
    ).first()
    if not row:
        return (None, None)
    anchor_id = row[0]
    created_at_val = row[1]
    created_at_iso = created_at_val.isoformat() if hasattr(created_at_val, "isoformat") else None
    return anchor_id, created_at_iso


def _run_page_loop(
    session: Session,
    *,
    api_key: str,
    service: str,
    throttle: float,
    page_size: int,
    start_page: int,
    end_page: int,
    commit_every: int,
    upsert_chunk: int,
) -> None:

    current_page = start_page
    batch_idx = 0
    total_pages = end_page - start_page + 1

    print(f"[sale-etl] BEGIN load {start_page}..{end_page} ({total_pages} pages)")

    while current_page <= end_page:
        start_idx = (current_page - 1) * page_size + 1
        end_idx = current_page * page_size

        print(
            f"[sale-scan] fetch page_no={current_page} "
            f"start={start_idx} end={end_idx} "
            f"({current_page - start_page + 1}/{total_pages})"
        )

        rows = _fetch_page_once(
            api_key=api_key,
            service=service,
            page_size=page_size,
            page_no=current_page,
            throttle=throttle,
            verbose=False,
        )

        if not rows:
            print(f"[sale-scan] ⚠️ page={current_page} empty, skipping")
            current_page += 1
            continue

        print(f"[sale-scan] ✅ fetched {len(rows)} rows, upserting into DB...")
        _upsert_rows(session, rows, chunk_size=upsert_chunk)

        batch_idx += 1
        if batch_idx % commit_every == 0:
            session.commit()
            print(f"[sale-scan] 💾 committed at page={current_page}")

        print(f"[sale-scan] done upsert for page={current_page}")
        current_page += 1

    session.commit()
    print(f"✅ sale load completed. pages {start_page}..{end_page}")


def main() -> None:
    logging.basicConfig(level=logging.INFO)

    api_key = (
        os.getenv("SEOUL_API_KEY_SALE")
        or os.getenv("SEOUL_API_KEY")
    )
    if not api_key:
        raise RuntimeError("SEOUL_API_KEY_SALE / SEOUL_API_KEY not set")

    service = (
        os.getenv("SEOUL_SALE_SERVICE")
        or "tbLnOpendataRtmsV"
    )

    page_size = int(os.getenv("SEOUL_PAGE_SIZE", "1000"))
    throttle = float(os.getenv("SEOUL_API_THROTTLE", "0.02"))
    seek_scan_pages = int(os.getenv("SEOUL_SEEK_SCAN_PAGES", "400"))

    commit_every = int(os.getenv("DB_COMMIT_EVERY", "5"))
    upsert_chunk = int(os.getenv("DB_UPSERT_CHUNK", "1000"))

    mode = os.getenv("SALE_MODE", "incremental").strip().lower()
    resume_env = (
        os.getenv("SALE_RESUME_PAGE")
        or os.getenv("SEOUL_RESUME_PAGE")
        or os.getenv("RESUME")
    )
    resume_page_override = int(resume_env) if resume_env else None

    with SessionLocal() as session:
        tail_page = get_last_page_index(
            api_key=api_key,
            service=service,
            page_size=page_size,
            throttle=throttle,
            verbose=True,
        )
        if tail_page == 0:
            print("[sale-etl] API dataset empty? Nothing to do.")
            return

        if mode == "full":
            start_page = 1
            if resume_page_override is not None:
                start_page = resume_page_override
                print(f"[sale-etl] RESUME override: start_page={start_page}")

            total_pages = tail_page - start_page + 1
            print("[sale-etl] page plan (FULL):")
            print(f"       SALE_MODE          = {mode}")
            print(f"       SALE_RESUME_PAGE   = {resume_page_override}")
            print(f"       tail_page          = {tail_page}")
            print(f"       anchor_page_used   = None")
            print(f"       start_page         = {start_page}")
            print(f"       total to pull      = {total_pages} pages")

            LOGGER.info(
                "BEGIN FULL load %s..%s (%s pages) mode=%s resume=%s",
                start_page, tail_page, total_pages, mode, resume_page_override,
            )

            _run_page_loop(
                session=session,
                api_key=api_key,
                service=service,
                throttle=throttle,
                page_size=page_size,
                start_page=start_page,
                end_page=tail_page,
                commit_every=commit_every,
                upsert_chunk=upsert_chunk,
            )
            return

        # incremental
        anchor_id, anchor_created_at = _get_anchor_latest_sale(session)
        if anchor_id is None:
            print("[sale-etl] sale table is empty. Treating as first incremental load.")
        else:
            print(f"[sale-etl] anchor row id={anchor_id} created_at={anchor_created_at}")

        if resume_page_override is not None:
            start_page = resume_page_override
            print(f"[sale-etl] RESUME override: start_page={start_page}")
            anchor_page_used = None
        else:
            if anchor_id is None:
                anchor_page = None
            else:
                print(f"[sale-etl] locating anchor_page for anchor_id={anchor_id} ...")
                anchor_page = find_anchor_page_reverse(
                    api_key=api_key,
                    service=service,
                    page_size=page_size,
                    throttle=throttle,
                    anchor_id=anchor_id,
                    max_scan_pages=seek_scan_pages,
                    verbose=True,
                )

            if anchor_page is None:
                start_page = tail_page
                anchor_page_used = None
                print("[sale-etl] WARNING: no anchor_page found. start_page defaults to tail_page.")
            else:
                start_page = anchor_page
                anchor_page_used = anchor_page
                print(f"[sale-etl] anchor_page={anchor_page} found. We'll re-load from that page.")

        if start_page > tail_page:
            start_page = tail_page

        total_pages = tail_page - start_page + 1

        print("[sale-etl] page plan (INCREMENTAL):")
        print(f"       SALE_MODE          = {mode}")
        print(f"       SALE_RESUME_PAGE   = {resume_page_override}")
        print(f"       tail_page          = {tail_page}")
        print(f"       anchor_page_used   = {anchor_page_used}")
        print(f"       start_page         = {start_page}")
        print(f"       total to pull      = {total_pages} pages")

        LOGGER.info(
            "BEGIN INCREMENTAL load %s..%s (%s pages) mode=%s resume=%s",
            start_page, tail_page, total_pages, mode, resume_page_override,
        )

        _run_page_loop(
            session=session,
            api_key=api_key,
            service=service,
            throttle=throttle,
            page_size=page_size,
            start_page=start_page,
            end_page=tail_page,
            commit_every=commit_every,
            upsert_chunk=upsert_chunk,
        )

if __name__ == "__main__":
    main()
