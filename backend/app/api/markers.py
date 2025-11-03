# backend/app/api/markers.py
from __future__ import annotations
from typing import Optional, List
from fastapi import APIRouter, Query
from pydantic import BaseModel
from sqlalchemy import text
from app.db.db_connection import SessionLocal

router = APIRouter(prefix="/api/markers", tags=["markers"])


# ───────────────────────────────
# 📌 Pydantic 모델 (응답 스키마)
# ───────────────────────────────
class MarkerItem(BaseModel):
    apt_cd: str
    apt_name: str
    lat: float
    lng: float
    score_label: Optional[str] = None  # "활발", "과열", "정체" 등 (현재는 None)


# ───────────────────────────────
# 📌 GET /api/markers
# ───────────────────────────────
@router.get("", response_model=List[MarkerItem])
def list_markers(
    min_lat: float = Query(..., description="BBOX 최소 위도 (남쪽 경계)"),
    max_lat: float = Query(..., description="BBOX 최대 위도 (북쪽 경계)"),
    min_lng: float = Query(..., description="BBOX 최소 경도 (서쪽 경계)"),
    max_lng: float = Query(..., description="BBOX 최대 경도 (동쪽 경계)"),
    limit: int = Query(1000, ge=1, le=5000, description="최대 반환 단지 수"),
    offset: int = Query(0, ge=0),
):
    """
    지도 뷰포트(BBOX) 안의 단지 마커 좌표를 반환합니다.
    - 출처: public.aptinfo_summary
    - 응답은 단지의 최소정보(코드, 이름, 좌표, 라벨)만 포함합니다.
    """

    sql = text("""
        SELECT
            apt_cd,
            apt_nm,
            lat,
            lng
        FROM public.aptinfo_summary
        WHERE lat BETWEEN :min_lat AND :max_lat
          AND lng BETWEEN :min_lng AND :max_lng
          AND lat IS NOT NULL
          AND lng IS NOT NULL
        ORDER BY apt_cd
        LIMIT :limit OFFSET :offset
    """)

    params = dict(
        min_lat=min_lat, max_lat=max_lat,
        min_lng=min_lng, max_lng=max_lng,
        limit=limit, offset=offset
    )

    with SessionLocal() as db:
        rows = db.execute(sql, params).mappings().all()

    return [
        MarkerItem(
            apt_cd=str(r["apt_cd"]),
            apt_name=r.get("apt_nm") or "",
            lat=float(r["lat"]),
            lng=float(r["lng"]),
            score_label=None,  # 현재는 None, 향후 고도화된 라벨 계산 후 대체
        )
        for r in rows
    ]
