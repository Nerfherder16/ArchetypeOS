"""action requests (mandatory execution envelope)

Revision ID: 0022
Revises: 0021
Create Date: 2026-07-11 01:40:00.000000

AOS-AUTHORITY-ENVELOPE-001 (finding P0-6): adds ``action_requests`` — the
execution envelope a high-impact action (write/deploy/destructive/sensitive
egress) must carry. The authority evaluator becomes a structural gate: the job
origination chokepoint refuses a high-impact action without an authorized
envelope. Dialect-agnostic DDL.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

import aos_core.models  # GUID / JSONField TypeDecorators


revision: str = '0022'
down_revision: Union[str, None] = '0021'
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
        'action_requests',
        sa.Column('action_class', sa.String(length=64), nullable=False),
        sa.Column('actor', sa.String(length=128), nullable=False),
        sa.Column('agent', sa.String(length=128), nullable=True),
        sa.Column('project_id', aos_core.models.GUID(), nullable=True),
        sa.Column('target', sa.Text(), nullable=True),
        sa.Column('sensitivity', sa.String(length=32), nullable=False),
        sa.Column('requested_capability', sa.String(length=128), nullable=True),
        sa.Column('payload_digest', sa.String(length=128), nullable=True),
        sa.Column('policy_decision', sa.String(length=32), nullable=False),
        sa.Column('approval_state', sa.String(length=32), nullable=False),
        sa.Column('execution_state', sa.String(length=32), nullable=False),
        *_audit_columns(),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_action_requests_action_class'), 'action_requests', ['action_class'], unique=False)
    op.create_index(op.f('ix_action_requests_project_id'), 'action_requests', ['project_id'], unique=False)
    op.create_index(op.f('ix_action_requests_approval_state'), 'action_requests', ['approval_state'], unique=False)
    op.create_index(op.f('ix_action_requests_execution_state'), 'action_requests', ['execution_state'], unique=False)
    op.create_index(op.f('ix_action_requests_status'), 'action_requests', ['status'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_action_requests_status'), table_name='action_requests')
    op.drop_index(op.f('ix_action_requests_execution_state'), table_name='action_requests')
    op.drop_index(op.f('ix_action_requests_approval_state'), table_name='action_requests')
    op.drop_index(op.f('ix_action_requests_project_id'), table_name='action_requests')
    op.drop_index(op.f('ix_action_requests_action_class'), table_name='action_requests')
    op.drop_table('action_requests')
