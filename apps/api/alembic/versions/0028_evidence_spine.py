"""evidence spine

Revision ID: 0028
Revises: 0027
Create Date: 2026-07-12 08:00:00.000000

RFC-0018 (Foundation Intelligence Slice 1: Evidence Spine, AOS-EVIDENCE-MODELS-001):
adds the ten evidence-domain tables — ``evidence_sources``,
``evidence_source_versions``, ``evidence_fragments``, ``claims``,
``claim_evidence_links``, ``claim_relationships``, ``evidence_conflicts``,
``corpus_snapshots``, ``corpus_snapshot_sources``, ``open_questions`` — the
claim-centric evidence graph as first-class, queryable, versioned rows.
Additive only, dialect-agnostic DDL (mirrors 0026/0027's style).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

import aos_core.models  # GUID / JSONField TypeDecorators


revision: str = '0028'
down_revision: Union[str, None] = '0027'
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
        'evidence_sources',
        sa.Column('project_id', aos_core.models.GUID(), nullable=False),
        sa.Column('source_type', sa.String(length=64), nullable=False),
        sa.Column('origin', sa.String(length=64), nullable=False),
        sa.Column('originator', sa.String(length=255), nullable=False),
        sa.Column('canonical_uri', sa.Text(), nullable=True),
        sa.Column('sensitivity', sa.String(length=32), nullable=False),
        sa.Column('authority_domains', aos_core.models.JSONField(), nullable=False),
        sa.Column('access_policy_id', sa.String(length=128), nullable=True),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('minted_by', sa.String(length=32), nullable=False),
        sa.Column('content_hash', sa.String(length=64), nullable=True),
        *_audit_columns(),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_evidence_sources_project_id'), 'evidence_sources', ['project_id'], unique=False)
    op.create_index(op.f('ix_evidence_sources_content_hash'), 'evidence_sources', ['content_hash'], unique=False)
    op.create_index(op.f('ix_evidence_sources_status'), 'evidence_sources', ['status'], unique=False)

    op.create_table(
        'evidence_source_versions',
        sa.Column('source_id', aos_core.models.GUID(), nullable=False),
        sa.Column('version_ref', sa.String(length=255), nullable=False),
        sa.Column('content_hash', sa.String(length=64), nullable=False),
        sa.Column('captured_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('effective_from', sa.DateTime(timezone=True), nullable=True),
        sa.Column('effective_until', sa.DateTime(timezone=True), nullable=True),
        sa.Column('supersedes_version_id', aos_core.models.GUID(), nullable=True),
        sa.Column('ingestion_method', sa.String(length=64), nullable=False),
        sa.Column('parser_version', sa.String(length=128), nullable=True),
        sa.Column('minted_by', sa.String(length=32), nullable=False),
        *_audit_columns(),
        sa.ForeignKeyConstraint(['source_id'], ['evidence_sources.id']),
        sa.ForeignKeyConstraint(['supersedes_version_id'], ['evidence_source_versions.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        op.f('ix_evidence_source_versions_source_id'), 'evidence_source_versions', ['source_id'], unique=False
    )
    op.create_index(
        op.f('ix_evidence_source_versions_content_hash'), 'evidence_source_versions', ['content_hash'], unique=False
    )
    op.create_index(
        op.f('ix_evidence_source_versions_supersedes_version_id'),
        'evidence_source_versions', ['supersedes_version_id'], unique=False,
    )
    op.create_index(
        op.f('ix_evidence_source_versions_status'), 'evidence_source_versions', ['status'], unique=False
    )

    op.create_table(
        'evidence_fragments',
        sa.Column('source_version_id', aos_core.models.GUID(), nullable=False),
        sa.Column('locator', aos_core.models.JSONField(), nullable=False),
        sa.Column('content_hash', sa.String(length=64), nullable=False),
        sa.Column('excerpt', sa.Text(), nullable=False),
        sa.Column('extraction_method', sa.String(length=64), nullable=False),
        sa.Column('extraction_confidence', sa.Float(), nullable=False),
        sa.Column('minted_by', sa.String(length=32), nullable=False),
        *_audit_columns(),
        sa.ForeignKeyConstraint(['source_version_id'], ['evidence_source_versions.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        op.f('ix_evidence_fragments_source_version_id'), 'evidence_fragments', ['source_version_id'], unique=False
    )
    op.create_index(
        op.f('ix_evidence_fragments_content_hash'), 'evidence_fragments', ['content_hash'], unique=False
    )
    op.create_index(op.f('ix_evidence_fragments_status'), 'evidence_fragments', ['status'], unique=False)

    op.create_table(
        'claims',
        sa.Column('project_id', aos_core.models.GUID(), nullable=False),
        sa.Column('statement', sa.Text(), nullable=False),
        sa.Column('claim_type', sa.String(length=64), nullable=False),
        sa.Column('truth_layer', sa.String(length=32), nullable=False),
        sa.Column('domain', sa.String(length=128), nullable=False),
        sa.Column('scope', aos_core.models.JSONField(), nullable=False),
        sa.Column('polarity', sa.String(length=32), nullable=False),
        sa.Column('confidence', sa.Float(), nullable=False),
        sa.Column('materiality', sa.String(length=32), nullable=False),
        sa.Column('valid_from', sa.DateTime(timezone=True), nullable=True),
        sa.Column('valid_until', sa.DateTime(timezone=True), nullable=True),
        sa.Column('derivation', aos_core.models.JSONField(), nullable=False),
        sa.Column('minted_by', sa.String(length=32), nullable=False),
        sa.Column('decision_id', aos_core.models.GUID(), nullable=True),
        sa.Column('content_hash', sa.String(length=64), nullable=True),
        *_audit_columns(),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id']),
        sa.ForeignKeyConstraint(['decision_id'], ['decisions.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_claims_project_id'), 'claims', ['project_id'], unique=False)
    op.create_index(op.f('ix_claims_truth_layer'), 'claims', ['truth_layer'], unique=False)
    op.create_index(op.f('ix_claims_decision_id'), 'claims', ['decision_id'], unique=False)
    op.create_index(op.f('ix_claims_content_hash'), 'claims', ['content_hash'], unique=False)
    op.create_index(op.f('ix_claims_status'), 'claims', ['status'], unique=False)
    op.create_index('ix_claims_project_id_truth_layer', 'claims', ['project_id', 'truth_layer'], unique=False)

    op.create_table(
        'claim_evidence_links',
        sa.Column('claim_id', aos_core.models.GUID(), nullable=False),
        sa.Column('fragment_id', aos_core.models.GUID(), nullable=False),
        sa.Column('relationship', sa.String(length=32), nullable=False),
        sa.Column('relevance', sa.Float(), nullable=False),
        sa.Column('strength', sa.String(length=32), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('minted_by', sa.String(length=32), nullable=False),
        *_audit_columns(),
        sa.ForeignKeyConstraint(['claim_id'], ['claims.id']),
        sa.ForeignKeyConstraint(['fragment_id'], ['evidence_fragments.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint(
            'claim_id', 'fragment_id', 'relationship', name='uq_claim_evidence_links_claim_fragment_rel'
        ),
    )
    op.create_index(op.f('ix_claim_evidence_links_claim_id'), 'claim_evidence_links', ['claim_id'], unique=False)
    op.create_index(
        op.f('ix_claim_evidence_links_fragment_id'), 'claim_evidence_links', ['fragment_id'], unique=False
    )
    op.create_index(op.f('ix_claim_evidence_links_status'), 'claim_evidence_links', ['status'], unique=False)

    op.create_table(
        'claim_relationships',
        sa.Column('from_claim_id', aos_core.models.GUID(), nullable=False),
        sa.Column('to_claim_id', aos_core.models.GUID(), nullable=False),
        sa.Column('relationship', sa.String(length=32), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('minted_by', sa.String(length=32), nullable=False),
        *_audit_columns(),
        sa.ForeignKeyConstraint(['from_claim_id'], ['claims.id']),
        sa.ForeignKeyConstraint(['to_claim_id'], ['claims.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_claim_relationships_from_claim_id'), 'claim_relationships', ['from_claim_id'], unique=False)
    op.create_index(op.f('ix_claim_relationships_to_claim_id'), 'claim_relationships', ['to_claim_id'], unique=False)
    op.create_index(op.f('ix_claim_relationships_status'), 'claim_relationships', ['status'], unique=False)

    op.create_table(
        'evidence_conflicts',
        sa.Column('project_id', aos_core.models.GUID(), nullable=False),
        sa.Column('claim_ids', aos_core.models.JSONField(), nullable=False),
        sa.Column('conflict_type', sa.String(length=64), nullable=False),
        sa.Column('materiality', sa.String(length=32), nullable=False),
        sa.Column('resolution', sa.Text(), nullable=True),
        sa.Column('resolution_decision_id', aos_core.models.GUID(), nullable=True),
        sa.Column('blocking_stages', aos_core.models.JSONField(), nullable=False),
        sa.Column('minted_by', sa.String(length=32), nullable=False),
        *_audit_columns(),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id']),
        sa.ForeignKeyConstraint(['resolution_decision_id'], ['decisions.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_evidence_conflicts_project_id'), 'evidence_conflicts', ['project_id'], unique=False)
    op.create_index(
        op.f('ix_evidence_conflicts_resolution_decision_id'),
        'evidence_conflicts', ['resolution_decision_id'], unique=False,
    )
    op.create_index(op.f('ix_evidence_conflicts_status'), 'evidence_conflicts', ['status'], unique=False)

    op.create_table(
        'corpus_snapshots',
        sa.Column('project_id', aos_core.models.GUID(), nullable=False),
        sa.Column('source_version_ids', aos_core.models.JSONField(), nullable=False),
        sa.Column('repository_refs', aos_core.models.JSONField(), nullable=False),
        sa.Column('claim_set_hash', sa.String(length=64), nullable=True),
        sa.Column('purpose', sa.String(length=255), nullable=False),
        *_audit_columns(),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_corpus_snapshots_project_id'), 'corpus_snapshots', ['project_id'], unique=False)
    op.create_index(
        op.f('ix_corpus_snapshots_claim_set_hash'), 'corpus_snapshots', ['claim_set_hash'], unique=False
    )
    op.create_index(op.f('ix_corpus_snapshots_status'), 'corpus_snapshots', ['status'], unique=False)

    op.create_table(
        'corpus_snapshot_sources',
        sa.Column('snapshot_id', aos_core.models.GUID(), nullable=False),
        sa.Column('source_version_id', aos_core.models.GUID(), nullable=False),
        *_audit_columns(),
        sa.ForeignKeyConstraint(['snapshot_id'], ['corpus_snapshots.id']),
        sa.ForeignKeyConstraint(['source_version_id'], ['evidence_source_versions.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint(
            'snapshot_id', 'source_version_id', name='uq_corpus_snapshot_sources_snapshot_version'
        ),
    )
    op.create_index(
        op.f('ix_corpus_snapshot_sources_snapshot_id'), 'corpus_snapshot_sources', ['snapshot_id'], unique=False
    )
    op.create_index(
        op.f('ix_corpus_snapshot_sources_source_version_id'),
        'corpus_snapshot_sources', ['source_version_id'], unique=False,
    )
    op.create_index(op.f('ix_corpus_snapshot_sources_status'), 'corpus_snapshot_sources', ['status'], unique=False)

    op.create_table(
        'open_questions',
        sa.Column('project_id', aos_core.models.GUID(), nullable=False),
        sa.Column('genome_snapshot_id', aos_core.models.GUID(), nullable=True),
        sa.Column('question', sa.Text(), nullable=False),
        sa.Column('affected_dimensions', aos_core.models.JSONField(), nullable=False),
        sa.Column('affected_foundation_domains', aos_core.models.JSONField(), nullable=False),
        sa.Column('materiality', sa.String(length=32), nullable=False),
        sa.Column('reason', sa.Text(), nullable=False),
        sa.Column('answer_type', sa.String(length=32), nullable=False),
        sa.Column('answer_claim_id', aos_core.models.GUID(), nullable=True),
        sa.Column('minted_by', sa.String(length=32), nullable=False),
        *_audit_columns(),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id']),
        sa.ForeignKeyConstraint(['answer_claim_id'], ['claims.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_open_questions_project_id'), 'open_questions', ['project_id'], unique=False)
    op.create_index(
        op.f('ix_open_questions_genome_snapshot_id'), 'open_questions', ['genome_snapshot_id'], unique=False
    )
    op.create_index(
        op.f('ix_open_questions_answer_claim_id'), 'open_questions', ['answer_claim_id'], unique=False
    )
    op.create_index(op.f('ix_open_questions_status'), 'open_questions', ['status'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_open_questions_status'), table_name='open_questions')
    op.drop_index(op.f('ix_open_questions_answer_claim_id'), table_name='open_questions')
    op.drop_index(op.f('ix_open_questions_genome_snapshot_id'), table_name='open_questions')
    op.drop_index(op.f('ix_open_questions_project_id'), table_name='open_questions')
    op.drop_table('open_questions')

    op.drop_index(op.f('ix_corpus_snapshot_sources_status'), table_name='corpus_snapshot_sources')
    op.drop_index(op.f('ix_corpus_snapshot_sources_source_version_id'), table_name='corpus_snapshot_sources')
    op.drop_index(op.f('ix_corpus_snapshot_sources_snapshot_id'), table_name='corpus_snapshot_sources')
    op.drop_table('corpus_snapshot_sources')

    op.drop_index(op.f('ix_corpus_snapshots_status'), table_name='corpus_snapshots')
    op.drop_index(op.f('ix_corpus_snapshots_claim_set_hash'), table_name='corpus_snapshots')
    op.drop_index(op.f('ix_corpus_snapshots_project_id'), table_name='corpus_snapshots')
    op.drop_table('corpus_snapshots')

    op.drop_index(op.f('ix_evidence_conflicts_status'), table_name='evidence_conflicts')
    op.drop_index(op.f('ix_evidence_conflicts_resolution_decision_id'), table_name='evidence_conflicts')
    op.drop_index(op.f('ix_evidence_conflicts_project_id'), table_name='evidence_conflicts')
    op.drop_table('evidence_conflicts')

    op.drop_index(op.f('ix_claim_relationships_status'), table_name='claim_relationships')
    op.drop_index(op.f('ix_claim_relationships_to_claim_id'), table_name='claim_relationships')
    op.drop_index(op.f('ix_claim_relationships_from_claim_id'), table_name='claim_relationships')
    op.drop_table('claim_relationships')

    op.drop_index(op.f('ix_claim_evidence_links_status'), table_name='claim_evidence_links')
    op.drop_index(op.f('ix_claim_evidence_links_fragment_id'), table_name='claim_evidence_links')
    op.drop_index(op.f('ix_claim_evidence_links_claim_id'), table_name='claim_evidence_links')
    op.drop_table('claim_evidence_links')

    op.drop_index('ix_claims_project_id_truth_layer', table_name='claims')
    op.drop_index(op.f('ix_claims_status'), table_name='claims')
    op.drop_index(op.f('ix_claims_content_hash'), table_name='claims')
    op.drop_index(op.f('ix_claims_decision_id'), table_name='claims')
    op.drop_index(op.f('ix_claims_truth_layer'), table_name='claims')
    op.drop_index(op.f('ix_claims_project_id'), table_name='claims')
    op.drop_table('claims')

    op.drop_index(op.f('ix_evidence_fragments_status'), table_name='evidence_fragments')
    op.drop_index(op.f('ix_evidence_fragments_content_hash'), table_name='evidence_fragments')
    op.drop_index(op.f('ix_evidence_fragments_source_version_id'), table_name='evidence_fragments')
    op.drop_table('evidence_fragments')

    op.drop_index(op.f('ix_evidence_source_versions_status'), table_name='evidence_source_versions')
    op.drop_index(op.f('ix_evidence_source_versions_supersedes_version_id'), table_name='evidence_source_versions')
    op.drop_index(op.f('ix_evidence_source_versions_content_hash'), table_name='evidence_source_versions')
    op.drop_index(op.f('ix_evidence_source_versions_source_id'), table_name='evidence_source_versions')
    op.drop_table('evidence_source_versions')

    op.drop_index(op.f('ix_evidence_sources_status'), table_name='evidence_sources')
    op.drop_index(op.f('ix_evidence_sources_content_hash'), table_name='evidence_sources')
    op.drop_index(op.f('ix_evidence_sources_project_id'), table_name='evidence_sources')
    op.drop_table('evidence_sources')
