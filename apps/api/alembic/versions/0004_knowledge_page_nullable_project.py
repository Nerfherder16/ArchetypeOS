"""knowledge_page nullable project

Revision ID: 0004
Revises: 0003
Create Date: 2026-07-06 00:00:00.000000

Makes ``knowledge_pages.project_id`` nullable: lessons synced from the repo
vault (RFC-0002 / RFC-0004 read path) are global, not project-scoped. sqlite
cannot ALTER COLUMN in place, so the change goes through ``batch_alter_table``
(table rebuild) which is a no-op shape change on Postgres.

"""
from typing import Sequence, Union

from alembic import op

import aos_core.models  # provides the GUID / JSONField TypeDecorators referenced below


# revision identifiers, used by Alembic.
revision: str = '0004'
down_revision: Union[str, None] = '0003'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("knowledge_pages") as batch:
        batch.alter_column(
            "project_id",
            existing_type=aos_core.models.GUID(),
            nullable=True,
        )


def downgrade() -> None:
    with op.batch_alter_table("knowledge_pages") as batch:
        batch.alter_column(
            "project_id",
            existing_type=aos_core.models.GUID(),
            nullable=False,
        )
