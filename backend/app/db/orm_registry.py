# backend/app/db/orm_registry.py
from __future__ import annotations

from typing import TYPE_CHECKING
from sqlalchemy.orm import declarative_base

# 모든 ORM 모델이 상속할 단일 Base
Base = declarative_base()

# 타입체커만 보라고 넣는 힌트 — 런타임엔 실행되지 않음(순환 방지)
if TYPE_CHECKING:  # pragma: no cover
    from app.models.aptinfo import AptInfo  # noqa: F401
    from app.models.rent import Rent        # noqa: F401
    from app.models.sale import Sale        # noqa: F401

def import_all_models() -> None:
    """
    필요 시 명시적으로 모델 모듈을 로드해 매퍼를 등록.
    - 웹앱 부팅 시 또는 Alembic env에서 호출.
    - 순환 임포트를 피하기 위해 여기서 지연 import.
    """
    import importlib

    for mod in (
        "app.models.aptinfo",
        "app.models.rent",
        "app.models.sale",
    ):
        importlib.import_module(mod)

__all__ = ["Base", "import_all_models"]
