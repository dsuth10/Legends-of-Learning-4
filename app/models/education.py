from datetime import datetime
from app.models.base import Base
from app.models import db
from sqlalchemy import JSON

class QuestionSet(Base):
    """A collection of questions (e.g., 'Math Level 1')."""
    __tablename__ = 'question_sets'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(128), nullable=False)
    description = db.Column(db.Text, nullable=True)
    teacher_id = db.Column(db.Integer, db.ForeignKey('teachers.id', ondelete='CASCADE'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)

    # Relationships
    questions = db.relationship('Question', backref='question_set', lazy='dynamic', cascade='all, delete-orphan')
    teacher = db.relationship('Teacher', backref='question_sets')

    def __repr__(self):
        return f'<QuestionSet {self.title}>'

class Question(Base):
    """An individual question in a set."""
    __tablename__ = 'questions'

    id = db.Column(db.Integer, primary_key=True)
    set_id = db.Column(db.Integer, db.ForeignKey('question_sets.id', ondelete='CASCADE'), nullable=False)
    text = db.Column(db.Text, nullable=False)
    question_type = db.Column(db.String(32), default='multiple_choice') # multiple_choice, true_false, etc.
    
    # Stored as JSON: ["Option A", "Option B", "Option C", "Option D"]
    options = db.Column(JSON, nullable=False, default=list)
    
    # The correct answer (e.g., "Option A" or the index 0)
    correct_answer = db.Column(db.String(256), nullable=False)
    
    difficulty = db.Column(db.Integer, default=1) # 1-5 scale

    def __repr__(self):
        return f'<Question {self.id} in Set {self.set_id}>'
