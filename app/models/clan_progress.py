from app.models.base import Base
from app.models import db
from datetime import datetime

class ClanProgressHistory(Base):
    __tablename__ = 'clan_progress_history'

    id = db.Column(db.Integer, primary_key=True)
    clan_id = db.Column(db.Integer, db.ForeignKey('clans.id', ondelete='CASCADE'), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Core metrics
    avg_completion_rate = db.Column(db.Float, nullable=False, default=0.0)
    total_points = db.Column(db.Integer, nullable=False, default=0)
    active_members = db.Column(db.Integer, nullable=False, default=0)

    # Advanced metrics
    avg_daily_points = db.Column(db.Float, nullable=True)
    quest_completion_rate = db.Column(db.Float, nullable=True)
    avg_member_level = db.Column(db.Float, nullable=True)
    percentile_rank = db.Column(db.Integer, nullable=True)

    # Relationships
    clan = db.relationship('Clan', backref=db.backref('progress_history', lazy='dynamic'))

    def __repr__(self):
        return f'<ClanProgressHistory clan_id={self.clan_id} timestamp={self.timestamp}>'

    def to_dict(self):
        return {
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "avg_completion_rate": self.avg_completion_rate,
            "total_points": self.total_points,
            "active_members": self.active_members,
            "avg_daily_points": self.avg_daily_points,
            "quest_completion_rate": self.quest_completion_rate,
            "avg_member_level": self.avg_member_level,
            "percentile_rank": self.percentile_rank,
        } 