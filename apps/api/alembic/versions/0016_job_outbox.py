"""job outbox (transactional job delivery)

Revision ID: 0016
Revises: 0015
Create Date: 2026-07-11 00:00:00.000000

AOS-JOBS-RELIABILITY-001 / RFC-0014 Slice 1: adds ``job_outbox``, written in the
same transaction as its ``Job`` so origination is atomic. A dispatcher publishes
undelivered rows to Redis and stamps ``delivered_at``; a Redis outage after the
job commits can no longer orphan a queued job (finding P0-1). Dialect-agnostic
DDL (GUID/JSONField degrade on sqlite) so it applies on the CI Postgres service
and the hermetic sqlite path alike.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

import aos_core.models  # GUID / JSONField TypeDecorators


revision: str = '0016'
down_revision: Union[str, None] = '0015'
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
        'job_outbox',
        sa.Column('job_id', aos_core.models.GUID(), nullable=False),
        sa.Column('delivered_at', sa.DateTime(timezone=True), nullable=True),
        *_audit_columns(),
        sa.ForeignKeyConstraint(['job_id'], ['jobs.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_job_outbox_job_id'), 'job_outbox', ['job_id'], unique=True)
    op.create_index(op.f('ix_job_outbox_status'), 'job_outbox', ['status'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_job_outbox_status'), table_name='job_outbox')
    op.drop_index(op.f('ix_job_outbox_job_id'), table_name='job_outbox')
    op.drop_table('job_outbox')
