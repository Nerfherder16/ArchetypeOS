"""foundation_baseline

Revision ID: 0032
Revises: 0031
Create Date: 2026-07-13 12:00:00.000000

RFC-0022 (Foundation Intelligence Slice 5: Foundation Baseline,
AOS-FOUNDATION-BASELINE-MODELS-001): adds the two baseline tables —
``foundation_baselines`` (the approved, immutable, versioned root-of-trust a
selected candidate mints into, AD-12/AD-15) and ``foundation_baseline_elements``
(a frozen per-element snapshot, membership-snapshot pattern like
``corpus_snapshot_sources``). Additive only, dialect-agnostic DDL (mirrors
0031's style; ``_audit_columns()`` copied verbatim, LES-042: status/version
come only from the helper, never redeclared).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

import aos_core.models  # GUID / JSONField TypeDecorators


revision: str = '0032'
down_revision: Union[str, None] = '0031'
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
        'foundation_baselines',
        sa.Column('project_id', aos_core.models.GUID(), nullable=False),
        sa.Column('candidate_id', aos_core.models.GUID(), nullable=False),
        sa.Column('selection_run_id', aos_core.models.GUID(), nullable=False),
        sa.Column('target_genome_snapshot_id', aos_core.models.GUID(), nullable=False),
        sa.Column('corpus_snapshot_id', aos_core.models.GUID(), nullable=True),
        sa.Column('approved_decision_id', aos_core.models.GUID(), nullable=False),
        sa.Column('supersedes_baseline_id', aos_core.models.GUID(), nullable=True),
        sa.Column('baseline_version', sa.String(length=32), nullable=False),
        sa.Column('element_set_hash', sa.String(length=64), nullable=False),
        sa.Column('baseline_hash', sa.String(length=64), nullable=False),
        sa.Column('review_triggers', aos_core.models.JSONField(), nullable=False),
        sa.Column('minted_by', sa.String(length=32), nullable=False),
        sa.Column('approved_by', sa.String(length=128), nullable=False),
        sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('effective_from', sa.DateTime(timezone=True), nullable=True),
        # `status` (BaselineStatus: active/superseded/retired) and `version`
        # come only from _audit_columns() below — do NOT redeclare (LES-042).
        *_audit_columns(),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id']),
        sa.ForeignKeyConstraint(['candidate_id'], ['foundation_candidates.id']),
        sa.ForeignKeyConstraint(['selection_run_id'], ['foundation_selection_runs.id']),
        sa.ForeignKeyConstraint(['target_genome_snapshot_id'], ['genome_snapshots.id']),
        sa.ForeignKeyConstraint(['corpus_snapshot_id'], ['corpus_snapshots.id']),
        sa.ForeignKeyConstraint(['approved_decision_id'], ['decisions.id']),
        sa.ForeignKeyConstraint(['supersedes_baseline_id'], ['foundation_baselines.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_foundation_baselines_project_id'), 'foundation_baselines', ['project_id'], unique=False)
    op.create_index(
        op.f('ix_foundation_baselines_candidate_id'), 'foundation_baselines', ['candidate_id'], unique=False
    )
    op.create_index(
        op.f('ix_foundation_baselines_selection_run_id'), 'foundation_baselines', ['selection_run_id'], unique=False
    )
    op.create_index(
        op.f('ix_foundation_baselines_target_genome_snapshot_id'), 'foundation_baselines',
        ['target_genome_snapshot_id'], unique=False,
    )
    op.create_index(
        op.f('ix_foundation_baselines_corpus_snapshot_id'), 'foundation_baselines', ['corpus_snapshot_id'],
        unique=False,
    )
    op.create_index(
        op.f('ix_foundation_baselines_approved_decision_id'), 'foundation_baselines', ['approved_decision_id'],
        unique=False,
    )
    op.create_index(
        op.f('ix_foundation_baselines_supersedes_baseline_id'), 'foundation_baselines', ['supersedes_baseline_id'],
        unique=False,
    )
    op.create_index(
        op.f('ix_foundation_baselines_baseline_hash'), 'foundation_baselines', ['baseline_hash'], unique=False
    )
    op.create_index(op.f('ix_foundation_baselines_status'), 'foundation_baselines', ['status'], unique=False)

    op.create_table(
        'foundation_baseline_elements',
        sa.Column('baseline_id', aos_core.models.GUID(), nullable=False),
        sa.Column('source_element_id', aos_core.models.GUID(), nullable=False),
        sa.Column('domain', sa.String(length=64), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('decision', sa.Text(), nullable=False),
        sa.Column('rationale', sa.Text(), nullable=False),
        sa.Column('verification_method', sa.Text(), nullable=False),
        sa.Column('technology_refs', aos_core.models.JSONField(), nullable=False),
        sa.Column('claim_ids', aos_core.models.JSONField(), nullable=False),
        sa.Column('requirement_ids', aos_core.models.JSONField(), nullable=False),
        sa.Column('alternatives_rejected', aos_core.models.JSONField(), nullable=False),
        sa.Column('tradeoffs', aos_core.models.JSONField(), nullable=False),
        sa.Column('risks', aos_core.models.JSONField(), nullable=False),
        sa.Column('content_hash', sa.String(length=64), nullable=False),
        *_audit_columns(),
        sa.ForeignKeyConstraint(['baseline_id'], ['foundation_baselines.id']),
        sa.ForeignKeyConstraint(['source_element_id'], ['foundation_elements.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        op.f('ix_foundation_baseline_elements_baseline_id'), 'foundation_baseline_elements', ['baseline_id'],
        unique=False,
    )
    op.create_index(
        op.f('ix_foundation_baseline_elements_source_element_id'), 'foundation_baseline_elements',
        ['source_element_id'], unique=False,
    )
    op.create_index(
        op.f('ix_foundation_baseline_elements_status'), 'foundation_baseline_elements', ['status'], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f('ix_foundation_baseline_elements_status'), table_name='foundation_baseline_elements')
    op.drop_index(
        op.f('ix_foundation_baseline_elements_source_element_id'), table_name='foundation_baseline_elements'
    )
    op.drop_index(op.f('ix_foundation_baseline_elements_baseline_id'), table_name='foundation_baseline_elements')
    op.drop_table('foundation_baseline_elements')

    op.drop_index(op.f('ix_foundation_baselines_status'), table_name='foundation_baselines')
    op.drop_index(op.f('ix_foundation_baselines_baseline_hash'), table_name='foundation_baselines')
    op.drop_index(op.f('ix_foundation_baselines_supersedes_baseline_id'), table_name='foundation_baselines')
    op.drop_index(op.f('ix_foundation_baselines_approved_decision_id'), table_name='foundation_baselines')
    op.drop_index(op.f('ix_foundation_baselines_corpus_snapshot_id'), table_name='foundation_baselines')
    op.drop_index(op.f('ix_foundation_baselines_target_genome_snapshot_id'), table_name='foundation_baselines')
    op.drop_index(op.f('ix_foundation_baselines_selection_run_id'), table_name='foundation_baselines')
    op.drop_index(op.f('ix_foundation_baselines_candidate_id'), table_name='foundation_baselines')
    op.drop_index(op.f('ix_foundation_baselines_project_id'), table_name='foundation_baselines')
    op.drop_table('foundation_baselines')
