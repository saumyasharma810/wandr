"""create trips table

Revision ID: 8f5442132a14
Revises: 
Create Date: 2026-04-24 02:47:45.218805

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8f5442132a14'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'trips',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('destination', sa.String(50), nullable=False),
        sa.Column('duration', sa.Integer),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('trips')
