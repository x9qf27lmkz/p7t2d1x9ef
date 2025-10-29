#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
도로명주소(apt_rdn_addr) -> 지번주소(lot_addr, lot_main, lot_sub, lot_union) ETL
- 대상: public.aptinfo_ext
- 처리: lot_addr IS NULL AND apt_rdn_addr NOT NULL
- VWorld Search API(type=address, category=road) 사용
"""

import os, time, re, argparse, logging
from typing import Optional, Tuple, List

import psycopg2
import psycopg2.extras
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())

# ---------------- 환경/상수 ----------------

VWORLD_KEY     = os.getenv("VWORLD_API_KEY", "")
VWORLD_URL     = "https://api.vworld.kr/req/search"  # ← Search API
DEFAULT_QPS    = 7.0
DEFAULT_BATCH  = 500
REQUEST_TIMEOUT = 8.0
RETRY_MAX      = 3
RETRY_BACKOFF  = 1.6

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s | %(message)s")
log = logging.getLogger("vworld-etl")

# ---------------- 유틸 ----------------

def normalize_lot_union(main: Optional[int], sub: Optional[int]) -> Optional[str]:
    if main is None:
        return None
    return f"{int(main)}-{int(sub)}" if (sub and int(sub) > 0) else f"{int(main)}"

def safe_int(v) -> Optional[int]:
    try:
        if v is None:
            return None
        s = str(v).strip()
        if not s or s.lower() == "null":
            return None
        return int(s)
    except Exception:
        return None

def make_http_session() -> requests.Session:
    """Connection 재사용 + 가벼운 재시도 설정."""
    s = requests.Session()
    retries = Retry(
        total=RETRY_MAX,
        backoff_factor=0.2,              # 네트워크 레벨 재시도(HTTP 5xx, connect 오류 등)
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=("GET",),
        raise_on_status=False,
    )
    s.mount("https://", HTTPAdapter(max_retries=retries))
    return s

# ---------------- VWorld (Search API) ----------------
#  - type=address, category=road 로 도로명주소를 질의
#  - 응답의 result.items[0].address.parcel 에 지번 문자열이 옴 (예: '삼평동 624' or '삼평동 123-4')

_PARCEL_RE_DASH = re.compile(r'(\d+)\s*-\s*(\d+)')
_PARCEL_RE_MAIN = re.compile(r'(\d+)')

def call_vworld_for_parcel(session: requests.Session, road_addr: str) -> Tuple[Optional[str], Optional[int], Optional[int]]:
    """
    Search API를 사용해 도로명주소 → 지번주소/본번/부번을 얻는다.
    """
    params = {
        "service": "search",
        "request": "search",
        "version": "2.0",
        "crs": "EPSG:4326",
        "size": "1",
        "page": "1",
        "type": "address",
        "category": "road",
        "format": "json",
        "errorformat": "json",
        "query": road_addr,
        "key": VWORLD_KEY,
    }

    for attempt in range(1, RETRY_MAX + 1):
        try:
            resp = session.get(VWORLD_URL, params=params, timeout=REQUEST_TIMEOUT)
            if resp.status_code != 200:
                raise RuntimeError(f"HTTP {resp.status_code}")
            data = resp.json()
            r = data.get("response", {})
            if r.get("status") != "OK":
                # NOT_FOUND 등은 정상 미스
                return None, None, None
            items: List[dict] = r.get("result", {}).get("items", [])
            if not items:
                return None, None, None

            addr = items[0].get("address", {}) or {}
            parcel_addr = addr.get("parcel")  # e.g. '삼평동 624' / '삼평동 123-4'
            if not parcel_addr:
                return None, None, None

            # 본번/부번 추출
            main_no = sub_no = None
            m = _PARCEL_RE_DASH.search(parcel_addr)
            if m:
                main_no, sub_no = safe_int(m.group(1)), safe_int(m.group(2))
            else:
                m2 = _PARCEL_RE_MAIN.search(parcel_addr)
                if m2:
                    main_no = safe_int(m2.group(1))

            return parcel_addr, main_no, sub_no

        except Exception as e:
            if attempt >= RETRY_MAX:
                log.warning(f"[VWORLD FAIL] addr='{road_addr}' err={e}")
                return None, None, None
            # 애플리케이션 레벨 백오프(세션 재시도와 별개)
            time.sleep(RETRY_BACKOFF ** (attempt - 1))

    return None, None, None

# ---------------- DB I/O ----------------

def fetch_targets(conn, batch_size: int):
    sql = """
        SELECT apt_cd, apt_nm, apt_rdn_addr
        FROM public.aptinfo_ext
        WHERE lot_addr IS NULL
          AND apt_rdn_addr IS NOT NULL
        ORDER BY apt_cd
        LIMIT %s
        FOR UPDATE SKIP LOCKED
    """
    with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        cur.execute(sql, (batch_size,))
        return cur.fetchall()

def update_row(conn, apt_cd: str, lot_addr: Optional[str], main_no: Optional[int], sub_no: Optional[int]) -> int:
    lot_union = normalize_lot_union(main_no, sub_no)
    sql = """
        UPDATE public.aptinfo_ext
           SET lot_addr   = %s,
               lot_main   = %s,
               lot_sub    = %s,
               lot_union  = %s,
               updated_at = now()
         WHERE apt_cd    = %s
           AND lot_addr IS NULL
    """
    with conn.cursor() as cur:
        cur.execute(sql, (lot_addr, main_no, sub_no, lot_union, apt_cd))
        return cur.rowcount

def ensure_indexes(conn):
    stmts = [
        # 남발 방지를 위해 부분 인덱스 하나와 apt_cd 인덱스만
        "CREATE INDEX IF NOT EXISTS ix_aptinfo_ext_lotaddr_null ON public.aptinfo_ext ((lot_addr IS NULL)) WHERE lot_addr IS NULL;",
        "CREATE INDEX IF NOT EXISTS ix_aptinfo_ext_aptcd ON public.aptinfo_ext (apt_cd);",
    ]
    with conn.cursor() as cur:
        for s in stmts:
            cur.execute(s)
    conn.commit()

def sanity_print(conn):
    with conn.cursor() as cur:
        cur.execute("SELECT current_database(), current_user, current_schema;")
        db, user, schema = cur.fetchone()
        cur.execute("SHOW search_path;")
        sp = cur.fetchone()[0]
        log.info(f"DB={db} user={user} schema={schema} search_path={sp}")
        cur.execute("""
            SELECT 'aptinfo' t, COUNT(*) FROM public.aptinfo
            UNION ALL
            SELECT 'aptinfo_ext', COUNT(*) FROM public.aptinfo_ext
        """)
        log.info(f"table counts: {cur.fetchall()}")

# ---------------- Main ----------------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--batch", type=int, default=DEFAULT_BATCH, help="한 번에 처리할 행 수")
    ap.add_argument("--qps",   type=float, default=DEFAULT_QPS, help="초당 호출 수(최대)")
    ap.add_argument("--dry-run", action="store_true", help="DB 업데이트 없이 로그만")
    args = ap.parse_args()

    if not VWORLD_KEY:
        raise SystemExit("환경변수 VWORLD_API_KEY 가 필요합니다.")

    min_interval = 1.0 / max(0.1, args.qps)

    conn = psycopg2.connect(
        host=os.getenv("PGHOST", "127.0.0.1"),
        port=int(os.getenv("PGPORT", "5432")),
        dbname=os.getenv("PGDATABASE", "postgres"),
        user=os.getenv("PGUSER", "postgres"),
        password=os.getenv("PGPASSWORD", ""),
    )
    conn.autocommit = False

    sanity_print(conn)
    ensure_indexes(conn)

    session = make_http_session()

    total_updated = 0
    loop = 0
    while True:
        loop += 1
        rows = fetch_targets(conn, args.batch)
        if not rows:
            log.info("더 이상 처리할 행이 없습니다. 종료합니다.")
            break

        log.info(f"[loop {loop}] batch fetched: {len(rows)} rows")
        started = time.time()
        updated_this_batch = 0

        for idx, row in enumerate(rows, 1):
            apt_cd = row["apt_cd"]
            rdn    = (row["apt_rdn_addr"] or "").strip()
            if not rdn:
                continue

            t0 = time.time()
            lot_addr, main_no, sub_no = call_vworld_for_parcel(session, rdn)
            dt = time.time() - t0
            if dt < min_interval:
                time.sleep(max(0.0, min_interval - dt))

            if args.dry_run:
                log.info(f"[DRY] {apt_cd} | {rdn} -> {lot_addr} ({main_no}-{sub_no})")
                continue

            if not lot_addr:
                log.debug(f"[MISS] {apt_cd} | vworld no parcel")
                continue

            try:
                rc = update_row(conn, apt_cd, lot_addr, main_no, sub_no)
                if rc == 1:
                    updated_this_batch += 1
                    total_updated      += 1
                else:
                    log.debug(f"[SKIP rc={rc}] {apt_cd} already set?")
            except Exception as e:
                log.warning(f"[UPDATE ERR] apt_cd={apt_cd} err={e}")

        conn.commit()
        log.info(f"[loop {loop}] committed: updated={updated_this_batch}, total={total_updated}, elapsed={time.time()-started:.1f}s")

    conn.close()
    log.info(f"완료! 총 업데이트: {total_updated} 건")

if __name__ == "__main__":
    main()
