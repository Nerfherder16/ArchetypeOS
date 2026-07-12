"""system genome

Revision ID: 0029
Revises: 0028
Create Date: 2026-07-12 09:00:00.000000

RFC-0019 (Foundation Intelligence Slice 2: System Genome MVP,
AOS-GENOME-MODELS-001): adds the five genome-domain tables —
``genome_snapshots``, ``genome_traits``, ``genome_trait_claims``,
``system_archetypes``, ``genome_deltas`` — the versioned, evidence-backed
system classification derived deterministically from ``claims`` (AD-4; never
from ``repository_dna`` directly). Also wires the ``open_questions.
genome_snapshot_id`` column (added nullable, no-FK, in 0028) to a real foreign
key now that ``genome_snapshots`` exists. Additive only, dialect-agnostic DDL
(mirrors 0028's style).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

import aos_core.models  # GUID / JSONField TypeDecorators


revision: str = '0029'
down_revision: Union[str, None] = '0028'
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
        'genome_snapshots',
        sa.Column('project_id', aos_core.models.GUID(), nullable=False),
        sa.Column('corpus_snapshot_id', aos_core.models.GUID(), nullable=True),
        sa.Column('state_view', sa.String(length=32), nullable=False),
        # `version` is provided by _audit_columns() below — do NOT list it here too
        # (a second 'version' collides: DuplicateColumnError on genome_snapshots; LES-042).
        sa.Column('summary', sa.Text(), nullable=False),
        sa.Column('coverage', sa.Float(), nullable=False),
        sa.Column('aggregate_confidence', sa.Float(), nullable=False),
        sa.Column('open_question_count', sa.Integer(), nullable=False),
        sa.Column('critical_conflict_count', sa.Integer(), nullable=False),
        sa.Column('generated_by', sa.String(length=128), nullable=False),
        sa.Column('approved_by', sa.String(length=128), nullable=True),
        sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True),
        *_audit_columns(),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id']),
        sa.ForeignKeyConstraint(['corpus_snapshot_id'], ['corpus_snapshots.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_genome_snapshots_project_id'), 'genome_snapshots', ['project_id'], unique=False)
    op.create_index(
        op.f('ix_genome_snapshots_corpus_snapshot_id'), 'genome_snapshots', ['corpus_snapshot_id'], unique=False
    )
    op.create_index(op.f('ix_genome_snapshots_state_view'), 'genome_snapshots', ['state_view'], unique=False)
    op.create_index(op.f('ix_genome_snapshots_status'), 'genome_snapshots', ['status'], unique=False)

    op.create_table(
        'genome_traits',
        sa.Column('genome_snapshot_id', aos_core.models.GUID(), nullable=False),
        sa.Column('dimension', sa.String(length=64), nullable=False),
        sa.Column('trait_key', sa.String(length=128), nullable=False),
        sa.Column('value', aos_core.models.JSONField(), nullable=True),
        sa.Column('value_type', sa.String(length=32), nullable=False),
        sa.Column('classification', sa.String(length=32), nullable=False),
        sa.Column('confidence', sa.Float(), nullable=False),
        sa.Column('stability', sa.String(length=32), nullable=False),
        sa.Column('criticality', sa.String(length=32), nullable=False),
        sa.Column('rationale', sa.Text(), nullable=False),
        sa.Column('source_methods', aos_core.models.JSONField(), nullable=False),
        sa.Column('human_locked', sa.Boolean(), nullable=False),
        *_audit_columns(),
        sa.ForeignKeyConstraint(['genome_snapshot_id'], ['genome_snapshots.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_genome_traits_genome_snapshot_id'), 'genome_traits', ['genome_snapshot_id'], unique=False)
    op.create_index(op.f('ix_genome_traits_status'), 'genome_traits', ['status'], unique=False)
    op.create_index(
        'ix_genome_traits_snapshot_dimension', 'genome_traits', ['genome_snapshot_id', 'dimension'], unique=False
    )

    op.create_table(
        'genome_trait_claims',
        sa.Column('trait_id', aos_core.models.GUID(), nullable=False),
        sa.Column('claim_id', aos_core.models.GUID(), nullable=False),
        sa.Column('polarity', sa.String(length=32), nullable=False),
        *_audit_columns(),
        sa.ForeignKeyConstraint(['trait_id'], ['genome_traits.id']),
        sa.ForeignKeyConstraint(['claim_id'], ['claims.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('trait_id', 'claim_id', 'polarity', name='uq_genome_trait_claims_trait_claim_polarity'),
    )
    op.create_index(op.f('ix_genome_trait_claims_trait_id'), 'genome_trait_claims', ['trait_id'], unique=False)
    op.create_index(op.f('ix_genome_trait_claims_claim_id'), 'genome_trait_claims', ['claim_id'], unique=False)
    op.create_index(op.f('ix_genome_trait_claims_status'), 'genome_trait_claims', ['status'], unique=False)

    op.create_table(
        'system_archetypes',
        sa.Column('genome_snapshot_id', aos_core.models.GUID(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('tier', sa.String(length=32), nullable=False),
        sa.Column('confidence', sa.Float(), nullable=False),
        sa.Column('trait_ids', aos_core.models.JSONField(), nullable=False),
        *_audit_columns(),
        sa.ForeignKeyConstraint(['genome_snapshot_id'], ['genome_snapshots.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        op.f('ix_system_archetypes_genome_snapshot_id'), 'system_archetypes', ['genome_snapshot_id'], unique=False
    )
    op.create_index(op.f('ix_system_archetypes_status'), 'system_archetypes', ['status'], unique=False)

    op.create_table(
        'genome_deltas',
        sa.Column('project_id', aos_core.models.GUID(), nullable=False),
        sa.Column('from_snapshot_id', aos_core.models.GUID(), nullable=False),
        sa.Column('to_snapshot_id', aos_core.models.GUID(), nullable=False),
        sa.Column('changes', aos_core.models.JSONField(), nullable=False),
        sa.Column('summary', sa.Text(), nullable=False),
        *_audit_columns(),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id']),
        sa.ForeignKeyConstraint(['from_snapshot_id'], ['genome_snapshots.id']),
        sa.ForeignKeyConstraint(['to_snapshot_id'], ['genome_snapshots.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_genome_deltas_project_id'), 'genome_deltas', ['project_id'], unique=False)
    op.create_index(op.f('ix_genome_deltas_from_snapshot_id'), 'genome_deltas', ['from_snapshot_id'], unique=False)
    op.create_index(op.f('ix_genome_deltas_to_snapshot_id'), 'genome_deltas', ['to_snapshot_id'], unique=False)
    op.create_index(op.f('ix_genome_deltas_status'), 'genome_deltas', ['status'], unique=False)

    # Wire the existing (0028, soft/no-FK) open_questions.genome_snapshot_id
    # column to genome_snapshots now that the table exists.
    op.create_foreign_key(
        'fk_open_questions_genome_snapshot_id', 'open_questions', 'genome_snapshots', ['genome_snapshot_id'], ['id']
    )


def downgrade() -> None:
    op.drop_constraint('fk_open_questions_genome_snapshot_id', 'open_questions', type_='foreignkey')

    op.drop_index(op.f('ix_genome_deltas_status'), table_name='genome_deltas')
    op.drop_index(op.f('ix_genome_deltas_to_snapshot_id'), table_name='genome_deltas')
    op.drop_index(op.f('ix_genome_deltas_from_snapshot_id'), table_name='genome_deltas')
    op.drop_index(op.f('ix_genome_deltas_project_id'), table_name='genome_deltas')
    op.drop_table('genome_deltas')

    op.drop_index(op.f('ix_system_archetypes_status'), table_name='system_archetypes')
    op.drop_index(op.f('ix_system_archetypes_genome_snapshot_id'), table_name='system_archetypes')
    op.drop_table('system_archetypes')

    op.drop_index(op.f('ix_genome_trait_claims_status'), table_name='genome_trait_claims')
    op.drop_index(op.f('ix_genome_trait_claims_claim_id'), table_name='genome_trait_claims')
    op.drop_index(op.f('ix_genome_trait_claims_trait_id'), table_name='genome_trait_claims')
    op.drop_table('genome_trait_claims')

    op.drop_index('ix_genome_traits_snapshot_dimension', table_name='genome_traits')
    op.drop_index(op.f('ix_genome_traits_status'), table_name='genome_traits')
    op.drop_index(op.f('ix_genome_traits_genome_snapshot_id'), table_name='genome_traits')
    op.drop_table('genome_traits')

    op.drop_index(op.f('ix_genome_snapshots_status'), table_name='genome_snapshots')
    op.drop_index(op.f('ix_genome_snapshots_state_view'), table_name='genome_snapshots')
    op.drop_index(op.f('ix_genome_snapshots_corpus_snapshot_id'), table_name='genome_snapshots')
    op.drop_index(op.f('ix_genome_snapshots_project_id'), table_name='genome_snapshots')
    op.drop_table('genome_snapshots')
