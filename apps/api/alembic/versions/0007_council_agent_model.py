"""council agent model (multi-model council)

Revision ID: 0006
Revises: 0005
Create Date: 2026-07-07 00:00:00.000000

AOS-LLM-EVAL-001 (flagship): record WHICH model produced each council agent's
output, so a multi-model council (each agent on a different free model) surfaces
its diversity. Adds a nullable ``agent_model`` column to
``council_agent_outputs``. Nullable so legacy rows + single-model councils are
valid. The hermetic sqlite path gets the column via ``create_all`` (model
definition); this migration is the Postgres upgrade path.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '0007'
down_revision: Union[str, None] = '0006'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "council_agent_outputs",
        sa.Column("agent_model", sa.String(length=128), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("council_agent_outputs", "agent_model")
