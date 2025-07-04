from datetime import datetime, timedelta
from typing import List, Optional
from sqlalchemy import String, Integer, Float, DateTime, ForeignKey, or_
from sqlalchemy.orm import Mapped, mapped_column, relationship
from pydantic import BaseModel, Field

from app.models import db
from app.models.base import Base

class Character(Base):
    """Character model representing a student's game avatar."""
    
    __tablename__ = 'characters'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), nullable=False)
    level = db.Column(db.Integer, default=1, nullable=False)
    experience = db.Column(db.Integer, default=0, nullable=False)
    health = db.Column(db.Integer, default=100, nullable=False)
    max_health = db.Column(db.Integer, default=100, nullable=False)
    strength = db.Column(db.Integer, default=10, nullable=False)
    defense = db.Column(db.Integer, default=10, nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    character_class = db.Column(db.String(32), nullable=False, default='Adventurer')
    gold = db.Column(db.Integer, default=0, nullable=False)
    
    # New fields for character creation customization
    gender = db.Column(db.String(16), nullable=True)
    avatar_url = db.Column(db.String(256), nullable=True)
    
    # Foreign Keys
    student_id = db.Column(db.Integer, db.ForeignKey('students.id', ondelete='CASCADE'), nullable=False)
    clan_id = db.Column(db.Integer, db.ForeignKey('clans.id', ondelete='SET NULL'), nullable=True)
    
    # Relationships
    student = db.relationship('Student', backref=db.backref('characters', lazy='dynamic', cascade='all, delete-orphan'))
    clan = db.relationship('Clan', foreign_keys=[clan_id], backref=db.backref('members', lazy='dynamic', foreign_keys='Character.clan_id'))
    # abilities = db.relationship('CharacterAbility', back_populates='character', lazy='dynamic')
    
    __table_args__ = (
        db.Index('idx_character_student', 'student_id'),  # For looking up student's characters
        db.Index('idx_character_clan', 'clan_id'),  # For clan member lookups
    )
    
    def __init__(self, name, student_id, **kwargs):
        super().__init__(**kwargs)
        self.name = name
        self.student_id = student_id
    
    def gain_experience(self, amount):
        """Add experience points and handle level ups."""
        self.experience += amount
        # Simple level up formula: level = experience // 1000
        new_level = (self.experience // 1000) + 1
        if new_level > self.level:
            self.level_up(new_level)
    
    def level_up(self, new_level):
        """Handle the level up process."""
        levels_gained = new_level - self.level
        self.level = new_level
        # Increase stats with each level
        self.max_health += 10 * levels_gained
        self.health = self.max_health  # Heal to full on level up
        self.strength += 2 * levels_gained
        self.defense += 2 * levels_gained
        self.save()
    
    def heal(self, amount):
        """Heal the character by the specified amount."""
        self.health = min(self.health + amount, self.max_health)
        self.save()
    
    def take_damage(self, amount):
        """Apply damage to the character."""
        self.health = max(0, self.health - amount)
        self.save()
        return self.health > 0  # Return True if still alive
    
    def join_clan(self, clan):
        """Join a clan if not already in one."""
        if self.clan_id:
            raise ValueError("Character is already in a clan")
        self.clan = clan
        self.save()
    
    def leave_clan(self):
        """Leave the current clan."""
        self.clan = None
        self.save()
    
    def __repr__(self):
        return f'<Character {self.name} ({self.character_class}) (Level {self.level})>'

    @property
    def learned_abilities(self):
        """Alias for abilities relationship."""
        return self.abilities

    # Helper properties for equipped items
    @property
    def equipped_weapon(self):
        return next((item for item in self.inventory_items if item.is_equipped and getattr(item.equipment, 'type', None) and str(item.equipment.type).lower() == 'weapon'), None)

    @property
    def equipped_armor(self):
        return next((item for item in self.inventory_items if item.is_equipped and getattr(item.equipment, 'type', None) and str(item.equipment.type).lower() == 'armor'), None)

    @property
    def equipped_accessory(self):
        return next((item for item in self.inventory_items if item.is_equipped and getattr(item.equipment, 'type', None) and str(item.equipment.type).lower() == 'accessory'), None)

    @property
    def total_health(self):
        bonus = 0
        for item in [self.equipped_weapon, self.equipped_armor, self.equipped_accessory]:
            if item and item.equipment and hasattr(item.equipment, 'health_bonus'):
                bonus += item.equipment.health_bonus
        # Add active status effects
        now = datetime.utcnow()
        effect_bonus = sum(
            effect.amount for effect in self.status_effects.filter(
                StatusEffect.stat_affected == 'health',
                StatusEffect.expires_at > now
            )
        )
        return self.health + bonus + effect_bonus

    @property
    def total_strength(self):
        bonus = 0
        for item in [self.equipped_weapon, self.equipped_armor, self.equipped_accessory]:
            if item and item.equipment and hasattr(item.equipment, 'strength_bonus'):
                bonus += item.equipment.strength_bonus
        now = datetime.utcnow()
        effect_bonus = sum(
            effect.amount for effect in self.status_effects.filter(
                StatusEffect.stat_affected == 'strength',
                StatusEffect.expires_at > now
            )
        )
        return self.strength + bonus + effect_bonus

    @property
    def total_defense(self):
        bonus = 0
        for item in [self.equipped_weapon, self.equipped_armor, self.equipped_accessory]:
            if item and item.equipment and hasattr(item.equipment, 'defense_bonus'):
                bonus += item.equipment.defense_bonus
        now = datetime.utcnow()
        effect_bonus = sum(
            effect.amount for effect in self.status_effects.filter(
                StatusEffect.stat_affected == 'defense',
                StatusEffect.expires_at > now
            )
        )
        return self.defense + bonus + effect_bonus

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "level": self.level,
            "avatar_url": self.avatar_url,
            "character_class": self.character_class,
            "is_active": self.is_active,
        }

# Pydantic models for validation
class CharacterBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=64)
    level: int = Field(default=1, ge=1)
    experience: int = Field(default=0, ge=0)
    health: int = Field(default=100, ge=0)
    max_health: int = Field(default=100, ge=0)
    strength: int = Field(default=10, ge=0)
    defense: int = Field(default=10, ge=0)
    is_active: bool = Field(default=True)

class CharacterCreate(CharacterBase):
    pass

class CharacterUpdate(CharacterBase):
    pass

class CharacterRead(CharacterBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class StatusEffect(db.Model):
    __tablename__ = 'status_effects'
    id = db.Column(db.Integer, primary_key=True)
    character_id = db.Column(db.Integer, db.ForeignKey('characters.id', ondelete='CASCADE'), nullable=False)
    effect_type = db.Column(db.String(32), nullable=False)  # e.g., 'buff', 'debuff', 'protect'
    stat_affected = db.Column(db.String(32), nullable=False)  # e.g., 'defense', 'strength', 'health'
    amount = db.Column(db.Integer, nullable=False)
    expires_at = db.Column(DateTime, nullable=False)
    source = db.Column(db.String(64), nullable=True)  # Ability or character name

    character = db.relationship('Character', back_populates='status_effects')

    def is_active(self):
        return self.expires_at > datetime.utcnow()

    def to_dict(self):
        return {
            'effect_type': self.effect_type,
            'stat_affected': self.stat_affected,
            'amount': self.amount,
            'expires_at': self.expires_at.isoformat(),
            'source': self.source
        }

Character.status_effects = db.relationship('StatusEffect', back_populates='character', lazy='dynamic', cascade='all, delete-orphan') 