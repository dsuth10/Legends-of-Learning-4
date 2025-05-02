from app.models import db, Base
from datetime import datetime

class AssistLog(Base):
    __tablename__ = 'assist_logs'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    target_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    ability_id = db.Column(db.Integer, db.ForeignKey('abilities.id', ondelete='SET NULL'), nullable=True)
    xp_awarded = db.Column(db.Integer, default=0, nullable=False)
    used_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    # Relationships
    user = db.relationship('User', foreign_keys=[user_id], backref=db.backref('assist_logs', lazy='dynamic'))
    target = db.relationship('User', foreign_keys=[target_id], backref=db.backref('assisted_by', lazy='dynamic'))
    ability = db.relationship('Ability', backref=db.backref('assist_logs', lazy='dynamic'))

    def __repr__(self):
        return f'<AssistLog user_id={self.user_id} target_id={self.target_id} xp_awarded={self.xp_awarded}>' 