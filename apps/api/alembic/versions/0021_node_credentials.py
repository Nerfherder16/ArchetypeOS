"""node service credentials (per-node identity)

Revision ID: 0021
Revises: 0020
Create Date: 2026-07-11 01:20:00.000000

AOS-NODE-IDENTITY-001 (finding P0-5): adds ``node_credentials`` — a per-node
service credential (SHA-256 hash only) issued at operator-approved enrollment, so
heartbeat/claim require a valid node token and a client can no longer report false
health or impersonate a node. Unique ``node_id`` (one live credential per node),
with rotation/revocation timestamps. Dialect-agnostic DDL.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

import aos_core.models  # GUID / JSONField TypeDecorators


revision: str = '0021'
down_revision: Union[str, None] = '0020'
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
        'node_credentials',
        sa.Column('node_id', aos_core.models.GUID(), nullable=False),
        sa.Column('token_hash', sa.String(length=128), nullable=False),
        sa.Column('issued_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('rotated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
        *_audit_columns(),
        sa.ForeignKeyConstraint(['node_id'], ['nodes.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_node_credentials_node_id'), 'node_credentials', ['node_id'], unique=True)
    op.create_index(op.f('ix_node_credentials_status'), 'node_credentials', ['status'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_node_credentials_status'), table_name='node_credentials')
    op.drop_index(op.f('ix_node_credentials_node_id'), table_name='node_credentials')
    op.drop_table('node_credentials')
