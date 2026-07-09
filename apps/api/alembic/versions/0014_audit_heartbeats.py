"""nightly audit heartbeats

Revision ID: 0014
Revises: 0013
Create Date: 2026-07-09 00:00:00.000000

AOS-SELFHEAL observability: adds ``audit_heartbeats`` — one row per nightly
self-learn probe (conflict/toil/coherence/session-pain/...), upserted each run
with its outcome (clean/findings/failed), the run day, and any review-PR url, so
a missed run is visible instead of silent. Dialect-agnostic DDL (GUID/JSONField
degrade on sqlite).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

import aos_core.models  # GUID / JSONField TypeDecorators


revision: str = '0014'
down_revision: Union[str, None] = '0013'
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
        'audit_heartbeats',
        sa.Column('routine', sa.String(length=64), nullable=False),
        sa.Column('heartbeat_status', sa.String(length=32), nullable=False),
        sa.Column('day', sa.String(length=32), nullable=False),
        sa.Column('pr_url', sa.Text(), nullable=True),
        sa.Column('detail', sa.Text(), nullable=True),
        *_audit_columns(),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_audit_heartbeats_routine'), 'audit_heartbeats', ['routine'], unique=True)
    op.create_index(op.f('ix_audit_heartbeats_status'), 'audit_heartbeats', ['status'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_audit_heartbeats_status'), table_name='audit_heartbeats')
    op.drop_index(op.f('ix_audit_heartbeats_routine'), table_name='audit_heartbeats')
    op.drop_table('audit_heartbeats')
