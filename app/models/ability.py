from datetime import datetime
from typing import List, Optional
from sqlalchemy import ForeignKey, String, Integer, Float, DateTime, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from pydantic import BaseModel, Field
from enum import Enum as PyEnum

from app.models.base import Base
from app.models.character import Character
from app.models import db

class AbilityTier(str, PyEnum):
    BASIC = "basic"
    ADVANCED = "advanced"
    ELITE = "elite"
    LEGENDARY = "legendary"

class AbilityTargetType(str, PyEnum):
    SELF = "self"
    SINGLE_ALLY = "single_ally"
    SINGLE_ENEMY = "single_enemy"
    ALL_ALLIES = "all_allies"
    ALL_ENEMIES = "all_enemies"
    AREA = "area"

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
    cooldown = db.Column(db.Integer, default=0, nullable=False)  # Cooldown in turns
    duration = db.Column(db.Integer, default=1, nullable=False)  # Duration in turns for buffs/debuffs
    # Metadata
    is_passive = db.Column(db.Boolean, default=False, nullable=False)
    is_ultimate = db.Column(db.Boolean, default=False, nullable=False)
    cost = db.Column(db.Integer, default=0, nullable=False)
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
    learned_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
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

# Pydantic models for validation
class AbilityBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: str = Field(..., min_length=1, max_length=500)
    tier: AbilityTier
    power_cost: int = Field(..., ge=0)
    cooldown: int = Field(..., ge=0)
    target_type: AbilityTargetType
    base_damage: Optional[float] = Field(None, ge=0)
    base_healing: Optional[float] = Field(None, ge=0)
    required_level: int = Field(..., ge=1)
    xp_reward: float = Field(..., ge=0)

    class Config:
        arbitrary_types_allowed = True

class AbilityCreate(AbilityBase):
    pass

class AbilityUpdate(AbilityBase):
    pass

class AbilityRead(AbilityBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
        arbitrary_types_allowed = True

# At the end of the file, after both classes are defined:
from app.models.character import Character
Character.abilities = db.relationship('CharacterAbility', back_populates='character', lazy='dynamic')
CharacterAbility.character = db.relationship('Character', back_populates='abilities') 