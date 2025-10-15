# app/routers/map.py
from typing import Literal, Optional
from fastapi import APIRouter, Query, Response
from sqlalchemy import text
from app.db.database import SessionLocal

router = APIRouter(prefix="/map", tags=["map"])

def label_fmt(mode: str, price_84: Optional[int]) -> str:
    if price_84 is None:
        return "데이터 없음"
    # mode는 확장 여지(전세/매매 동일 라벨 포맷)
    return f"{'매매' if mode == 'sale' else '전세'} {price_84/100_000_000:.1f}억"

@router.get("/markers")
def map_markers(
    response: Response,
    # 지도 BBOX (경도=lng=X, 위도=lat=Y)
    minX: float | None = Query(None),
    minY: float | None = Query(None),
    maxX: float | None = Query(None),
    maxY: float | None = Query(None),
    # 행정동 필터
    gu: str | None = Query(None),
    dong: str | None = Query(None),
    # 가격 없는 단지는 제외?
    only_with_price: bool = Query(False),
    # 라벨 표기를 위해 모드만 받음(현재는 price_84 사용)
    mode: Literal["sale", "jeonse"] = Query("sale"),
    # 안전장치
    limit: int = Query(2000, ge=1, le=10000),
):
    # CDN/프론트 캐싱 힌트 (확대일수록 짧게)
    ttl = 120
    response.headers["Cache-Control"] = f"public, max-age={ttl}, s-maxage={ttl}"

    base_sql = """
    SELECT apartment_id, apartment_name, gu, dong, lat, lng, price_84, deal_count
    FROM v_apartment_price_84
    """
    conds = []
    params: dict[str, object] = {}

    # BBOX 조건 (둘 다 들어오면 우선 BBOX, 없으면 gu/dong)
    if None not in (minX, minY, maxX, maxY):
        conds.append("lng BETWEEN :minX AND :maxX")
        conds.append("lat BETWEEN :minY AND :maxY")
        params.update(dict(minX=minX, maxX=maxX, minY=minY, maxY=maxY))
    else:
        if gu:
            conds.append("gu = :gu"); params["gu"] = gu
        if dong:
            conds.append("dong = :dong"); params["dong"] = dong

    if only_with_price:
        conds.append("price_84 IS NOT NULL")

    sql = base_sql
    if conds:
        sql += " WHERE " + " AND ".join(conds)

    sql += " ORDER BY apartment_id LIMIT :limit"
    params["limit"] = limit

    with SessionLocal() as db:
        rows = db.execute(text(sql), params).all()
        items = []
        for r in rows:
            price_84 = int(r.price_84) if r.price_84 is not None else None
            items.append({
                "id": r.apartment_id,
                "name": r.apartment_name,
                "gu": r.gu,
                "dong": r.dong,
                "lat": float(r.lat) if r.lat is not None else None,
                "lng": float(r.lng) if r.lng is not None else None,
                "price_84": price_84,
                "deals": int(r.deal_count) if r.deal_count is not None else 0,
                "label": label_fmt(mode, price_84),
            })

    return {"items": items, "mode": mode}
