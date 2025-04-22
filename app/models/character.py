from datetime import datetime
from typing import List, Optional
from sqlalchemy import String, Integer, Float, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from pydantic import BaseModel, Field

from app.models import db

class Character(db.Model):
    __tablename__ = "characters"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    level: Mapped[int] = mapped_column(Integer, default=1)
    experience: Mapped[int] = mapped_column(Integer, default=0)
    power: Mapped[float] = mapped_column(Float, default=100.0)
    max_power: Mapped[float] = mapped_column(Float, default=100.0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    abilities: Mapped[List["CharacterAbility"]] = relationship(back_populates="character")

# Pydantic models for validation
class CharacterBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    level: int = Field(default=1, ge=1)
    experience: int = Field(default=0, ge=0)
    power: float = Field(default=100.0, ge=0)
    max_power: float = Field(default=100.0, ge=0)

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