"""job leases (crash recovery)

Revision ID: 0017
Revises: 0016
Create Date: 2026-07-11 00:10:00.000000

AOS-JOBS-RELIABILITY-001 / RFC-0014 Slice 2: a worker takes a time-boxed lease
(``claimed_by`` + ``lease_expires_at``) when it claims a job via a compare-and-swap
UPDATE. If the worker process dies, the lease expires and a reaper recovers the
job (re-arming its outbox row for redelivery), closing the crash-recovery half of
finding P0-1. Additive nullable columns — no drops/alters.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '0017'
down_revision: Union[str, None] = '0016'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('jobs', sa.Column('claimed_by', sa.String(length=128), nullable=True))
    op.add_column('jobs', sa.Column('lease_expires_at', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column('jobs', 'lease_expires_at')
    op.drop_column('jobs', 'claimed_by')
