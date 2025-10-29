# backend/app/api/markers.py
from __future__ import annotations

from typing import Optional, List, Literal
from fastapi import APIRouter, Query
from sqlalchemy import text
from app.db.db_connection import SessionLocal
import math

router = APIRouter(prefix="/api/markers", tags=["markers"])

# 선택 가능한 기간 토큰
Period = Literal["1w", "1m", "3m", "6m", "12m", "24m", "36m"]
_PERIODS: List[str] = ["1w", "1m", "3m", "6m", "12m", "24m", "36m"]


def _fallback_order(req: Optional[Period]) -> List[str]:
    order = list(_PERIODS)
    if req in order:
        order.remove(req)
        order.insert(0, req)
    return order


def _safe_float(v) -> float:
    if v is None:
        return 0.0
    try:
        f = float(v)
        if math.isnan(f) or math.isinf(f):
            return 0.0
        return f
    except Exception:
        return 0.0


@router.get("")
def list_markers(
    north: float = Query(..., description="BBOX 북"),
    south: float = Query(..., description="BBOX 남"),
    east:  float = Query(..., description="BBOX 동"),
    west:  float = Query(..., description="BBOX 서"),
    q: Optional[str] = Query(None, description="단지명 부분검색(apt_nm ILIKE)"),
    limit: int = Query(2000, ge=1, le=5000),
    offset: int = Query(0, ge=0),
    period: Optional[Period] = Query(None, description="카드 표시 기간 (1w~36m)"),
):
    """
    BBOX 내 단지들의 '정보카드' 데이터(좌표 + 매매/전세 중위가 + 매매/전세 거래량)를 반환.
    - 출처: public.aptinfo_summary (좌표/요약치가 함께 들어있는 요약 테이블)
    - 금액 컬럼은 억 단위 저장 가정, 거래량은 건수
    """
    cols = """
        apt_cd, apt_nm, lat, lng,
        sale84_med_1w,  sale84_med_1m,  sale84_med_3m,  sale84_med_6m,  sale84_med_12m,  sale84_med_24m,  sale84_med_36m,
        rent84_med_1w,  rent84_med_1m,  rent84_med_3m,  rent84_med_6m,  rent84_med_12m,  rent84_med_24m,  rent84_med_36m,
        sale_tx_cnt_1w, sale_tx_cnt_1m, sale_tx_cnt_3m, sale_tx_cnt_6m, sale_tx_cnt_12m, sale_tx_cnt_24m, sale_tx_cnt_36m,
        rent_tx_cnt_1w, rent_tx_cnt_1m, rent_tx_cnt_3m, rent_tx_cnt_6m, rent_tx_cnt_12m, rent_tx_cnt_24m, rent_tx_cnt_36m
     """

    wheres = [
        "lat IS NOT NULL",
        "lng IS NOT NULL",
        "lat BETWEEN :south AND :north",
        "lng BETWEEN :west  AND :east",
    ]
    params = dict(north=north, south=south, east=east, west=west, limit=limit, offset=offset)

    if q:
        wheres.append("apt_nm ILIKE :q")
        params["q"] = f"%{q}%"

    sql = text(f"""
        SELECT {cols}
        FROM public.aptinfo_summary   -- ★ 스키마 명시
        WHERE {" AND ".join(wheres)}
        ORDER BY apt_cd
        LIMIT :limit OFFSET :offset
    """)

    with SessionLocal() as db:
        rows = db.execute(sql, params).mappings().all()

    order = _fallback_order(period)

    def pick(prefix: str, r) -> float:
        for p in order:
            v = r.get(f"{prefix}_{p}")
            f = _safe_float(v)
            if f != 0.0:
                return f
        return 0.0

    out = []
    for r in rows:
        lat = _safe_float(r.get("lat"))
        lng = _safe_float(r.get("lng"))
        out.append({
            "id": str(r["apt_cd"]),
            "name": r.get("apt_nm") or "",
            "lat": lat,
            "lng": lng,
            "sale_price": pick("sale84_med", r),   # 억 단위
            "rent_price": pick("rent84_med", r),   # 억 단위
            "sale_tx": pick("sale_tx_cnt", r),  # 건수
            "rent_tx": pick("rent_tx_cnt", r),  # 건수
        })

    return out
