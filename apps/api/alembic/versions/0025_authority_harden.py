"""authority envelope hardening: binding, execution linkage, expiry, repo sensitivity

Revision ID: 0025
Revises: 0024
Create Date: 2026-07-11 13:00:00.000000

AOS-AUTHORITY-HARDEN-001: binds an ActionRequest to its repository, links the job
that consumed it (execution trace), and gives it an expiry; adds a repository
sensitivity policy so egress derives its authority sensitivity from the repo instead
of hardcoding public. Additive nullable/defaulted columns; dialect-agnostic (no FK
constraints added via ALTER — the ORM models carry the FKs for create_all/Postgres).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

import aos_core.models  # GUID TypeDecorator


revision: str = '0025'
down_revision: Union[str, None] = '0024'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('action_requests', sa.Column('repository_id', aos_core.models.GUID(), nullable=True))
    op.add_column('action_requests', sa.Column('job_id', aos_core.models.GUID(), nullable=True))
    op.add_column('action_requests', sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True))
    op.create_index(op.f('ix_action_requests_repository_id'), 'action_requests', ['repository_id'], unique=False)
    op.create_index(op.f('ix_action_requests_job_id'), 'action_requests', ['job_id'], unique=False)
    op.add_column('repositories', sa.Column('sensitivity', sa.String(length=32), nullable=False, server_default='public'))


def downgrade() -> None:
    op.drop_column('repositories', 'sensitivity')
    op.drop_index(op.f('ix_action_requests_job_id'), table_name='action_requests')
    op.drop_index(op.f('ix_action_requests_repository_id'), table_name='action_requests')
    op.drop_column('action_requests', 'expires_at')
    op.drop_column('action_requests', 'job_id')
    op.drop_column('action_requests', 'repository_id')
