"""repository embedding (pgvector)

Revision ID: 0005
Revises: 0004
Create Date: 2026-07-06 00:00:00.000000

RFC-0010 (Embedding Relevance Tier, Part 1 — AOS-EMBED-001): add the pgvector
semantic index to ``knowledge_pages``. Creates the ``vector`` extension, a
nullable ``embedding vector(384)`` column, and a cosine (ivfflat /
``vector_cosine_ops``) index for ``embedding <=> need`` retrieval.

Postgres-path DDL: ``VECTOR`` + ``CREATE EXTENSION`` are Postgres-only, so this
migration is a no-op on any other dialect (the hermetic sqlite path uses
``Base.metadata.create_all`` with the model's dialect-variant column, which
degrades to a benign JSON column there). Downgrade drops the index + column and
leaves the extension in place (it may be shared by other objects).
"""
from typing import Sequence, Union

from alembic import op

from aos_core.config import EMBEDDING_DIM


# revision identifiers, used by Alembic.
revision: str = '0005'
down_revision: Union[str, None] = '0004'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_INDEX_NAME = "ix_knowledge_pages_embedding_cosine"


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        # Postgres-only DDL; sqlite/other dialects get the column via create_all.
        return
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute(f"ALTER TABLE knowledge_pages ADD COLUMN embedding vector({EMBEDDING_DIM})")
    # Cosine ANN index (ivfflat, vector_cosine_ops) for `embedding <=> need_vec`
    # ordering. ivfflat needs a non-empty table to build good lists but is valid
    # (and re-buildable) on an empty one; the retrieval path also works without it.
    op.execute(
        f"CREATE INDEX {_INDEX_NAME} ON knowledge_pages "
        "USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100)"
    )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return
    op.execute(f"DROP INDEX IF EXISTS {_INDEX_NAME}")
    op.execute("ALTER TABLE knowledge_pages DROP COLUMN IF EXISTS embedding")
    # The `vector` extension is intentionally left installed (shared, cheap).
