# app/main.py
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from app.api import complex_summary

# SQLAlchemy 세션
from app.db.database import SessionLocal

# Routers
from app.routers.map import router as map_router
from app.routers.geo import router as geo_router
from app.routers.deals import router as deals_router
from app.routers.seoul_trade import router as seoul_trade_router
from app.routers.query import router as query_router

# --- lifespan: 별도 비동기 풀 초기화 없음 (Alembic/SQLAlchemy만 사용) ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 필요 시 여기서 캐시/스케줄러 등 초기화
    yield
    # 종료 훅도 현재는 없음

app = FastAPI(
    title="HomeSweetHome Public Viewer API",
    lifespan=lifespan,
)

# CORS (개발 중 편의 — 배포 시 도메인 제한 권장)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- 헬스체크 ---
@app.get("/health")
async def health():
    return {"ok": True}

@app.get("/health/db")
async def health_db():
    # SQLAlchemy로 간단 DB 체크
    try:
        with SessionLocal() as db:
            db.execute(text("SELECT 1"))
        return {"db": True}
    except Exception:
        return {"db": False}

# --- 라우터 등록 (한 번씩만) ---
app.include_router(map_router)
app.include_router(geo_router)
app.include_router(deals_router)
app.include_router(seoul_trade_router)
app.include_router(query_router)
app.include_router(complex_summary.router)
