"""Classroom behavior, Cursed Die sentences, incidents, and fallen-character events."""

import enum
from app.models.base import Base
from app.models import db


class FallenStatus(str, enum.Enum):
    AWAITING_RESCUE = "awaiting_rescue"
    RESCUED = "rescued"
    SENTENCED = "sentenced"


class FallenTriggerSource(str, enum.Enum):
    BEHAVIOR = "behavior"
    CASCADE = "cascade"


class ClassroomBehaviorSettings(Base):
    """Per-class settings for consequence/sentence system."""

    __tablename__ = "classroom_behavior_settings"

    id = db.Column(db.Integer, primary_key=True)
    classroom_id = db.Column(
        db.Integer,
        db.ForeignKey("classrooms.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    cascade_hp_damage = db.Column(db.Integer, nullable=False, default=10)
    rescue_window_minutes = db.Column(db.Integer, nullable=False, default=5)

    classroom = db.relationship("Classroom", backref=db.backref("behavior_settings", uselist=False))


class BehaviorInfraction(Base):
    """Teacher-defined negative behavior with default HP cost."""

    __tablename__ = "behavior_infractions"

    id = db.Column(db.Integer, primary_key=True)
    classroom_id = db.Column(
        db.Integer,
        db.ForeignKey("classrooms.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name = db.Column(db.String(128), nullable=False)
    hp_cost = db.Column(db.Integer, nullable=False, default=5)
    description = db.Column(db.Text, nullable=True)
    is_active = db.Column(db.Boolean, nullable=False, default=True)

    classroom = db.relationship("Classroom", backref=db.backref("behavior_infractions", lazy="dynamic"))


class CursedDieFace(Base):
    """One of six configurable Cursed Die faces for a classroom."""

    __tablename__ = "cursed_die_faces"

    id = db.Column(db.Integer, primary_key=True)
    classroom_id = db.Column(
        db.Integer,
        db.ForeignKey("classrooms.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    face_number = db.Column(db.Integer, nullable=False)  # 1-6
    description = db.Column(db.Text, nullable=False)
    is_nothing = db.Column(db.Boolean, nullable=False, default=False)

    classroom = db.relationship("Classroom", backref=db.backref("cursed_die_faces", lazy="dynamic"))

    __table_args__ = (
        db.UniqueConstraint("classroom_id", "face_number", name="uq_cursed_die_face_class_slot"),
    )


class BehaviorIncident(Base):
    """Log of an HP deduction for behavior."""

    __tablename__ = "behavior_incidents"

    id = db.Column(db.Integer, primary_key=True)
    character_id = db.Column(
        db.Integer,
        db.ForeignKey("characters.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    classroom_id = db.Column(
        db.Integer,
        db.ForeignKey("classrooms.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    infraction_id = db.Column(
        db.Integer,
        db.ForeignKey("behavior_infractions.id", ondelete="SET NULL"),
        nullable=True,
    )
    hp_deducted = db.Column(db.Integer, nullable=False)
    applied_by_user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    description = db.Column(db.Text, nullable=False)

    character = db.relationship("Character", backref=db.backref("behavior_incidents", lazy="dynamic"))
    classroom = db.relationship("Classroom", backref=db.backref("behavior_incidents", lazy="dynamic"))
    infraction = db.relationship("BehaviorInfraction", backref=db.backref("incidents", lazy="dynamic"))
    applied_by = db.relationship("User", foreign_keys=[applied_by_user_id])


class FallenEvent(Base):
    """Tracks 0 HP fall, rescue window, and sentence resolution."""

    __tablename__ = "fallen_events"

    id = db.Column(db.Integer, primary_key=True)
    character_id = db.Column(
        db.Integer,
        db.ForeignKey("characters.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    classroom_id = db.Column(
        db.Integer,
        db.ForeignKey("classrooms.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    incident_id = db.Column(
        db.Integer,
        db.ForeignKey("behavior_incidents.id", ondelete="SET NULL"),
        nullable=True,
    )
    trigger_source = db.Column(db.String(32), nullable=False, default=FallenTriggerSource.BEHAVIOR.value)
    status = db.Column(db.String(32), nullable=False, default=FallenStatus.AWAITING_RESCUE.value, index=True)
    rescue_deadline = db.Column(db.DateTime, nullable=True)
    rescued_by_character_id = db.Column(
        db.Integer,
        db.ForeignKey("characters.id", ondelete="SET NULL"),
        nullable=True,
    )
    rescue_ability_id = db.Column(
        db.Integer,
        db.ForeignKey("abilities.id", ondelete="SET NULL"),
        nullable=True,
    )
    die_roll_result = db.Column(db.Integer, nullable=True)
    second_die_roll = db.Column(db.Integer, nullable=True)  # for Cheat Death
    sentence_face_id = db.Column(
        db.Integer,
        db.ForeignKey("cursed_die_faces.id", ondelete="SET NULL"),
        nullable=True,
    )
    team_damage_applied = db.Column(db.Boolean, nullable=False, default=False)
    resolved_at = db.Column(db.DateTime, nullable=True)

    character = db.relationship(
        "Character",
        foreign_keys=[character_id],
        backref=db.backref("fallen_events", lazy="dynamic"),
    )
    classroom = db.relationship("Classroom", backref=db.backref("fallen_events", lazy="dynamic"))
    incident = db.relationship("BehaviorIncident", backref=db.backref("fallen_events", lazy="dynamic"))
    rescued_by = db.relationship("Character", foreign_keys=[rescued_by_character_id])
    rescue_ability = db.relationship("Ability", foreign_keys=[rescue_ability_id])
    sentence_face = db.relationship("CursedDieFace", foreign_keys=[sentence_face_id])
