# app/db/__init__.py
from .database import SessionLocal, get_db  # 기존 의존성
from .database import async_engine  # 종료 시 dispose 용

def init_db() -> None:
    # 현재는 미리 초기화할 게 없음 (엔진/세션은 lazy하게 생성)
    return

async def close_db() -> None:
    # 서버 종료 시 커넥션 풀 정리
    try:
        await async_engine.dispose()
    except Exception:
        pass

__all__ = ["SessionLocal", "get_db", "init_db", "close_db"]
