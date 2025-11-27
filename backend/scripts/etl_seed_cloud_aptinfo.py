# -*- coding: utf-8 -*-
from __future__ import annotations

import os, json, logging
from typing import Iterable, Sequence, List, Optional, Tuple

from dotenv import load_dotenv
load_dotenv(dotenv_path=os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"), override=False)

from sqlalchemy import text
from sqlalchemy.orm import Session
from app.db.db_connection import SessionLocal

# v2 스캐너 (정방향 스캔 + 폴백 + 강제 id 탐색 지원)
from app.utils.seoul_tail_scanner_v2 import (
    get_last_page_index,
    fetch_page,
    find_anchor_page_forward,
    locate_page_by_id,
)

from app.utils.normalize import stable_bigint_id

LOG = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# ---------- helpers ----------
def _iter_chunks(it: Iterable[dict], n: int) -> Iterable[List[dict]]:
    buf: List[dict] = []
    for x in it:
        buf.append(x)
        if len(buf) >= n:
            yield buf; buf = []
    if buf:
        yield buf

def _transform_row(row: dict) -> dict:
    """
    cloud_aptinfo 스키마에 맞게 필수 컬럼을 구성:
      - apt_cd (PK, NOT NULL)
      - id     (고유 해시 bigint)
      - raw    (원본 jsonb)
    """
    raw = dict(row)
    apt_cd = (row.get("APT_CD") or "").strip()
    if not apt_cd:
        raise ValueError(f"APT_CD missing in row: {row}")
    return {"apt_cd": apt_cd, "id": stable_bigint_id(raw), "raw": raw}

INSERT_SQL = text("""
    INSERT INTO public.cloud_aptinfo (apt_cd, raw, id)
    VALUES (:apt_cd, CAST(:raw AS jsonb), :id)
    ON CONFLICT (apt_cd) DO UPDATE SET
        raw = EXCLUDED.raw,
        id  = EXCLUDED.id,
        updated_at = now()
""")

def _insert_rows(session: Session, rows: Sequence[dict], chunk_size: int) -> None:
    if not rows:
        return
    ok_batch: List[dict] = []
    skipped = 0
    for r in rows:
        try:
            ok_batch.append(_transform_row(r))
        except ValueError:
            skipped += 1
            continue
    if skipped:
        print(f"[aptinfo-etl] ⚠️ skipped {skipped} rows without APT_CD")

    for part in _iter_chunks(ok_batch, chunk_size):
        for rec in part:
            rec["raw"] = json.dumps(rec["raw"], ensure_ascii=False)
        session.execute(INSERT_SQL, part)

def _get_anchor_info(session: Session) -> Tuple[Optional[int], Optional[str]]:
    """
    최신 업서트 row의 (id, created_at)을 앵커로 사용. created_at은 로그용.
    """
    row = session.execute(text("""
        SELECT id, created_at
        FROM public.cloud_aptinfo
        ORDER BY created_at DESC NULLS LAST, id DESC
        LIMIT 1
    """)).first()
    return (row[0], str(row[1]) if (row and len(row) > 1) else None) if row else (None, None)

def _env_int(name: str) -> Optional[int]:
    v = os.getenv(name)
    if not v:
        return None
    v = v.strip()
    try:
        return int(v)
    except Exception:
        return None

# ---------- planning ----------
def _plan_forward_until_anchor_page(
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
    안정성 우선: 항상 1페이지부터 end_page까지 '통째로' 적재.
    우선순위
      1) APTINFO_RESUME_PAGE: 1..resume_page
      2) FORCE_APTINFO_ANCHOR_ID/APTINFO_LOCATE_ID로 locate_page_by_id()
      3) DB 앵커 id로 find_anchor_page_forward()
      4) 헤드 윈도우 1..N
    """
    # 1) 수동 재개
    if resume_page and resume_page > 0:
        end = max(1, min(resume_page, last_page))
        return 1, end, None, f"resume-1..{end}"

    # 2) 강제 id 지정
    forced_id = _env_int("FORCE_APTINFO_ANCHOR_ID") or _env_int("APTINFO_LOCATE_ID")
    if forced_id is not None:
        print(f"[aptinfo-etl] FORCE id specified via ENV -> id={forced_id}")
        _ = get_last_page_index(api_key=api_key, service=service, page_size=page_size,
                                throttle=throttle, verbose=True)
        print(f"[anchor-scan] total last_page={last_page}")

        page = locate_page_by_id(
            api_key=api_key,
            service=service,
            page_size=page_size,
            target_id=forced_id,
            strategy=(os.getenv("APTINFO_LOCATE_STRATEGY") or "forward").strip().lower(),
            max_scan_pages=max_scan_pages,
            throttle=throttle,
            verbose=True,
        )
        if page is not None:
            print(f"[aptinfo-etl] anchor_page={page} found by FORCE id. We'll load 1..{page}.")
            return 1, page, page, f"from-forced-id page={page}"
        print("[aptinfo-etl] ⚠️ forced id not found → falling back")

    # 3) DB 앵커 id로 정방향 탐색
    if db_anchor_id is not None:
        print(f"[aptinfo-etl] locating anchor_page for anchor_id={db_anchor_id} ...")
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
            print(f"[aptinfo-etl] anchor_page={anchor_page} found. We'll load 1..{anchor_page}.")
            return 1, anchor_page, anchor_page, f"from-db-anchor page={anchor_page}"

    # 4) 헤드 윈도우 1..N
    end = min(last_page, max(1, head_window_pages))
    return 1, end, None, f"head-window=1..{end}"

# ---------- main ----------
def main():
    api_key = os.getenv("SEOUL_API_KEY_APTINFO") or os.getenv("SEOUL_API_KEY")
    if not api_key:
        raise RuntimeError("SEOUL_API_KEY_APTINFO / SEOUL_API_KEY not set")
    service = os.getenv("SEOUL_APTINFO_SERVICE") or "OpenAptInfo"

    page_size     = int(os.getenv("SEOUL_PAGE_SIZE", "1000"))
    throttle      = float(os.getenv("SEOUL_API_THROTTLE", os.getenv("SEOOL_API_THROTTLE", "0.02")))
    commit_every  = int(os.getenv("DB_COMMIT_EVERY", "5"))
    upsert_chunk  = int(os.getenv("DB_UPSERT_CHUNK", "1000"))

    head_window_pages = int(os.getenv("CLOUD_PULL_WINDOW", "3"))
    forward_max_scan_env = os.getenv("ANCHOR_MAX_SCAN_PAGES")
    max_scan_pages: Optional[int] = int(forward_max_scan_env) if (forward_max_scan_env and forward_max_scan_env.isdigit()) else None

    mode = (os.getenv("APTINFO_MODE") or "incremental").strip().lower()
    resume_page_env = os.getenv("APTINFO_RESUME_PAGE")
    resume_page = int(resume_page_env) if (resume_page_env and resume_page_env.isdigit()) else None

    # HEAD
    last_page = get_last_page_index(api_key=api_key, service=service,
                                    page_size=page_size, throttle=throttle, verbose=True)
    if last_page == 0:
        print("[cloud-aptinfo] dataset empty"); return

    with SessionLocal() as session:
        if mode == "full":
            start_page, end_page, anchor_page, mode_msg = 1, last_page, None, "full-scan"
        else:
            db_anchor_id, anchor_ts = _get_anchor_info(session)
            if db_anchor_id is not None:
                print(f"[aptinfo-etl] anchor row id={db_anchor_id} created_at={anchor_ts}")
            else:
                print("[aptinfo-etl] no anchor in DB (empty or just created)")

            start_page, end_page, anchor_page, mode_msg = _plan_forward_until_anchor_page(
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
        print(f"[aptinfo-etl] page plan (INCREMENTAL):" if mode != "full" else "[aptinfo-etl] page plan (FULL):")
        print(f"       APTINFO_MODE        = {mode}")
        print(f"       APTINFO_RESUME_PAGE = {resume_page}")
        print(f"       tail_page           = {last_page}")
        print(f"       anchor_page_used    = {anchor_page}")
        print(f"       start_page          = {start_page}")
        print(f"       total to pull       = {total_pages} pages")
        LOG.info(f"BEGIN {mode.upper()} load {start_page}..{end_page} ({total_pages} pages) mode={mode} resume={resume_page}")

        # 적재 루프(1..end_page)
        print(f"[aptinfo-etl] BEGIN load {start_page}..{end_page} ({total_pages} pages)")
        batch = 0
        for i, page in enumerate(range(start_page, end_page + 1), start=1):
            start_idx = (page - 1) * page_size + 1
            end_idx   = page * page_size
            print(f"[aptinfo-scan] fetch page_no={page} start={start_idx} end={end_idx} ({i}/{total_pages})")

            rows = fetch_page(
                api_key=api_key,
                service=service,
                page_size=page_size,
                page_no=page,
                throttle=throttle,
                verbose=False,
            )
            if not rows:
                print(f"[aptinfo-scan] ⚠️ empty page={page}, skip")
                continue

            print(f"[aptinfo-scan] ✅ fetched {len(rows)} rows, upserting into DB...")
            _insert_rows(session, rows, chunk_size=upsert_chunk)
            print(f"[aptinfo-scan] done upsert for page={page}")

            batch += 1
            if batch % commit_every == 0:
                session.commit()
                print(f"[aptinfo-scan] 💾 committed at page={page}")

        session.commit()
        print(f"✅ cloud_aptinfo load done. pages {start_page}..{end_page}")

if __name__ == "__main__":
    main()
