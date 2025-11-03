# backend/app/api/aptinfo_basic.py
from __future__ import annotations
from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel
from sqlalchemy import text
from app.db.db_connection import SessionLocal
from typing import Optional
from datetime import date  # ← date 타입 필요

router = APIRouter(prefix="/api/aptinfo", tags=["aptinfo-basic"])

class AptBasic(BaseModel):
    apt_cd: Optional[str] = None
    apt_nm: Optional[str] = None
    apt_rdn_addr: Optional[str] = None

    # 🔁 whol_dong_cnt로 통일 (SQL과 맞춤)
    whol_dong_cnt: Optional[int] = None

    tnohsh: Optional[int] = None

    # 🔁 date로 받도록 수정 (원래 str이었던 부분)
    use_aprv_ymd: Optional[date] = None

    lat: Optional[float] = None
    lng: Optional[float] = None

@router.get("/basic", response_model=AptBasic)
def get_basic(
    apt_cd: str = Query(..., description="단지코드")
):
    """
    단지의 정적/기초 정보만 반환.
    - 이름, 주소, 세대수, 동수, 사용승인일, 좌표 등
    - 거래지표/통계/거래량 등은 절대 포함하지 않음
    """

    sql = text("""
        SELECT
            apt_cd,
            apt_nm,
            apt_rdn_addr,
            whol_dong_cnt,
            tnohsh,
            use_aprv_ymd,
            lat,
            lng
        FROM public.aptinfo_summary
        WHERE apt_cd = :apt_cd
        LIMIT 1
    """)

    with SessionLocal() as db:
        row = db.execute(sql, {"apt_cd": apt_cd}).mappings().first()

    if not row:
        raise HTTPException(status_code=404, detail="apt not found")

    # row 는 RowMapping 이라 dict처럼 바로 언팩 가능 (키 이름이 위 모델과 일치하므로)
    return AptBasic(**row)
