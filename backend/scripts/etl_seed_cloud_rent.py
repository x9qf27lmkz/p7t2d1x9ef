# backend/scripts/etl_seed_cloud_rent.py
# -*- coding: utf-8 -*-
from __future__ import annotations

import os, json, logging
from typing import Iterable, Sequence, List, Optional, Tuple
from decimal import Decimal, InvalidOperation

from dotenv import load_dotenv
load_dotenv(dotenv_path=os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"), override=False)

from sqlalchemy import text
from sqlalchemy.orm import Session
from app.db.db_connection import SessionLocal

# v2 스캐너 (정순스캔 + 폴백 + 재시도)
from app.utils.seoul_tail_scanner_v2 import (
    get_last_page_index,
    fetch_page,
    find_anchor_page_forward,
    locate_page_by_id,   # FORCE id가 있을 때 사용
)

from app.utils.normalize import stable_bigint_id

LOG = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# ---------- helpers ----------
def _none_if_blank(v):
    if v is None: return None
    s = str(v).strip()
    return s if s else None

def _to_int(v):
    s = _none_if_blank(v)
    if s is None: return None
    try:
        return int(s)
    except Exception:
        try:
            return int(Decimal(s))
        except Exception:
            return None

def _to_decimal(v):
    s = _none_if_blank(v)
    if s is None: return None
    try:
        return Decimal(s)
    except (InvalidOperation, ValueError, TypeError):
        return None

def _iter_chunks(it: Iterable[dict], n: int) -> Iterable[List[dict]]:
    buf: List[dict] = []
    for x in it:
        buf.append(x)
        if len(buf) >= n:
            yield buf; buf = []
    if buf: yield buf

def _transform_row(row: dict) -> dict:
    raw = dict(row)
    return {
        "id": stable_bigint_id(raw),
        "rcpt_yr": _to_int(row.get("RCPT_YR")),
        "cgg_cd": _none_if_blank(row.get("CGG_CD")),
        "cgg_nm": _none_if_blank(row.get("CGG_NM")),
        "stdg_cd": _none_if_blank(row.get("STDG_CD")),
        "stdg_nm": _none_if_blank(row.get("STDG_NM")),
        "lotno_se": _none_if_blank(row.get("LOTNO_SE")),
        "lotno_se_nm": _none_if_blank(row.get("LOTNO_SE_NM")),
        "mno": _none_if_blank(row.get("MNO")),
        "sno": _none_if_blank(row.get("SNO")),
        "flr": _to_int(row.get("FLR")),
        "ctrt_day": _none_if_blank(row.get("CTRT_DAY")),
        "rent_se": _none_if_blank(row.get("RENT_SE")),
        "rent_area": _to_decimal(row.get("RENT_AREA")),
        "grfe_mwon": _to_int(row.get("GRFE")),
        "rtfe_mwon": _to_int(row.get("RTFE")),
        "bldg_nm": _none_if_blank(row.get("BLDG_NM")),
        "arch_yr": _to_int(row.get("ARCH_YR")),
        "bldg_usg": _none_if_blank(row.get("BLDG_USG")),
        "ctrt_prd": _none_if_blank(row.get("CTRT_PRD")),
        "new_updt_yn": _none_if_blank(row.get("NEW_UPDT_YN")),
        "ctrt_updt_use_yn": _none_if_blank(row.get("CTRT_UPDT_USE_YN")),
        "bfr_grfe_mwon": _to_int(row.get("BFR_GRFE")),
        "bfr_rtfe_mwon": _to_int(row.get("BFR_RTFE")),
        "raw": raw,
    }

INSERT_SQL = text("""
    INSERT INTO public.cloud_rent(
        rcpt_yr, cgg_cd, cgg_nm, stdg_cd, stdg_nm,
        lotno_se, lotno_se_nm, mno, sno, flr, ctrt_day,
        rent_se, rent_area, grfe_mwon, rtfe_mwon, bldg_nm,
        arch_yr, bldg_usg, ctrt_prd, new_updt_yn, ctrt_updt_use_yn,
        bfr_grfe_mwon, bfr_rtfe_mwon, raw, id
    )
    VALUES (
        :rcpt_yr, :cgg_cd, :cgg_nm, :stdg_cd, :stdg_nm,
        :lotno_se, :lotno_se_nm, :mno, :sno, :flr, :ctrt_day,
        :rent_se, :rent_area, :grfe_mwon, :rtfe_mwon, :bldg_nm,
        :arch_yr, :bldg_usg, :ctrt_prd, :new_updt_yn, :ctrt_updt_use_yn,
        :bfr_grfe_mwon, :bfr_rtfe_mwon, CAST(:raw AS jsonb), :id
    )
    ON CONFLICT (id) DO UPDATE SET
        rcpt_yr = EXCLUDED.rcpt_yr,
        cgg_cd = EXCLUDED.cgg_cd,
        cgg_nm = EXCLUDED.cgg_nm,
        stdg_cd = EXCLUDED.stdg_cd,
        stdg_nm = EXCLUDED.stdg_nm,
        lotno_se = EXCLUDED.lotno_se,
        lotno_se_nm = EXCLUDED.lotno_se_nm,
        mno = EXCLUDED.mno,
        sno = EXCLUDED.sno,
        flr = EXCLUDED.flr,
        ctrt_day = EXCLUDED.ctrt_day,
        rent_se = EXCLUDED.rent_se,
        rent_area = EXCLUDED.rent_area,
        grfe_mwon = EXCLUDED.grfe_mwon,
        rtfe_mwon = EXCLUDED.rtfe_mwon,
        bldg_nm = EXCLUDED.bldg_nm,
        arch_yr = EXCLUDED.arch_yr,
        bldg_usg = EXCLUDED.bldg_usg,
        ctrt_prd = EXCLUDED.ctrt_prd,
        new_updt_yn = EXCLUDED.new_updt_yn,
        ctrt_updt_use_yn = EXCLUDED.ctrt_updt_use_yn,
        bfr_grfe_mwon = EXCLUDED.bfr_grfe_mwon,
        bfr_rtfe_mwon = EXCLUDED.bfr_rtfe_mwon,
        raw = EXCLUDED.raw
""")

def _insert_rows(session: Session, rows: Sequence[dict], chunk_size: int) -> None:
    if not rows: return
    for part in _iter_chunks([_transform_row(r) for r in rows], chunk_size):
        for rec in part:
            rec["raw"] = json.dumps(rec["raw"], ensure_ascii=False)
        session.execute(INSERT_SQL, part)

def _get_anchor_info(session: Session) -> Tuple[Optional[int], Optional[str]]:
    """
    가장 최근 적재 레코드를 '앵커 후보'로 사용.
    """
    row = session.execute(text("""
        SELECT id, created_at
        FROM public.cloud_rent
        ORDER BY created_at DESC NULLS LAST, id DESC
        LIMIT 1
    """)).first()
    return (row[0], str(row[1]) if (row and len(row) > 1) else None) if row else (None, None)

# ---------- planning ----------
def _env_int(name: str) -> Optional[int]:
    v = os.getenv(name)
    if not v: return None
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
    정책: '행 순서 불신' 전제 → **1페이지부터 앵커 페이지까지 전부 적재**
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
            api_key=api_key, service=service, page_size=page_size,
            target_id=forced_id, strategy=(os.getenv("RENT_LOCATE_STRATEGY") or "forward").strip().lower(),
            max_scan_pages=max_scan_pages, throttle=throttle, verbose=True,
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
            api_key=api_key, service=service, page_size=page_size,
            anchor_id=anchor_id, max_scan_pages=max_scan_pages,
            throttle=throttle, verbose=True,
        )
        if page is not None:
            print(f"[rent-etl] anchor_page={page} found. We'll re-load **1..{page}**.")
            return 1, page, page, f"incremental 1..{page} (db-anchor)", anchor_id

    # 4) 헤드 윈도 (보수적)
    end = min(last_page, max(1, head_window_pages))
    return 1, end, None, f"head-window=1..{end}", None

# ---------- main ----------
def main():
    api_key = os.getenv("SEOUL_API_KEY_RENT") or os.getenv("SEOUL_API_KEY")
    if not api_key:
        raise RuntimeError("SEOUL_API_KEY_RENT / SEOUL_API_KEY not set")
    service = os.getenv("SEOUL_RENT_SERVICE") or "tbLnOpendataRentV"

    page_size = int(os.getenv("SEOUL_PAGE_SIZE", "1000"))
    throttle  = float(os.getenv("SEOUL_API_THROTTLE", "0.02"))
    commit_every = int(os.getenv("DB_COMMIT_EVERY", "5"))
    upsert_chunk  = int(os.getenv("DB_UPSERT_CHUNK", "1000"))

    head_window_pages = int(os.getenv("CLOUD_PULL_WINDOW", "3"))
    forward_max_scan_env = os.getenv("ANCHOR_MAX_SCAN_PAGES")
    max_scan_pages: Optional[int] = int(forward_max_scan_env) if (forward_max_scan_env and forward_max_scan_env.isdigit()) else None

    mode = (os.getenv("RENT_MODE") or "incremental").strip().lower()
    resume_page_env = os.getenv("RENT_RESUME_PAGE")
    resume_page = int(resume_page_env) if (resume_page_env and resume_page_env.isdigit()) else None

    # ── HEAD (로그 스타일 유지) ─────────────────────────────────────────────
    last_page = get_last_page_index(api_key=api_key, service=service,
                                    page_size=page_size, throttle=throttle, verbose=True)
    if last_page == 0:
        print("[cloud-rent] dataset empty"); return

    with SessionLocal() as session:
        if mode == "full":
            start_page, end_page, anchor_page, mode_msg, anchor_id_used = 1, last_page, None, "full-scan", None
        else:
            db_anchor_id, anchor_ts = _get_anchor_info(session)
            if db_anchor_id is not None:
                print(f"[rent-etl] anchor row id={db_anchor_id} created_at={anchor_ts}")
            else:
                print("[rent-etl] no anchor in DB (empty or just created)")

            start_page, end_page, anchor_page, mode_msg, anchor_id_used = _plan_incremental_until_anchor_page(
                api_key=api_key, service=service, page_size=page_size, throttle=throttle,
                last_page=last_page, anchor_id=db_anchor_id, resume_page=resume_page,
                head_window_pages=head_window_pages, max_scan_pages=max_scan_pages,
            )

        total_pages = end_page - start_page + 1

        # ── 페이지 플랜 로그 ────────────────────────────────────────────────
        print(f"[rent-etl] page plan (INCREMENTAL):" if mode != "full" else "[rent-etl] page plan (FULL):")
        print(f"       RENT_MODE          = {mode}")
        print(f"       RENT_RESUME_PAGE   = {resume_page}")
        print(f"       tail_page          = {last_page}")
        print(f"       anchor_page_used   = {anchor_page}")
        print(f"       start_page         = {start_page}")
        print(f"       total to pull      = {total_pages} pages")
        LOG.info(f"BEGIN {mode.upper()} load {start_page}..{end_page} ({total_pages} pages) mode={mode} resume={resume_page}")

        # ── 적재 루프 (앵커 페이지도 '통으로' 적재) ───────────────────────────
        print(f"[rent-etl] BEGIN load {start_page}..{end_page} ({total_pages} pages)")
        batch = 0
        for i, page in enumerate(range(start_page, end_page + 1), start=1):
            start_idx = (page - 1) * page_size + 1
            end_idx   = page * page_size
            print(f"[rent-scan] fetch page_no={page} start={start_idx} end={end_idx} ({i}/{total_pages})")

            rows = fetch_page(
                api_key=api_key, service=service, page_size=page_size, page_no=page,
                throttle=throttle, verbose=False,
            )
            if not rows:
                print(f"[rent-scan] ⚠️ empty page={page}, skip")
                continue

            print(f"[rent-scan] ✅ fetched {len(rows)} rows, upserting into DB...")
            _insert_rows(session, rows, chunk_size=upsert_chunk)
            print(f"[rent-scan] done upsert for page={page}")

            batch += 1
            if batch % commit_every == 0:
                session.commit()
                print(f"[rent-scan] 💾 committed at page={page}")

        session.commit()
        print(f"✅ rent load completed. pages {start_page}..{end_page}")

if __name__ == "__main__":
    main()
