import os
import sys
from logging.config import fileConfig

from sqlalchemy import create_engine, pool
from sqlalchemy.orm import sessionmaker

from alembic import context

# ✅ 프로젝트 루트(app 경로)를 PYTHONPATH에 추가
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "app")))

from app.db.database import Base
from app import models  # ✅ 모든 모델을 import 해야 metadata 반영됨

# ✅ Alembic config object
config = context.config

# ✅ 로깅 설정 (alembic.ini 참고)
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# ✅ 메타데이터 설정
target_metadata = Base.metadata

# ✅ DATABASE_URL 설정 (환경변수 없을 경우 기본 SQLite 경로 사용)
db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "app", "db", "homesweethome.db"))
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{db_path}")

# ✅ 오프라인 모드 마이그레이션 실행
def run_migrations_offline():
    context.configure(
        url=DATABASE_URL,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()

# ✅ 온라인 모드 마이그레이션 실행
def run_migrations_online():
    connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

    engine = create_engine(DATABASE_URL, connect_args=connect_args, poolclass=pool.NullPool)
    with engine.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
            render_as_batch=True  # ✅ SQLite 호환을 위한 핵심 옵션
        )

        with context.begin_transaction():
            context.run_migrations()

# ✅ 실행 분기 처리
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
