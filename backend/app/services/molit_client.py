import httpx
from app.core.settings import settings

BASE_SALE = "https://apis.data.go.kr/1613000/RTMSDataSvcAptTrade/getRTMSDataSvcAptTrade"
BASE_RENT = "https://apis.data.go.kr/1613000/RTMSDataSvcAptRent/getRTMSDataSvcAptRent"

def month_range(fr: str, to: str):
    y1, m1 = int(fr[:4]), int(fr[4:])
    y2, m2 = int(to[:4]), int(to[4:])
    y, m = y1, m1
    out=[]
    while (y < y2) or (y==y2 and m<=m2):
        out.append(f"{y}{m:02d}")
        m += 1
        if m>12: y+=1; m=1
    return out

async def fetch_month(kind: str, lawd: str, ym: str):
    base = BASE_SALE if kind=="sale" else BASE_RENT
    params = {
        "serviceKey": settings.MOLIT_SERVICE_KEY,
        "LAWD_CD": lawd,
        "DEAL_YMD": ym,
        "_type": "json",
        "numOfRows": "9999",
        "pageNo": "1",
    }
    async with httpx.AsyncClient(timeout=20.0) as c:
        r = await c.get(base, params=params)
        r.raise_for_status()
        return r.json()

def normalize(kind: str, items):
    if isinstance(items, dict):
        items = [items]
    out=[]
    for it in (items or []):
        if kind=="sale":
            price = int(str(it.get("거래금액","0")).replace(",","").strip() or 0)
            out.append({
                "type":"sale",
                "apt": it.get("아파트"), "dong": it.get("법정동"), "jibun": it.get("지번"),
                "area_m2": float(it.get("전용면적",0)), "floor": it.get("층"),
                "deal_date": f'{it.get("년")}-{int(it.get("월")):02d}-{int(it.get("일")):02d}',
                "price": price, "build_year": it.get("건축년도"),
            })
        else:
            deposit = int(str(it.get("보증금액","0")).replace(",","").strip() or 0)
            monthly = int(str(it.get("월세금액","0")).replace(",","").strip() or 0)
            out.append({
                "type":"rent",
                "apt": it.get("아파트"), "dong": it.get("법정동"), "jibun": it.get("지번"),
                "area_m2": float(it.get("전용면적",0)), "floor": it.get("층"),
                "deal_date": f'{it.get("년")}-{int(it.get("월")):02d}-{int(it.get("일")):02d}',
                "deposit": deposit, "monthly": monthly, "rent_div": it.get("전월세구분"),
            })
    return out
