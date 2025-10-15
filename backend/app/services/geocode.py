# app/services/geocode.py
import os, httpx
KAKAO_KEY = os.getenv("KAKAO_REST_API_KEY")

async def geocode(addr: str):
    headers = {"Authorization": f"KakaoAK {KAKAO_KEY}"}
    url = "https://dapi.kakao.com/v2/local/search/address.json"
    async with httpx.AsyncClient(timeout=10.0) as client:
        r = await client.get(url, params={"query": addr}, headers=headers)
    j = r.json()
    docs = j.get("documents", [])
    if not docs: return None, None
    x, y = docs[0]["x"], docs[0]["y"]
    return float(y), float(x)  # lat, lng
