"""connector registry + policy center

Revision ID: 0011
Revises: 0010
Create Date: 2026-07-08 00:00:00.000000

AOS-CONNECTOR-001 (eval Finding 9): govern external connections as first-class
assets. Adds ``connectors`` — one row per known connection carrying its governance
posture (connector_type/tier/privacy_class/egress_allowed/browser_exposed/
quota_policy), a settings-derived ``configured`` flag, and recorded health
(``last_health_status``/``last_error``/``last_checked_at``). Rows are reconciled
from a declarative catalog at runtime; this migration only creates the table.
Dialect-agnostic DDL (GUID/JSONField degrade on sqlite).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

import aos_core.models  # GUID / JSONField TypeDecorators


revision: str = '0011'
down_revision: Union[str, None] = '0010'
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
        'connectors',
        sa.Column('name', sa.String(length=128), nullable=False),
        sa.Column('connector_type', sa.String(length=64), nullable=False),
        sa.Column('tier', sa.String(length=64), nullable=False),
        sa.Column('enabled', sa.Boolean(), nullable=False),
        sa.Column('configured', sa.Boolean(), nullable=False),
        sa.Column('privacy_class', sa.String(length=32), nullable=False),
        sa.Column('egress_allowed', sa.Boolean(), nullable=False),
        sa.Column('browser_exposed', sa.Boolean(), nullable=False),
        sa.Column('quota_policy', sa.String(length=128), nullable=False),
        sa.Column('last_health_status', sa.String(length=32), nullable=False),
        sa.Column('last_error', sa.Text(), nullable=True),
        sa.Column('last_checked_at', sa.DateTime(timezone=True), nullable=True),
        *_audit_columns(),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_connectors_name'), 'connectors', ['name'], unique=True)
    op.create_index(op.f('ix_connectors_last_health_status'), 'connectors', ['last_health_status'], unique=False)
    op.create_index(op.f('ix_connectors_status'), 'connectors', ['status'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_connectors_status'), table_name='connectors')
    op.drop_index(op.f('ix_connectors_last_health_status'), table_name='connectors')
    op.drop_index(op.f('ix_connectors_name'), table_name='connectors')
    op.drop_table('connectors')
