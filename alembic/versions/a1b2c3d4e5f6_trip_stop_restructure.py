"""Trip → Trip + TripStop restructure

Revision ID: a1b2c3d4e5f6
Revises: 69958cd38490
Create Date: 2026-06-26

Data-preserving migration:
1. Create tripstop table (empty).
2. Backfill: one stop per existing trip, copying city/country/vibe/notes/highlight/lowlight/would_return.
3. Drop the now-redundant per-city columns from trip.
4. Add title and ai_summary columns to trip.

downgrade() reverses in the opposite order.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = '69958cd38490'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create tripstop table with a DB-level CASCADE FK to trip.
    op.create_table(
        'tripstop',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('trip_id', sa.Integer(), nullable=False),
        sa.Column('city', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('country', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('arrival_date', sa.Date(), nullable=False),
        sa.Column('departure_date', sa.Date(), nullable=False),
        sa.Column('vibe', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('notes', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column('highlight', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column('lowlight', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column('would_return', sa.Boolean(), nullable=False),
        sa.Column('order', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['trip_id'], ['trip.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_tripstop_trip_id', 'tripstop', ['trip_id'], unique=False)

    # 2. Backfill: one stop row per existing trip.
    #    COALESCE guards against NULLs in columns that were optional in the old schema.
    #    CURRENT_DATE is standard SQL (works on both PostgreSQL and SQLite).
    op.execute("""
        INSERT INTO tripstop
            (trip_id, city, country, arrival_date, departure_date,
             vibe, notes, highlight, lowlight, would_return, "order", created_at)
        SELECT
            id,
            COALESCE(city, ''),
            country,
            COALESCE(start_date, CURRENT_DATE),
            COALESCE(end_date,   CURRENT_DATE),
            COALESCE(vibe, 'neutral'),
            notes,
            highlight,
            lowlight,
            COALESCE(would_return, false),
            0,
            created_at
        FROM trip
    """)

    # 3. Add new trip-level columns and drop the per-city ones.
    op.add_column('trip', sa.Column('title', sqlmodel.sql.sqltypes.AutoString(), nullable=True))
    op.add_column('trip', sa.Column('ai_summary', sqlmodel.sql.sqltypes.AutoString(), nullable=True))
    op.drop_column('trip', 'country')
    op.drop_column('trip', 'city')
    op.drop_column('trip', 'duration_days')
    op.drop_column('trip', 'vibe')
    op.drop_column('trip', 'notes')
    op.drop_column('trip', 'highlight')
    op.drop_column('trip', 'lowlight')
    op.drop_column('trip', 'would_return')


def downgrade() -> None:
    # 1. Re-add per-city columns to trip (nullable — can't guarantee non-NULL on re-add).
    op.drop_column('trip', 'title')
    op.drop_column('trip', 'ai_summary')
    op.add_column('trip', sa.Column('country', sqlmodel.sql.sqltypes.AutoString(), nullable=True))
    op.add_column('trip', sa.Column('city', sqlmodel.sql.sqltypes.AutoString(), nullable=True))
    op.add_column('trip', sa.Column('duration_days', sa.Integer(), nullable=True))
    op.add_column('trip', sa.Column('vibe', sqlmodel.sql.sqltypes.AutoString(), nullable=True))
    op.add_column('trip', sa.Column('notes', sqlmodel.sql.sqltypes.AutoString(), nullable=True))
    op.add_column('trip', sa.Column('highlight', sqlmodel.sql.sqltypes.AutoString(), nullable=True))
    op.add_column('trip', sa.Column('lowlight', sqlmodel.sql.sqltypes.AutoString(), nullable=True))
    op.add_column('trip', sa.Column('would_return', sa.Boolean(), nullable=True))

    # 2. Copy data back from the first stop (lowest order, then id) for each trip.
    op.execute("""
        UPDATE trip SET
            country      = (SELECT country      FROM tripstop WHERE tripstop.trip_id = trip.id ORDER BY "order", id LIMIT 1),
            city         = (SELECT city         FROM tripstop WHERE tripstop.trip_id = trip.id ORDER BY "order", id LIMIT 1),
            vibe         = (SELECT vibe         FROM tripstop WHERE tripstop.trip_id = trip.id ORDER BY "order", id LIMIT 1),
            notes        = (SELECT notes        FROM tripstop WHERE tripstop.trip_id = trip.id ORDER BY "order", id LIMIT 1),
            highlight    = (SELECT highlight    FROM tripstop WHERE tripstop.trip_id = trip.id ORDER BY "order", id LIMIT 1),
            lowlight     = (SELECT lowlight     FROM tripstop WHERE tripstop.trip_id = trip.id ORDER BY "order", id LIMIT 1),
            would_return = (SELECT would_return FROM tripstop WHERE tripstop.trip_id = trip.id ORDER BY "order", id LIMIT 1)
    """)

    # 3. Drop tripstop table.
    op.drop_index('ix_tripstop_trip_id', table_name='tripstop')
    op.drop_table('tripstop')
