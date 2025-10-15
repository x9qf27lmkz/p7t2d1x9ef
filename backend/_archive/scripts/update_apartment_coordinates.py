# scripts/update_apartment_coordinates.py
from __future__ import annotations

import os
import time
import argparse
from typing import Optional, Tuple

import requests
from sqlalchemy import select, or_, and_
from sqlalchemy.orm import Session

from app.db.database import SessionLocal
from app.models.apartment import Apartment

# ------------------------------------------------------------------------------
# 환경변수
# ------------------------------------------------------------------------------
KAKAO_KEY = os.getenv("KAKAO_REST_API_KEY") or os.getenv("KAKAO_REST_KEY")
if not KAKAO_KEY:
    raise RuntimeError("KAKAO_REST_API_KEY (or KAKAO_REST_KEY) is missing in .env")

HEADERS = {"Authorization": f"KakaoAK {KAKAO_KEY}"}

# ------------------------------------------------------------------------------
# 좌표계 판별
# ------------------------------------------------------------------------------
def guess_coord_system(x: Optional[float], y: Optional[float]) -> str:
    """
    x,y가 어느 좌표계 같은지 대강 추정:
      - WGS84 경위도: x(경도) 120~135, y(위도) 30~45
      - TM/UTM-K: 대체로 1e5 이상(예: 9xxxxx~2xxxxx 범위)
      - 알 수 없으면 'unknown'
    """
    if x is None or y is None:
        return "unknown"
    if 120 <= x <= 135 and 30 <= y <= 45:
        return "wgs84"
    if abs(x) >= 1e5 or abs(y) >= 1e5:
        return "tm"
    return "unknown"

# ------------------------------------------------------------------------------
# Kakao API helpers
# ------------------------------------------------------------------------------
def _req_with_backoff(url: str, params: dict, timeout: float = 8.0, max_retry: int = 3):
    delay = 0.6
    for i in range(max_retry):
        try:
            r = requests.get(url, headers=HEADERS, params=params, timeout=timeout)
            if r.status_code == 429:
                time.sleep(delay)
                delay = min(delay * 1.7, 4.0)
                continue
            r.raise_for_status()
            return r
        except requests.HTTPError as e:
            # 5xx도 약간의 백오프
            if 500 <= r.status_code < 600:
                time.sleep(delay)
                delay = min(delay * 1.7, 4.0)
                continue
            raise e
    return None

def kakao_transcoord(x: float, y: float, input_coord: str = "TM") -> Tuple[Optional[float], Optional[float]]:
    """ TM(x,y) → WGS84(lat,lng) """
    r = _req_with_backoff(
        "https://dapi.kakao.com/v2/local/geo/transcoord.json",
        {"x": x, "y": y, "input_coord": input_coord.lower(), "output_coord": "WGS84"},
        timeout=8.0,
    )
    if not r:
        return None, None
    docs = (r.json() or {}).get("documents", [])
    if docs:
        return float(docs[0]["y"]), float(docs[0]["x"])
    return None, None

def kakao_geocode(addr: str) -> Tuple[Optional[float], Optional[float], Optional[str], Optional[str]]:
    """ 도로명/지번 주소로 WGS84 좌표와 행정동(구/동) 얻기 """
    r = _req_with_backoff(
        "https://dapi.kakao.com/v2/local/search/address.json",
        {"query": addr},
        timeout=8.0,
    )
    if not r:
        return None, None, None, None

    docs = (r.json() or {}).get("documents", [])
    if not docs:
        return None, None, None, None

    d0 = docs[0]
    lat = float(d0["y"])
    lng = float(d0["x"])

    gu, dong = None, None
    if "address" in d0 and d0["address"]:
        gu = d0["address"].get("region_2depth_name")
        dong = d0["address"].get("region_3depth_name")
    if "road_address" in d0 and d0["road_address"]:
        gu = gu or d0["road_address"].get("region_2depth_name")
        dong = dong or d0["road_address"].get("region_3depth_name")

    return lat, lng, gu, dong

def kakao_reverse(lng: float, lat: float) -> Tuple[Optional[str], Optional[str]]:
    """ 좌표(WGS84) → 행정동(구/동) (역지오코딩) """
    r = _req_with_backoff(
        "https://dapi.kakao.com/v2/local/geo/coord2address.json",
        {"x": lng, "y": lat},
        timeout=8.0,
    )
    if not r:
        return None, None

    docs = (r.json() or {}).get("documents", [])
    if not docs:
        return None, None

    gu, dong = None, None
    if "address" in docs[0] and docs[0]["address"]:
        gu = docs[0]["address"].get("region_2depth_name")
        dong = docs[0]["address"].get("region_3depth_name")
    if "road_address" in docs[0] and docs[0]["road_address"]:
        gu = gu or docs[0]["road_address"].get("region_2depth_name")
        dong = dong or docs[0]["road_address"].get("region_3depth_name")
    return gu, dong

# ------------------------------------------------------------------------------
# Worker
# ------------------------------------------------------------------------------
def fill_coords_for_apartment(apt: Apartment, fill_admin_when_coords: bool = True) -> bool:
    """
    좌표/행정동 보완 로직:
      1) lat/lng 없으면 xcrd/ycrd 좌표계 판별 → 변환 or 주소 지오코딩
      2) lat/lng 이미 있는데 gu/dong 비었으면 역지오코딩으로 채움 (옵션)
    """
    updated = False

    # 1) 좌표 보정
    if apt.lat is None or apt.lng is None:
        if apt.xcrd is not None and apt.ycrd is not None:
            system = guess_coord_system(apt.xcrd, apt.ycrd)

            if system == "wgs84":
                apt.lng = float(apt.xcrd)
                apt.lat = float(apt.ycrd)
                updated = True

            elif system == "tm":
                y, x = kakao_transcoord(float(apt.xcrd), float(apt.ycrd), input_coord="TM")
                if y is not None and x is not None:
                    apt.lat, apt.lng = y, x
                    updated = True

        if (apt.lat is None or apt.lng is None) and (apt.addr_road or apt.addr_jibun):
            addr = apt.addr_road or apt.addr_jibun
            y, x, gu, dong = kakao_geocode(addr)
            if y is not None and x is not None:
                apt.lat, apt.lng = y, x
                updated = True
            if gu and not apt.gu:
                apt.gu = gu
                updated = True
            if dong and not apt.dong:
                apt.dong = dong
                updated = True

    # 2) 좌표는 있는데 행정동이 비어 있으면 역지오코딩
    if fill_admin_when_coords and (apt.lat is not None and apt.lng is not None):
        if (apt.gu is None) or (apt.dong is None):
            gu, dong = kakao_reverse(float(apt.lng), float(apt.lat))
            if gu and not apt.gu:
                apt.gu = gu
                updated = True
            if dong and not apt.dong:
                apt.dong = dong
                updated = True

    return updated

# ------------------------------------------------------------------------------
# Runner
# ------------------------------------------------------------------------------
def run(batch: int = 200, limit: Optional[int] = None, sleep: float = 0.15, fill_admin: bool = True) -> None:
    processed = 0
    updated_cnt = 0

    with SessionLocal() as db:
        while True:
            where_clause = or_(
                Apartment.lat.is_(None),
                Apartment.lng.is_(None),
                and_(fill_admin, or_(Apartment.gu.is_(None), Apartment.dong.is_(None))),
            )

            q = select(Apartment).where(where_clause).limit(batch)
            rows = db.execute(q).scalars().all()
            if not rows:
                break

            for apt in rows:
                changed = fill_coords_for_apartment(apt, fill_admin_when_coords=fill_admin)
                if changed:
                    updated_cnt += 1
                processed += 1

                if sleep:
                    time.sleep(sleep)
                if limit and processed >= limit:
                    break

            db.commit()
            print(f"[coords] processed={processed} updated={updated_cnt}")

            if limit and processed >= limit:
                break

    print(f"[coords] done. processed={processed}, updated={updated_cnt}")

# ------------------------------------------------------------------------------
# CLI
# ------------------------------------------------------------------------------
if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Backfill apartment coordinates and admin areas")
    ap.add_argument("--batch", type=int, default=200, help="Rows per round-trip")
    ap.add_argument("--limit", type=int, default=None, help="Stop after processing N rows")
    ap.add_argument("--sleep", type=float, default=0.15, help="Sleep between rows (sec)")
    ap.add_argument("--no-fill-admin", action="store_true", help="Do not reverse-geocode gu/dong when coords exist")
    args = ap.parse_args()

    run(
        batch=args.batch,
        limit=args.limit,
        sleep=args.sleep,
        fill_admin=(not args.no_fill_admin),
    )
