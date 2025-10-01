from fastapi import APIRouter, Query
import asyncio
from app.services.molit_client import month_range, fetch_month, normalize

router = APIRouter(prefix="/deals", tags=["deals"])

async def _fetch_range(kind: str, lawd: str, fr: str, to: str):
    tasks = [fetch_month(kind, lawd, ym) for ym in month_range(fr, to)]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    rows=[]
    for r in results:
        if isinstance(r, Exception):  # 월별 실패 스킵
            continue
        items = (r.get("response",{}).get("body",{}).get("items",{}) or {}).get("item", [])
        rows.extend(normalize(kind, items))
    return rows

@router.get("/sale")
async def sale(lawd: str = Query(..., min_length=5, max_length=5),
               date_from: str = Query(..., regex=r"^\d{6}$"),
               date_to: str = Query(..., regex=r"^\d{6}$")):
    data = await _fetch_range("sale", lawd, date_from, date_to)
    return {"count": len(data), "data": data, "source": "MOLIT.AptTrade"}

@router.get("/rent")
async def rent(lawd: str = Query(..., min_length=5, max_length=5),
               date_from: str = Query(..., regex=r"^\d{6}$"),
               date_to: str = Query(..., regex=r"^\d{6}$")):
    data = await _fetch_range("rent", lawd, date_from, date_to)
    return {"count": len(data), "data": data, "source": "MOLIT.AptRent"}
