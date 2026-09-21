"""create audio_meter_sessions

Revision ID: a5b6c7d8e9f0
Revises: 002_battle_adventure_node
Create Date: 2026-09-21 15:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "a5b6c7d8e9f0"
down_revision: Union[str, None] = "002_battle_adventure_node"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    insp = sa.inspect(conn)
    if insp.has_table("audio_meter_sessions"):
        return
    if not insp.has_table("classrooms") or not insp.has_table("users"):
        return
    op.create_table(
        "audio_meter_sessions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("classroom_id", sa.Integer(), nullable=False),
        sa.Column("teacher_user_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("target_type", sa.String(length=16), nullable=False),
        sa.Column("target_clan_ids", sa.JSON(), nullable=False),
        sa.Column("target_student_ids", sa.JSON(), nullable=False),
        sa.Column("participant_character_ids", sa.JSON(), nullable=False),
        sa.Column("base_xp", sa.Integer(), nullable=False),
        sa.Column("base_gold", sa.Integer(), nullable=False),
        sa.Column("timer_seconds", sa.Integer(), nullable=False),
        sa.Column("hp_damage_enabled", sa.Boolean(), nullable=False),
        sa.Column("hp_damage_amount", sa.Integer(), nullable=False),
        sa.Column("trigger_count", sa.Integer(), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("xp_awarded_each", sa.Integer(), nullable=True),
        sa.Column("gold_awarded_each", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["classroom_id"], ["classrooms.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["teacher_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_audio_meter_session_classroom_status",
        "audio_meter_sessions",
        ["classroom_id", "status"],
        unique=False,
    )
    op.create_index(
        op.f("ix_audio_meter_sessions_classroom_id"),
        "audio_meter_sessions",
        ["classroom_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_audio_meter_sessions_status"),
        "audio_meter_sessions",
        ["status"],
        unique=False,
    )


def downgrade() -> None:
    conn = op.get_bind()
    insp = sa.inspect(conn)
    if not insp.has_table("audio_meter_sessions"):
        return
    op.drop_index(op.f("ix_audio_meter_sessions_status"), table_name="audio_meter_sessions")
    op.drop_index(op.f("ix_audio_meter_sessions_classroom_id"), table_name="audio_meter_sessions")
    op.drop_index("idx_audio_meter_session_classroom_status", table_name="audio_meter_sessions")
    op.drop_table("audio_meter_sessions")
