"""usage event ledger

Revision ID: 0006
Revises: 0005
Create Date: 2026-07-07 00:00:00.000000

AOS-USAGE-001: the LLM usage ledger. One ``usage_events`` row per reasoned
``generate()`` (the deterministic CI floor records none), carrying the provider's
real (or explicitly ``estimated``) token/cost numbers and the derived tier
(claude / local / free). Dialect-agnostic DDL (GUID/JSONField degrade on sqlite),
so it applies on the CI pgvector Postgres service and on the hermetic sqlite path
alike.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

import aos_core.models  # provides the GUID / JSONField TypeDecorators referenced below


# revision identifiers, used by Alembic.
revision: str = '0006'
down_revision: Union[str, None] = '0005'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'usage_events',
        sa.Column('ts', sa.DateTime(timezone=True), nullable=False),
        sa.Column('provider', sa.String(length=128), nullable=False),
        sa.Column('tier', sa.String(length=64), nullable=False),
        sa.Column('model', sa.String(length=255), nullable=True),
        sa.Column('input_tokens', sa.Integer(), nullable=True),
        sa.Column('output_tokens', sa.Integer(), nullable=True),
        sa.Column('cost_usd', sa.Float(), nullable=True),
        sa.Column('estimated', sa.Boolean(), nullable=False),
        sa.Column('agent', sa.String(length=128), nullable=True),
        sa.Column('session', sa.String(length=128), nullable=True),
        sa.Column('context', sa.String(length=128), nullable=True),
        sa.Column('id', aos_core.models.GUID(), nullable=False),
        sa.Column('status', sa.String(length=64), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_by', sa.String(length=128), nullable=False),
        sa.Column('updated_by', sa.String(length=128), nullable=False),
        sa.Column('metadata', aos_core.models.JSONField(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_usage_events_provider'), 'usage_events', ['provider'], unique=False)
    op.create_index(op.f('ix_usage_events_status'), 'usage_events', ['status'], unique=False)
    op.create_index(op.f('ix_usage_events_tier'), 'usage_events', ['tier'], unique=False)
    op.create_index(op.f('ix_usage_events_ts'), 'usage_events', ['ts'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_usage_events_ts'), table_name='usage_events')
    op.drop_index(op.f('ix_usage_events_tier'), table_name='usage_events')
    op.drop_index(op.f('ix_usage_events_status'), table_name='usage_events')
    op.drop_index(op.f('ix_usage_events_provider'), table_name='usage_events')
    op.drop_table('usage_events')
