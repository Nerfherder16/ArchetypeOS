"""job-output idempotency (unique origin job)

Revision ID: 0018
Revises: 0017
Create Date: 2026-07-11 00:20:00.000000

AOS-JOBS-RELIABILITY-001 / RFC-0014 Slice 3: a job's domain output is unique to
its originating job, so a redelivered job (recovered after a crash between the
domain commit and job completion) cannot create a duplicate (finding P0-3).
Adds ``job_id`` to ``nightly_digests`` and ``research_notes`` (``council_reviews``
and ``research_runs`` already carry it) and a unique constraint on ``job_id`` for
all four. NULL job_id is exempt — Postgres treats NULLs as distinct, so rows
created outside a job never collide. Constraint DDL is ALTER-based (Postgres
path, like migration 0015); the hermetic sqlite tests build the same constraints
via ``Base.metadata.create_all`` from the models' ``__table_args__``.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

import aos_core.models  # GUID TypeDecorator


revision: str = '0018'
down_revision: Union[str, None] = '0017'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # New job_id columns (+ FK + index) on the two tables that lacked them.
    for table in ('nightly_digests', 'research_notes'):
        op.add_column(table, sa.Column('job_id', aos_core.models.GUID(), nullable=True))
        op.create_index(op.f(f'ix_{table}_job_id'), table, ['job_id'], unique=False)
        op.create_foreign_key(f'fk_{table}_job_id', table, 'jobs', ['job_id'], ['id'])

    # Unique (origin) job across all four job-output tables.
    op.create_unique_constraint('uq_council_reviews_job_id', 'council_reviews', ['job_id'])
    op.create_unique_constraint('uq_research_runs_job_id', 'research_runs', ['job_id'])
    op.create_unique_constraint('uq_nightly_digests_job_id', 'nightly_digests', ['job_id'])
    op.create_unique_constraint('uq_research_notes_job_id', 'research_notes', ['job_id'])


def downgrade() -> None:
    op.drop_constraint('uq_research_notes_job_id', 'research_notes', type_='unique')
    op.drop_constraint('uq_nightly_digests_job_id', 'nightly_digests', type_='unique')
    op.drop_constraint('uq_research_runs_job_id', 'research_runs', type_='unique')
    op.drop_constraint('uq_council_reviews_job_id', 'council_reviews', type_='unique')

    for table in ('research_notes', 'nightly_digests'):
        op.drop_constraint(f'fk_{table}_job_id', table, type_='foreignkey')
        op.drop_index(op.f(f'ix_{table}_job_id'), table_name=table)
        op.drop_column(table, 'job_id')
