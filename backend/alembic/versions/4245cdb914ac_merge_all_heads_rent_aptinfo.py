"""merge all heads (rent + aptinfo)

Revision ID: 4245cdb914ac
Revises: <자동생성값>, beafedb8bed4
Create Date: 2025-10-18 21:04:21.322802

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4245cdb914ac'
down_revision: Union[str, None] = ('<자동생성값>', 'beafedb8bed4')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
