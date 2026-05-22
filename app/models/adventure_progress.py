"""Adventures assignment and per-character progress models."""

from enum import Enum

from sqlalchemy.orm import validates

from app.models import db
from app.utils.date_utils import get_utc_now


class AdventureProgressStatus(str, Enum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    ABANDONED = "abandoned"


class NodeProgressStatus(str, Enum):
    LOCKED = "locked"
    AVAILABLE = "available"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class AdventureAssignment(db.Model):
    """Binds a published adventure to a classroom, clan, or individual character."""

    __tablename__ = "adventure_assignments"

    id = db.Column(db.Integer, primary_key=True)
    adventure_id = db.Column(
        db.Integer,
        db.ForeignKey("adventures.id", ondelete="CASCADE"),
        nullable=False,
    )
    adventure_version = db.Column(db.Integer, nullable=False)
    classroom_id = db.Column(
        db.Integer, db.ForeignKey("classrooms.id", ondelete="SET NULL"), nullable=True
    )
    clan_id = db.Column(
        db.Integer, db.ForeignKey("clans.id", ondelete="SET NULL"), nullable=True
    )
    character_id = db.Column(
        db.Integer, db.ForeignKey("characters.id", ondelete="SET NULL"), nullable=True
    )
    assigned_by_user_id = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    starts_at = db.Column(db.DateTime, nullable=True)
    ends_at = db.Column(db.DateTime, nullable=True)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, nullable=False, default=get_utc_now)

    adventure = db.relationship("Adventure", back_populates="assignments")
    classroom = db.relationship("Classroom", backref="adventure_assignments")
    clan = db.relationship("Clan", backref="adventure_assignments")
    character = db.relationship("Character", backref="direct_adventure_assignments")
    assigned_by = db.relationship("User", backref="adventure_assignments_created")
    progress_rows = db.relationship(
        "CharacterAdventureProgress",
        back_populates="assignment",
        lazy="dynamic",
    )

    __table_args__ = (
        db.CheckConstraint(
            "((classroom_id IS NOT NULL) + (clan_id IS NOT NULL) + (character_id IS NOT NULL)) = 1",
            name="ck_assignment_exactly_one_target",
        ),
        db.CheckConstraint(
            "starts_at IS NULL OR ends_at IS NULL OR ends_at > starts_at",
            name="ck_assignment_date_window",
        ),
        db.Index("idx_assignments_adventure_active", "adventure_id", "is_active"),
        db.Index("idx_assignments_classroom", "classroom_id", "is_active"),
        db.Index("idx_assignments_clan", "clan_id", "is_active"),
        db.Index("idx_assignments_character", "character_id", "is_active"),
    )

    def __repr__(self):
        return f"<AdventureAssignment {self.id} adventure={self.adventure_id}>"


class CharacterAdventureProgress(db.Model):
    """Per-character standing in an adventure."""

    __tablename__ = "character_adventure_progress"

    id = db.Column(db.Integer, primary_key=True)
    character_id = db.Column(
        db.Integer,
        db.ForeignKey("characters.id", ondelete="CASCADE"),
        nullable=False,
    )
    adventure_id = db.Column(
        db.Integer,
        db.ForeignKey("adventures.id", ondelete="CASCADE"),
        nullable=False,
    )
    assignment_id = db.Column(
        db.Integer,
        db.ForeignKey("adventure_assignments.id", ondelete="SET NULL"),
        nullable=True,
    )
    snapshot_json = db.Column(db.JSON, nullable=True)
    status = db.Column(
        db.String(16),
        nullable=False,
        default=AdventureProgressStatus.NOT_STARTED.value,
    )
    current_node_id = db.Column(
        db.Integer,
        db.ForeignKey("adventure_nodes.id", ondelete="SET NULL"),
        nullable=True,
    )
    started_at = db.Column(db.DateTime, nullable=True)
    completed_at = db.Column(db.DateTime, nullable=True)
    last_active_at = db.Column(db.DateTime, nullable=True)

    character = db.relationship("Character", backref="adventure_progress")
    adventure = db.relationship("Adventure", back_populates="progress_rows")
    assignment = db.relationship("AdventureAssignment", back_populates="progress_rows")
    current_node = db.relationship("AdventureNode", foreign_keys=[current_node_id])

    __table_args__ = (
        db.UniqueConstraint(
            "character_id", "adventure_id", name="uq_character_adventure_progress"
        ),
        db.Index("idx_char_adv_progress_status", "character_id", "status"),
        db.Index("idx_char_adv_progress_assignment", "assignment_id"),
    )

    @validates("status")
    def _validate_status(self, _key, value):
        if isinstance(value, AdventureProgressStatus):
            value = value.value
        if value not in {s.value for s in AdventureProgressStatus}:
            raise ValueError(f"Invalid adventure progress status: {value}")
        return value

    def __repr__(self):
        return f"<CharacterAdventureProgress char={self.character_id} adv={self.adventure_id}>"


class CharacterNodeProgress(db.Model):
    """Per-character per-node standing."""

    __tablename__ = "character_node_progress"

    id = db.Column(db.Integer, primary_key=True)
    character_id = db.Column(
        db.Integer,
        db.ForeignKey("characters.id", ondelete="CASCADE"),
        nullable=False,
    )
    node_id = db.Column(
        db.Integer,
        db.ForeignKey("adventure_nodes.id", ondelete="CASCADE"),
        nullable=False,
    )
    status = db.Column(
        db.String(16), nullable=False, default=NodeProgressStatus.LOCKED.value
    )
    attempts = db.Column(db.Integer, nullable=False, default=0)
    score = db.Column(db.Integer, nullable=True)
    progress_data = db.Column(db.JSON, nullable=False, default=dict)
    choice_made = db.Column(db.String(64), nullable=True)
    started_at = db.Column(db.DateTime, nullable=True)
    completed_at = db.Column(db.DateTime, nullable=True)
    updated_at = db.Column(
        db.DateTime, nullable=False, default=get_utc_now, onupdate=get_utc_now
    )

    character = db.relationship("Character", backref="node_progress")
    node = db.relationship("AdventureNode", back_populates="progress_rows")

    __table_args__ = (
        db.UniqueConstraint("character_id", "node_id", name="uq_character_node_progress"),
        db.Index("idx_char_node_progress_status", "character_id", "status"),
        db.Index("idx_char_node_progress_node", "node_id", "status"),
    )

    @validates("status")
    def _validate_status(self, _key, value):
        if isinstance(value, NodeProgressStatus):
            value = value.value
        if value not in {s.value for s in NodeProgressStatus}:
            raise ValueError(f"Invalid node progress status: {value}")
        return value

    def __repr__(self):
        return f"<CharacterNodeProgress char={self.character_id} node={self.node_id}>"
