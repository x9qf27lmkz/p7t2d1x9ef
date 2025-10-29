"""create aptinfo table only

Revision ID: beafedb8bed4
Revises: 1d3f1d8b4a4d
Create Date: 2025-10-18 18:34:34.542407
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "beafedb8bed4"
down_revision: Union[str, None] = "1d3f1d8b4a4d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema — create aptinfo table only."""
    op.create_table(
        "aptinfo",
        sa.Column("apt_cd", sa.Text(), primary_key=True, nullable=False),
        sa.Column("sn", sa.Integer(), nullable=True),
        sa.Column("apt_nm", sa.Text(), nullable=True),
        sa.Column("cmpx_clsf", sa.Text(), nullable=True),
        sa.Column("apt_stdg_addr", sa.Text(), nullable=True),
        sa.Column("apt_rdn_addr", sa.Text(), nullable=True),
        sa.Column("ctpv_addr", sa.Text(), nullable=True),
        sa.Column("sgg_addr", sa.Text(), nullable=True),
        sa.Column("emd_addr", sa.Text(), nullable=True),
        sa.Column("daddr", sa.Text(), nullable=True),
        sa.Column("rdn_addr", sa.Text(), nullable=True),
        sa.Column("road_daddr", sa.Text(), nullable=True),
        sa.Column("telno", sa.Text(), nullable=True),
        sa.Column("fxno", sa.Text(), nullable=True),
        sa.Column("apt_cmpx", sa.Text(), nullable=True),
        sa.Column("apt_atch_file", sa.Text(), nullable=True),
        sa.Column("hh_type", sa.Text(), nullable=True),
        sa.Column("mng_mthd", sa.Text(), nullable=True),
        sa.Column("road_type", sa.Text(), nullable=True),
        sa.Column("mn_mthd", sa.Text(), nullable=True),
        sa.Column("whol_dong_cnt", sa.Integer(), nullable=True),
        sa.Column("tnohsh", sa.Integer(), nullable=True),
        sa.Column("bldr", sa.Text(), nullable=True),
        sa.Column("dvlr", sa.Text(), nullable=True),
        sa.Column("use_aprv_ymd", sa.Date(), nullable=True),
        sa.Column("gfa", sa.Numeric(14, 2), nullable=True),
        sa.Column("rsdt_xuar", sa.Numeric(14, 2), nullable=True),
        sa.Column("mnco_levy_area", sa.Numeric(14, 2), nullable=True),
        sa.Column("xuar_hh_stts60", sa.Numeric(14, 2), nullable=True),
        sa.Column("xuar_hh_stts85", sa.Numeric(14, 2), nullable=True),
        sa.Column("xuar_hh_stts135", sa.Numeric(14, 2), nullable=True),
        sa.Column("xuar_hh_stts136", sa.Numeric(14, 2), nullable=True),
        sa.Column("hmpg", sa.Text(), nullable=True),
        sa.Column("reg_ymd", sa.Date(), nullable=True),
        sa.Column("mdfcn_ymd", sa.Date(), nullable=True),
        sa.Column("epis_mng_no", sa.Text(), nullable=True),
        sa.Column("eps_mng_form", sa.Text(), nullable=True),
        sa.Column("hh_elct_ctrt_mthd", sa.Text(), nullable=True),
        sa.Column("clng_mng_form", sa.Text(), nullable=True),
        sa.Column("bdar", sa.Numeric(14, 2), nullable=True),
        sa.Column("prk_cntom", sa.Integer(), nullable=True),
        sa.Column("se_cd", sa.Text(), nullable=True),
        sa.Column("cmpx_aprv_day", sa.Date(), nullable=True),
        sa.Column("use_yn", sa.Text(), nullable=True),
        sa.Column("mnco_uld_yn", sa.Text(), nullable=True),
        sa.Column("lng", sa.Numeric(10, 7), nullable=True),
        sa.Column("lat", sa.Numeric(10, 7), nullable=True),
        sa.Column("cmpx_apld_day", sa.Date(), nullable=True),
        sa.Column("gu_key", sa.Text(), nullable=True),
        sa.Column("dong_key", sa.Text(), nullable=True),
        sa.Column("name_key", sa.Text(), nullable=True),
        sa.Column("lot_key", sa.Text(), nullable=True),
        sa.Column("raw", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            onupdate=sa.text("now()"),
            nullable=False,
        ),
    )

    # 인덱스 생성
    op.create_index("ix_aptinfo_apt_nm", "aptinfo", ["apt_nm"])
    op.create_index("ix_aptinfo_gu_key", "aptinfo", ["gu_key"])
    op.create_index("ix_aptinfo_dong_key", "aptinfo", ["dong_key"])
    op.create_index("ix_aptinfo_name_key", "aptinfo", ["name_key"])
    op.create_index("ix_aptinfo_lot_key", "aptinfo", ["lot_key"])


def downgrade() -> None:
    """Downgrade schema — drop aptinfo table only."""
    op.drop_index("ix_aptinfo_lot_key", table_name="aptinfo")
    op.drop_index("ix_aptinfo_name_key", table_name="aptinfo")
    op.drop_index("ix_aptinfo_dong_key", table_name="aptinfo")
    op.drop_index("ix_aptinfo_gu_key", table_name="aptinfo")
    op.drop_index("ix_aptinfo_apt_nm", table_name="aptinfo")
    op.drop_table("aptinfo")
