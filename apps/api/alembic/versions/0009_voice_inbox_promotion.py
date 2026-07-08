"""voice inbox promotion linkage

Revision ID: 0009
Revises: 0008
Create Date: 2026-07-08 00:00:00.000000

AOS-VOICE-005: when a Voice Inbox item is approved, a mapped intent promotes it
into a concrete draft entity (research_note / decision). Adds two nullable
columns recording that linkage (``promoted_kind`` + ``promoted_id``). Nullable so
existing rows and unmapped/no-project items are valid. The hermetic sqlite path
gets the columns via ``create_all``; this migration is the Postgres upgrade path.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

import aos_core.models  # provides the GUID TypeDecorator referenced below


# revision identifiers, used by Alembic.
revision: str = '0009'
down_revision: Union[str, None] = '0008'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("voice_inbox_items", sa.Column("promoted_kind", sa.String(length=64), nullable=True))
    op.add_column("voice_inbox_items", sa.Column("promoted_id", aos_core.models.GUID(), nullable=True))


def downgrade() -> None:
    op.drop_column("voice_inbox_items", "promoted_id")
    op.drop_column("voice_inbox_items", "promoted_kind")
