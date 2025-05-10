from datetime import datetime
from sqlalchemy.types import JSON
from app.models import db
from app.models.base import Base
from enum import Enum
from sqlalchemy.orm import validates

class EventType(Enum):
    LOGIN = 'LOGIN'
    LOGOUT = 'LOGOUT'
    USER_LOGIN = 'USER_LOGIN'
    USER_LOGOUT = 'USER_LOGOUT'
    CHARACTER_CREATE = 'CHARACTER_CREATE'
    CHARACTER_UPDATE = 'CHARACTER_UPDATE'
    PURCHASE = 'PURCHASE'
    QUEST_START = 'QUEST_START'
    QUEST_COMPLETE = 'QUEST_COMPLETE'
    QUEST_FAIL = 'QUEST_FAIL'
    CLAN_JOIN = 'CLAN_JOIN'
    CLAN_LEAVE = 'CLAN_LEAVE'
    ABILITY_LEARN = 'ABILITY_LEARN'
    EQUIPMENT_CHANGE = 'EQUIPMENT_CHANGE'
    GOLD_TRANSACTION = 'GOLD_TRANSACTION'
    XP_GAIN = 'XP_GAIN'
    LEVEL_UP = 'LEVEL_UP'

class AuditLog(Base):
    """Model for tracking important game events and changes.

    For batch actions (e.g., batch character updates), use:
      AuditLog.log_event(
        EventType.CHARACTER_UPDATE,
        event_data={
          'action': 'batch-reset-health',
          'character_ids': [1,2,3],
          'by': <user_id>,
          'results': {1: {...}, 2: {...}, ...}
        },
        user_id=<user_id>
      )
    """
    
    __tablename__ = 'audit_log'
    
    id = db.Column(db.Integer, primary_key=True)
    event_type = db.Column(db.String(50), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=True)
    character_id = db.Column(db.Integer, db.ForeignKey('characters.id', ondelete='CASCADE'), nullable=True)
    event_data = db.Column(JSON, nullable=False)  # Stores event-specific data
    ip_address = db.Column(db.String(45), nullable=True)  # IPv4/IPv6 address
    event_timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)
    
    # Relationships
    user = db.relationship('User', back_populates='audit_logs')
    character = db.relationship('Character', backref=db.backref('audit_logs', lazy='dynamic'))
    
    EVENT_TYPES = {
        'LOGIN': 'User login',
        'LOGOUT': 'User logout',
        'USER_LOGIN': 'User login',
        'USER_LOGOUT': 'User logout',
        'CHARACTER_CREATE': 'Character creation',
        'CHARACTER_UPDATE': 'Character update',
        'PURCHASE': 'Shop purchase',
        'QUEST_START': 'Quest started',
        'QUEST_COMPLETE': 'Quest completed',
        'QUEST_FAIL': 'Quest failed',
        'CLAN_JOIN': 'Joined clan',
        'CLAN_LEAVE': 'Left clan',
        'ABILITY_LEARN': 'Learned ability',
        'EQUIPMENT_CHANGE': 'Equipment changed',
        'GOLD_TRANSACTION': 'Gold transaction',
        'XP_GAIN': 'Experience gained',
        'LEVEL_UP': 'Level up'
    }
    
    @classmethod
    def log_event(cls, event_type, event_data, user_id=None, character_id=None, ip_address=None):
        """Create a new audit log entry."""
        if isinstance(event_type, EventType):
            event_type = event_type.value
        if event_type not in cls.EVENT_TYPES:
            raise ValueError(f"Invalid event type: {event_type}")
            
        log = cls(
            event_type=event_type,
            user_id=user_id,
            character_id=character_id,
            event_data=event_data,
            ip_address=ip_address
        )
        log.save()
        return log
    
    @classmethod
    def get_user_events(cls, user_id, event_type=None, start_date=None, end_date=None):
        """Get audit logs for a specific user with optional filters."""
        query = cls.query.filter_by(user_id=user_id)
        
        if event_type:
            query = query.filter_by(event_type=event_type)
        if start_date:
            query = query.filter(cls.event_timestamp >= start_date)
        if end_date:
            query = query.filter(cls.event_timestamp <= end_date)
            
        return query.order_by(cls.event_timestamp.desc()).all()
    
    @classmethod
    def get_character_events(cls, character_id, event_type=None, start_date=None, end_date=None):
        """Get audit logs for a specific character with optional filters."""
        query = cls.query.filter_by(character_id=character_id)
        
        if event_type:
            query = query.filter_by(event_type=event_type)
        if start_date:
            query = query.filter(cls.event_timestamp >= start_date)
        if end_date:
            query = query.filter(cls.event_timestamp <= end_date)
            
        return query.order_by(cls.event_timestamp.desc()).all()
    
    @classmethod
    def get_recent_events(cls, limit=50, event_type=None):
        """Get the most recent audit logs with optional event type filter."""
        query = cls.query
        
        if event_type:
            query = query.filter_by(event_type=event_type)
            
        return query.order_by(cls.event_timestamp.desc()).limit(limit).all()

    @validates('event_type')
    def validate_event_type(self, key, value):
        if value not in self.EVENT_TYPES:
            raise ValueError(f"Invalid event type: {value}")
        return value 