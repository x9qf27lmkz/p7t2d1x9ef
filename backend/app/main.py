# backend/app/main.py
from __future__ import annotations

from contextlib import asynccontextmanager
import os
from typing import List

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.db.db_connection import SessionLocal

# 외부 API 프록시 (routers/)
from app.routers.vworld_proxy import router as vworld_router

# 내부 데이터 API (api/)
from app.api.markers import router as markers_router          # /api/markers
from app.api.summary import router as summary_router          # /api/summary
from app.api.geo_summary import router as geo_summary_router  # /api/geo-summary
from app.api.bounds import router as bounds_router
from app.api.aptinfo_basic import router as aptinfo_basic_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 여기에 추후 배치/캐시 warm-up 등을 넣을 수 있음
    yield


app = FastAPI(
    title="HomeSweetHome Public Viewer API",
    lifespan=lifespan,
)

# ───── CORS ─────
# .env에서 콤마 구분으로 여러 개 지정 가능. 미지정 시 로컬 기본 허용.
def _cors_origins_from_env() -> List[str]:
    raw = os.getenv("HS_API_ALLOWED_ORIGINS", "").strip()
    if raw:
        return [o.strip() for o in raw.split(",") if o.strip()]
    # 기본 로컬 개발 도메인
    return [
        "http://localhost:8081",
        "http://127.0.0.1:8081",
        "http://localhost:19006",  # Expo web(dev) optional
        "http://127.0.0.1:19006",
        "null",  # srcdoc/sandbox 환경에서 발생하는 opaque origin
    ]

ALLOWED_ORIGINS = _cors_origins_from_env()

ALLOW_ALL = os.getenv("HS_API_ALLOW_ALL", "0") == "1"
app.add_middleware(
   CORSMiddleware,
   allow_origins=(["*"] if ALLOW_ALL else ALLOWED_ORIGINS),
   allow_origin_regex=(".*" if ALLOW_ALL else None),
   allow_methods=["*"],
   allow_headers=["*"],
   allow_credentials=False,  # 세션 쿠키 미사용
)

# ───── Health ─────
@app.get("/health")
async def health():
    return {"ok": True}

@app.get("/health/db")
async def health_db():
    try:
        with SessionLocal() as db:
            db.execute(text("SELECT 1"))
        return {"db": True}
    except Exception:
        return {"db": False}

# ───── Routers ─────
# 내부 DB → 프런트 API
app.include_router(markers_router)    # /api/markers
app.include_router(summary_router)    # /api/summary
app.include_router(geo_summary_router) # /api/geo-summary
app.include_router(bounds_router)  # /api/bounds
app.include_router(aptinfo_basic_router)

# 외부 서비스 프록시
app.include_router(vworld_router)

# ───── DEBUG: DB 연결/테이블 존재 확인 ─────
from fastapi import HTTPException
from sqlalchemy import text
from app.db.db_connection import SessionLocal

@app.get("/__debug/db")
def debug_db():
    try:
        with SessionLocal() as s:
            info = s.execute(text("""
                SELECT current_database() AS db,
                       current_user      AS usr,
                       inet_server_addr()::text AS host,
                       inet_server_port()       AS port,
                       version() AS ver
            """)).mappings().one()

            exists = s.execute(text("""
                SELECT EXISTS (
                  SELECT 1
                  FROM information_schema.tables
                  WHERE table_schema='public' AND table_name='aptinfo_summary'
                ) AS ok
            """)).scalar()

            sample = None
            if exists:
                sample = s.execute(text("SELECT 1 FROM public.aptinfo_summary LIMIT 1")).scalar()

            return {"info": dict(info), "aptinfo_summary_exists": bool(exists), "sample": sample}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


import time
@app.middleware("http")
async def log_timing(request, call_next):
    t0 = time.perf_counter()
    resp = await call_next(request)
    dt = (time.perf_counter() - t0) * 1000
    # 쿼리까지 같이 보이면 원인 파악 쉬움
    print(f"[{request.method}] {request.url.path}?{request.query_params} -> {resp.status_code} {dt:.1f}ms")
    return resp
