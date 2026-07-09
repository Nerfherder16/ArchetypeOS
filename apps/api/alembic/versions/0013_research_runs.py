"""research runs (executor)

Revision ID: 0013
Revises: 0012
Create Date: 2026-07-09 00:00:00.000000

AOS-RESEARCH-003 (eval Finding 15, criteria 2-5): adds ``research_runs`` — one row
per execution of a research plan. Records the phases it ran, every source it
considered with an accept/reject decision + reason, findings citing accepted
sources, conflicts kept visible, a confidence, and the open questions (which the
executor turns into follow-up plans). Dialect-agnostic DDL (GUID/JSONField degrade
on sqlite).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

import aos_core.models  # GUID / JSONField TypeDecorators


revision: str = '0013'
down_revision: Union[str, None] = '0012'
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
        'research_runs',
        sa.Column('plan_id', aos_core.models.GUID(), nullable=False),
        sa.Column('project_id', aos_core.models.GUID(), nullable=False),
        sa.Column('job_id', aos_core.models.GUID(), nullable=True),
        sa.Column('run_status', sa.String(length=32), nullable=False),
        sa.Column('phases', aos_core.models.JSONField(), nullable=False),
        sa.Column('sources', aos_core.models.JSONField(), nullable=False),
        sa.Column('findings', aos_core.models.JSONField(), nullable=False),
        sa.Column('conflicts', aos_core.models.JSONField(), nullable=False),
        sa.Column('open_questions', aos_core.models.JSONField(), nullable=False),
        sa.Column('confidence', sa.Float(), nullable=False),
        *_audit_columns(),
        sa.ForeignKeyConstraint(['plan_id'], ['research_plans.id']),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id']),
        sa.ForeignKeyConstraint(['job_id'], ['jobs.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_research_runs_plan_id'), 'research_runs', ['plan_id'], unique=False)
    op.create_index(op.f('ix_research_runs_project_id'), 'research_runs', ['project_id'], unique=False)
    op.create_index(op.f('ix_research_runs_job_id'), 'research_runs', ['job_id'], unique=False)
    op.create_index(op.f('ix_research_runs_status'), 'research_runs', ['status'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_research_runs_status'), table_name='research_runs')
    op.drop_index(op.f('ix_research_runs_job_id'), table_name='research_runs')
    op.drop_index(op.f('ix_research_runs_project_id'), table_name='research_runs')
    op.drop_index(op.f('ix_research_runs_plan_id'), table_name='research_runs')
    op.drop_table('research_runs')
