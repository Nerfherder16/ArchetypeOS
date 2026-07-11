"""concurrency-safe node & heartbeat constraints

Revision ID: 0019
Revises: 0018
Create Date: 2026-07-11 00:30:00.000000

AOS-NODE-CONSTRAINTS-001 (finding P1-3): the node registry and audit-heartbeat
board relied on query-then-insert with no backing uniqueness, so concurrent
writers could create duplicate logical nodes, duplicate (node_id, capability)
rows, and duplicate global (routine, NULL) heartbeats (SQL treats NULLs as
distinct, so the existing composite unique did not cover them). Adds:

- unique ``nodes.name``
- unique ``(node_id, capability)`` on ``node_capabilities``
- a partial unique index on ``audit_heartbeats.routine WHERE project_id IS NULL``

Constraint DDL is ALTER-based (Postgres path, like migrations 0015/0018); the
hermetic sqlite tests build the same constraints via ``create_all`` from the
models' ``__table_args__``. Assumes no existing duplicates (a fresh dedupe step
would precede this on a dirty database).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '0019'
down_revision: Union[str, None] = '0018'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_unique_constraint('uq_nodes_name', 'nodes', ['name'])
    op.create_unique_constraint(
        'uq_node_capabilities_node_capability', 'node_capabilities', ['node_id', 'capability']
    )
    op.create_index(
        'uq_audit_heartbeats_routine_global',
        'audit_heartbeats',
        ['routine'],
        unique=True,
        postgresql_where=sa.text('project_id IS NULL'),
        sqlite_where=sa.text('project_id IS NULL'),
    )


def downgrade() -> None:
    op.drop_index('uq_audit_heartbeats_routine_global', table_name='audit_heartbeats')
    op.drop_constraint('uq_node_capabilities_node_capability', 'node_capabilities', type_='unique')
    op.drop_constraint('uq_nodes_name', 'nodes', type_='unique')
