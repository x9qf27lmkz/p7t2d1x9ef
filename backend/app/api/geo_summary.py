# backend/app/api/geo_summary.py
from fastapi import APIRouter, Query, HTTPException
from typing import Literal
from sqlalchemy import text
from app.db.db_connection import SessionLocal

router = APIRouter(prefix="/api/geo-summary", tags=["geo-summary"])

Period = Literal["1w","1m","3m","6m","12m","24m","36m"]
Scope  = Literal["sgg","emd"]

@router.get("")
def geo_summary(
    scope: Scope = Query(..., description="sgg | emd"),
    period: Period = Query(..., description="1w~36m")
):
    tbl = "mv_sgg_stats_long" if scope=="sgg" else "mv_emd_stats_long"
    code_col = "sig_cd" if scope=="sgg" else "emd_cd"

    sql = text(f"""
      SELECT
        {code_col} AS code,
        name,
        period,
        sale_med, rent_med, sale_tx, rent_tx,
        ST_Y(rep_pt) AS lat, ST_X(rep_pt) AS lng
      FROM {tbl}
      WHERE period = :period
      ORDER BY name
    """)

    with SessionLocal() as db:
        rows = db.execute(sql, {"period": period}).mappings().all()
        return list(rows)
