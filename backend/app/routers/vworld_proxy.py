# backend/app/routers/vworld_proxy.py
from __future__ import annotations

import math
import os
from typing import Dict, List, Tuple

import httpx
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse

router = APIRouter(prefix="/api/vworld", tags=["vworld"])

# -------------------------------------------------------------------
# Config
# -------------------------------------------------------------------
VWORLD_DATA_KEY = os.getenv("VWORLD_DATA_KEY", "").strip()
VWORLD_SEARCH_KEY = os.getenv("VWORLD_SEARCH_KEY", "").strip()
VWORLD_DOMAIN = os.getenv("VWORLD_DOMAIN", "http://localhost:8081").strip()

ENDPOINT_DATA = "https://api.vworld.kr/req/data"
ENDPOINT_SEARCH = "https://api.vworld.kr/req/search"

DATASET = {
    "sido": "LT_C_ADSIDO_INFO",
    "sigg": "LT_C_ADSIGG_INFO",
    "emd": "LT_C_ADEMD_INFO",
}

# 레벨에 따른 bbox 허용 최대 스팬(경도/위도, 도 단위) — 이 값보다 크면 자동 분할
# 너무 느슨하면 API에서 INVALID_RANGE, 너무 빡빡하면 호출이 많아짐.
MAX_SPAN_BY_LEVEL = {
    "emd": 0.25,   # 읍면동은 더 촘촘하게
    "sigg": 0.60,  # 시군구
    "sido": 1.20,  # 광역시도
}

# VWorld size 권장 상한
MAX_SIZE = 1000

# -------------------------------------------------------------------
# Helpers
# -------------------------------------------------------------------
def _is_num(v) -> bool:
    try:
        return math.isfinite(float(v))
    except Exception:
        return False


def _normalize_bbox(w: float, s: float, e: float, n: float) -> Tuple[float, float, float, float]:
    """서/동, 남/북 순서를 강제로 올바르게 정렬."""
    west, east = (w, e) if w <= e else (e, w)
    south, north = (s, n) if s <= n else (n, s)
    return west, south, east, north


def _span_ok(level: str, w: float, s: float, e: float, n: float) -> bool:
    span_x = abs(e - w)
    span_y = abs(n - s)
    limit = MAX_SPAN_BY_LEVEL.get(level, 0.6)
    return span_x <= limit and span_y <= limit


def _mid(a: float, b: float) -> float:
    return (a + b) / 2.0


def _empty_fc() -> Dict:
    return {"type": "FeatureCollection", "features": []}


def _wrap_ok(feature_collection: Dict) -> Dict:
    """프론트가 기대하는 vworld 래핑 형태로 감싸서 반환."""
    return {
        "response": {
            "status": "OK",
            "result": {
                "featureCollection": feature_collection
            }
        }
    }


def _wrap_error(code: str, text: str, level: int = 2) -> Dict:
    return {
        "response": {
            "status": "ERROR",
            "error": {"level": level, "code": code, "text": text}
        }
    }


async def _call_vworld_data(
    client: httpx.AsyncClient,
    *,
    level: str,
    west: float,
    south: float,
    east: float,
    north: float,
    domain: str,
    size: int,
) -> Dict:
    """VWorld Data API 호출 (한 번). OK/ERROR 원문 그대로 반환."""
    geom = f"BOX({west},{south},{east},{north})"
    params = {
        "service": "data",
        "request": "GetFeature",
        "data": DATASET[level],
        "key": VWORLD_DATA_KEY,
        "domain": domain,
        "format": "json",
        "size": str(size),
        "crs": "EPSG:4326",
        "geomFilter": geom,
    }

    print(
        f"[VWORLD] → {level:<4} bbox=({west:.6f},{south:.6f},{east:.6f},{north:.6f}) "
        f"size={size} domain={domain} key=****{VWORLD_DATA_KEY[-4:]}"
    )
    r = await client.get(ENDPOINT_DATA, params=params)
    try:
        payload = r.json()
    except Exception:
        raise HTTPException(502, "Invalid VWorld response")

    status = (payload.get("response") or {}).get("status")
    if status != "OK":
        err = (payload.get("response") or {}).get("error")
        print(f"[VWORLD] ◁ status={status} err={err}")
    else:
        features = (
            payload.get("response", {})
            .get("result", {})
            .get("featureCollection", {})
            .get("features", [])
        )
        print(f"[VWORLD] ◁ OK features={len(features)}")

    return payload


async def _fetch_bbox_recursive(
    client: httpx.AsyncClient,
    *,
    level: str,
    west: float,
    south: float,
    east: float,
    north: float,
    domain: str,
    size: int,
    depth: int = 0,
    max_depth: int = 4,
) -> Dict:
    """
    bbox가 너무 크면 2×2로 나눠 재귀 호출.
    최종적으로 FeatureCollection을 합쳐서 VWorld 래핑 형태로 반환.
    """
    west, south, east, north = _normalize_bbox(west, south, east, north)

    # 범위가 너무 크면 분할
    if not _span_ok(level, west, south, east, north):
        if depth >= max_depth:
            # 더 쪼갤 수 없으면 빈 컬렉션으로 반환
            print(f"[VWORLD] ⚠ span too large but depth limit reached (level={level})")
            return _wrap_ok(_empty_fc())

        mx = _mid(west, east)
        my = _mid(south, north)
        # 4분할
        quads = [
            (west, south, mx, my),
            (mx, south, east, my),
            (west, my, mx, north),
            (mx, my, east, north),
        ]

        merged: List[Dict] = []
        for (w, s, e, n) in quads:
            part = await _fetch_bbox_recursive(
                client,
                level=level,
                west=w, south=s, east=e, north=n,
                domain=domain, size=size,
                depth=depth + 1, max_depth=max_depth,
            )
            feats = (
                part.get("response", {})
                .get("result", {})
                .get("featureCollection", {})
                .get("features", [])
            )
            merged.extend(feats)

        fc = {"type": "FeatureCollection", "features": merged}
        return _wrap_ok(fc)

    # 허용 스팬 이하 → 실제 호출
    payload = await _call_vworld_data(
        client, level=level, west=west, south=south, east=east, north=north, domain=domain, size=size
    )
    status = (payload.get("response") or {}).get("status")
    if status == "OK":
        # 그대로 래핑 유지
        return payload

    # ERROR의 경우: INVALID_RANGE 등일 때도 재귀 분할 시도
    err = (payload.get("response") or {}).get("error") or {}
    code = str(err.get("code", "")).upper()

    if code in {"INVALID_RANGE"} and depth < max_depth:
        print(f"[VWORLD] ↺ INVALID_RANGE → split & retry (depth={depth})")
        mx = _mid(west, east)
        my = _mid(south, north)
        quads = [
            (west, south, mx, my),
            (mx, south, east, my),
            (west, my, mx, north),
            (mx, my, east, north),
        ]
        merged: List[Dict] = []
        for (w, s, e, n) in quads:
            part = await _fetch_bbox_recursive(
                client,
                level=level,
                west=w, south=s, east=e, north=n,
                domain=domain, size=size,
                depth=depth + 1, max_depth=max_depth,
            )
            feats = (
                part.get("response", {})
                .get("result", {})
                .get("featureCollection", {})
                .get("features", [])
            )
            merged.extend(feats)

        return _wrap_ok({"type": "FeatureCollection", "features": merged})

    # 그 외 에러는 그대로 전달
    return payload


# -------------------------------------------------------------------
# Routes
# -------------------------------------------------------------------
@router.get("/bounds")
async def bounds(
    west: float,
    south: float,
    east: float,
    north: float,
    level: str = Query(..., pattern="^(sido|sigg|emd)$"),
    size: int = 2000,
    # 디버그용: 쿼리스트링으로 도메인 덮어쓰기 (없으면 .env 사용)
    domain: str | None = None,
):
    """
    VWorld 2D 행정경계 프록시.
    - bbox가 너무 크면 자동 분할해 합쳐서 반환
    - 응답은 프론트가 기대하는 래핑(response.result.featureCollection.features)으로 맞춤
    """
    if not VWORLD_DATA_KEY:
        raise HTTPException(500, "VWORLD_DATA_KEY not set")

    if not all(_is_num(v) for v in [west, south, east, north]):
        raise HTTPException(400, "Invalid bbox")

    domain = (domain or VWORLD_DOMAIN).strip()
    if not domain:
        raise HTTPException(400, "Invalid domain")

    # size 클램프
    size = max(1, min(int(size or 1000), MAX_SIZE))

    west, south, east, north = _normalize_bbox(west, south, east, north)

    async with httpx.AsyncClient(timeout=20) as client:
        payload = await _fetch_bbox_recursive(
            client,
            level=level,
            west=west,
            south=south,
            east=east,
            north=north,
            domain=domain,
            size=size,
            max_depth=4,
        )

    # 로그 출력(최종)
    status = (payload.get("response") or {}).get("status")
    if status == "OK":
        feats = (
            payload.get("response", {})
            .get("result", {})
            .get("featureCollection", {})
            .get("features", [])
        )
        print(f"[VWORLD][final] OK features={len(feats)}")
    else:
        print(f"[VWORLD][final] ERROR -> {payload.get('response', {}).get('error')}")

    return JSONResponse(payload)


@router.get("/search")
async def search(
    query: str,
    type: str = Query("address", pattern="^(address|place)$"),
    size: int = 1,
    domain: str | None = None,
):
    """
    VWorld 검색 프록시 (주소/POI).
    """
    if not VWORLD_SEARCH_KEY:
        raise HTTPException(500, "VWORLD_SEARCH_KEY not set")

    domain = (domain or VWORLD_DOMAIN).strip()
    if not domain:
        raise HTTPException(400, "Invalid domain")

    size = max(1, min(int(size or 1), 10))  # 검색은 너무 크게 할 필요 없음

    params = {
        "service": "search",
        "request": "search",
        "version": "2.0",
        "query": query,
        "size": str(size),
        "format": "json",
        "type": type,
        "key": VWORLD_SEARCH_KEY,
        "domain": domain,
    }
    print(
        f"[VWORLD][search] → type={type} q='{query}' size={size} "
        f"domain={domain} key=****{VWORLD_SEARCH_KEY[-4:]}"
    )

    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.get(ENDPOINT_SEARCH, params=params)

    try:
        payload = r.json()
    except Exception:
        raise HTTPException(502, "Invalid VWorld response")

    status = (payload.get("response") or {}).get("status")
    if status != "OK":
        err = (payload.get("response") or {}).get("error")
        print(f"[VWORLD][search] ◁ status={status} err={err}")
    else:
        items = (payload.get("response", {}).get("result", {}) or {}).get("items", []) or []
        print(f"[VWORLD][search] ◁ OK items={len(items)}")

    return JSONResponse(payload)
