# app/db/db_connection.py
import os
from sqlalchemy import create_engine, text, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession

from dotenv import load_dotenv
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")            # async (FastAPI)
SYNC_DATABASE_URL = os.getenv("SYNC_DATABASE_URL")  # sync (scripts/alembic)

# ---- async 엔진 (웹서버에서만 사용) ----
async_engine = None
AsyncSessionLocal = None
if DATABASE_URL:
    async_engine = create_async_engine(
        DATABASE_URL,
        echo=False,
        future=True,
        pool_pre_ping=True,
    )
    # async에서도 search_path 고정하고 싶다면 아래처럼 이벤트를 걸 수 있음
    @event.listens_for(async_engine.sync_engine, "connect")
    def _set_search_path_async(dbapi_conn, conn_record):
        with dbapi_conn.cursor() as cur:
            cur.execute("SET search_path TO public")

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

# ---- sync 엔진 (FastAPI 내부 동기 쿼리/스크립트/알렘빅) ----
if not SYNC_DATABASE_URL:
    raise RuntimeError("SYNC_DATABASE_URL is not set. Check your .env.")

sync_engine = create_engine(
    SYNC_DATABASE_URL,
    echo=False,
    future=True,
    pool_pre_ping=True,
)

# 접속 시 search_path 고정
@event.listens_for(sync_engine, "connect")
def _set_search_path_sync(dbapi_conn, conn_record):
    with dbapi_conn.cursor() as cur:
        cur.execute("SET search_path TO public")

SessionLocal = sessionmaker(bind=sync_engine, autocommit=False, autoflush=False)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
