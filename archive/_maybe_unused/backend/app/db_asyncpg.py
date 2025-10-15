import asyncpg
from .settings import settings

pool: asyncpg.Pool | None = None

async def init_db():
    global pool
    if pool is None:
        pool = await asyncpg.create_pool(settings.DATABASE_URL, min_size=1, max_size=5)
    return pool  # ← 반환!

async def close_db():
    global pool
    if pool:
        await pool.close()
        pool = None
