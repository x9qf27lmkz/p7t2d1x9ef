"""phase2: add year_approved meta column"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "1d3f1d8b4a4d"
down_revision = "8f0fa1e58d5e"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("aptinfo", sa.Column("year_approved", sa.Integer(), nullable=True))
    op.execute(
        """
        UPDATE aptinfo
        SET year_approved = EXTRACT(YEAR FROM approval_date)::int
        WHERE approval_date IS NOT NULL
        """
    )


def downgrade() -> None:
    op.drop_column("aptinfo", "year_approved")
