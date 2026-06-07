"""add chatmessage table

Revision ID: 69958cd38490
Revises: c8c2d2d56f0d
Create Date: 2026-06-07 21:40:29.710067

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '69958cd38490'
down_revision: Union[str, Sequence[str], None] = 'c8c2d2d56f0d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('chatmessage',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('conversation_id', sa.Integer(), nullable=False),
    sa.Column('role', sa.String(), nullable=False),
    sa.Column('content', sa.String(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_chatmessage_conversation_id'), 'chatmessage', ['conversation_id'], unique=False)
    op.create_index(op.f('ix_chatmessage_user_id'), 'chatmessage', ['user_id'], unique=False)

def downgrade() -> None:
    op.drop_index(op.f('ix_chatmessage_conversation_id'), table_name='chatmessage')
    op.drop_index(op.f('ix_chatmessage_user_id'), table_name='chatmessage')
    op.drop_table('chatmessage')

