from datetime import datetime
from typing import List, Optional
from sqlalchemy import ForeignKey, String, Integer, Float, DateTime, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from pydantic import BaseModel, Field

from app.models import db
from app.models.character import Character

class AbilityTier(str, Enum):
    BASIC = "basic"
    ADVANCED = "advanced"
    ELITE = "elite"
    LEGENDARY = "legendary"

class AbilityTargetType(str, Enum):
    SELF = "self"
    SINGLE_ALLY = "single_ally"
    SINGLE_ENEMY = "single_enemy"
    ALL_ALLIES = "all_allies"
    ALL_ENEMIES = "all_enemies"
    AREA = "area"

class Ability(db.Model):
    __tablename__ = "abilities"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    tier: Mapped[AbilityTier] = mapped_column(Enum(AbilityTier), nullable=False)
    power_cost: Mapped[int] = mapped_column(Integer, nullable=False)
    cooldown: Mapped[int] = mapped_column(Integer, nullable=False)  # in seconds
    target_type: Mapped[AbilityTargetType] = mapped_column(Enum(AbilityTargetType), nullable=False)
    base_damage: Mapped[float] = mapped_column(Float, nullable=True)
    base_healing: Mapped[float] = mapped_column(Float, nullable=True)
    required_level: Mapped[int] = mapped_column(Integer, nullable=False)
    xp_reward: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    character_abilities: Mapped[List["CharacterAbility"]] = relationship(back_populates="ability")

class CharacterAbility(db.Model):
    __tablename__ = "character_abilities"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    character_id: Mapped[int] = mapped_column(ForeignKey("characters.id"), nullable=False)
    ability_id: Mapped[int] = mapped_column(ForeignKey("abilities.id"), nullable=False)
    slot_number: Mapped[int] = mapped_column(Integer, nullable=False)
    times_used: Mapped[int] = mapped_column(Integer, default=0)
    last_used_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    unlocked_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # Relationships
    character: Mapped[Character] = relationship(back_populates="abilities")
    ability: Mapped[Ability] = relationship(back_populates="character_abilities")

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