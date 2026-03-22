from app.utils.date_utils import get_utc_now
from enum import Enum as PyEnum

from app.models.base import Base
from app.models import db


class AbilityTier(str, PyEnum):
    BASIC = "basic"
    ADVANCED = "advanced"
    ELITE = "elite"


class AbilityTargetType(str, PyEnum):
    SELF = "self"
    SINGLE_ALLY = "single_ally"
    SINGLE_ENEMY = "single_enemy"
    ALL_ALLIES = "all_allies"


class AbilityType(str, PyEnum):
    ATTACK = 'attack'
    DEFENSE = 'defense'
    HEAL = 'heal'
    BUFF = 'buff'
    DEBUFF = 'debuff'
    UTILITY = 'utility'


class Ability(Base):
    """Ability model for character skills and powers."""
    __tablename__ = 'abilities'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), nullable=False)
    description = db.Column(db.Text)
    type = db.Column(db.String(32), nullable=False)  # Store as string, validate with AbilityType
    level_requirement = db.Column(db.Integer, default=1, nullable=False)
    # Ability stats
    power = db.Column(db.Integer, default=10, nullable=False)  # Base effectiveness
    cooldown = db.Column(db.Integer, default=0, nullable=False)  # Cooldown in seconds
    duration = db.Column(db.Integer, default=1, nullable=False)  # Buff/debuff duration in minutes
    # Metadata
    is_passive = db.Column(db.Boolean, default=False, nullable=False)
    is_ultimate = db.Column(db.Boolean, default=False, nullable=False)
    cost = db.Column(db.Integer, default=0, nullable=False)  # Power resource spent to activate
    # Powers system (Classcraft-style progression)
    tier = db.Column(db.String(16), nullable=False, default='basic')  # basic, advanced, elite
    class_restriction = db.Column(db.String(32), nullable=True)  # Warrior, Sorcerer, Druid, or None = any
    target_type = db.Column(db.String(32), nullable=False, default='self')
    prerequisite_id = db.Column(db.Integer, db.ForeignKey('abilities.id', ondelete='SET NULL'), nullable=True)
    pp_cost = db.Column(db.Integer, default=1, nullable=False)  # Power Points to learn
    is_default = db.Column(db.Boolean, default=True, nullable=False)
    created_by_teacher_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    # Optional effect hook for non-standard resolution (revive, full party heal, restore ally power)
    special_effect = db.Column(db.String(32), nullable=True)

    prerequisite = db.relationship(
        'Ability',
        remote_side=[id],
        foreign_keys=[prerequisite_id],
        backref=db.backref('dependent_powers', lazy='dynamic'),
    )
    created_by_teacher = db.relationship('User', foreign_keys=[created_by_teacher_id])

    def __init__(self, name, type, cost=0, **kwargs):
        super().__init__(**kwargs)
        self.name = name
        if isinstance(type, AbilityType):
            self.type = type.value
        else:
            self.type = AbilityType(type).value
        self.cost = cost

    @property
    def ability_type(self) -> AbilityType:
        """Get the ability type as an enum."""
        return AbilityType(self.type)

    def __repr__(self):
        return f'<Ability {self.name} ({self.type}) - Cost: {self.cost}>'


class CharacterAbility(Base):
    """Association model between characters and their learned abilities."""
    __tablename__ = 'character_abilities'
    id = db.Column(db.Integer, primary_key=True)
    character_id = db.Column(db.Integer, db.ForeignKey('characters.id', ondelete='CASCADE'), nullable=False)
    ability_id = db.Column(db.Integer, db.ForeignKey('abilities.id', ondelete='CASCADE'), nullable=False)
    level = db.Column(db.Integer, default=1, nullable=False)  # Ability can be leveled up
    is_equipped = db.Column(db.Boolean, default=False, nullable=False)  # Some abilities might need to be "equipped" to be used
    learned_at = db.Column(db.DateTime, nullable=False, default=get_utc_now)
    last_used_at = db.Column(db.DateTime, nullable=True)  # Track when ability was last used
    # Relationships
    character = db.relationship('Character', back_populates='abilities')
    ability = db.relationship('Ability')
    __table_args__ = (
        db.Index('idx_char_ability_char', 'character_id'),  # For looking up character's abilities
        db.Index('idx_char_ability_equipped', 'character_id', 'is_equipped'),  # For equipped abilities
        db.UniqueConstraint('character_id', 'ability_id', name='uq_char_ability'),  # Can't learn same ability twice
    )

    def __init__(self, character_id, ability_id, **kwargs):
        super().__init__(**kwargs)
        self.character_id = character_id
        self.ability_id = ability_id

    def level_up(self):
        self.level += 1
        self.save()

    def equip(self):
        equipped_count = CharacterAbility.query.filter_by(
            character_id=self.character_id,
            is_equipped=True
        ).count()
        if not self.is_equipped and equipped_count >= 4:
            raise ValueError("Cannot equip more than 4 abilities")
        self.is_equipped = True
        self.save()

    def unequip(self):
        self.is_equipped = False
        self.save()

    def __repr__(self):
        status = "equipped" if self.is_equipped else "learned"
        return f'<CharacterAbility {self.ability.name} (Level {self.level}, {status})>'
