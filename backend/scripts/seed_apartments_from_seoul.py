# scripts/seed_apartments_from_seoul.py
from __future__ import annotations

import os
import re
import time
import math
from typing import Any, Dict, Iterable, Optional, Tuple

import requests
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import SQLAlchemyError
from app.db.database import SessionLocal
from app.models.apartment import Apartment

# ============================================================================
# 환경 변수
# ============================================================================
SEOUL_KEY = os.getenv("SEOUL_APTINFO_API_KEY") or os.getenv("SEOUL_API_KEY")
KAKAO_KEY = os.getenv("KAKAO_REST_API_KEY") or os.getenv("KAKAO_REST_KEY")

# 반드시 http 사용 (일부 오픈API는 https 리다이렉트/인증 이슈)
BASE = "http://openapi.seoul.go.kr:8088"

# 서비스명은 간혹 바뀜 → 프로빙으로 자동 결정
SERVICE_CANDIDATES = ["OpenAptInfo", "AptInfo", "ApartmentInfo"]

# 튜닝 파라미터
PAGE_SIZE = 1000
REQ_TIMEOUT = 10
SLEEP_BETWEEN = 0.2  # 각 페이지 처리 후 대기 (rate-limit 완화)

# ============================================================================
# 유틸
# ============================================================================
def _get(url: str, **kwargs) -> requests.Response:
    """http 강제 + 리다이렉트 금지 + 타임아웃 기본값."""
    url = url.replace("https://", "http://")
    kwargs.setdefault("timeout", REQ_TIMEOUT)
    kwargs.setdefault("allow_redirects", False)
    return requests.get(url, **kwargs)

def _json(r: requests.Response) -> Dict[str, Any]:
    try:
        return r.json()
    except Exception:
        raise RuntimeError(f"Non-JSON response (status {r.status_code}): {r.text[:300]}")

def safe_num(v: Any) -> Optional[float]:
    try:
        if v in (None, "", "null"):
            return None
        return float(v)
    except Exception:
        return None

def find_node_has_count(obj: Any) -> Dict[str, Any]:
    """응답 트리에서 list_total_count 가진 dict를 찾아 반환."""
    stack: list[Any] = [obj]
    while stack:
        cur = stack.pop()
        if isinstance(cur, dict):
            if "list_total_count" in cur:
                return cur
            stack.extend(cur.values())
        elif isinstance(cur, list):
            stack.extend(cur)
    raise KeyError("list_total_count not found in response.")

def find_rows(obj: Any) -> Iterable[Dict[str, Any]]:
    """응답 트리에서 'row' 또는 'ROW' key를 가진 리스트를 찾아 반환."""
    stack: list[Any] = [obj]
    while stack:
        cur = stack.pop()
        if isinstance(cur, dict):
            if "row" in cur and isinstance(cur["row"], list):
                return cur["row"]
            if "ROW" in cur and isinstance(cur["ROW"], list):
                return cur["ROW"]
            stack.extend(cur.values())
        elif isinstance(cur, list):
            stack.extend(cur)
    return []

def kakao_to_wgs84(x: float, y: float, from_coord: str = "TM") -> Tuple[Optional[float], Optional[float]]:
    """Kakao 좌표 변환. 실패하면 (None, None) 반환."""
    if not KAKAO_KEY:
        return None, None
    try:
        url = "https://dapi.kakao.com/v2/local/geo/transcoord.json"
        headers = {"Authorization": f"KakaoAK {KAKAO_KEY}"}
        params = {"x": x, "y": y, "input_coord": from_coord.lower(), "output_coord": "WGS84"}
        r = requests.get(url, headers=headers, params=params, timeout=5)
        r.raise_for_status()
        docs = r.json().get("documents", [])
        if docs:
            return docs[0].get("y"), docs[0].get("x")  # (lat, lng)
    except Exception:
        pass
    return None, None

# ---- 입력값 가드/정규화 ------------------------------------------------------
def _is_wgs84_pair(x, y) -> bool:
    """한국 경위도 범위(경도 120~135, 위도 30~45)면 WGS84로 간주."""
    try:
        return x is not None and y is not None and 120 <= float(x) <= 135 and 30 <= float(y) <= 45
    except Exception:
        return False

def _guard_lat_lng(lat: Optional[float], lng: Optional[float]) -> tuple[Optional[float], Optional[float]]:
    """위도/경도 값이 한국 범위를 벗어나면 NULL 처리."""
    if lat is not None and not (30 <= float(lat) <= 45):
        lat = None
    if lng is not None and not (120 <= float(lng) <= 135):
        lng = None
    return lat, lng

def _year_only(dtstr: Optional[str]) -> Optional[int]:
    """'2003-12-26 00:00:00.0' 등에서 연도만 추출."""
    if not dtstr:
        return None
    m = re.match(r"(\d{4})", str(dtstr))
    return int(m.group(1)) if m else None

def _guard_year(y: Optional[int]) -> Optional[int]:
    """현실 범위 밖 연도는 버림 (1970~2035 정도 허용)."""
    if y is None:
        return None
    return y if 1970 <= y <= 2035 else None

def _build_jibun(gu: Optional[str], dong: Optional[str], daddr: Optional[str]) -> Optional[str]:
    """
    DADDR 예: '47-1', '857', '서울시 노원구 월계2동 940번지' 등.
    숫자/하이픈 우선 추출 → gu/dong와 조합.
    """
    if not (gu or dong or daddr):
        return None
    cleaned = None
    if daddr:
        m = re.search(r"(\d[\d\-]*)", str(daddr))
        cleaned = m.group(1) if m else str(daddr).strip()
    parts = [p for p in [gu, dong, cleaned] if p]
    return " ".join(parts) if parts else None

# ============================================================================
# 서울 API
# ============================================================================
def probe_service_name() -> str:
    """SERVICE_CANDIDATES 순서대로 1건 요청해 보고, list_total_count가 나오는 서비스명을 반환."""
    if not SEOUL_KEY:
        raise RuntimeError("SEOUL_APTINFO_API_KEY is missing in environment (.env).")
    for svc in SERVICE_CANDIDATES:
        url = f"{BASE}/{SEOUL_KEY}/json/{svc}/1/1"
        r = _get(url)
        try:
            r.raise_for_status()
            data = _json(r)
            _ = find_node_has_count(data)
            return svc
        except Exception:
            continue
    raise RuntimeError(f"Cannot detect service name among {SERVICE_CANDIDATES}. Verify the dataset page or key.")

def fetch_count(service: str) -> int:
    url = f"{BASE}/{SEOUL_KEY}/json/{service}/1/1"
    r = _get(url)
    r.raise_for_status()
    payload = find_node_has_count(_json(r))
    return int(payload["list_total_count"])

def fetch_page(service: str, start: int, end: int) -> Iterable[Dict[str, Any]]:
    url = f"{BASE}/{SEOUL_KEY}/json/{service}/{start}/{end}"
    r = _get(url)
    r.raise_for_status()
    return find_rows(_json(r))

# ============================================================================
# 매핑 + UPSERT
# ============================================================================
def map_row(r: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """서울시 공동주택(OpenAptInfo/AptInfo 등) 1행을 apartments 레코드로 매핑."""
    apt_cd = r.get("APT_CD") or r.get("APARTMENT_CD")
    name   = r.get("APT_NM") or r.get("APARTMENT_NM")
    if not apt_cd or not name:
        return None  # 필수키 없으면 skip

    # 행정구역
    gu   = r.get("SGG_ADDR") or r.get("SIGG_ADDR") or r.get("GU")
    dong = r.get("EMD_ADDR") or r.get("DONG")

    # 주소
    addr_road = (
        r.get("APT_RDN_ADDR") or  # 전체 도로명 주소 (샘플 XML 기준 가장 신뢰)
        r.get("ROAD_ADDR") or
        r.get("DORO_ADDR")
    )
    addr_jibun = (
        r.get("APT_STDG_ADDR") or  # 표준 지번 주소가 오면 1순위로 사용
        r.get("JIBUN_ADDR") or
        _build_jibun(gu, dong, r.get("DADDR"))
    )

    # 좌표
    xcrd = safe_num(r.get("XCRD"))
    ycrd = safe_num(r.get("YCRD"))
    lat  = safe_num(r.get("WGS84_Y"))
    lng  = safe_num(r.get("WGS84_X"))

    # XCRD/YCRD가 이미 WGS84 범위라면 그대로 lat/lng로 사용
    if (lat is None or lng is None) and _is_wgs84_pair(xcrd, ycrd):
        lng = lng or xcrd
        lat = lat or ycrd
    # 그 외의 경우에만 Kakao 변환 시도
    elif (lat is None or lng is None) and (xcrd is not None and ycrd is not None):
        y_lat, x_lng = kakao_to_wgs84(xcrd, ycrd, from_coord="TM")
        lat = lat or y_lat
        lng = lng or x_lng

    # 좌표/연도 가드
    lat, lng = _guard_lat_lng(lat, lng)
    year_approved = _guard_year(_year_only(
        r.get("USE_APRV_YMD") or
        r.get("CMPX_APRV_DAY") or
        r.get("CMPLX_APPRV_DAY") or
        r.get("CMPLX_APPRV_DT")
    ))

    return {
        "source": "SEOUL_APT",
        "source_id": str(apt_cd),
        "name": name,
        "addr_road": addr_road,
        "addr_jibun": addr_jibun,
        "gu": gu,
        "dong": dong,
        "year_approved": year_approved,
        "xcrd": xcrd,
        "ycrd": ycrd,
        "lat": lat,
        "lng": lng,
        "use_yn": (r.get("USE_YN") or "Y")[:1],
    }

def upsert_row(db, r: Dict[str, Any]) -> None:
    data = map_row(r)
    if not data:
        return  # 필수 누락 → skip

    ins = insert(Apartment).values(**data)

    # 새 값이 있을 때만 덮어쓰는 안전한 UPSERT
    stmt = ins.on_conflict_do_update(
        index_elements=[Apartment.source, Apartment.source_id],
        set_={
            "name": ins.excluded.name,
            "addr_road": ins.excluded.addr_road if data["addr_road"] is not None else Apartment.addr_road,
            "addr_jibun": ins.excluded.addr_jibun if data["addr_jibun"] is not None else Apartment.addr_jibun,
            "gu": ins.excluded.gu if data["gu"] is not None else Apartment.gu,
            "dong": ins.excluded.dong if data["dong"] is not None else Apartment.dong,
            "year_approved": ins.excluded.year_approved,
            "xcrd": ins.excluded.xcrd if data["xcrd"] is not None else Apartment.xcrd,
            "ycrd": ins.excluded.ycrd if data["ycrd"] is not None else Apartment.ycrd,
            "lat": ins.excluded.lat if data["lat"] is not None else Apartment.lat,
            "lng": ins.excluded.lng if data["lng"] is not None else Apartment.lng,
            "use_yn": ins.excluded.use_yn,
        },
    )
    db.execute(stmt)

# ============================================================================
# 실행
# ============================================================================
def run() -> None:
    service = probe_service_name()
    print(f"[seed-apartments] detected service = {service}")

    with SessionLocal() as db:
        total = fetch_count(service)
        pages = math.ceil(total / PAGE_SIZE)
        print(f"[seed-apartments] total={total:,} page_size={PAGE_SIZE} pages={pages}")

        for p in range(pages):
            start = p * PAGE_SIZE + 1
            end = (p + 1) * PAGE_SIZE
            try:
                rows = list(fetch_page(service, start, end))
            except Exception as e:
                print(f"[seed-apartments] fetch error p={p+1}/{pages} range={start}-{end}: {e}")
                time.sleep(SLEEP_BETWEEN)
                continue

            # 같은 페이지 내 동일 APT_CD 중복 제거(간헐적 중복 방지)
            uniq: dict[tuple[str, str], Dict[str, Any]] = {}
            for r in rows:
                key = (
                    (r.get("APT_CD") or r.get("APARTMENT_CD")),
                    (r.get("APT_NM") or r.get("APARTMENT_NM")),
                )
                if key[0] and key not in uniq:
                    uniq[key] = r
            rows = list(uniq.values())

            err_cnt = 0
            for r in rows:
                try:
                    upsert_row(db, r)
                except SQLAlchemyError as e:
                    err_cnt += 1
                    apt_cd = r.get("APT_CD") or r.get("APARTMENT_CD")
                    apt_nm = r.get("APT_NM") or r.get("APARTMENT_NM")
                    detail = getattr(e, "orig", None) or e
                    print(f"[seed-apartments] upsert error apt={apt_cd}/{apt_nm}: {detail}")
                    db.rollback()  # ✅ 중요: 행 단위 롤백 (연쇄 오류 방지)
                except Exception as e:
                    err_cnt += 1
                    apt_cd = r.get("APT_CD") or r.get("APARTMENT_CD")
                    apt_nm = r.get("APT_NM") or r.get("APARTMENT_NM")
                    print(f"[seed-apartments] upsert error apt={apt_cd}/{apt_nm}: {e}")
                    db.rollback()

            try:
                db.commit()
            except SQLAlchemyError as e:
                print(f"[seed-apartments] COMMIT error p={p+1}/{pages} ({start}-{end}): {getattr(e, 'orig', e)}")
                db.rollback()
            except Exception as e:
                print(f"[seed-apartments] COMMIT error p={p+1}/{pages} ({start}-{end}): {e}")
                db.rollback()
            else:
                print(f"[seed-apartments] committed p={p+1}/{pages} ({start}-{end})  errors={err_cnt}")

            time.sleep(SLEEP_BETWEEN)

if __name__ == "__main__":
    run()
