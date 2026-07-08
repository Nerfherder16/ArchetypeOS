"""voice inbox items (Voice Command Center)

Revision ID: 0008
Revises: 0007
Create Date: 2026-07-08 00:00:00.000000

AOS-VOICE-001: the Voice Command Center spine. One ``voice_inbox_items`` row per
voice turn — a review-first draft (transcript, detected intent/project, suggested
action, confidence, spoken reply). Voice mode captures and prepares work; it never
performs destructive actions directly, so every turn lands here for later approval.
Dialect-agnostic DDL (GUID/JSONField degrade on sqlite), so it applies on the CI
Postgres service and the hermetic sqlite path alike.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

import aos_core.models  # provides the GUID / JSONField TypeDecorators referenced below


# revision identifiers, used by Alembic.
revision: str = '0008'
down_revision: Union[str, None] = '0007'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'voice_inbox_items',
        sa.Column('project_id', aos_core.models.GUID(), nullable=True),
        sa.Column('transcript', sa.Text(), nullable=False),
        sa.Column('summary', sa.Text(), nullable=False),
        sa.Column('detected_intent', sa.String(length=64), nullable=False),
        sa.Column('detected_project', sa.String(length=255), nullable=True),
        sa.Column('suggested_action', sa.Text(), nullable=False),
        sa.Column('confidence', sa.Float(), nullable=False),
        sa.Column('required_review', sa.Boolean(), nullable=False),
        sa.Column('review_state', sa.String(length=32), nullable=False),
        sa.Column('source_device', sa.String(length=128), nullable=False),
        sa.Column('reply_text', sa.Text(), nullable=False),
        sa.Column('id', aos_core.models.GUID(), nullable=False),
        sa.Column('status', sa.String(length=64), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_by', sa.String(length=128), nullable=False),
        sa.Column('updated_by', sa.String(length=128), nullable=False),
        sa.Column('metadata', aos_core.models.JSONField(), nullable=False),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_voice_inbox_items_detected_intent'), 'voice_inbox_items', ['detected_intent'], unique=False)
    op.create_index(op.f('ix_voice_inbox_items_project_id'), 'voice_inbox_items', ['project_id'], unique=False)
    op.create_index(op.f('ix_voice_inbox_items_review_state'), 'voice_inbox_items', ['review_state'], unique=False)
    op.create_index(op.f('ix_voice_inbox_items_status'), 'voice_inbox_items', ['status'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_voice_inbox_items_status'), table_name='voice_inbox_items')
    op.drop_index(op.f('ix_voice_inbox_items_review_state'), table_name='voice_inbox_items')
    op.drop_index(op.f('ix_voice_inbox_items_project_id'), table_name='voice_inbox_items')
    op.drop_index(op.f('ix_voice_inbox_items_detected_intent'), table_name='voice_inbox_items')
    op.drop_table('voice_inbox_items')
