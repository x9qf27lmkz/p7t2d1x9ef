# backend/scripts/etl_seed_rent.py
# -*- coding: utf-8 -*-
from __future__ import annotations

"""
서울시 전월세(tbLnOpendataRentV) 적재 파이프라인 (full / incremental / resume)

- 대상 테이블: public.rent (ORM: app.models.rent.Rent)
- 스캐너: seoul_tail_scanner_v2 사용
- 정책:
  1) 공공 API의 행 순서를 신뢰하지 않는다.
  2) incremental 모드에서는 항상 **1페이지부터 앵커 페이지까지 전부 재적재**한다.
  3) 우선순위:
     (a) RENT_RESUME_PAGE 지정 시: resume..last_page
     (b) FORCE_RENT_ANCHOR_ID / RENT_LOCATE_ID → locate_page_by_id()로 페이지 탐색 → 1..anchor_page
     (c) DB 최신 앵커 id → find_anchor_page_forward() → 1..anchor_page
     (d) 앵커 미발견 시: 1..CLOUD_PULL_WINDOW
"""

import os
import logging
from decimal import Decimal, InvalidOperation
from typing import Iterable, Sequence, Dict, Tuple, List, Optional

from dotenv import load_dotenv
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

# v2 스캐너 (정순 스캔 + 폴백 + 재시도)
from app.utils.seoul_tail_scanner_v2 import (
    get_last_page_index,
    fetch_page,
    find_anchor_page_forward,
    locate_page_by_id,
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

        # 파생 컬럼들 (rent 테이블 전용)
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

        # 동일 id가 여러 번 들어와도 마지막 값만 남도록 메모리 내 dedup
        dedup_by_id: Dict[int, dict] = {}
        for t in transformed:
            dedup_by_id[t["id"]] = t
        payload = list(dedup_by_id.values())
        if not payload:
            continue

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

# ─────────────────────────────────
# 앵커 정보 조회 (rent 테이블 기준)
# ─────────────────────────────────
def _get_anchor_info(session: Session) -> Tuple[int | None, str | None]:
    """
    rent 테이블에서 가장 최근 created_at 기준 레코드를 앵커로 사용.
    """
    row = session.execute(text("""
        SELECT id, created_at
        FROM public.rent
        ORDER BY created_at DESC NULLS LAST, id DESC
        LIMIT 1
    """)).first()
    if not row:
        return (None, None)
    anchor_id = row[0]
    created_at_val = row[1]
    created_at_iso = created_at_val.isoformat() if hasattr(created_at_val, "isoformat") else str(created_at_val)
    return anchor_id, created_at_iso

# ─────────────────────────────────
# planning helpers (cloud_rent 버전과 동일 전략)
# ─────────────────────────────────
def _env_int(name: str) -> Optional[int]:
    v = os.getenv(name)
    if not v:
        return None
    try:
        return int(v.strip())
    except Exception:
        return None

def _plan_incremental_until_anchor_page(
    *,
    api_key: str,
    service: str,
    page_size: int,
    throttle: float,
    last_page: int,
    anchor_id: Optional[int],          # DB 앵커 id
    resume_page: Optional[int],
    head_window_pages: int,
    max_scan_pages: Optional[int],
) -> Tuple[int, int, Optional[int], str, Optional[int]]:
    """
    정책: '행 순서 불신' 전제 → **1페이지부터 앵커 페이지까지 전부 재적재**
      - 앵커 페이지도 '통으로' 적재 (슬라이싱 없음)
      - 우선순위:
        1) RENT_RESUME_PAGE 지정 시: resume..last_page
        2) FORCE_RENT_ANCHOR_ID(or RENT_LOCATE_ID) → locate_page_by_id()로 페이지 찾음 → 1..anchor_page
        3) DB 앵커 id → find_anchor_page_forward() → 1..anchor_page
        4) 앵커 못 찾으면: 1..head_window_pages
    반환: (start_page, end_page, anchor_page, mode_msg, anchor_id_used)
    """
    # 1) 수동 재개
    if resume_page and resume_page > 0:
        start = max(1, min(resume_page, last_page))
        return start, last_page, None, f"resume-from={start}", None

    # 2) FORCE id 우선
    forced_id = _env_int("FORCE_RENT_ANCHOR_ID") or _env_int("RENT_LOCATE_ID")
    if forced_id is not None:
        print(f"[rent-etl] FORCE id specified via ENV -> id={forced_id}")
        _ = get_last_page_index(api_key=api_key, service=service, page_size=page_size,
                                throttle=throttle, verbose=True)
        print(f"[anchor-scan] total last_page={last_page}")
        page = locate_page_by_id(
            api_key=api_key,
            service=service,
            page_size=page_size,
            target_id=forced_id,
            strategy=(os.getenv("RENT_LOCATE_STRATEGY") or "forward").strip().lower(),
            max_scan_pages=max_scan_pages,
            throttle=throttle,
            verbose=True,
        )
        if page is not None:
            print(f"[rent-etl] anchor_page={page} found by FORCE id. We'll re-load **1..{page}**.")
            return 1, page, page, f"incremental 1..{page} (forced-id)", forced_id
        print("[rent-etl] ⚠️ forced id not found → falling back")

    # 3) DB 앵커
    if anchor_id is not None:
        print(f"[rent-etl] locating anchor_page for anchor_id={anchor_id} ...")
        _ = get_last_page_index(api_key=api_key, service=service, page_size=page_size,
                                throttle=throttle, verbose=True)
        print(f"[anchor-scan] total last_page={last_page}")

        page = find_anchor_page_forward(
            api_key=api_key,
            service=service,
            page_size=page_size,
            anchor_id=anchor_id,
            max_scan_pages=max_scan_pages,
            throttle=throttle,
            verbose=True,
        )
        if page is not None:
            print(f"[rent-etl] anchor_page={page} found. We'll re-load **1..{page}**.")
            return 1, page, page, f"incremental 1..{page} (db-anchor)", anchor_id

    # 4) 헤드 윈도우 (보수적 폴백)
    end = min(last_page, max(1, head_window_pages))
    return 1, end, None, f"head-window=1..{end}", None

# ─────────────────────────────────
# main
# ─────────────────────────────────
def main() -> None:
    api_key = os.getenv("SEOUL_API_KEY_RENT") or os.getenv("SEOUL_API_KEY")
    if not api_key:
        raise RuntimeError("SEOUL_API_KEY_RENT / SEOUL_API_KEY not set")

    service = os.getenv("SEOUL_RENT_SERVICE") or "tbLnOpendataRentV"

    page_size = int(os.getenv("SEOUL_PAGE_SIZE", "1000"))
    throttle = float(os.getenv("SEOUL_API_THROTTLE", "0.02"))

    commit_every = int(os.getenv("DB_COMMIT_EVERY", "5"))
    upsert_chunk = int(os.getenv("DB_UPSERT_CHUNK", "1000"))

    head_window_pages = int(os.getenv("CLOUD_PULL_WINDOW", "3"))
    forward_max_scan_env = os.getenv("ANCHOR_MAX_SCAN_PAGES")
    max_scan_pages: Optional[int] = int(forward_max_scan_env) if (forward_max_scan_env and forward_max_scan_env.isdigit()) else None

    mode = (os.getenv("RENT_MODE") or "incremental").strip().lower()
    if mode not in ("full", "incremental"):
        print(f"[rent-etl] WARNING: RENT_MODE={mode!r} not recognized. Using 'incremental'.")
        mode = "incremental"

    resume_page_env = os.getenv("RENT_RESUME_PAGE")
    resume_page = int(resume_page_env) if (resume_page_env and resume_page_env.isdigit()) else None

    # ── HEAD (전체 페이지 수 조회) ─────────────────────────────────────
    tail_page = get_last_page_index(
        api_key=api_key,
        service=service,
        page_size=page_size,
        throttle=throttle,
        verbose=True,
    )
    if tail_page == 0:
        print("[rent-etl] API dataset seems empty. Nothing to do.")
        return

    with SessionLocal() as session:
        if mode == "full":
            start_page, end_page, anchor_page, mode_msg, anchor_id_used = 1, tail_page, None, "full-scan", None
        else:
            anchor_id, anchor_created_at = _get_anchor_info(session)
            if anchor_id is None:
                print("[rent-etl] rent table has no rows (no anchor).")
            else:
                print(f"[rent-etl] anchor row id={anchor_id} created_at={anchor_created_at}")

            start_page, end_page, anchor_page, mode_msg, anchor_id_used = _plan_incremental_until_anchor_page(
                api_key=api_key,
                service=service,
                page_size=page_size,
                throttle=throttle,
                last_page=tail_page,
                anchor_id=anchor_id,
                resume_page=resume_page,
                head_window_pages=head_window_pages,
                max_scan_pages=max_scan_pages,
            )

        if start_page < 1:
            start_page = 1
        if start_page > end_page:
            start_page = end_page

        total_pages = end_page - start_page + 1

        # ── 페이지 플랜 로그 ───────────────────────────────────────────
        print("[rent-etl] page plan (INCREMENTAL):" if mode != "full" else "[rent-etl] page plan (FULL):")
        print(f"       RENT_MODE          = {mode}")
        print(f"       RENT_RESUME_PAGE   = {resume_page}")
        print(f"       tail_page          = {tail_page}")
        print(f"       anchor_page_used   = {anchor_page}")
        print(f"       start_page         = {start_page}")
        print(f"       end_page           = {end_page}")
        print(f"       total to pull      = {total_pages} pages")
        print(f"       plan_msg           = {mode_msg}")
        LOGGER.info(
            "BEGIN %s load %s..%s (%s pages) resume=%s anchor_page=%s anchor_id_used=%s",
            mode.upper(), start_page, end_page, total_pages, resume_page, anchor_page, anchor_id_used,
        )

        # ── 적재 루프 (앵커 페이지도 '통으로' 적재) ───────────────────────
        print(f"[rent-etl] BEGIN load {start_page}..{end_page} ({total_pages} pages)")
        batch_idx = 0

        for i, current_page in enumerate(range(start_page, end_page + 1), start=1):
            start_idx = (current_page - 1) * page_size + 1
            end_idx = current_page * page_size
            print(
                f"[rent-scan] fetch page_no={current_page} "
                f"start={start_idx} end={end_idx} "
                f"({i}/{total_pages})"
            )

            rows = fetch_page(
                api_key=api_key,
                service=service,
                page_size=page_size,
                page_no=current_page,
                throttle=throttle,
                verbose=False,
            )

            if not rows:
                print(f"[rent-scan] ⚠️ empty page={current_page}, skip")
                continue

            print(f"[rent-scan] ✅ fetched {len(rows)} rows, upserting into DB...")
            _upsert_rows(session, rows, chunk_size=upsert_chunk)
            print(f"[rent-scan] done upsert for page={current_page}")

            batch_idx += 1
            if batch_idx % commit_every == 0:
                session.commit()
                print(f"[rent-scan] 💾 committed at page={current_page}")

        session.commit()
        print(f"✅ rent load completed. pages {start_page}..{end_page} (mode={mode}, resume={resume_page})")
        LOGGER.info(
            "rent load completed. pages %s..%s mode=%s resume=%s",
            start_page, end_page, mode, resume_page,
        )

if __name__ == "__main__":
    main()
