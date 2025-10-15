# alembic/env.py
import os, sys
from logging.config import fileConfig
from alembic import context

# 프로젝트 루트(backend) 경로 추가
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# .env 읽기
from dotenv import load_dotenv
load_dotenv()

# Alembic Config 객체
config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# ✅ 우리의 Base / 모델 로드 (database.py가 아님!)
from app.db.base import Base  # 모든 모델 import는 base.py 안에서 관리
import app.models.apartment   # noqa: F401
import app.models.trade       # noqa: F401
# 필요시 다른 모델도 import
# import app.models.rental_contract  # noqa: F401
# import app.models.household_status  # noqa: F401
# import app.models.unit_type  # noqa: F401
# import app.models.sale_record  # noqa: F401

target_metadata = Base.metadata

# ---- 동기 URL 강제 (async -> sync 변환) ----
db_url = os.getenv("SYNC_DATABASE_URL") or os.getenv("DATABASE_URL") or ""
if db_url.startswith("postgresql+asyncpg"):
    db_url = db_url.replace("postgresql+asyncpg", "postgresql")
config.set_main_option("sqlalchemy.url", db_url)


def run_migrations_offline():
    """오프라인 모드 실행 (SQL 출력 전용)"""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    """온라인 모드 실행 (DB 연결)"""
    from sqlalchemy import engine_from_config, pool
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
