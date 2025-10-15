# app/db/database.py
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession

# .env 로드 (스크립트 실행 시에도 보장)
from dotenv import load_dotenv
load_dotenv()

# 환경변수
DATABASE_URL = os.getenv("DATABASE_URL")            # async (FastAPI)
SYNC_DATABASE_URL = os.getenv("SYNC_DATABASE_URL")  # sync (scripts/alembic)

# ---- async 엔진 (웹서버에서만 사용) ----
async_engine = None
AsyncSessionLocal = None
if DATABASE_URL:
    async_engine = create_async_engine(DATABASE_URL, echo=False, future=True)
    AsyncSessionLocal = sessionmaker(
        bind=async_engine,
        autocommit=False,
        autoflush=False,
        class_=AsyncSession,
    )

async def get_async_db():
    if AsyncSessionLocal is None:
        raise RuntimeError("Async engine not initialized (DATABASE_URL missing).")
    async with AsyncSessionLocal() as session:
        yield session

# ---- sync 엔진 (스크립트/알레믹에서 사용) ----
if not SYNC_DATABASE_URL:
    raise RuntimeError("SYNC_DATABASE_URL is not set. Check your .env.")

sync_engine = create_engine(SYNC_DATABASE_URL, echo=False, future=True)
SessionLocal = sessionmaker(bind=sync_engine, autocommit=False, autoflush=False)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
