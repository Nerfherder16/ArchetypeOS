"""repository capabilities (capability-level reuse)

Revision ID: 0026
Revises: 0025
Create Date: 2026-07-11 04:00:00.000000

RFC-0013 (Capability-Level Reuse Matching, Slice 2): persists the named,
reuse-oriented capabilities distillation already extracts (``{name, description,
provenance}``) at **capability granularity** so the Transfer Engine can match a
reuse need against a single capability's embedding instead of a whole-product
blob. Adds ``repository_capabilities`` with a nullable pgvector ``embedding``
column + a cosine (ivfflat) index for ``embedding <=> need`` retrieval.

The base table DDL is dialect-agnostic (``op.create_table``); the ``VECTOR`` +
``CREATE EXTENSION`` + ivfflat index are Postgres-only, so on any other dialect
the embedding column is added as a benign JSON column (parity with the model's
``EmbeddingColumn`` dialect variant, which the hermetic sqlite path gets via
``Base.metadata.create_all``). Downgrade drops the table (and its index);
the ``vector`` extension is left installed (shared, cheap).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

import aos_core.models  # GUID / JSONField TypeDecorators
from aos_core.config import EMBEDDING_DIM


revision: str = '0026'
down_revision: Union[str, None] = '0025'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_INDEX_NAME = "ix_repository_capabilities_embedding_cosine"


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
        'repository_capabilities',
        sa.Column('repository_id', aos_core.models.GUID(), nullable=False),
        sa.Column('knowledge_page_id', aos_core.models.GUID(), nullable=True),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('provenance', aos_core.models.JSONField(), nullable=False),
        *_audit_columns(),
        sa.ForeignKeyConstraint(['repository_id'], ['repositories.id']),
        sa.ForeignKeyConstraint(['knowledge_page_id'], ['knowledge_pages.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        op.f('ix_repository_capabilities_repository_id'),
        'repository_capabilities', ['repository_id'], unique=False,
    )
    op.create_index(
        op.f('ix_repository_capabilities_knowledge_page_id'),
        'repository_capabilities', ['knowledge_page_id'], unique=False,
    )
    op.create_index(
        op.f('ix_repository_capabilities_status'),
        'repository_capabilities', ['status'], unique=False,
    )

    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("CREATE EXTENSION IF NOT EXISTS vector")
        op.execute(
            f"ALTER TABLE repository_capabilities ADD COLUMN embedding vector({EMBEDDING_DIM})"
        )
        # Cosine ANN index (ivfflat, vector_cosine_ops) for `embedding <=> need_vec`
        # ordering. Valid (and re-buildable) on an empty table; retrieval also works
        # without it.
        op.execute(
            f"CREATE INDEX {_INDEX_NAME} ON repository_capabilities "
            "USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100)"
        )
    else:
        # Non-postgres deploy migrated via alembic: add the benign JSON embedding
        # column so the schema matches the model's dialect-variant column (the
        # hermetic sqlite unit/CI path builds it via create_all instead).
        op.add_column(
            'repository_capabilities', sa.Column('embedding', sa.JSON(), nullable=True)
        )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute(f"DROP INDEX IF EXISTS {_INDEX_NAME}")
    op.drop_index(op.f('ix_repository_capabilities_status'), table_name='repository_capabilities')
    op.drop_index(op.f('ix_repository_capabilities_knowledge_page_id'), table_name='repository_capabilities')
    op.drop_index(op.f('ix_repository_capabilities_repository_id'), table_name='repository_capabilities')
    op.drop_table('repository_capabilities')
