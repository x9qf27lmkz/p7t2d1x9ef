# backend/scripts/etl_seed_rent.py
# -*- coding: utf-8 -*-
from __future__ import annotations

"""
서울시 전월세(tbLnOpendataRentV) 적재 파이프라인 (full / incremental / resume)
...
(설명 주석 동일)
"""

import os
import time
import logging
from decimal import Decimal, InvalidOperation
from typing import Iterable, Sequence, Dict, Tuple, List

# 👇 추가: .env 자동 로드
from dotenv import load_dotenv
# backend/.env 기준으로 로드 시도
load_dotenv(dotenv_path=os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"), override=False)

from sqlalchemy import func, text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.db.db_connection import SessionLocal
from app.models.rent import Rent
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

# ─────────────────────────────────
# small helpers
# ─────────────────────────────────
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
    m, s = _none_if_blank(row.get("MNO")), _none_if_blank(row.get("SNO"))
    if not m:
        return None
    lot = m if not s else f"{m}-{s}"
    return clean_lot_jibun(lot)

def _transform_row(row: dict) -> dict:
    raw = dict(row)
    return {
        "id": stable_bigint_id(raw),

        "rcpt_yr": _to_int(row.get("RCPT_YR")),
        "cgg_cd": row.get("CGG_CD"),
        "cgg_nm": row.get("CGG_NM"),
        "stdg_cd": row.get("STDG_CD"),
        "stdg_nm": row.get("STDG_NM"),
        "lotno_se": row.get("LOTNO_SE"),
        "lotno_se_nm": row.get("LOTNO_SE_NM"),
        "mno": _none_if_blank(row.get("MNO")),
        "sno": _none_if_blank(row.get("SNO")),
        "flr": _to_int(row.get("FLR")),
        "ctrt_day": _none_if_blank(row.get("CTRT_DAY")),  # YYYYMMDD (문자 그대로 유지)
        "rent_se": row.get("RENT_SE"),
        "rent_area": _to_decimal(row.get("RENT_AREA")),
        "grfe_mwon": _to_int(row.get("GRFE")),
        "rtfe_mwon": _to_int(row.get("RTFE")),
        "bldg_nm": row.get("BLDG_NM"),
        "arch_yr": _to_int(row.get("ARCH_YR")),
        "bldg_usg": row.get("BLDG_USG"),
        "ctrt_prd": row.get("CTRT_PRD"),
        "new_updt_yn": row.get("NEW_UPDT_YN"),
        "ctrt_updt_use_yn": row.get("CTRT_UPDT_USE_YN"),
        "bfr_grfe_mwon": _to_int(row.get("BFR_GRFE")),
        "bfr_rtfe_mwon": _to_int(row.get("BFR_RTFE")),

        # 파생
        "contract_date": yyyymmdd_to_date(row.get("CTRT_DAY")),
        "area_m2": _to_decimal(row.get("RENT_AREA")),
        "deposit_krw": mwon_to_krw(_none_if_blank(row.get("GRFE"))),
        "rent_krw": mwon_to_krw(_none_if_blank(row.get("RTFE"))),
        "lot_key": _lot_from(row),
        "gu_key": norm_text(row.get("CGG_NM")),
        "dong_key": norm_text(row.get("STDG_NM")),
        "name_key": norm_text(row.get("BLDG_NM")),
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

        from sqlalchemy import func
        from sqlalchemy.dialects.postgresql import insert
        from app.models.rent import Rent

        stmt = insert(Rent).values(payload)

        update_map = {
            col.name: getattr(stmt.excluded, col.name)
            for col in Rent.__table__.columns
            if col.name not in ("id", "created_at", "updated_at")
        }
        update_map["updated_at"] = func.now()

        session.execute(
            stmt.on_conflict_do_update(
                index_elements=[Rent.id],
                set_=update_map,
            ),
            execution_options={"synchronize_session": False},
        )

def _get_anchor_latest_rent(session: Session) -> Tuple[int | None, str | None]:
    row = session.execute(
        text("SELECT id, created_at FROM rent ORDER BY created_at DESC LIMIT 1")
    ).first()
    if not row:
        return (None, None)
    anchor_id = row[0]
    created_at_val = row[1]
    created_at_iso = created_at_val.isoformat() if hasattr(created_at_val, "isoformat") else None
    return anchor_id, created_at_iso

def _decide_start_page(
    *,
    mode: str,
    resume_page_env: str | None,
    anchor_id: int | None,
    tail_page: int,
    api_key: str,
    service: str,
    page_size: int,
    throttle: float,
    hint_pages: int,
) -> Tuple[int, int | None]:

    if resume_page_env:
        if resume_page_env.isdigit():
            forced_page = int(resume_page_env)
            print(f"[etl] RESUME override: start_page={forced_page}")
            return forced_page, None
        else:
            print(f"[etl] WARNING: RENT_RESUME_PAGE={resume_page_env!r} is not a digit. Ignoring.")

    if mode == "full":
        print("[etl] RENT_MODE=full → full reload from page 1")
        return 1, None

    if anchor_id is None:
        print("[etl] incremental mode but rent table is empty → fallback to tail_page only")
        return tail_page, None

    print(f"[etl] RENT_MODE=incremental → locating anchor_page for anchor_id={anchor_id} ...")
    anchor_page = find_anchor_page_reverse(
        api_key=api_key,
        service=service,
        page_size=page_size,
        throttle=throttle,
        anchor_id=anchor_id,
        max_scan_pages=hint_pages,
        verbose=True,
    )

    if anchor_page is None:
        print("[etl] WARNING: anchor_id not found in recent window. fallback start_page=tail_page")
        return tail_page, None

    print(f"[etl] anchor_page={anchor_page} found. We'll re-load from that page.")
    return anchor_page, anchor_page

def main() -> None:
    api_key = os.getenv("SEOUL_API_KEY_RENT") or os.getenv("SEOUL_API_KEY")
    if not api_key:
        raise RuntimeError("SEOUL_API_KEY_RENT / SEOUL_API_KEY not set")

    service = os.getenv("SEOUL_RENT_SERVICE") or "tbLnOpendataRentV"

    page_size = int(os.getenv("SEOUL_PAGE_SIZE", "1000"))
    throttle = float(os.getenv("SEOUL_API_THROTTLE", "0.02"))
    hint_pages = int(os.getenv("SEOUL_SEEK_SCAN_PAGES", "400"))

    commit_every = int(os.getenv("DB_COMMIT_EVERY", "5"))
    upsert_chunk = int(os.getenv("DB_UPSERT_CHUNK", "1000"))

    mode = (os.getenv("RENT_MODE") or "incremental").strip().lower()
    if mode not in ("full", "incremental"):
        print(f"[etl] WARNING: RENT_MODE={mode!r} not recognized. Using 'incremental'.")
        mode = "incremental"

    resume_page_env = os.getenv("RENT_RESUME_PAGE")

    with SessionLocal() as session:
        anchor_id, anchor_created_at = _get_anchor_latest_rent(session)
        if anchor_id is None:
            print("[etl] rent table has no rows (no anchor).")
        else:
            print(f"[etl] anchor row id={anchor_id} created_at={anchor_created_at}")

        tail_page = get_last_page_index(
            api_key=api_key,
            service=service,
            page_size=page_size,
            throttle=throttle,
            verbose=True,
        )
        if tail_page == 0:
            print("[etl] API dataset seems empty. Nothing to do.")
            return

        start_page, anchor_page_used = _decide_start_page(
            mode=mode,
            resume_page_env=resume_page_env,
            anchor_id=anchor_id,
            tail_page=tail_page,
            api_key=api_key,
            service=service,
            page_size=page_size,
            throttle=throttle,
            hint_pages=hint_pages,
        )

        if start_page < 1:
            start_page = 1
        if start_page > tail_page:
            start_page = tail_page

        total_pages = tail_page - start_page + 1

        print("[etl] page plan:")
        print(f"       RENT_MODE         = {mode}")
        print(f"       RENT_RESUME_PAGE  = {resume_page_env}")
        print(f"       tail_page         = {tail_page}")
        print(f"       anchor_page_used  = {anchor_page_used}")
        print(f"       start_page        = {start_page}")
        print(f"       total to pull     = {total_pages} pages")

        LOGGER.info(
            "BEGIN load %s..%s (%s pages) mode=%s resume=%s",
            start_page, tail_page, total_pages, mode, resume_page_env,
        )

        current_page = start_page
        batch_idx = 0

        print(f"[etl] BEGIN load {start_page}..{tail_page} ({total_pages} pages)")
        while current_page <= tail_page:
            start_idx = (current_page - 1) * page_size + 1
            end_idx = current_page * page_size
            print(
                f"[etl-scan] fetch page_no={current_page} "
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
                print(f"[etl-scan] ⚠️ page={current_page} empty, skipping")
                current_page += 1
                continue

            print(f"[etl-scan] ✅ fetched {len(rows)} rows, upserting into DB...")
            _upsert_rows(session, rows, chunk_size=upsert_chunk)

            batch_idx += 1
            if batch_idx % commit_every == 0:
                session.commit()
                print(f"[etl-scan] 💾 committed at page={current_page}")

            print(f"[etl-scan] done upsert for page={current_page}")
            current_page += 1

        session.commit()
        print(f"✅ rent load completed. pages {start_page}..{tail_page} (mode={mode}, resume={resume_page_env})")
        LOGGER.info(
            "rent load completed. pages %s..%s mode=%s resume=%s",
            start_page, tail_page, mode, resume_page_env,
        )

if __name__ == "__main__":
    main()
