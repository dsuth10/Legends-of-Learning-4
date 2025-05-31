from app.models import db

clan_badges = db.Table(
    'clan_badges',
    db.Column('clan_id', db.Integer, db.ForeignKey('clans.id'), primary_key=True),
    db.Column('badge_id', db.Integer, db.ForeignKey('achievement_badge.id'), primary_key=True)
)

character_badges = db.Table(
    'character_badges',
    db.Column('character_id', db.Integer, db.ForeignKey('characters.id'), primary_key=True),
    db.Column('badge_id', db.Integer, db.ForeignKey('achievement_badge.id'), primary_key=True)
)

class AchievementBadge(db.Model):
    __tablename__ = 'achievement_badge'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), nullable=False)
    description = db.Column(db.Text, nullable=True)
    icon = db.Column(db.String(256), nullable=False)  # Path/URL to badge icon
    criteria = db.Column(db.Text, nullable=True)      # JSON or text description of how to earn
    is_clan = db.Column(db.Boolean, default=False)
    is_student = db.Column(db.Boolean, default=False)

    clans = db.relationship('Clan', secondary=clan_badges, backref='badges')
    characters = db.relationship('Character', secondary=character_badges, backref='badges') 