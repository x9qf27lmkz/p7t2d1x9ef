from fastapi import APIRouter, Query
from app.services.kakao_local import address_to_coord, coord2region, pick_lawd
from fastapi import HTTPException  # 파일 상단 import에 추가

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

@router.get("/address-to-lawd")
async def geo_address_to_lawd(q: str = Query(..., description="주소 검색어")):
    # 1) 주소 -> 좌표
    arr = await address_to_coord(q, size=1)
    if not arr:
        raise HTTPException(status_code=404, detail="address not found")
    item = arr[0]
    x, y = item["x"], item["y"]
    # 2) 좌표 -> 법정동코드
    docs = await coord2region(x, y)
    code10, lawd = pick_lawd(docs)
    if not lawd:
        raise HTTPException(status_code=404, detail="region code not found")
    return {
        "query": q,
        "address_name": item["address_name"],
        "x": x, "y": y,
        "code10": code10,
        "lawd_cd": lawd,
        "source": "kakao.address+coord2region"
    }
