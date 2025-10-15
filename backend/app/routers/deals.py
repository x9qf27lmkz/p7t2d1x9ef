from fastapi import APIRouter, Query
import asyncio
from app.core.settings import settings
from app.services.molit_client import month_range, yyyymm_recent, fetch_month_sale, normalize_sale

router = APIRouter(prefix="/deals", tags=["deals"])

async def _fetch_range(lawd: str, fr: str, to: str):
    months = month_range(fr, to)
    tasks = [fetch_month_sale(settings.MOLIT_SERVICE_KEY, lawd, ym) for ym in months]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    rows, errors = [], []
    for r in results:
        if isinstance(r, Exception):
            errors.append({"status": 0, "reason": "python", "detail": str(r)}); continue
        if r.get("error"):
            errors.append(r["error"]); continue
        items = (r.get("response",{}).get("body",{}).get("items",{}) or {}).get("item", [])
        rows.extend(normalize_sale(items))
    return rows, errors

@router.get("/sale")
async def sale(lawd: str = Query(..., min_length=5, max_length=5),
               date_from: str = Query(..., regex=r"^\d{6}$"),
               date_to: str = Query(..., regex=r"^\d{6}$")):
    data, errs = await _fetch_range(lawd, date_from, date_to)
    return {"count": len(data), "data": data, "note": "일부 월 누락 가능" if errs else None}

@router.get("/sale/recent")
async def sale_recent(lawd: str = Query(..., min_length=5, max_length=5),
                      months: int = 3):
    fr, to = yyyymm_recent(months)
    data, errs = await _fetch_range(lawd, fr, to)
    return {"range": {"from": fr, "to": to}, "count": len(data), "data": data,
            "note": "일부 월 누락 가능" if errs else None}
