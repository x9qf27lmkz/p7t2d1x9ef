from fastapi import APIRouter, Query
from app.services.kakao_local import address_to_coord, coord2region, pick_lawd

router = APIRouter(prefix="/geo", tags=["geo"])

@router.get("/address")
async def geo_address(q: str = Query(..., description="주소 검색어"), size: int = 5):
    data = await address_to_coord(q, size=size)
    return {"count": len(data), "data": data, "source": "kakao.address"}

@router.get("/lawd")
async def geo_lawd(x: float = Query(...), y: float = Query(...)):
    docs = await coord2region(x, y)
    code10, lawd = pick_lawd(docs)
    return {"data": {"x": x, "y": y, "code10": code10, "lawd_cd": lawd}, "source": "kakao.coord2region"}
