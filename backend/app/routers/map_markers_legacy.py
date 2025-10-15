# app/routers/map_markers.py
from fastapi import APIRouter, Query
from sqlalchemy import text
from app.db.database import SessionLocal

router = APIRouter(prefix="/map", tags=["map"])

@router.get("/markers")
def map_markers(
    gu: str | None = Query(None),
    dong: str | None = Query(None),
    only_with_price: bool = Query(False)
):
    base_sql = """
    SELECT apartment_id, apartment_name, gu, dong, lat, lng, price_84, deal_count
    FROM v_apartment_price_84
    """
    conds, params = [], {}
    if gu:
        conds.append("gu = :gu"); params["gu"] = gu
    if dong:
        conds.append("dong = :dong"); params["dong"] = dong
    if only_with_price:
        conds.append("price_84 IS NOT NULL")
    if conds:
        base_sql += " WHERE " + " AND ".join(conds)
    base_sql += " ORDER BY gu, dong, apartment_name"

    with SessionLocal() as db:
        rows = db.execute(text(base_sql), params).all()
        return {"items": [
            {
              "id": r.apartment_id,
              "name": r.apartment_name,
              "gu": r.gu, "dong": r.dong,
              "lat": float(r.lat) if r.lat is not None else None,
              "lng": float(r.lng) if r.lng is not None else None,
              "price_84": int(r.price_84) if r.price_84 is not None else None,
              "deals": int(r.deal_count)
            } for r in rows
        ]}
