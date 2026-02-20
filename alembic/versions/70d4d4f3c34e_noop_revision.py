"""noop revision

Revision ID: 70d4d4f3c34e
Revises: 7d3405968bc2
Create Date: 2026-02-20 18:24:28.635763

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '70d4d4f3c34e'
down_revision: Union[str, Sequence[str], None] = '7d3405968bc2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
