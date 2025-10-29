from alembic import op
import sqlalchemy as sa

revision = "853b41ce4cc5"
down_revision = "4245cdb914ac"
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.alter_column("rent", "deposit_krw", type_=sa.BigInteger())
    op.alter_column("rent", "rent_krw", type_=sa.BigInteger())
    op.alter_column("rent", "grfe_mwon", type_=sa.BigInteger())
    op.alter_column("rent", "rtfe_mwon", type_=sa.BigInteger())
    op.alter_column("rent", "bfr_grfe_mwon", type_=sa.BigInteger())
    op.alter_column("rent", "bfr_rtfe_mwon", type_=sa.BigInteger())

def downgrade() -> None:
    op.alter_column("rent", "deposit_krw", type_=sa.Integer())
    op.alter_column("rent", "rent_krw", type_=sa.Integer())
    op.alter_column("rent", "grfe_mwon", type_=sa.Integer())
    op.alter_column("rent", "rtfe_mwon", type_=sa.Integer())
    op.alter_column("rent", "bfr_grfe_mwon", type_=sa.Integer())
    op.alter_column("rent", "bfr_rtfe_mwon", type_=sa.Integer())
