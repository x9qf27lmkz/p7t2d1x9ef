#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
cloud_aptinfo.apt_rdn_addr -> join_key(동주소) 적재
- 대상: public.cloud_aptinfo
- 조건: join_key IS NULL AND apt_rdn_addr IS NOT NULL
- 실패 행은 join_key='__MISS__' 로 마킹해 재조회 방지 (스키마 변경 없음)
- --retry-miss 옵션으로 실패 마킹을 NULL로 되돌려 재시도 가능
"""

import os, sys, time, re, argparse, logging
from typing import Optional, Tuple, List

import psycopg2
import psycopg2.extras
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())

# ---------- 환경/상수 ----------
VWORLD_KEY       = os.getenv("VWORLD_API_KEY", "")
VWORLD_URL       = "https://api.vworld.kr/req/search"
DEFAULT_QPS      = 7.0
DEFAULT_BATCH    = 500
REQUEST_TIMEOUT  = 8.0
RETRY_MAX        = 3

SENTINEL_MISS    = "__MISS__"

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s | %(message)s")
log = logging.getLogger("vworld-cloud-aptinfo")

# ---------- 유틸 ----------
# parcel 예: '화곡동 151-39' / '목동 925'
_RE_MAIN_SUB = re.compile(r'(\d+)\s*-\s*(\d+)')
_RE_MAIN     = re.compile(r'(\d+)')

def parse_parcel(parcel_addr: str) -> Tuple[Optional[str], Optional[int], Optional[int]]:
    if not parcel_addr:
        return None, None, None
    parts = parcel_addr.strip().split()
    if not parts:
        return None, None, None
    dong = parts[0].replace(" ", "")
    main_no = sub_no = None
    m = _RE_MAIN_SUB.search(parcel_addr)
    if m:
        main_no, sub_no = int(m.group(1)), int(m.group(2))
    else:
        m2 = _RE_MAIN.search(parcel_addr)
        if m2:
            main_no = int(m2.group(1))
    return dong, main_no, sub_no

def make_join_key(dong: Optional[str], main_no: Optional[int], sub_no: Optional[int]) -> Optional[str]:
    if not dong or main_no is None:
        return None
    return f"{dong}{int(main_no)}-{int(sub_no)}" if sub_no and int(sub_no) > 0 else f"{dong}{int(main_no)}"

def make_http_session() -> requests.Session:
    s = requests.Session()
    retries = Retry(
        total=RETRY_MAX,
        backoff_factor=0.2,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=("GET",),
        raise_on_status=False,
    )
    s.mount("https://", HTTPAdapter(max_retries=retries))
    return s

def call_vworld(session: requests.Session, road_addr: str) -> Optional[str]:
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
    try:
        resp = session.get(VWORLD_URL, params=params, timeout=REQUEST_TIMEOUT)
        if resp.status_code != 200:
            return None
        data = resp.json()
        r = data.get("response", {})
        if r.get("status") != "OK":
            return None
        items: List[dict] = r.get("result", {}).get("items", [])
        if not items:
            return None
        addr = items[0].get("address", {}) or {}
        return addr.get("parcel")  # 예: '화곡동 151-39'
    except Exception:
        return None

# ---------- DB ----------
def ensure_indexes(conn):
    stmts = [
        "CREATE INDEX IF NOT EXISTS ix_cloud_aptinfo_joinkey_null ON public.cloud_aptinfo ((join_key IS NULL)) WHERE join_key IS NULL;",
        "CREATE INDEX IF NOT EXISTS ix_cloud_aptinfo_rdn ON public.cloud_aptinfo (apt_rdn_addr);",
        f"CREATE INDEX IF NOT EXISTS ix_cloud_aptinfo_miss ON public.cloud_aptinfo (join_key) WHERE join_key = '{SENTINEL_MISS}';",
    ]
    with conn.cursor() as cur:
        for s in stmts:
            cur.execute(s)
    conn.commit()

def fetch_targets(conn, limit_n: int):
    sql = """
        SELECT apt_cd, apt_nm, apt_rdn_addr
        FROM public.cloud_aptinfo
        WHERE join_key IS NULL
          AND apt_rdn_addr IS NOT NULL
        ORDER BY apt_cd
        LIMIT %s
        FOR UPDATE SKIP LOCKED
    """
    with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        cur.execute(sql, (limit_n,))
        return cur.fetchall()

def update_join_key(conn, apt_cd: str, join_key: str) -> int:
    sql = """
        UPDATE public.cloud_aptinfo
           SET join_key = %s
         WHERE apt_cd = %s
           AND (join_key IS NULL OR join_key <> %s)
    """
    with conn.cursor() as cur:
        cur.execute(sql, (join_key, apt_cd, join_key))
        return cur.rowcount

def mark_miss(conn, apt_cd: str) -> int:
    # 실패표시로 SENTINEL_MISS 입력 (스키마 변경 없이 재조회 방지)
    return update_join_key(conn, apt_cd, SENTINEL_MISS)

def count_remaining(conn) -> int:
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM public.cloud_aptinfo WHERE join_key IS NULL AND apt_rdn_addr IS NOT NULL;")
        return cur.fetchone()[0]

def reset_miss_to_null(conn) -> int:
    with conn.cursor() as cur:
        cur.execute("UPDATE public.cloud_aptinfo SET join_key = NULL WHERE join_key = %s;", (SENTINEL_MISS,))
        n = cur.rowcount
    conn.commit()
    return n

def sanity_print(conn):
    with conn.cursor() as cur:
        cur.execute("SELECT current_database(), current_user, current_schema;")
        db, user, schema = cur.fetchone()
        cur.execute("SHOW search_path;")
        sp = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM public.cloud_aptinfo;")
        total = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM public.cloud_aptinfo WHERE join_key IS NULL AND apt_rdn_addr IS NOT NULL;")
        remain = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM public.cloud_aptinfo WHERE join_key = %s;", (SENTINEL_MISS,))
        miss = cur.fetchone()[0]
    log.info(f"DB={db} user={user} schema={schema} search_path={sp} total={total} remain(NULL)={remain} miss={miss}")

# ---------- Main ----------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--batch", type=int, default=DEFAULT_BATCH, help="한 번에 처리할 행 수")
    ap.add_argument("--qps",   type=float, default=DEFAULT_QPS, help="초당 호출 수(최대)")
    ap.add_argument("--dry-run", action="store_true", help="DB 업데이트 없이 로그만")
    ap.add_argument("--retry-miss", action="store_true", help="SENTINEL_MISS를 NULL로 되돌려 재시도")
    args = ap.parse_args()

    if not VWORLD_KEY:
        raise SystemExit("환경변수 VWORLD_API_KEY 필요")

    min_interval = 1.0 / max(0.1, args.qps)

    conn = psycopg2.connect(
        host=os.getenv("PGHOST", "127.0.0.1"),
        port=int(os.getenv("PGPORT", "5432")),
        dbname=os.getenv("PGDATABASE", "postgres"),
        user=os.getenv("PGUSER", "postgres"),
        password=os.getenv("PGPASSWORD", ""),
    )
    conn.autocommit = False

    ensure_indexes(conn)

    if args.retry_miss:
        n = reset_miss_to_null(conn)
        log.info(f"retry-miss: {n} rows reset from '{SENTINEL_MISS}' to NULL")

    sanity_print(conn)
    session = make_http_session()

    total_updated = 0
    last_remain = None

    while True:
        rows = fetch_targets(conn, args.batch)
        if not rows:
            remain = count_remaining(conn)
            log.info(f"처리할 행 없음. 남은 NULL={remain}")
            break

        start_t = time.time()
        stats = {"updated": 0, "miss": 0, "skip": 0, "error": 0}

        for row in rows:
            apt_cd = row["apt_cd"]
            rdn    = (row["apt_rdn_addr"] or "").strip()
            if not rdn:
                stats["skip"] += 1
                continue

            t0 = time.time()
            parcel = call_vworld(session, rdn)
            # QPS 제어
            dt = time.time() - t0
            if (need := min_interval - dt) > 0:
                time.sleep(need)

            try:
                if not parcel:
                    if not args.dry_run:
                        mark_miss(conn, apt_cd)
                    stats["miss"] += 1
                    continue

                dong, main_no, sub_no = parse_parcel(parcel)
                jkey = make_join_key(dong, main_no, sub_no)
                if not jkey:
                    if not args.dry_run:
                        mark_miss(conn, apt_cd)
                    stats["miss"] += 1
                    continue

                if args.dry_run:
                    log.info(f"[DRY] apt_cd={apt_cd} | {rdn} -> '{parcel}' -> join_key='{jkey}'")
                else:
                    rc = update_join_key(conn, apt_cd, jkey)
                    if rc == 1:
                        stats["updated"] += 1
                        total_updated    += 1
                    else:
                        stats["skip"] += 1

            except Exception as e:
                stats["error"] += 1
                log.warning(f"[UPDATE ERR] apt_cd={apt_cd} err={e}")

        conn.commit()
        remain = count_remaining(conn)
        log.info(f"commit ok. batch_stats={stats}, total_updated={total_updated}, remain(NULL)={remain}, elapsed={time.time()-start_t:.1f}s")

        # 종료 안전장치: 남은 수가 줄지 않으면 루프 중단
        if last_remain is not None and remain >= last_remain:
            log.warning(f"남은 NULL이 더 이상 줄지 않음. 무한루프 방지를 위해 종료. remain={remain}, last_remain={last_remain}")
            break
        last_remain = remain

    sanity_print(conn)
    conn.close()
    log.info(f"완료. 총 join_key 세팅: {total_updated}")

if __name__ == "__main__":
    main()
