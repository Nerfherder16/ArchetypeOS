"""multi-phase research plans

Revision ID: 0012
Revises: 0011
Create Date: 2026-07-09 00:00:00.000000

AOS-RESEARCH-003 (eval Finding 15): mature research from a single-shot dossier
into a repeatable, multi-phase investigation. Adds ``research_plans`` — one row
per planned investigation carrying the question, its sensitivity, the source
types it requires, the search queries to run, the verification steps to apply,
and the synthesis policy. The plan is recorded before any source is fetched.
Dialect-agnostic DDL (GUID/JSONField degrade on sqlite). This migration only
creates the plan table; the run table follows in a later slice.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

import aos_core.models  # GUID / JSONField TypeDecorators


revision: str = '0012'
down_revision: Union[str, None] = '0011'
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
        'research_plans',
        sa.Column('project_id', aos_core.models.GUID(), nullable=False),
        sa.Column('question', sa.Text(), nullable=False),
        sa.Column('sensitivity', sa.String(length=32), nullable=False),
        sa.Column('plan_status', sa.String(length=32), nullable=False),
        sa.Column('required_source_types', aos_core.models.JSONField(), nullable=False),
        sa.Column('search_queries', aos_core.models.JSONField(), nullable=False),
        sa.Column('verification_steps', aos_core.models.JSONField(), nullable=False),
        sa.Column('synthesis_policy', aos_core.models.JSONField(), nullable=False),
        *_audit_columns(),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_research_plans_project_id'), 'research_plans', ['project_id'], unique=False)
    op.create_index(op.f('ix_research_plans_status'), 'research_plans', ['status'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_research_plans_status'), table_name='research_plans')
    op.drop_index(op.f('ix_research_plans_project_id'), table_name='research_plans')
    op.drop_table('research_plans')
