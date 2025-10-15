from fastapi import APIRouter
from app.core.settings import settings
import httpx

router = APIRouter(prefix="/health", tags=["health"])

@router.get("/kakao")
async def health_kakao():
    try:
        async with httpx.AsyncClient(timeout=5.0) as c:
            r = await c.get(
                "https://dapi.kakao.com/v2/local/search/address.json",
                headers={"Authorization": f"KakaoAK {settings.KAKAO_REST_API_KEY}"},
                params={"query": "서울특별시"},
            )
            ok = 200 <= r.status_code < 400
            return {"ok": ok, "status": r.status_code}
    except Exception as e:
        return {"ok": False, "error": str(e)}
