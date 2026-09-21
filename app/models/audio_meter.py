"""Timed quiet-time sessions for the classroom volume meter."""

import enum

from app.models import db
from app.models.base import Base


class AudioMeterSessionStatus(str, enum.Enum):
    """Lifecycle state of one audio meter session."""

    ACTIVE = "active"
    COMPLETED = "completed"
    ABANDONED = "abandoned"


class AudioMeterSession(Base):
    """One quiet-time run: participant snapshot, locked settings, trigger count."""

    __tablename__ = "audio_meter_sessions"
    __table_args__ = (
        db.Index(
            "idx_audio_meter_session_classroom_status",
            "classroom_id",
            "status",
        ),
    )

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    classroom_id = db.Column(
        db.Integer,
        db.ForeignKey("classrooms.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    teacher_user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    status = db.Column(
        db.String(16),
        nullable=False,
        default=AudioMeterSessionStatus.ACTIVE.value,
        index=True,
    )
    target_type = db.Column(db.String(16), nullable=False)
    target_clan_ids = db.Column(db.JSON, nullable=False)
    target_student_ids = db.Column(db.JSON, nullable=False)
    participant_character_ids = db.Column(db.JSON, nullable=False)
    base_xp = db.Column(db.Integer, nullable=False)
    base_gold = db.Column(db.Integer, nullable=False)
    timer_seconds = db.Column(db.Integer, nullable=False)
    hp_damage_enabled = db.Column(db.Boolean, nullable=False, default=False)
    hp_damage_amount = db.Column(db.Integer, nullable=False, default=0)
    trigger_count = db.Column(db.Integer, nullable=False, default=0)
    started_at = db.Column(db.DateTime, nullable=False)
    completed_at = db.Column(db.DateTime, nullable=True)
    xp_awarded_each = db.Column(db.Integer, nullable=True)
    gold_awarded_each = db.Column(db.Integer, nullable=True)

    classroom = db.relationship(
        "Classroom",
        backref=db.backref("audio_meter_sessions", lazy="dynamic"),
    )
    teacher = db.relationship(
        "User",
        backref=db.backref("audio_meter_sessions", lazy="dynamic"),
    )

    def __repr__(self):
        return (
            f"<AudioMeterSession id={self.id} class={self.classroom_id} "
            f"status={self.status!r}>"
        )
