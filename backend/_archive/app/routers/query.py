# app/routers/query.py
from fastapi import APIRouter, Query
from sqlalchemy import select, func
from app.db import SessionLocal
from app.models.trade import SeoulTrade

router = APIRouter(prefix="/trades", tags=["trades"])

@router.get("/markers")
def markers(gu: str):
    """대표 좌표(단지/동 기준) 반환"""
    with SessionLocal() as db:
        q = select(
            SeoulTrade.complex, SeoulTrade.dong, func.avg(SeoulTrade.lat), func.avg(SeoulTrade.lng)
        ).where(SeoulTrade.gu == gu).group_by(SeoulTrade.complex, SeoulTrade.dong)
        rows = db.execute(q).all()
    return [{"complex": c, "dong": d, "lat": float(lat), "lng": float(lng)} for c,d,lat,lng in rows if lat and lng]

@router.get("/stats/avg")
def avg_price(gu: str, months: int = 3):
    """최근 N개월 평균가 (단순 예시)"""
    from datetime import date, timedelta
    today = date.today()
    start = date(today.year - (months//12), ((today.month - months) % 12) or 12, 1)
    with SessionLocal() as db:
        q = select(func.avg(SeoulTrade.price_krw)).where(
            SeoulTrade.gu == gu, SeoulTrade.contract_date >= start
        )
        avg_ = db.execute(q).scalar()
    return {"gu": gu, "months": months, "avg_price": int(avg_) if avg_ else None}
