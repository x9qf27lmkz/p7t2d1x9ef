from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql as psql

# revision identifiers
revision: str = "bbaf1bce807c"
down_revision: Union[str, None] = "853b41ce4cc5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Recreate sale table with full API columns."""
    # 안전하게: 있으면 삭제
    op.execute("DROP TABLE IF EXISTS sale CASCADE;")

    op.create_table(
        "sale",
        sa.Column("id", sa.BigInteger(), primary_key=True),

        # 원본 JSON
        sa.Column("raw", psql.JSONB, nullable=False),

        # 핵심 파생값
        sa.Column("contract_date", sa.Date(), index=True),
        sa.Column("price_krw", sa.BigInteger()),
        sa.Column("area_m2", sa.Numeric(10, 2)),
        sa.Column("gu_key", sa.Text(), index=True),
        sa.Column("dong_key", sa.Text(), index=True),
        sa.Column("name_key", sa.Text(), index=True),
        sa.Column("lot_key", sa.Text(), index=True),
        sa.Column("lat", sa.Numeric(10, 7)),
        sa.Column("lng", sa.Numeric(10, 7)),

        # API 원문 주요 필드(필요분 확장)
        sa.Column("cgg_nm", sa.Text()),
        sa.Column("stdg_nm", sa.Text()),
        sa.Column("bldg_nm", sa.Text()),
        sa.Column("bldg_dtl_nm", sa.Text()),
        sa.Column("plat_plc", sa.Text()),
        sa.Column("road_nm", sa.Text()),
        sa.Column("bonbun", sa.Text()),
        sa.Column("bubun", sa.Text()),
        sa.Column("floor", sa.Text()),
        sa.Column("arch_area", sa.Numeric(10, 2)),
        sa.Column("deal_amt", sa.BigInteger()),
        sa.Column("deal_day", sa.Date()),
        sa.Column("thing_amt", sa.BigInteger()),
        sa.Column("sum_amt", sa.BigInteger()),
        sa.Column("mv_cnt", sa.Integer()),
        sa.Column("rent_area", sa.Numeric(10, 2)),
        sa.Column("use_apr_day", sa.Text()),
        sa.Column("wgs84_x", sa.Numeric(10, 7)),
        sa.Column("wgs84_y", sa.Numeric(10, 7)),

        # 메타
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  server_default=sa.text("CURRENT_TIMESTAMP"),
                  onupdate=sa.text("CURRENT_TIMESTAMP")),
    )


def downgrade() -> None:
    """Drop sale table (idempotent)."""
    # 테이블이 없어도 에러가 안 나게 IF EXISTS 사용
    op.execute("DROP TABLE IF EXISTS sale CASCADE;")
