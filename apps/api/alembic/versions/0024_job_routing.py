"""job node-routing fields

Revision ID: 0024
Revises: 0023
Create Date: 2026-07-11 12:00:00.000000

AOS-NODE-EXECUTION-001: persists a job's execution requirements + routing decision
so a job runs only on an eligible assigned node. Additive nullable/defaulted
columns; dialect-agnostic DDL (no FK constraint added via ALTER, so it applies on
SQLite too — the ORM model carries the FK for fresh-DB create_all + Postgres).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

import aos_core.models  # GUID TypeDecorator


revision: str = '0024'
down_revision: Union[str, None] = '0023'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('jobs', sa.Column('required_capability', sa.String(length=128), nullable=True))
    op.add_column('jobs', sa.Column('sensitivity', sa.String(length=32), nullable=False, server_default='public'))
    op.add_column('jobs', sa.Column('requires_write', sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column('jobs', sa.Column('assigned_node_id', aos_core.models.GUID(), nullable=True))
    op.add_column('jobs', sa.Column('routing_status', sa.String(length=32), nullable=False, server_default='unrouted'))
    op.add_column('jobs', sa.Column('routing_explanation', sa.Text(), nullable=True))
    op.add_column('jobs', sa.Column('routed_at', sa.DateTime(timezone=True), nullable=True))
    op.create_index(op.f('ix_jobs_assigned_node_id'), 'jobs', ['assigned_node_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_jobs_assigned_node_id'), table_name='jobs')
    op.drop_column('jobs', 'routed_at')
    op.drop_column('jobs', 'routing_explanation')
    op.drop_column('jobs', 'routing_status')
    op.drop_column('jobs', 'assigned_node_id')
    op.drop_column('jobs', 'requires_write')
    op.drop_column('jobs', 'sensitivity')
    op.drop_column('jobs', 'required_capability')
