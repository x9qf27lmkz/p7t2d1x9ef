from logging.config import fileConfig
from alembic import context
import os, sys
from sqlalchemy import create_engine
from sqlalchemy import pool

# env.py 상단의 sys.path 설정을 다음으로 교체
here = os.path.abspath(os.path.dirname(__file__))
backend_dir   = os.path.abspath(os.path.join(here, ".."))      # .../backend
project_root  = os.path.abspath(os.path.join(here, "../.."))   # .../homesweethome
for p in (backend_dir, project_root):
    if p not in sys.path:
        sys.path.append(p)

# 모델 메타데이터
from app.db.orm_registry import Base  # Base.metadata
from app import models  # noqa: F401  (모든 모델 import)

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

def run_migrations_offline():
    url = os.getenv("SYNC_DATABASE_URL")
    if not url:
        raise RuntimeError("SYNC_DATABASE_URL not set")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online():
    url = os.getenv("SYNC_DATABASE_URL")
    if not url:
        raise RuntimeError("SYNC_DATABASE_URL not set")
    connectable = create_engine(url, poolclass=pool.NullPool, future=True)
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata, compare_type=True)
        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
