"""add sale derived keys + coords

Revision ID: ae514dc40527
Revises: 77fa0931ba41
Create Date: 2025-10-22 11:45:04.652845
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "ae514dc40527"
down_revision: Union[str, None] = "77fa0931ba41"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


ADDED_COLUMNS = [
    ("gu_key", sa.Text(), True),
    ("dong_key", sa.Text(), True),
    ("name_key", sa.Text(), True),
    ("lot_key", sa.Text(), True),
    ("lat", sa.Numeric(10, 7), True),
    ("lng", sa.Numeric(10, 7), True),
]

ADDED_INDEXES = [
    ("ix_sale_gu_key", ["gu_key"]),
    ("ix_sale_dong_key", ["dong_key"]),
    ("ix_sale_name_key", ["name_key"]),
    ("ix_sale_lot_key", ["lot_key"]),
]


def upgrade() -> None:
    """Add derived key/coord columns and indexes to sale if missing."""
    bind = op.get_bind()
    insp = sa.inspect(bind)

    if not insp.has_table("sale"):
        raise RuntimeError(
            "Table 'sale' does not exist. Make sure revision 77fa0931ba41 has been applied."
        )

    # 현재 컬럼/인덱스 조회
    existing_cols = {c["name"] for c in insp.get_columns("sale")}
    existing_indexes = {ix["name"] for ix in insp.get_indexes("sale")}

    # 컬럼 추가 (없을 때만)
    for col_name, col_type, nullable in ADDED_COLUMNS:
        if col_name not in existing_cols:
            op.add_column("sale", sa.Column(col_name, col_type, nullable=nullable))

    # 인덱스 추가 (없을 때만)
    for ix_name, cols in ADDED_INDEXES:
        if ix_name not in existing_indexes:
            op.create_index(ix_name, "sale", cols, unique=False)


def downgrade() -> None:
    """Drop only the columns and indexes added by this migration."""
    bind = op.get_bind()
    insp = sa.inspect(bind)

    if not insp.has_table("sale"):
        # 이미 테이블이 없으면 더 할 일 없음
        return

    existing_indexes = {ix["name"] for ix in insp.get_indexes("sale")}
    # 인덱스부터 제거
    for ix_name, _ in ADDED_INDEXES:
        if ix_name in existing_indexes:
            op.drop_index(ix_name, table_name="sale")

    # 컬럼 제거 (존재할 때만)
    existing_cols = {c["name"] for c in insp.get_columns("sale")}
    # 역순으로 드롭(의존 가능성 최소화)
    for col_name, _, _ in reversed(ADDED_COLUMNS):
        if col_name in existing_cols:
            op.drop_column("sale", col_name)
