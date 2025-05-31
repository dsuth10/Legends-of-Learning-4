from app.models.base import Base
from app.models import db

class Item(Base):
    __tablename__ = 'items'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), nullable=False)
    description = db.Column(db.Text, nullable=True)
    type = db.Column(db.String(32), nullable=False)
    tier = db.Column(db.Integer, nullable=False)
    slot = db.Column(db.String(32), nullable=True)
    class_restriction = db.Column(db.String(32), nullable=True)
    level_requirement = db.Column(db.Integer, nullable=False, default=1)
    price = db.Column(db.Integer, nullable=False)
    image_path = db.Column(db.String(256), nullable=True)

    def __repr__(self):
        return f'<Item {self.name} (type={self.type}, tier={self.tier})>' 