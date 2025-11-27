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

# v2 스캐너 (재시도/폴백/정순 스캔 + id 직접 탐색)
from app.utils.seoul_tail_scanner_v2 import (
    get_last_page_index,
    fetch_page,
    find_anchor_page_forward,
    locate_page_by_id,   # FORCE_SALE_ANCHOR_ID로 직접 페이지 탐색
)

from app.utils.normalize import stable_bigint_id, yyyymmdd_to_date

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
        "thing_amt": _to_int(row.get("THING_AMT")),
        "arch_area": _to_decimal(row.get("ARCH_AREA")),
        "land_area": _to_decimal(row.get("LAND_AREA")),
        "flr": _none_if_blank(row.get("FLR")),
        "rght_se": _none_if_blank(row.get("RGHT_SE")),
        "rtrcn_day": _none_if_blank(row.get("RTRCN_DAY")),
        "arch_yr": _to_int(row.get("ARCH_YR")),
        "bldg_usg": _none_if_blank(row.get("BLDG_USG")),
        "dclr_se": _none_if_blank(row.get("DCLR_SE")),
        "opbiz_restagnt_sgg_nm": _none_if_blank(row.get("OPBIZ_RESTAGNT_SGG_NM")),
        "raw": raw,
    }

INSERT_SQL = text("""
    INSERT INTO public.cloud_sale(
        rcpt_yr, cgg_cd, cgg_nm, stdg_cd, stdg_nm,
        lotno_se, lotno_se_nm, mno, sno, bldg_nm,
        ctrt_day, thing_amt, arch_area, land_area, flr,
        rght_se, rtrcn_day, arch_yr, bldg_usg, dclr_se, opbiz_restagnt_sgg_nm,
        raw, id
    )
    VALUES (
        :rcpt_yr, :cgg_cd, :cgg_nm, :stdg_cd, :stdg_nm,
        :lotno_se, :lotno_se_nm, :mno, :sno, :bldg_nm,
        :ctrt_day, :thing_amt, :arch_area, :land_area, :flr,
        :rght_se, :rtrcn_day, :arch_yr, :bldg_usg, :dclr_se, :opbiz_restagnt_sgg_nm,
        CAST(:raw AS jsonb), :id
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
        bldg_nm = EXCLUDED.bldg_nm,
        ctrt_day = EXCLUDED.ctrt_day,
        thing_amt = EXCLUDED.thing_amt,
        arch_area = EXCLUDED.arch_area,
        land_area = EXCLUDED.land_area,
        flr = EXCLUDED.flr,
        rght_se = EXCLUDED.rght_se,
        rtrcn_day = EXCLUDED.rtrcn_day,
        arch_yr = EXCLUDED.arch_yr,
        bldg_usg = EXCLUDED.bldg_usg,
        dclr_se = EXCLUDED.dclr_se,
        opbiz_restagnt_sgg_nm = EXCLUDED.opbiz_restagnt_sgg_nm,
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
    가장 최근 적재 레코드의 id/created_at을 '앵커'로 사용.
    """
    row = session.execute(text("""
        SELECT id, created_at
        FROM public.cloud_sale
        ORDER BY created_at DESC NULLS LAST, id DESC
        LIMIT 1
    """)).first()
    return (row[0], str(row[1]) if (row and len(row) > 1) else None) if row else (None, None)

# ---------- planning ----------
def _env_int(name: str) -> Optional[int]:
    v = os.getenv(name)
    if not v: return None
    v = v.strip()
    try:
        return int(v)
    except Exception:
        return None

def _plan_incremental_include_anchor_page(
    *,
    api_key: str,
    service: str,
    page_size: int,
    throttle: float,
    last_page: int,
    db_anchor_id: Optional[int],
    resume_page: Optional[int],
    head_window_pages: int,
    max_scan_pages: Optional[int],
) -> Tuple[int, int, Optional[int], str]:
    """
    요구사항(안정형): '앵커 페이지'까지 1..anchor_page 전체를 적재한다 (앵커 페이지 포함).
    우선순위:
      1) SALE_RESUME_PAGE 지정 시: resume..last_page (운영자가 직접 재개)
      2) FORCE_SALE_ANCHOR_ID (또는 SALE_LOCATE_ID)로 명시된 id → locate_page_by_id()로 페이지 찾기
      3) DB 앵커 id → find_anchor_page_forward()
      4) 헤드 윈도우 1..N (안전 범위)
    반환: (start_page, end_page, anchor_page, mode_msg)
    """
    if resume_page and resume_page > 0:
        start = max(1, min(resume_page, last_page))
        return start, last_page, None, f"resume-from={start}"

    forced_id = _env_int("FORCE_SALE_ANCHOR_ID") or _env_int("SALE_LOCATE_ID")
    locate_strategy = (os.getenv("SALE_LOCATE_STRATEGY") or "forward").strip().lower()  # "forward"|"reverse"

    if forced_id is not None:
        print(f"[sale-etl] FORCE id specified via ENV -> id={forced_id}")
        _ = get_last_page_index(api_key=api_key, service=service, page_size=page_size,
                                throttle=throttle, verbose=True)
        print(f"[anchor-scan] total last_page={last_page}")

        page = locate_page_by_id(
            api_key=api_key,
            service=service,
            page_size=page_size,
            target_id=forced_id,
            strategy=locate_strategy,
            max_scan_pages=max_scan_pages,
            throttle=throttle,
            verbose=True,
        )
        if page is not None:
            print(f"[sale-etl] anchor_page={page} found by FORCE id. We'll load 1..{page}.")
            return 1, page, page, f"incremental-from-forced-id head..{page}"

        print("[sale-etl] ⚠️ forced id not found → fallback to DB anchor")

    if db_anchor_id is not None:
        print(f"[sale-etl] locating anchor_page for anchor_id={db_anchor_id} ...")
        _ = get_last_page_index(api_key=api_key, service=service, page_size=page_size,
                                throttle=throttle, verbose=True)
        print(f"[anchor-scan] total last_page={last_page}")

        anchor_page = find_anchor_page_forward(
            api_key=api_key,
            service=service,
            page_size=page_size,
            anchor_id=db_anchor_id,
            max_scan_pages=max_scan_pages,
            throttle=throttle,
            verbose=True,
        )
        if anchor_page is not None:
            print(f"[sale-etl] anchor_page={anchor_page} found. We'll load 1..{anchor_page}.")
            return 1, anchor_page, anchor_page, f"incremental-from-db-anchor head..{anchor_page}"

    # 헤드 윈도우 보수적 스캔: 1..N
    end = min(last_page, max(1, head_window_pages))
    return 1, end, None, f"head-window=1..{end}"

# ---------- main ----------
def main():
    api_key = os.getenv("SEOUL_API_KEY_SALE") or os.getenv("SEOUL_API_KEY")
    if not api_key:
        raise RuntimeError("SEOUL_API_KEY_SALE / SEOUL_API_KEY not set")
    service = os.getenv("SEOUL_SALE_SERVICE") or "tbLnOpendataRtmsV"

    page_size = int(os.getenv("SEOUL_PAGE_SIZE", "1000"))
    throttle  = float(os.getenv("SEOUL_API_THROTTLE", os.getenv("SEOOL_API_THROTTLE", "0.02")))
    commit_every = int(os.getenv("DB_COMMIT_EVERY", "5"))
    upsert_chunk  = int(os.getenv("DB_UPSERT_CHUNK", "1000"))

    head_window_pages = int(os.getenv("CLOUD_PULL_WINDOW", "3"))
    forward_max_scan_env = os.getenv("ANCHOR_MAX_SCAN_PAGES")
    max_scan_pages: Optional[int] = int(forward_max_scan_env) if (forward_max_scan_env and forward_max_scan_env.isdigit()) else None

    mode = (os.getenv("SALE_MODE") or "incremental").strip().lower()
    resume_page_env = os.getenv("SALE_RESUME_PAGE")
    resume_page = int(resume_page_env) if (resume_page_env and resume_page_env.isdigit()) else None

    # ── tail-scan HEAD (로그 스타일 유지) ────────────────────────────────────
    last_page = get_last_page_index(api_key=api_key, service=service,
                                    page_size=page_size, throttle=throttle, verbose=True)
    if last_page == 0:
        print("[cloud-sale] dataset empty"); return

    with SessionLocal() as session:
        if mode == "full":
            start_page, end_page, anchor_page, mode_msg = 1, last_page, None, "full-scan"
        else:
            db_anchor_id, anchor_ts = _get_anchor_info(session)
            if db_anchor_id is not None:
                print(f"[sale-etl] anchor row id={db_anchor_id} created_at={anchor_ts}")
            else:
                print("[sale-etl] no anchor in DB (empty or just created)")

            start_page, end_page, anchor_page, mode_msg = _plan_incremental_include_anchor_page(
                api_key=api_key,
                service=service,
                page_size=page_size,
                throttle=throttle,
                last_page=last_page,
                db_anchor_id=db_anchor_id,
                resume_page=resume_page,
                head_window_pages=head_window_pages,
                max_scan_pages=max_scan_pages,
            )

        total_pages = end_page - start_page + 1

        # ── 페이지 플랜 출력 (네가 쓰던 스타일로) ─────────────────────────────
        print(f"[sale-etl] page plan (INCREMENTAL):" if mode != "full" else "[sale-etl] page plan (FULL):")
        print(f"       SALE_MODE          = {mode}")
        print(f"       SALE_RESUME_PAGE   = {resume_page}")
        print(f"       tail_page          = {last_page}")
        print(f"       anchor_page_used   = {anchor_page}")
        print(f"       start_page         = {start_page}")
        print(f"       total to pull      = {total_pages} pages")
        LOG.info(f"BEGIN {mode.upper()} load {start_page}..{end_page} ({total_pages} pages) mode={mode} resume={resume_page}")

        # ── 적재 루프 (1..anchor_page 포함) ─────────────────────────────────
        print(f"[sale-etl] BEGIN load {start_page}..{end_page} ({total_pages} pages)")
        batch = 0
        for i, page in enumerate(range(start_page, end_page + 1), start=1):
            start_idx = (page - 1) * page_size + 1
            end_idx   = page * page_size
            print(f"[sale-scan] fetch page_no={page} start={start_idx} end={end_idx} ({i}/{total_pages})")

            rows = fetch_page(
                api_key=api_key,
                service=service,
                page_size=page_size,
                page_no=page,
                throttle=throttle,
                verbose=False,
            )
            if not rows:
                print(f"[sale-scan] ⚠️ empty page={page}, skip")
                continue

            print(f"[sale-scan] ✅ fetched {len(rows)} rows, upserting into DB...")
            _insert_rows(session, rows, chunk_size=upsert_chunk)
            print(f"[sale-scan] done upsert for page={page}")

            batch += 1
            if batch % commit_every == 0:
                session.commit()
                print(f"[sale-scan] 💾 committed at page={page}")

        session.commit()
        print(f"✅ cloud_sale load done. pages {start_page}..{end_page}")

if __name__ == "__main__":
    main()
