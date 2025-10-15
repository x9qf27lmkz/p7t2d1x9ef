from __future__ import annotations

"""
서울시 실거래가 적재 스크립트 (리팩토링판)
- 연도는 공백/콤마 모두 허용: --years 2023 2024 2025 또는 --years 2023,2024,2025
- 구 이름/코드 모두 허용: --gus 노원구 강남구 또는 --gus 11350 11680
- 페이지네이션 처리 (start/end)
- 요청 재시도/백오프 (urllib3 Retry)
- 필드 키 자동 감지 (APT_NM/BLDG_NM, EXCLUSE_AR/ARCH_AREA, SUM_AMT/THING_AMT, CNTRCT_DE/CTRT_DAY)
- SQLAlchemy 세션 배치 커밋
- 상세 로깅

필수 환경변수: SEOUL_API_KEY ('.env'에 넣고 export)
"""

import os
import math
import time
import argparse
from typing import Dict, Tuple, List, Any, Optional
from datetime import datetime

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.db.database import SessionLocal  # 동기 세션
from app.models.trade import SeoulTrade   # ORM 모델

BASE = "http://openapi.seoul.go.kr:8088"
SERVICE = "tbLnOpendataRtmsV"
PAGE_SIZE = 1000
SLEEP_PER_PAGE = 0.25  # rate-limit 완화

# 서울 25개 구 코드
GU_CODE_MAP: Dict[str, str] = {
    "종로구": "11110", "중구": "11140", "용산구": "11170",
    "성동구": "11200", "광진구": "11215", "동대문구": "11230",
    "중랑구": "11260", "성북구": "11290", "강북구": "11305",
    "도봉구": "11320", "노원구": "11350", "은평구": "11380",
    "서대문구": "11410", "마포구": "11440", "양천구": "11470",
    "강서구": "11500", "구로구": "11530", "금천구": "11545",
    "영등포구": "11560", "동작구": "11590", "관악구": "11620",
    "서초구": "11650", "강남구": "11680", "송파구": "11710",
    "강동구": "11740",
}

# --------------------------- Utils ---------------------------

def get_api_key() -> str:
    api_key = os.getenv("SEOUL_API_KEY")
    if not api_key:
        raise RuntimeError("SEOUL_API_KEY 가 .env 에 설정되어 있어야 합니다.")
    return api_key


def new_http() -> requests.Session:
    s = requests.Session()
    retries = Retry(
        total=5,
        backoff_factor=0.5,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset(["GET"]),
        respect_retry_after_header=True,
    )
    adapter = HTTPAdapter(max_retries=retries)
    s.mount("http://", adapter)
    s.mount("https://", adapter)
    s.headers.update({"User-Agent": "homesweethome-etl/1.0"})
    return s


def to_int(v: Any) -> Optional[int]:
    try:
        if v in (None, "", " "): return None
        if isinstance(v, str): v = v.replace(",", "")
        return int(float(v))
    except Exception:
        return None


def to_float(v: Any) -> Optional[float]:
    try:
        if v in (None, "", " "): return None
        if isinstance(v, str): v = v.replace(",", "")
        return float(v)
    except Exception:
        return None


def to_date8(s: Optional[str]):
    if s and len(s) == 8:
        try:
            return datetime.strptime(s, "%Y%m%d").date()
        except Exception:
            return None
    return None


# --------------------------- API I/O ---------------------------

def make_url(api_key: str, year: str, sgg_param: str, start: int, end: int) -> str:
    return f"{BASE}/{api_key}/json/{SERVICE}/{start}/{end}/{year}/{sgg_param}"


def fetch_page(http, api_key, year, sgg_param, start, end):
    url = make_url(api_key, year, sgg_param, start, end)
    for attempt in range(3):
        r = http.get(url, timeout=20)
        try:
            payload = r.json().get(SERVICE, {})
        except ValueError:  # JSON 파싱 실패 (빈 응답/HTML 등)
            time.sleep(0.6 * (attempt + 1))
            continue
        code = (payload.get("RESULT") or {}).get("CODE")
        total = int(payload.get("list_total_count") or 0)
        rows = payload.get("row") or []
        return code, total, rows, url
    # 3회 실패 시 마지막 응답 내용 일부 출력
    raise RuntimeError(f"Non-JSON or invalid response after retries: {url}")



def decide_sgg_param(http: requests.Session, api_key: str, year: str, sgg_name_or_code: str) -> Tuple[str, int]:
    """한글 구명 → 실패 시 코드 → 그래도 실패면 raise"""
    # 1) 한글 구명 시도
    from urllib.parse import quote
    sgg_try = quote(sgg_name_or_code)
    code, total, _, url = fetch_page(http, api_key, year, sgg_try, 1, 5)
    print(f"[CHECK] name-try code={code} total={total} url={url}")
    if code == "INFO-000":
        return sgg_try, total

    # 2) 구코드 시도
    sgg_code = GU_CODE_MAP.get(sgg_name_or_code, sgg_name_or_code)
    code, total, _, url = fetch_page(http, api_key, year, sgg_code, 1, 5)
    print(f"[CHECK] code-try code={code} total={total} url={url}")
    if code == "INFO-000":
        return sgg_code, total

    raise RuntimeError(f"API 비정상 응답: {code} (year={year}, sgg={sgg_name_or_code})")


# --------------------------- Normalization ---------------------------

def normalize_row(r: dict) -> dict:
    """서울시 tbLnOpendataRtmsV → DB 스키마 매핑 (키 자동 감지)"""
    # 이름/면적/금액/일자 키 자동 감지
    name = r.get("BLDG_NM") or r.get("APT_NM") or r.get("BLDG_NM_KOR")
    area = r.get("ARCH_AREA") or r.get("EXCLUSE_AR") or r.get("AREA")
    price = r.get("THING_AMT") or r.get("SUM_AMT") or r.get("DEAL_AMT")
    date8 = r.get("CTRT_DAY") or r.get("CNTRCT_DE") or r.get("DEAL_YMD")

    lot = f"{r.get('MNO')}-{r.get('SNO')}" if r.get("MNO") else None
    floor_val = r.get("FLR") or r.get("FLOOR")
    floor = None
    if floor_val not in (None, "", " "):
        try:
            floor = int(float(str(floor_val).replace(",", "")))
        except Exception:
            floor = None

    price_krw = to_int(price)
    if price_krw is not None:
        # 일부 API는 '만원' 단위로 내려옴 → 원화로 변환
        if price_krw < 10_000_000:  # heuristic
            price_krw *= 10_000

    return {
        "gu": r.get("CGG_NM") or r.get("SGG_NM") or r.get("GU") or r.get("SGG") ,
        "dong": r.get("STDG_NM") or r.get("DONG") or r.get("BJDONG_NM"),
        "complex": name,
        "lot_number": lot,
        "building_use": r.get("BLDG_USG"),
        "area_m2": to_float(area),
        "price_krw": price_krw,
        "contract_date": to_date8(date8),
        "build_year": to_int(r.get("ARCH_YR") or r.get("BUILD_YEAR")),
        "floor": floor,
        "report_year": to_int(r.get("RCPT_YR")),
        "declare_type": r.get("DCLR_SE"),
        "opr_sgg": r.get("OPBIZ_RESTAGNT_SGG_NM"),
        "lat": None,
        "lng": None,
        "raw_json": r,
    }


# --------------------------- Save ---------------------------

def save_rows(db: Session, rows: List[dict], batch: int = 1000) -> Tuple[int, int]:
    tried = 0
    inserted = 0
    for i, r in enumerate(rows, 1):
        tried += 1
        data = normalize_row(r)
        obj = SeoulTrade(**data)
        try:
            db.add(obj)
            db.flush()  # UniqueConstraint 위반 시 IntegrityError 발생
            inserted += 1
        except IntegrityError:
            db.rollback()
            continue
        if (i % batch) == 0:
            db.commit()
    db.commit()
    return inserted, tried


# --------------------------- Main ETL ---------------------------

def ingest(year: str, sgg: str):
    api_key = get_api_key()
    http = new_http()

    sgg_param, total = decide_sgg_param(http, api_key, year, sgg)
    if total <= 0:
        print(f"✅ API 정상이나 해당 조건({year}/{sgg}) 총건수 0")
        return

    pages = math.ceil(total / PAGE_SIZE)
    print(f"[INFO] {sgg} {year}: total={total}, pages={pages}, page_size={PAGE_SIZE}")

    inserted_sum = 0
    tried_sum = 0

    db: Session = SessionLocal()
    try:
        for p in range(pages):
            start = p * PAGE_SIZE + 1
            end = min((p + 1) * PAGE_SIZE, total)
            code_p, total_p, rows_p, url_p = fetch_page(http, api_key, year, sgg_param, start, end)
            print(f"[PAGE] {p+1}/{pages} code={code_p} rows={len(rows_p)} url={url_p}")

            if code_p != "INFO-000" or not rows_p:
                time.sleep(0.5)
                code_p, total_p, rows_p, url_p = fetch_page(http, api_key, year, sgg_param, start, end)
                print(f"[RETRY] code={code_p} rows={len(rows_p)} url={url_p}")
                if code_p != "INFO-000" or not rows_p:
                    print(f"❌ 페이지 실패: p={p+1} code={code_p}")
                    continue

            ins, tr = save_rows(db, rows_p)
            inserted_sum += ins
            tried_sum += tr
            time.sleep(SLEEP_PER_PAGE)

        print(f"✅ Done: {sgg} {year} → Inserted {inserted_sum} / Tried {tried_sum}")
    finally:
        db.close()


def _split_args(tokens: List[str]) -> List[str]:
    out: List[str] = []
    for t in tokens:
        out += [x.strip() for x in t.split(',') if x.strip()]
    return out


def main():
    parser = argparse.ArgumentParser(description="서울시 부동산 실거래가 적재")
    parser.add_argument("--years", nargs="+", help="예: 2023 2024 2025 또는 2023,2024,2025", required=True)
    parser.add_argument("--gus", nargs="+", help="예: 노원구 강남구 또는 11350 11680", required=True)
    args = parser.parse_args()

    years = _split_args(args.years)
    gus   = _split_args(args.gus)

    for y in years:
        for g in gus:
            try:
                ingest(y, g)
            except Exception as e:
                print(f"❌ {g} {y} 실패: {e}")


if __name__ == "__main__":
    main()
