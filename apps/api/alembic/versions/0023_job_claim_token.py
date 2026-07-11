"""job claim fencing token

Revision ID: 0023
Revises: 0022
Create Date: 2026-07-11 06:40:00.000000

AOS-JOB-FENCING-001: adds ``jobs.claim_token`` — an opaque fencing token minted on
every successful lease claim. Worker-side transitions (renew/complete/fail/retry)
compare-and-swap on it, so a stale worker that lost its lease can no longer mutate
a job another worker (or the reaper) has re-claimed. Additive, nullable column;
dialect-agnostic DDL.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '0023'
down_revision: Union[str, None] = '0022'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('jobs', sa.Column('claim_token', sa.String(length=64), nullable=True))


def downgrade() -> None:
    op.drop_column('jobs', 'claim_token')
