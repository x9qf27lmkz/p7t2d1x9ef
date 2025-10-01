from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# 라우터 임포트 (우리가 만든 /geo)
from app.routers import geo

app = FastAPI(title="HomeSweetHome Public Viewer API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우터 등록
app.include_router(geo.router)

# 헬스체크
@app.get("/health")
def health():
    return {"ok": True}
