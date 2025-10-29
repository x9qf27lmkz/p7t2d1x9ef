"""widen sale area numerics

Revision ID: c51d72f0729a
Revises: ae514dc40527
Create Date: 2025-10-22 20:32:43.058768

"""
"""widen sale area numerics"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# rev ids
revision: str = "c51d72f0729a"
down_revision: Union[str, None] = "ae514dc40527"  # 현재 head 직전 리비전으로 맞춰주세요
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 면적 컬럼 폭 확장
    op.alter_column("sale", "arch_area", type_=sa.Numeric(14, 3), existing_nullable=True)
    op.alter_column("sale", "land_area", type_=sa.Numeric(14, 3), existing_nullable=True)


def downgrade() -> None:
    # 되돌리기 (필요 시)
    op.alter_column("sale", "arch_area", type_=sa.Numeric(10, 2), existing_nullable=True)
    op.alter_column("sale", "land_area", type_=sa.Numeric(10, 2), existing_nullable=True)
