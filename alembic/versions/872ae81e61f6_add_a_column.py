"""Add a column

Revision ID: 872ae81e61f6
Revises: 8f5442132a14
Create Date: 2026-04-24 03:05:31.848175

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '872ae81e61f6'
down_revision: Union[str, Sequence[str], None] = '8f5442132a14'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('trips', sa.Column('start_date', sa.DateTime))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('trips', 'start_date')
