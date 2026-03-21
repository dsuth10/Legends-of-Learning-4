from app.models import db, Base
from app.utils.date_utils import get_utc_now

class Student(Base):
    __tablename__ = 'students'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    class_id = db.Column(db.Integer, db.ForeignKey('classrooms.id', ondelete='CASCADE'), nullable=True)
    clan_id = db.Column(db.Integer, db.ForeignKey('clans.id', ondelete='SET NULL'), nullable=True)
    xp = db.Column(db.Integer, default=0, nullable=False)
    level = db.Column(db.Integer, default=1, nullable=False)
    health = db.Column(db.Integer, default=100, nullable=False)
    power = db.Column(db.Integer, default=100, nullable=False)
    gold = db.Column(db.Integer, default=0, nullable=False)
    last_activity = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=get_utc_now)
    updated_at = db.Column(db.DateTime, nullable=False, default=get_utc_now, onupdate=get_utc_now)
    status = db.Column(db.String(32), nullable=False, default='active')

    # Relationships
    user = db.relationship('User', backref=db.backref('student_profile', uselist=False))
    classroom = db.relationship('Classroom', backref=db.backref('student_members', lazy='dynamic'))
    clan = db.relationship('Clan', backref=db.backref('clan_members', lazy='dynamic'))
    purchases = db.relationship(
        'ShopPurchase', back_populates='student', cascade='all, delete-orphan'
    )

    def __repr__(self):
        return f'<Student user_id={self.user_id} class_id={self.class_id} level={self.level}>' 