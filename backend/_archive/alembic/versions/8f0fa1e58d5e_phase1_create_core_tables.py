"""phase1: create aptinfo/sale/rent"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "8f0fa1e58d5e"
down_revision = "62a3c3f9492d"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "aptinfo",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("raw", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("approval_date", sa.Date(), nullable=True),
        sa.Column("gu_key", sa.Text(), nullable=True),
        sa.Column("dong_key", sa.Text(), nullable=True),
        sa.Column("name_key", sa.Text(), nullable=True),
        sa.Column("lot_key", sa.Text(), nullable=True),
        sa.Column("lat", sa.Numeric(10, 7), nullable=True),
        sa.Column("lng", sa.Numeric(10, 7), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_aptinfo_dong_key", "aptinfo", ["dong_key"], unique=False)
    op.create_index("ix_aptinfo_gu_key", "aptinfo", ["gu_key"], unique=False)
    op.create_index("ix_aptinfo_lot_key", "aptinfo", ["lot_key"], unique=False)
    op.create_index("ix_aptinfo_name_key", "aptinfo", ["name_key"], unique=False)

    op.create_table(
        "sale",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("raw", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("contract_date", sa.Date(), nullable=True),
        sa.Column("price_krw", sa.BigInteger(), nullable=True),
        sa.Column("area_m2", sa.Numeric(10, 2), nullable=True),
        sa.Column("gu_key", sa.Text(), nullable=True),
        sa.Column("dong_key", sa.Text(), nullable=True),
        sa.Column("name_key", sa.Text(), nullable=True),
        sa.Column("lot_key", sa.Text(), nullable=True),
        sa.Column("lat", sa.Numeric(10, 7), nullable=True),
        sa.Column("lng", sa.Numeric(10, 7), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_sale_contract_date", "sale", ["contract_date"], unique=False)
    op.create_index("ix_sale_dong_key", "sale", ["dong_key"], unique=False)
    op.create_index("ix_sale_gu_key", "sale", ["gu_key"], unique=False)
    op.create_index("ix_sale_lot_key", "sale", ["lot_key"], unique=False)
    op.create_index("ix_sale_name_key", "sale", ["name_key"], unique=False)

    op.create_table(
        "rent",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("raw", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("contract_date", sa.Date(), nullable=True),
        sa.Column("deposit_krw", sa.BigInteger(), nullable=True),
        sa.Column("rent_krw", sa.BigInteger(), nullable=True),
        sa.Column("area_m2", sa.Numeric(10, 2), nullable=True),
        sa.Column("gu_key", sa.Text(), nullable=True),
        sa.Column("dong_key", sa.Text(), nullable=True),
        sa.Column("name_key", sa.Text(), nullable=True),
        sa.Column("lot_key", sa.Text(), nullable=True),
        sa.Column("lat", sa.Numeric(10, 7), nullable=True),
        sa.Column("lng", sa.Numeric(10, 7), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_rent_contract_date", "rent", ["contract_date"], unique=False)
    op.create_index("ix_rent_dong_key", "rent", ["dong_key"], unique=False)
    op.create_index("ix_rent_gu_key", "rent", ["gu_key"], unique=False)
    op.create_index("ix_rent_lot_key", "rent", ["lot_key"], unique=False)
    op.create_index("ix_rent_name_key", "rent", ["name_key"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_rent_name_key", table_name="rent")
    op.drop_index("ix_rent_lot_key", table_name="rent")
    op.drop_index("ix_rent_gu_key", table_name="rent")
    op.drop_index("ix_rent_dong_key", table_name="rent")
    op.drop_index("ix_rent_contract_date", table_name="rent")
    op.drop_table("rent")

    op.drop_index("ix_sale_name_key", table_name="sale")
    op.drop_index("ix_sale_lot_key", table_name="sale")
    op.drop_index("ix_sale_gu_key", table_name="sale")
    op.drop_index("ix_sale_dong_key", table_name="sale")
    op.drop_index("ix_sale_contract_date", table_name="sale")
    op.drop_table("sale")

    op.drop_index("ix_aptinfo_name_key", table_name="aptinfo")
    op.drop_index("ix_aptinfo_lot_key", table_name="aptinfo")
    op.drop_index("ix_aptinfo_gu_key", table_name="aptinfo")
    op.drop_index("ix_aptinfo_dong_key", table_name="aptinfo")
    op.drop_table("aptinfo")
