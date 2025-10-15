import httpx

BASE_SALE = "https://apis.data.go.kr/1613000/RTMSDataSvcAptTrade/getRTMSDataSvcAptTrade"

def month_range(fr: str, to: str):
    y1,m1 = int(fr[:4]), int(fr[4:]); y2,m2 = int(to[:4]), int(to[4:])
    y,m=y1,m1; out=[]
    while (y<y2) or (y==y2 and m<=m2):
        out.append(f"{y}{m:02d}"); m+=1
        if m>12: y+=1; m=1
    return out

def yyyymm_recent(months: int):
    from datetime import date
    today = date.today()
    y, m = today.year, today.month
    to = f"{y}{m:02d}"
    # months 개월 전의 첫달
    y2, m2 = y, m
    for _ in range(months-1):
        m2 -= 1
        if m2 == 0: y2 -= 1; m2 = 12
    fr = f"{y2}{m2:02d}"
    return fr, to

async def fetch_month_sale(service_key: str, lawd: str, ym: str):
    params = {
        "serviceKey": service_key,
        "LAWD_CD": lawd,
        "DEAL_YMD": ym,
        "_type": "json",
        "numOfRows": "9999",
        "pageNo": "1",
    }
    try:
        async with httpx.AsyncClient(timeout=15.0) as c:
            r = await c.get(BASE_SALE, params=params)
            r.raise_for_status()
            return r.json()
    except httpx.HTTPStatusError as e:
        return {"error": {"status": e.response.status_code, "reason": "upstream"}}
    except httpx.RequestError as e:
        return {"error": {"status": 0, "reason": "network", "detail": str(e)}}

def normalize_sale(items):
    if isinstance(items, dict): items=[items]
    out=[]
    for it in (items or []):
        price=int(str(it.get("거래금액","0")).replace(",","").strip() or 0)
        out.append({
            "apt": it.get("아파트"),
            "dong": it.get("법정동"),
            "jibun": it.get("지번"),
            "area_m2": float(it.get("전용면적",0)),
            "floor": it.get("층"),
            "deal_date": f'{it.get("년")}-{int(it.get("월")):02d}-{int(it.get("일")):02d}',
            "price": price,
            "build_year": it.get("건축년도"),
        })
    # 최신일자 우선 정렬
    out.sort(key=lambda x: x["deal_date"], reverse=True)
    return out
