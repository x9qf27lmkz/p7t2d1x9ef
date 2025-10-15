from fastapi import APIRouter, Query
from sqlalchemy import text
from app.db.database import SessionLocal

router = APIRouter(prefix="/api/complex", tags=["complex"])

@router.get("/summary")
def get_summary(gu: str = Query(..., description="예: 노원구")):
    sql = text(
        """
        SELECT
          complex_name AS name,
          lat,
          lng,
          pyeong,
          avg_sale_price_32p   AS "salePrice",
          avg_jeonse_price_32p AS "jeonsePrice"
        FROM mv_latest_avg_prices_3m
        WHERE gu = :gu
        ORDER BY name
        """
    )
    with SessionLocal() as s:
        result = s.execute(sql, {"gu": gu}).mappings().all()
        return [dict(r) for r in result]
