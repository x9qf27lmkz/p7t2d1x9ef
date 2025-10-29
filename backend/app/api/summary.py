# backend/app/api/summary.py
from typing import List, Optional, Literal
from fastapi import APIRouter, Depends, Query, HTTPException
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.db_connection import get_db  # 기존 의존성 주입

router = APIRouter(prefix="/api/summary", tags=["summary"])

# 프론트 카드용 최소 스키마
class AptCard(BaseModel):
    id: str
    name: str
    lat: float
    lng: float
    sale_price: float  # 억 단위
    rent_price: float  # 억 단위

# 상세 보기(선택)
class AptDetail(BaseModel):
    apt_cd: str
    apt_nm: Optional[str]
    lat: Optional[float]
    lng: Optional[float]
    sale: dict
    rent: dict

# 기간 토큰
PERIOD = Literal["1w", "1m", "3m", "6m", "12m", "24m", "36m"]
_PERIODS = ["1w", "1m", "3m", "6m", "12m", "24m", "36m"]

def _fallback_order(req: Optional[str]) -> List[str]:
    order = list(_PERIODS)
    if req in order:
        order.remove(req)
        order.insert(0, req)
    return order

@router.get("", response_model=List[AptCard])
def list_cards(
    north: float = Query(...),
    south: float = Query(...),
    east:  float = Query(...),
    west:  float = Query(...),
    period: Optional[PERIOD] = Query(None, description="없으면 1w→1m→3m→… 폴백 순서"),
    limit: int = Query(500, ge=1, le=5000),
    offset:int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """
    bbox 안 단지들의 정보카드 값(매매/전세 중위가, 억 단위)을 반환.
    aptinfo_summary를 직접 조회.
    """
    cols = """
        apt_cd, apt_nm, lat, lng,
        sale84_med_1w, sale84_med_1m, sale84_med_3m, sale84_med_6m, sale84_med_12m, sale84_med_24m, sale84_med_36m,
        rent84_med_1w, rent84_med_1m, rent84_med_3m, rent84_med_6m, rent84_med_12m, rent84_med_24m, rent84_med_36m
    """
    sql = text(f"""
        SELECT {cols}
        FROM aptinfo_summary
        WHERE lat IS NOT NULL AND lng IS NOT NULL
          AND lat BETWEEN :south AND :north
          AND lng BETWEEN :west  AND :east
        ORDER BY apt_cd
        LIMIT :limit OFFSET :offset
    """)
    rows = db.execute(sql, {
        "north": north, "south": south, "east": east, "west": west,
        "limit": limit, "offset": offset
    }).mappings().all()

    order = _fallback_order(period)

    def pick(prefix: str, r) -> float:
        # prefix: 'sale84_med' / 'rent84_med'
        for p in order:
            v = r.get(f"{prefix}_{p}")
            if v is not None:
                return float(v)
        return 0.0

    out: List[AptCard] = []
    for r in rows:
        out.append(AptCard(
            id   = r["apt_cd"],
            name = r.get("apt_nm") or "",
            lat  = float(r["lat"]),
            lng  = float(r["lng"]),
            sale_price = pick("sale84_med", r),  # 억단위로 채워져있다고 가정
            rent_price = pick("rent84_med", r),
        ))
    return out


@router.get("/{apt_cd}", response_model=AptDetail)
def get_detail(apt_cd: str, db: Session = Depends(get_db)):
    """
    단지 하나의 모든 기간별 중위가/거래량을 한 번에 반환 (상세 카드용).
    """
    sql = text("""
      SELECT
        apt_cd, apt_nm, lat, lng,
        sale84_med_1w, sale84_med_1m, sale84_med_3m, sale84_med_6m, sale84_med_12m, sale84_med_24m, sale84_med_36m,
        rent84_med_1w, rent84_med_1m, rent84_med_3m, rent84_med_6m, rent84_med_12m, rent84_med_24m, rent84_med_36m,
        sale_tx_cnt_1w, sale_tx_cnt_1m, sale_tx_cnt_3m, sale_tx_cnt_6m, sale_tx_cnt_12m, sale_tx_cnt_24m, sale_tx_cnt_36m,
        rent_tx_cnt_1w, rent_tx_cnt_1m, rent_tx_cnt_3m, rent_tx_cnt_6m, rent_tx_cnt_12m, rent_tx_cnt_24m, rent_tx_cnt_36m
      FROM aptinfo_summary
      WHERE apt_cd = :apt_cd
      LIMIT 1
    """)
    r = db.execute(sql, {"apt_cd": apt_cd}).mappings().first()
    if not r:
        raise HTTPException(status_code=404, detail="apt not found")

    sale = { f"med_{p}": r.get(f"sale84_med_{p}") for p in _PERIODS }
    sale.update({ f"tx_{p}": r.get(f"sale_tx_cnt_{p}") for p in _PERIODS })
    rent = { f"med_{p}": r.get(f"rent84_med_{p}") for p in _PERIODS }
    rent.update({ f"tx_{p}": r.get(f"rent_tx_cnt_{p}") for p in _PERIODS })

    return AptDetail(
        apt_cd=r["apt_cd"], apt_nm=r.get("apt_nm"),
        lat=(float(r["lat"]) if r["lat"] is not None else None),
        lng=(float(r["lng"]) if r["lng"] is not None else None),
        sale=sale, rent=rent
    )
