"""schedule fires (exactly-once occurrence firing)

Revision ID: 0020
Revises: 0019
Create Date: 2026-07-11 01:00:00.000000

AOS-SCHEDULER-RELIABILITY-001 (finding P0-2): adds ``schedule_fires``, one row per
materialized firing, unique on ``(schedule_id, nominal_fire_at)`` so a schedule's
occurrence fires exactly once even across scheduler replicas or a crash-and-retry.
Dialect-agnostic DDL (GUID/JSONField degrade on sqlite); the unique constraint is
part of ``CREATE TABLE`` so it applies on both the CI Postgres service and the
hermetic sqlite path.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

import aos_core.models  # GUID / JSONField TypeDecorators


revision: str = '0020'
down_revision: Union[str, None] = '0019'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _audit_columns() -> list:
    return [
        sa.Column('id', aos_core.models.GUID(), nullable=False),
        sa.Column('status', sa.String(length=64), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_by', sa.String(length=128), nullable=False),
        sa.Column('updated_by', sa.String(length=128), nullable=False),
        sa.Column('metadata', aos_core.models.JSONField(), nullable=False),
    ]


def upgrade() -> None:
    op.create_table(
        'schedule_fires',
        sa.Column('schedule_id', aos_core.models.GUID(), nullable=False),
        sa.Column('nominal_fire_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('job_id', aos_core.models.GUID(), nullable=True),
        *_audit_columns(),
        sa.ForeignKeyConstraint(['schedule_id'], ['schedules.id']),
        sa.ForeignKeyConstraint(['job_id'], ['jobs.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('schedule_id', 'nominal_fire_at', name='uq_schedule_fires_schedule_nominal'),
    )
    op.create_index(op.f('ix_schedule_fires_schedule_id'), 'schedule_fires', ['schedule_id'], unique=False)
    op.create_index(op.f('ix_schedule_fires_job_id'), 'schedule_fires', ['job_id'], unique=False)
    op.create_index(op.f('ix_schedule_fires_status'), 'schedule_fires', ['status'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_schedule_fires_status'), table_name='schedule_fires')
    op.drop_index(op.f('ix_schedule_fires_job_id'), table_name='schedule_fires')
    op.drop_index(op.f('ix_schedule_fires_schedule_id'), table_name='schedule_fires')
    op.drop_table('schedule_fires')
