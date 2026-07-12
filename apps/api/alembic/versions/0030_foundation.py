"""foundation

Revision ID: 0030
Revises: 0029
Create Date: 2026-07-12 10:00:00.000000

RFC-0020 (Foundation Intelligence Slice 3: Requirements & Candidates,
AOS-FOUNDATION-MODELS-001): adds the five foundation-domain tables —
``foundation_selection_runs``, ``foundation_requirements``,
``foundation_candidates``, ``foundation_elements``, ``foundation_scores`` —
that turn the RFC-0017 foundation contracts (already merged in Slice 0) into
persisted, guarded records. Additive only, dialect-agnostic DDL (mirrors
0029's style; ``_audit_columns()`` copied verbatim).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

import aos_core.models  # GUID / JSONField TypeDecorators


revision: str = '0030'
down_revision: Union[str, None] = '0029'
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
        'foundation_selection_runs',
        sa.Column('project_id', aos_core.models.GUID(), nullable=False),
        sa.Column('target_genome_snapshot_id', aos_core.models.GUID(), nullable=False),
        sa.Column('corpus_snapshot_id', aos_core.models.GUID(), nullable=True),
        sa.Column('state', sa.String(length=32), nullable=False),
        sa.Column('summary', sa.Text(), nullable=False),
        *_audit_columns(),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id']),
        sa.ForeignKeyConstraint(['target_genome_snapshot_id'], ['genome_snapshots.id']),
        sa.ForeignKeyConstraint(['corpus_snapshot_id'], ['corpus_snapshots.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        op.f('ix_foundation_selection_runs_project_id'), 'foundation_selection_runs', ['project_id'], unique=False
    )
    op.create_index(
        op.f('ix_foundation_selection_runs_target_genome_snapshot_id'),
        'foundation_selection_runs', ['target_genome_snapshot_id'], unique=False,
    )
    op.create_index(
        op.f('ix_foundation_selection_runs_corpus_snapshot_id'),
        'foundation_selection_runs', ['corpus_snapshot_id'], unique=False,
    )
    op.create_index(op.f('ix_foundation_selection_runs_state'), 'foundation_selection_runs', ['state'], unique=False)
    op.create_index(op.f('ix_foundation_selection_runs_status'), 'foundation_selection_runs', ['status'], unique=False)

    op.create_table(
        'foundation_requirements',
        sa.Column('selection_run_id', aos_core.models.GUID(), nullable=False),
        sa.Column('genome_snapshot_id', aos_core.models.GUID(), nullable=True),
        sa.Column('requirement_type', sa.String(length=32), nullable=False),
        sa.Column('domain', sa.String(length=64), nullable=False),
        sa.Column('statement', sa.Text(), nullable=False),
        sa.Column('priority', sa.String(length=16), nullable=False),
        sa.Column('weight', sa.Float(), nullable=False),
        sa.Column('veto_if_unsatisfied', sa.Boolean(), nullable=False),
        sa.Column('verification_method', sa.Text(), nullable=False),
        sa.Column('claim_ids', aos_core.models.JSONField(), nullable=False),
        *_audit_columns(),
        sa.ForeignKeyConstraint(['selection_run_id'], ['foundation_selection_runs.id']),
        sa.ForeignKeyConstraint(['genome_snapshot_id'], ['genome_snapshots.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        op.f('ix_foundation_requirements_selection_run_id'), 'foundation_requirements', ['selection_run_id'],
        unique=False,
    )
    op.create_index(
        op.f('ix_foundation_requirements_genome_snapshot_id'), 'foundation_requirements', ['genome_snapshot_id'],
        unique=False,
    )
    op.create_index(op.f('ix_foundation_requirements_domain'), 'foundation_requirements', ['domain'], unique=False)
    op.create_index(op.f('ix_foundation_requirements_status'), 'foundation_requirements', ['status'], unique=False)
    op.create_index(
        'ix_foundation_requirements_run_type', 'foundation_requirements', ['selection_run_id', 'requirement_type'],
        unique=False,
    )

    op.create_table(
        'foundation_candidates',
        sa.Column('selection_run_id', aos_core.models.GUID(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('summary', sa.Text(), nullable=False),
        sa.Column('architecture_style', aos_core.models.JSONField(), nullable=False),
        sa.Column('recommendation_ref', aos_core.models.GUID(), nullable=True),
        sa.Column('assumption_claim_ids', aos_core.models.JSONField(), nullable=False),
        sa.Column('satisfied_requirement_ids', aos_core.models.JSONField(), nullable=False),
        sa.Column('unsatisfied_requirement_ids', aos_core.models.JSONField(), nullable=False),
        sa.Column('hard_constraint_violations', aos_core.models.JSONField(), nullable=False),
        sa.Column('reversibility', sa.String(length=16), nullable=False),
        sa.Column('lock_in_profile', aos_core.models.JSONField(), nullable=False),
        sa.Column('estimated_cost', aos_core.models.JSONField(), nullable=False),
        sa.Column('estimated_effort', aos_core.models.JSONField(), nullable=False),
        sa.Column('score_summary', aos_core.models.JSONField(), nullable=False),
        sa.Column('confidence', sa.Float(), nullable=False),
        # `status` is provided by _audit_columns() below and carries
        # CandidateStatus (draft/eligible/.../rejected/selected) — do NOT list
        # it here too (LES-042: a second 'status' collides).
        *_audit_columns(),
        sa.ForeignKeyConstraint(['selection_run_id'], ['foundation_selection_runs.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        op.f('ix_foundation_candidates_selection_run_id'), 'foundation_candidates', ['selection_run_id'],
        unique=False,
    )
    op.create_index(
        op.f('ix_foundation_candidates_recommendation_ref'), 'foundation_candidates', ['recommendation_ref'],
        unique=False,
    )
    op.create_index(op.f('ix_foundation_candidates_status'), 'foundation_candidates', ['status'], unique=False)

    op.create_table(
        'foundation_elements',
        sa.Column('candidate_id', aos_core.models.GUID(), nullable=False),
        sa.Column('domain', sa.String(length=64), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('decision', sa.Text(), nullable=False),
        sa.Column('rationale', sa.Text(), nullable=False),
        sa.Column('technology_refs', aos_core.models.JSONField(), nullable=False),
        sa.Column('claim_ids', aos_core.models.JSONField(), nullable=False),
        sa.Column('requirement_ids', aos_core.models.JSONField(), nullable=False),
        sa.Column('alternatives_rejected', aos_core.models.JSONField(), nullable=False),
        sa.Column('tradeoffs', aos_core.models.JSONField(), nullable=False),
        sa.Column('risks', aos_core.models.JSONField(), nullable=False),
        sa.Column('verification_method', sa.Text(), nullable=False),
        *_audit_columns(),
        sa.ForeignKeyConstraint(['candidate_id'], ['foundation_candidates.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        op.f('ix_foundation_elements_candidate_id'), 'foundation_elements', ['candidate_id'], unique=False
    )
    op.create_index(op.f('ix_foundation_elements_domain'), 'foundation_elements', ['domain'], unique=False)
    op.create_index(op.f('ix_foundation_elements_status'), 'foundation_elements', ['status'], unique=False)

    op.create_table(
        'foundation_scores',
        sa.Column('candidate_id', aos_core.models.GUID(), nullable=False),
        sa.Column('criterion', sa.String(length=64), nullable=False),
        sa.Column('raw_score', sa.Float(), nullable=False),
        sa.Column('weight', sa.Float(), nullable=False),
        sa.Column('confidence', sa.Float(), nullable=False),
        sa.Column('uncertainty_penalty', sa.Float(), nullable=False),
        sa.Column('adjusted_score', sa.Float(), nullable=False),
        sa.Column('rationale', sa.Text(), nullable=False),
        sa.Column('supporting_claim_ids', aos_core.models.JSONField(), nullable=False),
        sa.Column('evaluation_ref', aos_core.models.GUID(), nullable=True),
        *_audit_columns(),
        sa.ForeignKeyConstraint(['candidate_id'], ['foundation_candidates.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('candidate_id', 'criterion', name='uq_foundation_scores_candidate_criterion'),
    )
    op.create_index(op.f('ix_foundation_scores_candidate_id'), 'foundation_scores', ['candidate_id'], unique=False)
    op.create_index(
        op.f('ix_foundation_scores_evaluation_ref'), 'foundation_scores', ['evaluation_ref'], unique=False
    )
    op.create_index(op.f('ix_foundation_scores_status'), 'foundation_scores', ['status'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_foundation_scores_status'), table_name='foundation_scores')
    op.drop_index(op.f('ix_foundation_scores_evaluation_ref'), table_name='foundation_scores')
    op.drop_index(op.f('ix_foundation_scores_candidate_id'), table_name='foundation_scores')
    op.drop_table('foundation_scores')

    op.drop_index(op.f('ix_foundation_elements_status'), table_name='foundation_elements')
    op.drop_index(op.f('ix_foundation_elements_domain'), table_name='foundation_elements')
    op.drop_index(op.f('ix_foundation_elements_candidate_id'), table_name='foundation_elements')
    op.drop_table('foundation_elements')

    op.drop_index(op.f('ix_foundation_candidates_status'), table_name='foundation_candidates')
    op.drop_index(op.f('ix_foundation_candidates_recommendation_ref'), table_name='foundation_candidates')
    op.drop_index(op.f('ix_foundation_candidates_selection_run_id'), table_name='foundation_candidates')
    op.drop_table('foundation_candidates')

    op.drop_index('ix_foundation_requirements_run_type', table_name='foundation_requirements')
    op.drop_index(op.f('ix_foundation_requirements_status'), table_name='foundation_requirements')
    op.drop_index(op.f('ix_foundation_requirements_domain'), table_name='foundation_requirements')
    op.drop_index(op.f('ix_foundation_requirements_genome_snapshot_id'), table_name='foundation_requirements')
    op.drop_index(op.f('ix_foundation_requirements_selection_run_id'), table_name='foundation_requirements')
    op.drop_table('foundation_requirements')

    op.drop_index(op.f('ix_foundation_selection_runs_status'), table_name='foundation_selection_runs')
    op.drop_index(op.f('ix_foundation_selection_runs_state'), table_name='foundation_selection_runs')
    op.drop_index(op.f('ix_foundation_selection_runs_corpus_snapshot_id'), table_name='foundation_selection_runs')
    op.drop_index(
        op.f('ix_foundation_selection_runs_target_genome_snapshot_id'), table_name='foundation_selection_runs'
    )
    op.drop_index(op.f('ix_foundation_selection_runs_project_id'), table_name='foundation_selection_runs')
    op.drop_table('foundation_selection_runs')
