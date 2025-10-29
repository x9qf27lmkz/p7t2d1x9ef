"""recreate sale with full api columns (model-aligned)"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql as psql

# revision identifiers, used by Alembic.
revision: str = "77fa0931ba41"          # ← 당신의 파일 revision 값 유지/수정
down_revision: Union[str, None] = "bbaf1bce807c"  # ← 이전 리비전으로 설정
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)

    # 존재하면 깔끔히 제거(개발/재생성 편의)
    if insp.has_table("sale"):
        op.drop_table("sale")

    op.create_table(
        "sale",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("raw", psql.JSONB(astext_type=sa.Text()), nullable=False),

        # 원본 컬럼
        sa.Column("rcpt_yr", sa.Integer(), nullable=True),
        sa.Column("cgg_cd", sa.Integer(), nullable=True),
        sa.Column("cgg_nm", sa.Text(), nullable=True),
        sa.Column("stdg_cd", sa.Integer(), nullable=True),
        sa.Column("stdg_nm", sa.Text(), nullable=True),
        sa.Column("lotno_se", sa.Integer(), nullable=True),
        sa.Column("lotno_se_nm", sa.Text(), nullable=True),
        sa.Column("mno", sa.Text(), nullable=True),
        sa.Column("sno", sa.Text(), nullable=True),
        sa.Column("bldg_nm", sa.Text(), nullable=True),
        sa.Column("ctrt_day", sa.Date(), nullable=True),
        sa.Column("thing_amt", sa.BigInteger(), nullable=True),
        sa.Column("arch_area", sa.Numeric(12, 3), nullable=True),
        sa.Column("land_area", sa.Numeric(12, 3), nullable=True),
        sa.Column("flr", sa.Text(), nullable=True),
        sa.Column("rght_se", sa.Text(), nullable=True),
        sa.Column("rtrcn_day", sa.Text(), nullable=True),
        sa.Column("arch_yr", sa.Integer(), nullable=True),
        sa.Column("bldg_usg", sa.Text(), nullable=True),
        sa.Column("dclr_se", sa.Text(), nullable=True),
        sa.Column("opbiz_restagnt_sgg_nm", sa.Text(), nullable=True),

        # 파생 키/좌표
        sa.Column("gu_key", sa.Text(), nullable=True),
        sa.Column("dong_key", sa.Text(), nullable=True),
        sa.Column("name_key", sa.Text(), nullable=True),
        sa.Column("lot_key", sa.Text(), nullable=True),
        sa.Column("lat", sa.Numeric(10, 7), nullable=True),
        sa.Column("lng", sa.Numeric(10, 7), nullable=True),

        # 메타
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    # 인덱스
    op.create_index(op.f("ix_sale_ctrt_day"), "sale", ["ctrt_day"], unique=False)
    op.create_index(op.f("ix_sale_gu_key"), "sale", ["gu_key"], unique=False)
    op.create_index(op.f("ix_sale_dong_key"), "sale", ["dong_key"], unique=False)
    op.create_index(op.f("ix_sale_name_key"), "sale", ["name_key"], unique=False)
    op.create_index(op.f("ix_sale_lot_key"), "sale", ["lot_key"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_sale_lot_key"), table_name="sale")
    op.drop_index(op.f("ix_sale_name_key"), table_name="sale")
    op.drop_index(op.f("ix_sale_dong_key"), table_name="sale")
    op.drop_index(op.f("ix_sale_gu_key"), table_name="sale")
    op.drop_index(op.f("ix_sale_ctrt_day"), table_name="sale")
    op.drop_table("sale")
