"""per-project audit toggle

Revision ID: 0015
Revises: 0014
Create Date: 2026-07-09 00:00:00.000000

AOS-SELFHEAL (per-project MVP): a project opts into the nightly audit loop with
``projects.audits_enabled``; ``audit_heartbeats`` gains a soft ``project_id`` so
the same routine can report independently per project. The old single-column
unique index on ``routine`` becomes non-unique and a composite unique
(routine, project_id) replaces it (a global routine keeps project_id NULL).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

import aos_core.models  # GUID / JSONField TypeDecorators


revision: str = '0015'
down_revision: Union[str, None] = '0014'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'projects',
        sa.Column('audits_enabled', sa.Boolean(), nullable=False, server_default=sa.false()),
    )

    op.add_column('audit_heartbeats', sa.Column('project_id', aos_core.models.GUID(), nullable=True))
    op.create_index(
        op.f('ix_audit_heartbeats_project_id'), 'audit_heartbeats', ['project_id'], unique=False
    )
    # Replace the single-column unique index on routine with a non-unique index +
    # a composite unique (routine, project_id) so per-project rows don't collide.
    op.drop_index(op.f('ix_audit_heartbeats_routine'), table_name='audit_heartbeats')
    op.create_index(op.f('ix_audit_heartbeats_routine'), 'audit_heartbeats', ['routine'], unique=False)
    op.create_unique_constraint(
        'uq_audit_heartbeats_routine_project', 'audit_heartbeats', ['routine', 'project_id']
    )


def downgrade() -> None:
    op.drop_constraint('uq_audit_heartbeats_routine_project', 'audit_heartbeats', type_='unique')
    op.drop_index(op.f('ix_audit_heartbeats_routine'), table_name='audit_heartbeats')
    op.create_index(op.f('ix_audit_heartbeats_routine'), 'audit_heartbeats', ['routine'], unique=True)
    op.drop_index(op.f('ix_audit_heartbeats_project_id'), table_name='audit_heartbeats')
    op.drop_column('audit_heartbeats', 'project_id')

    op.drop_column('projects', 'audits_enabled')
