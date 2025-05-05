from app.models.base import Base
from app.models import db
from datetime import datetime

class Clan(Base):
    """Clan model for organizing students into teams."""
    
    __tablename__ = 'clans'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), nullable=False)
    description = db.Column(db.Text, nullable=True)
    emblem = db.Column(db.String(256), nullable=True)  # Path/URL to clan emblem image
    level = db.Column(db.Integer, default=1, nullable=False)
    experience = db.Column(db.Integer, default=0, nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Foreign Keys
    class_id = db.Column(db.Integer, db.ForeignKey('classrooms.id', ondelete='CASCADE'), nullable=False)
    leader_id = db.Column(db.Integer, db.ForeignKey('characters.id', ondelete='SET NULL'), nullable=True)
    
    # Relationships
    class_ = db.relationship(
        'Classroom',
        backref=db.backref('classroom_clans', lazy='dynamic', overlaps="clans,classroom"),
        overlaps="clans,classroom"
    )
    leader = db.relationship('Character', foreign_keys=[leader_id], backref=db.backref('leading_clan', uselist=False), post_update=True)
    # Note: members relationship is defined in Character model
    
    __table_args__ = (
        db.Index('idx_clan_class', 'class_id'),  # For looking up clans in a classroom
        db.UniqueConstraint('name', 'class_id', name='uq_clan_name_class'),  # Unique clan names within a classroom
    )
    
    def __init__(self, name, class_id, description=None, **kwargs):
        super().__init__(**kwargs)
        self.name = name
        self.class_id = class_id
        self.description = description
    
    def set_leader(self, character):
        """Set a character as the clan leader."""
        if character not in self.members:
            raise ValueError("Character must be a clan member to become leader")
        self.leader = character
        self.save()
    
    def add_member(self, character):
        """Add a character to the clan."""
        max_size = self.class_.max_clan_size if self.class_ and self.class_.max_clan_size is not None else 9999
        if len(self.members.all()) >= max_size:
            raise ValueError("Clan is full")
        character.join_clan(self)
        self.save()
    
    def remove_member(self, character):
        """Remove a character from the clan."""
        if character == self.leader:
            self.leader = None
        character.leave_clan()
        self.save()
    
    def gain_experience(self, amount):
        """Add experience points and handle clan level ups."""
        self.experience += amount
        # Simple level up formula: level = experience // 5000
        new_level = (self.experience // 5000) + 1
        if new_level > self.level:
            self.level = new_level
            self.save()
    
    def get_member_count(self):
        """Get the current number of members in the clan."""
        return self.members.count()
    
    def __repr__(self):
        return f'<Clan {self.name} (Level {self.level})>' 