"""implementation plans

Revision ID: 0027
Revises: 0026
Create Date: 2026-07-11 08:00:00.000000

AOS-BUILD-PLAN-001 (RFC-0015 Design §1): adds ``implementation_plans`` — a
governed, draft-first plan drafted from an approved ``Decision``
(``services/build_plan.py:plan_from_decision``) and approved by a named human
(``approve_plan``), mirroring the ``decisions`` table shape. Additive only,
dialect-agnostic DDL.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

import aos_core.models  # GUID / JSONField TypeDecorators


revision: str = '0027'
down_revision: Union[str, None] = '0026'
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
        'implementation_plans',
        sa.Column('decision_id', aos_core.models.GUID(), nullable=False),
        sa.Column('project_id', aos_core.models.GUID(), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('objective', sa.Text(), nullable=True),
        sa.Column('tasks', aos_core.models.JSONField(), nullable=False),
        sa.Column('acceptance_criteria', aos_core.models.JSONField(), nullable=False),
        sa.Column('verification_requirements', aos_core.models.JSONField(), nullable=False),
        sa.Column('target_repository_id', aos_core.models.GUID(), nullable=True),
        sa.Column('risk', sa.Text(), nullable=True),
        sa.Column('effort', sa.String(length=128), nullable=True),
        sa.Column('evidence', aos_core.models.JSONField(), nullable=False),
        sa.Column('approved_by', sa.String(length=128), nullable=True),
        sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True),
        *_audit_columns(),
        sa.ForeignKeyConstraint(['decision_id'], ['decisions.id'], ),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ),
        sa.ForeignKeyConstraint(['target_repository_id'], ['repositories.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_implementation_plans_decision_id'), 'implementation_plans', ['decision_id'], unique=False)
    op.create_index(op.f('ix_implementation_plans_project_id'), 'implementation_plans', ['project_id'], unique=False)
    op.create_index(op.f('ix_implementation_plans_target_repository_id'), 'implementation_plans', ['target_repository_id'], unique=False)
    op.create_index(op.f('ix_implementation_plans_status'), 'implementation_plans', ['status'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_implementation_plans_status'), table_name='implementation_plans')
    op.drop_index(op.f('ix_implementation_plans_target_repository_id'), table_name='implementation_plans')
    op.drop_index(op.f('ix_implementation_plans_project_id'), table_name='implementation_plans')
    op.drop_index(op.f('ix_implementation_plans_decision_id'), table_name='implementation_plans')
    op.drop_table('implementation_plans')
