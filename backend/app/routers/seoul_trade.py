# app/routers/seoul_trade.py
import os, math
from fastapi import APIRouter, HTTPException
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
import httpx

from app.db import SessionLocal
from app.models.trade import SeoulTrade
from app.services.normalize import normalize_row

router = APIRouter(prefix="/snapshot", tags=["snapshot"])

SEOUL_KEY = os.getenv("SEOUL_API_KEY")
BASE = "http://openapi.seoul.go.kr:8088"

@router.post("/seoul/trade")
async def snapshot_seoul_trade(year: int, gu: str, start: int = 1, end: int = 1000):
    """연도/구 기준으로 서울시 실거래가를 스냅샷 적재"""
    if not SEOUL_KEY:
        raise HTTPException(500, "SEOUL_API_KEY not configured")

    url = f"{BASE}/{SEOUL_KEY}/json/tbLnOpendataRtmsV/{start}/{end}/{year}/{gu}"
    async with httpx.AsyncClient(timeout=20.0) as client:
        resp = await client.get(url)
    if resp.status_code != 200:
        raise HTTPException(resp.status_code, resp.text)

    data = resp.json().get("tbLnOpendataRtmsV", {})
    result = data.get("RESULT", {})
    if result.get("CODE") != "INFO-000":
        raise HTTPException(502, f"Seoul API error: {result}")

    rows = data.get("row", [])
    if not rows:
        return {"inserted": 0, "message": "no rows"}

    inserted, skipped = 0, 0
    with SessionLocal() as db:
        for r in rows:
            doc = normalize_row(r)
            # PostgreSQL upsert (unique key 기준)
            stmt = pg_insert(SeoulTrade).values(**doc).on_conflict_do_nothing(
                index_elements=["gu","dong","complex","lot_number","area_m2","contract_date","price_krw"]
            )
            res = db.execute(stmt)
            if res.rowcount and res.rowcount > 0:
                inserted += 1
            else:
                skipped += 1
        db.commit()

    return {"inserted": inserted, "skipped": skipped, "count_in_payload": len(rows)}
