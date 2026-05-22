"""Adventures map template models: Adventure, nodes, edges, rewards, consequences."""

from enum import Enum

from sqlalchemy.orm import validates

from app.models import db
from app.models.base import Base
from app.utils.date_utils import get_utc_now


class AdventureStatus(str, Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class EndSemantics(str, Enum):
    ALL = "all"
    ANY = "any"


class NodeType(str, Enum):
    START = "start"
    STORY = "story"
    BATTLE = "battle"
    QUIZ = "quiz"
    CHOICE = "choice"
    REWARD = "reward"
    MILESTONE = "milestone"
    BOSS = "boss"
    END = "end"


class EdgeConditionType(str, Enum):
    ALWAYS = "always"
    CHOICE = "choice"
    CRITERIA = "criteria"


class UnlockSemantics(str, Enum):
    AND = "and"
    OR = "or"


class AdventureRewardType(str, Enum):
    """Reward types for node_rewards (includes BADGE; legacy RewardType does not)."""

    EXPERIENCE = "experience"
    GOLD = "gold"
    EQUIPMENT = "equipment"
    ABILITY = "ability"
    CLAN_EXPERIENCE = "clan_experience"
    SPECIAL_CURRENCY = "special_currency"
    BADGE = "badge"


# Alias used in data-model.md
RewardType = AdventureRewardType


class Adventure(Base):
    """Reusable map template authored by a teacher."""

    __tablename__ = "adventures"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(128), nullable=False)
    description = db.Column(db.Text, nullable=True)
    teacher_id = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    background_image_url = db.Column(db.String(512), nullable=True)
    theme = db.Column(db.String(32), nullable=False, default="fantasy")
    width = db.Column(db.Integer, nullable=False, default=2000)
    height = db.Column(db.Integer, nullable=False, default=1500)
    status = db.Column(db.String(16), nullable=False, default=AdventureStatus.DRAFT.value)
    is_public = db.Column(db.Boolean, nullable=False, default=False)
    end_semantics = db.Column(db.String(8), nullable=False, default=EndSemantics.ALL.value)
    version = db.Column(db.Integer, nullable=False, default=1)
    created_at = db.Column(db.DateTime, nullable=False, default=get_utc_now)
    updated_at = db.Column(
        db.DateTime, nullable=False, default=get_utc_now, onupdate=get_utc_now
    )

    teacher = db.relationship("User", backref=db.backref("adventures", lazy="dynamic"))
    nodes = db.relationship(
        "AdventureNode",
        back_populates="adventure",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )
    edges = db.relationship(
        "AdventureEdge",
        back_populates="adventure",
        cascade="all, delete-orphan",
        lazy="dynamic",
        foreign_keys="AdventureEdge.adventure_id",
    )
    assignments = db.relationship(
        "AdventureAssignment",
        back_populates="adventure",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )
    progress_rows = db.relationship(
        "CharacterAdventureProgress",
        back_populates="adventure",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )

    __table_args__ = (
        db.Index("idx_adventures_teacher", "teacher_id"),
        db.Index("idx_adventures_status_public", "status", "is_public"),
    )

    @validates("status")
    def _validate_status(self, _key, value):
        if isinstance(value, AdventureStatus):
            value = value.value
        if value not in {s.value for s in AdventureStatus}:
            raise ValueError(f"Invalid adventure status: {value}")
        return value

    @validates("end_semantics")
    def _validate_end_semantics(self, _key, value):
        if isinstance(value, EndSemantics):
            value = value.value
        if value not in {s.value for s in EndSemantics}:
            raise ValueError(f"Invalid end_semantics: {value}")
        return value

    def __repr__(self):
        return f"<Adventure {self.id} {self.title!r}>"


class AdventureNode(Base):
    """A placed task on the adventure map."""

    __tablename__ = "adventure_nodes"

    id = db.Column(db.Integer, primary_key=True)
    adventure_id = db.Column(
        db.Integer,
        db.ForeignKey("adventures.id", ondelete="CASCADE"),
        nullable=False,
    )
    slug = db.Column(db.String(64), nullable=False)
    title = db.Column(db.String(128), nullable=False)
    description = db.Column(db.Text, nullable=True)
    lore = db.Column(db.Text, nullable=True)
    icon_url = db.Column(db.String(512), nullable=True)
    node_type = db.Column(db.String(16), nullable=False)
    x = db.Column(db.Float, nullable=False, default=0.0)
    y = db.Column(db.Float, nullable=False, default=0.0)
    is_optional = db.Column(db.Boolean, nullable=False, default=False)
    is_start = db.Column(db.Boolean, nullable=False, default=False)
    is_end = db.Column(db.Boolean, nullable=False, default=False)
    question_set_id = db.Column(
        db.Integer, db.ForeignKey("question_sets.id", ondelete="SET NULL"), nullable=True
    )
    monster_id = db.Column(
        db.Integer, db.ForeignKey("monsters.id", ondelete="SET NULL"), nullable=True
    )
    completion_rules = db.Column(db.JSON, nullable=False, default=dict)
    on_complete_actions = db.Column(db.JSON, nullable=False, default=dict)
    created_at = db.Column(db.DateTime, nullable=False, default=get_utc_now)
    updated_at = db.Column(
        db.DateTime, nullable=False, default=get_utc_now, onupdate=get_utc_now
    )

    adventure = db.relationship("Adventure", back_populates="nodes")
    question_set = db.relationship("QuestionSet", backref="adventure_nodes")
    monster = db.relationship("Monster", backref="adventure_nodes")
    outbound_edges = db.relationship(
        "AdventureEdge",
        foreign_keys="AdventureEdge.from_node_id",
        back_populates="from_node",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )
    inbound_edges = db.relationship(
        "AdventureEdge",
        foreign_keys="AdventureEdge.to_node_id",
        back_populates="to_node",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )
    rewards = db.relationship(
        "NodeReward",
        back_populates="node",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )
    consequences = db.relationship(
        "NodeConsequence",
        back_populates="node",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )
    progress_rows = db.relationship(
        "CharacterNodeProgress",
        back_populates="node",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )

    __table_args__ = (
        db.UniqueConstraint("adventure_id", "slug", name="uq_adventure_node_slug"),
        db.CheckConstraint("x >= 0 AND y >= 0", name="ck_adventure_node_coords_nonneg"),
        db.Index("idx_nodes_adventure", "adventure_id"),
        db.Index("idx_nodes_adventure_type", "adventure_id", "node_type"),
    )

    @validates("node_type")
    def _validate_node_type(self, _key, value):
        if isinstance(value, NodeType):
            value = value.value
        if value not in {t.value for t in NodeType}:
            raise ValueError(f"Invalid node_type: {value}")
        return value

    def __repr__(self):
        return f"<AdventureNode {self.id} {self.slug!r}>"


class AdventureEdge(db.Model):
    """Directed connection between two adventure nodes."""

    __tablename__ = "adventure_edges"

    id = db.Column(db.Integer, primary_key=True)
    adventure_id = db.Column(
        db.Integer,
        db.ForeignKey("adventures.id", ondelete="CASCADE"),
        nullable=False,
    )
    from_node_id = db.Column(
        db.Integer,
        db.ForeignKey("adventure_nodes.id", ondelete="CASCADE"),
        nullable=False,
    )
    to_node_id = db.Column(
        db.Integer,
        db.ForeignKey("adventure_nodes.id", ondelete="CASCADE"),
        nullable=False,
    )
    label = db.Column(db.String(128), nullable=True)
    condition_type = db.Column(
        db.String(16), nullable=False, default=EdgeConditionType.ALWAYS.value
    )
    condition_data = db.Column(db.JSON, nullable=False, default=dict)
    unlock_semantics = db.Column(
        db.String(8), nullable=False, default=UnlockSemantics.AND.value
    )
    sort_order = db.Column(db.Integer, nullable=False, default=0)
    created_at = db.Column(db.DateTime, nullable=False, default=get_utc_now)

    adventure = db.relationship(
        "Adventure",
        back_populates="edges",
        foreign_keys=[adventure_id],
    )
    from_node = db.relationship(
        "AdventureNode",
        foreign_keys=[from_node_id],
        back_populates="outbound_edges",
    )
    to_node = db.relationship(
        "AdventureNode",
        foreign_keys=[to_node_id],
        back_populates="inbound_edges",
    )

    __table_args__ = (
        db.UniqueConstraint("from_node_id", "to_node_id", name="uq_adventure_edge_pair"),
        db.CheckConstraint(
            "from_node_id != to_node_id", name="ck_adventure_edge_no_self_loop"
        ),
        db.Index("idx_edges_from", "adventure_id", "from_node_id"),
        db.Index("idx_edges_to", "adventure_id", "to_node_id"),
    )

    @validates("condition_type")
    def _validate_condition_type(self, _key, value):
        if isinstance(value, EdgeConditionType):
            value = value.value
        if value not in {c.value for c in EdgeConditionType}:
            raise ValueError(f"Invalid condition_type: {value}")
        return value

    @validates("unlock_semantics")
    def _validate_unlock_semantics(self, _key, value):
        if isinstance(value, UnlockSemantics):
            value = value.value
        if value not in {u.value for u in UnlockSemantics}:
            raise ValueError(f"Invalid unlock_semantics: {value}")
        return value

    def __repr__(self):
        return f"<AdventureEdge {self.from_node_id}->{self.to_node_id}>"


class NodeReward(db.Model):
    """Reward tied to an adventure node."""

    __tablename__ = "node_rewards"

    id = db.Column(db.Integer, primary_key=True)
    node_id = db.Column(
        db.Integer,
        db.ForeignKey("adventure_nodes.id", ondelete="CASCADE"),
        nullable=False,
    )
    type = db.Column(db.String(24), nullable=False)
    amount = db.Column(db.Integer, nullable=False, default=0)
    item_id = db.Column(
        db.Integer, db.ForeignKey("equipment.id", ondelete="SET NULL"), nullable=True
    )
    ability_id = db.Column(
        db.Integer, db.ForeignKey("abilities.id", ondelete="SET NULL"), nullable=True
    )
    badge_id = db.Column(
        db.Integer,
        db.ForeignKey("achievement_badge.id", ondelete="SET NULL"),
        nullable=True,
    )
    is_conditional = db.Column(db.Boolean, nullable=False, default=False)
    condition_json = db.Column(db.JSON, nullable=False, default=dict)

    node = db.relationship("AdventureNode", back_populates="rewards")
    equipment = db.relationship("Equipment")
    ability = db.relationship("Ability")
    badge = db.relationship("AchievementBadge")

    __table_args__ = (db.Index("idx_node_rewards_node", "node_id"),)

    @validates("type")
    def _validate_type(self, _key, value):
        if isinstance(value, AdventureRewardType):
            value = value.value
        if value not in {r.value for r in AdventureRewardType}:
            raise ValueError(f"Invalid reward type: {value}")
        return value

    def __repr__(self):
        return f"<NodeReward {self.type} node={self.node_id}>"


class NodeConsequence(db.Model):
    """Penalty applied when a student exhausts retries on a node."""

    __tablename__ = "node_consequences"

    id = db.Column(db.Integer, primary_key=True)
    node_id = db.Column(
        db.Integer,
        db.ForeignKey("adventure_nodes.id", ondelete="CASCADE"),
        nullable=False,
    )
    description = db.Column(db.Text, nullable=True)
    xp_penalty = db.Column(db.Integer, nullable=False, default=0)
    gold_penalty = db.Column(db.Integer, nullable=False, default=0)
    hp_penalty = db.Column(db.Integer, nullable=False, default=0)
    custom_json = db.Column(db.JSON, nullable=False, default=dict)

    node = db.relationship("AdventureNode", back_populates="consequences")

    __table_args__ = (db.Index("idx_node_consequences_node", "node_id"),)

    def __repr__(self):
        return f"<NodeConsequence node={self.node_id}>"
