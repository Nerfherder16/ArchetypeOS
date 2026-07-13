"""council_validation

Revision ID: 0031
Revises: 0030
Create Date: 2026-07-13 10:00:00.000000

RFC-0021 (Foundation Intelligence Slice 4: Council & Validation,
AOS-COUNCIL-VALIDATION-MODELS-001): adds the four adjudication-layer tables —
``validation_tasks``, ``validation_results``, ``foundation_objections``,
``foundation_dossiers`` — plus two nullable link columns
(``candidate_id``, ``selection_run_id``) on ``council_reviews`` so a council
review can attach to a Foundation candidate/run. Additive only, dialect-agnostic
DDL (mirrors 0030's style; ``_audit_columns()`` copied verbatim; the two
``council_reviews`` columns are plain nullable ``ADD COLUMN`` — no existing
column on that table is touched, LES-042).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

import aos_core.models  # GUID / JSONField TypeDecorators


revision: str = '0031'
down_revision: Union[str, None] = '0030'
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
        'validation_tasks',
        sa.Column('candidate_id', aos_core.models.GUID(), nullable=False),
        sa.Column('selection_run_id', aos_core.models.GUID(), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('validation_type', sa.String(length=32), nullable=False),
        sa.Column('question', sa.Text(), nullable=False),
        sa.Column('method', sa.Text(), nullable=False),
        sa.Column('success_criteria', aos_core.models.JSONField(), nullable=False),
        sa.Column('failure_criteria', aos_core.models.JSONField(), nullable=False),
        sa.Column('required_evidence', aos_core.models.JSONField(), nullable=False),
        sa.Column('blocking', sa.Boolean(), nullable=False),
        sa.Column('result_claim_ids', aos_core.models.JSONField(), nullable=False),
        # `status` is provided by _audit_columns() below and carries
        # ValidationStatus (proposed/approved/running/passed/failed/inconclusive)
        # — do NOT list it here too (LES-042: a second 'status' collides).
        *_audit_columns(),
        sa.ForeignKeyConstraint(['candidate_id'], ['foundation_candidates.id']),
        sa.ForeignKeyConstraint(['selection_run_id'], ['foundation_selection_runs.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_validation_tasks_candidate_id'), 'validation_tasks', ['candidate_id'], unique=False)
    op.create_index(
        op.f('ix_validation_tasks_selection_run_id'), 'validation_tasks', ['selection_run_id'], unique=False
    )
    op.create_index(op.f('ix_validation_tasks_status'), 'validation_tasks', ['status'], unique=False)
    op.create_index(
        'ix_validation_tasks_run_status', 'validation_tasks', ['selection_run_id', 'status'], unique=False
    )

    op.create_table(
        'validation_results',
        sa.Column('validation_task_id', aos_core.models.GUID(), nullable=False),
        sa.Column('outcome', sa.String(length=32), nullable=False),
        sa.Column('summary', sa.Text(), nullable=True),
        sa.Column('evidence', aos_core.models.JSONField(), nullable=False),
        sa.Column('benchmark_ref', aos_core.models.GUID(), nullable=True),
        sa.Column('experiment_ref', aos_core.models.GUID(), nullable=True),
        sa.Column('result_claim_ids', aos_core.models.JSONField(), nullable=False),
        *_audit_columns(),
        sa.ForeignKeyConstraint(['validation_task_id'], ['validation_tasks.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        op.f('ix_validation_results_validation_task_id'), 'validation_results', ['validation_task_id'],
        unique=False,
    )
    op.create_index(op.f('ix_validation_results_benchmark_ref'), 'validation_results', ['benchmark_ref'], unique=False)
    op.create_index(
        op.f('ix_validation_results_experiment_ref'), 'validation_results', ['experiment_ref'], unique=False
    )
    op.create_index(op.f('ix_validation_results_status'), 'validation_results', ['status'], unique=False)

    op.create_table(
        'foundation_objections',
        sa.Column('candidate_id', aos_core.models.GUID(), nullable=False),
        sa.Column('review_id', aos_core.models.GUID(), nullable=True),
        sa.Column('raised_by', sa.String(length=128), nullable=False),
        sa.Column('objection', sa.Text(), nullable=False),
        sa.Column('materiality', sa.String(length=32), nullable=False),
        sa.Column('blocking', sa.Boolean(), nullable=False),
        sa.Column('resolution', sa.Text(), nullable=True),
        sa.Column('resolution_validation_task_id', aos_core.models.GUID(), nullable=True),
        sa.Column('resolution_decision_id', aos_core.models.GUID(), nullable=True),
        # `status` is provided by _audit_columns() below and carries the
        # objection workflow (open/resolved/accepted_exception/
        # converted_to_validation) — do NOT list it here too (LES-042).
        *_audit_columns(),
        sa.ForeignKeyConstraint(['candidate_id'], ['foundation_candidates.id']),
        sa.ForeignKeyConstraint(['review_id'], ['council_reviews.id']),
        sa.ForeignKeyConstraint(['resolution_validation_task_id'], ['validation_tasks.id']),
        sa.ForeignKeyConstraint(['resolution_decision_id'], ['decisions.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        op.f('ix_foundation_objections_candidate_id'), 'foundation_objections', ['candidate_id'], unique=False
    )
    op.create_index(
        op.f('ix_foundation_objections_review_id'), 'foundation_objections', ['review_id'], unique=False
    )
    op.create_index(
        op.f('ix_foundation_objections_resolution_validation_task_id'), 'foundation_objections',
        ['resolution_validation_task_id'], unique=False,
    )
    op.create_index(
        op.f('ix_foundation_objections_resolution_decision_id'), 'foundation_objections',
        ['resolution_decision_id'], unique=False,
    )
    op.create_index(op.f('ix_foundation_objections_status'), 'foundation_objections', ['status'], unique=False)

    op.create_table(
        'foundation_dossiers',
        sa.Column('selection_run_id', aos_core.models.GUID(), nullable=False),
        sa.Column('recommended_candidate_id', aos_core.models.GUID(), nullable=True),
        sa.Column('verdict', sa.String(length=64), nullable=False),
        sa.Column('reasons', aos_core.models.JSONField(), nullable=False),
        sa.Column('remaining_uncertainty', aos_core.models.JSONField(), nullable=False),
        sa.Column('rejected_alternatives', aos_core.models.JSONField(), nullable=False),
        sa.Column('conditions_of_approval', aos_core.models.JSONField(), nullable=False),
        sa.Column('required_future_reviews', aos_core.models.JSONField(), nullable=False),
        sa.Column('approved_by', sa.String(length=128), nullable=True),
        sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True),
        *_audit_columns(),
        sa.ForeignKeyConstraint(['selection_run_id'], ['foundation_selection_runs.id']),
        sa.ForeignKeyConstraint(['recommended_candidate_id'], ['foundation_candidates.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        op.f('ix_foundation_dossiers_selection_run_id'), 'foundation_dossiers', ['selection_run_id'], unique=False
    )
    op.create_index(
        op.f('ix_foundation_dossiers_recommended_candidate_id'), 'foundation_dossiers',
        ['recommended_candidate_id'], unique=False,
    )
    op.create_index(op.f('ix_foundation_dossiers_status'), 'foundation_dossiers', ['status'], unique=False)

    # LES-042: plain nullable ADD COLUMN — no existing council_reviews column is
    # touched. RFC-0021 C2: a candidate review *is* a council review with a
    # subject, so these two link columns replace a parallel review table.
    op.add_column('council_reviews', sa.Column('candidate_id', aos_core.models.GUID(), nullable=True))
    op.add_column('council_reviews', sa.Column('selection_run_id', aos_core.models.GUID(), nullable=True))
    op.create_index(
        op.f('ix_council_reviews_candidate_id'), 'council_reviews', ['candidate_id'], unique=False
    )
    op.create_index(
        op.f('ix_council_reviews_selection_run_id'), 'council_reviews', ['selection_run_id'], unique=False
    )
    op.create_foreign_key(
        'fk_council_reviews_candidate_id', 'council_reviews', 'foundation_candidates', ['candidate_id'], ['id']
    )
    op.create_foreign_key(
        'fk_council_reviews_selection_run_id', 'council_reviews', 'foundation_selection_runs',
        ['selection_run_id'], ['id'],
    )


def downgrade() -> None:
    op.drop_constraint('fk_council_reviews_selection_run_id', 'council_reviews', type_='foreignkey')
    op.drop_constraint('fk_council_reviews_candidate_id', 'council_reviews', type_='foreignkey')
    op.drop_index(op.f('ix_council_reviews_selection_run_id'), table_name='council_reviews')
    op.drop_index(op.f('ix_council_reviews_candidate_id'), table_name='council_reviews')
    op.drop_column('council_reviews', 'selection_run_id')
    op.drop_column('council_reviews', 'candidate_id')

    op.drop_index(op.f('ix_foundation_dossiers_status'), table_name='foundation_dossiers')
    op.drop_index(op.f('ix_foundation_dossiers_recommended_candidate_id'), table_name='foundation_dossiers')
    op.drop_index(op.f('ix_foundation_dossiers_selection_run_id'), table_name='foundation_dossiers')
    op.drop_table('foundation_dossiers')

    op.drop_index(op.f('ix_foundation_objections_status'), table_name='foundation_objections')
    op.drop_index(op.f('ix_foundation_objections_resolution_decision_id'), table_name='foundation_objections')
    op.drop_index(
        op.f('ix_foundation_objections_resolution_validation_task_id'), table_name='foundation_objections'
    )
    op.drop_index(op.f('ix_foundation_objections_review_id'), table_name='foundation_objections')
    op.drop_index(op.f('ix_foundation_objections_candidate_id'), table_name='foundation_objections')
    op.drop_table('foundation_objections')

    op.drop_index(op.f('ix_validation_results_status'), table_name='validation_results')
    op.drop_index(op.f('ix_validation_results_experiment_ref'), table_name='validation_results')
    op.drop_index(op.f('ix_validation_results_benchmark_ref'), table_name='validation_results')
    op.drop_index(op.f('ix_validation_results_validation_task_id'), table_name='validation_results')
    op.drop_table('validation_results')

    op.drop_index('ix_validation_tasks_run_status', table_name='validation_tasks')
    op.drop_index(op.f('ix_validation_tasks_status'), table_name='validation_tasks')
    op.drop_index(op.f('ix_validation_tasks_selection_run_id'), table_name='validation_tasks')
    op.drop_index(op.f('ix_validation_tasks_candidate_id'), table_name='validation_tasks')
    op.drop_table('validation_tasks')
