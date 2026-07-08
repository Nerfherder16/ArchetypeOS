"""node registry (distributed runtime)

Revision ID: 0010
Revises: 0009
Create Date: 2026-07-08 00:00:00.000000

AOS-NODE-001: make the distributed runtime first-class. Adds ``nodes`` (registered
execution nodes; read-only by default, with a max_sensitivity ceiling),
``node_capabilities`` (what each node can do — for capability-aware routing), and
``node_heartbeats`` (health over time). Dialect-agnostic DDL (GUID/JSONField degrade
on sqlite), so it applies on the CI Postgres service and the hermetic sqlite path.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

import aos_core.models  # GUID / JSONField TypeDecorators


revision: str = '0010'
down_revision: Union[str, None] = '0009'
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
        'nodes',
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('node_type', sa.String(length=64), nullable=False),
        sa.Column('endpoint', sa.Text(), nullable=True),
        sa.Column('node_status', sa.String(length=32), nullable=False),
        sa.Column('last_seen_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('max_sensitivity', sa.String(length=32), nullable=False),
        sa.Column('write_access', sa.Boolean(), nullable=False),
        *_audit_columns(),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_nodes_node_status'), 'nodes', ['node_status'], unique=False)
    op.create_index(op.f('ix_nodes_status'), 'nodes', ['status'], unique=False)

    op.create_table(
        'node_capabilities',
        sa.Column('node_id', aos_core.models.GUID(), nullable=False),
        sa.Column('capability', sa.String(length=128), nullable=False),
        sa.Column('capability_version', sa.String(length=64), nullable=True),
        sa.Column('capability_status', sa.String(length=32), nullable=False),
        sa.Column('limits', aos_core.models.JSONField(), nullable=False),
        *_audit_columns(),
        sa.ForeignKeyConstraint(['node_id'], ['nodes.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_node_capabilities_node_id'), 'node_capabilities', ['node_id'], unique=False)
    op.create_index(op.f('ix_node_capabilities_status'), 'node_capabilities', ['status'], unique=False)

    op.create_table(
        'node_heartbeats',
        sa.Column('node_id', aos_core.models.GUID(), nullable=False),
        sa.Column('health', sa.String(length=32), nullable=False),
        sa.Column('observed_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('metrics', aos_core.models.JSONField(), nullable=False),
        *_audit_columns(),
        sa.ForeignKeyConstraint(['node_id'], ['nodes.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_node_heartbeats_node_id'), 'node_heartbeats', ['node_id'], unique=False)
    op.create_index(op.f('ix_node_heartbeats_status'), 'node_heartbeats', ['status'], unique=False)


def downgrade() -> None:
    op.drop_table('node_heartbeats')
    op.drop_table('node_capabilities')
    op.drop_index(op.f('ix_nodes_status'), table_name='nodes')
    op.drop_index(op.f('ix_nodes_node_status'), table_name='nodes')
    op.drop_table('nodes')
