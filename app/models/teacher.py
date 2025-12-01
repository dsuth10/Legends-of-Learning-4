from app.models import db, Base
from datetime import datetime

class Teacher(Base):
    __tablename__ = 'teachers'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    
    # Teacher specific fields can go here
    title = db.Column(db.String(32), nullable=True)  # e.g., Mr., Mrs., Dr.
    bio = db.Column(db.Text, nullable=True)
    
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', backref=db.backref('teacher_profile', uselist=False))
    
    def __repr__(self):
        return f'<Teacher user_id={self.user_id}>'
