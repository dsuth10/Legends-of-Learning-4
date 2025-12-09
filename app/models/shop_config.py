from app.models.base import Base
from app.models import db
from datetime import datetime

class ShopItemOverride(Base):
    """Model for overriding shop item properties per classroom."""
    
    __tablename__ = 'shop_item_overrides'
    
    id = db.Column(db.Integer, primary_key=True)
    classroom_id = db.Column(db.Integer, db.ForeignKey('classrooms.id', ondelete='CASCADE'), nullable=False)
    item_type = db.Column(db.String(20), nullable=False)  # 'equipment' or 'ability'
    item_id = db.Column(db.Integer, nullable=False)
    
    # Overrides (Null means use default)
    override_cost = db.Column(db.Integer, nullable=True)
    override_level_req = db.Column(db.Integer, nullable=True)
    is_visible = db.Column(db.Boolean, default=True, nullable=False)
    
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    classroom = db.relationship('Classroom', backref=db.backref('shop_overrides', lazy='dynamic', cascade='all, delete-orphan'))
    
    __table_args__ = (
        db.UniqueConstraint('classroom_id', 'item_type', 'item_id', name='uq_classroom_item_override'),
        db.Index('idx_shop_override_classroom', 'classroom_id'),
    )
    
    def __init__(self, classroom_id, item_type, item_id, **kwargs):
        super().__init__(**kwargs)
        self.classroom_id = classroom_id
        self.item_type = item_type
        self.item_id = item_id
    
    def __repr__(self):
        return f'<ShopItemOverride Class:{self.classroom_id} Item:{self.item_type}:{self.item_id}>'
