import httpx
from fastapi import HTTPException
from app.core.settings import settings

BASE = "https://dapi.kakao.com"
HEADERS = {"Authorization": f"KakaoAK {settings.KAKAO_REST_API_KEY}"}

class KakaoLocalError(HTTPException): ...

def _check(r: httpx.Response):
    if r.status_code == 200: return
    try:
        j = r.json(); code, msg = j.get("code"), j.get("msg")
    except Exception:
        code, msg = None, r.text
    raise KakaoLocalError(status_code=r.status_code, detail={"code": code, "msg": msg})

async def address_to_coord(query: str, size: int = 5):
    url = f"{BASE}/v2/local/search/address.json"
    async with httpx.AsyncClient(timeout=10.0, headers=HEADERS) as c:
        r = await c.get(url, params={"query": query, "size": size}); _check(r)
    docs = r.json().get("documents", [])
    return [{
        "address_name": d.get("address_name"),
        "x": float(d.get("x")), "y": float(d.get("y")),
        "b_code": (d.get("address") or {}).get("b_code"),
    } for d in docs]

async def coord2region(x: float, y: float):
    url = f"{BASE}/v2/local/geo/coord2regioncode.json"
    async with httpx.AsyncClient(timeout=10.0, headers=HEADERS) as c:
        r = await c.get(url, params={"x": x, "y": y}); _check(r)
    return r.json().get("documents", [])

def pick_lawd(docs: list[dict]) -> tuple[str | None, str | None]:
    # 법정동(B) code(10자리) 앞 5자리 = LAWD_CD
    for d in docs:
        if d.get("region_type") == "B":
            code10 = d.get("code"); return code10, (code10[:5] if code10 else None)
    if docs:
        code10 = docs[0].get("code"); return code10, (code10[:5] if code10 else None)
    return None, None
