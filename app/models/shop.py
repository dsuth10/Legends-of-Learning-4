from datetime import datetime
from sqlalchemy.orm import validates
from app.models import db
from app.models.base import Base
from app.models.character import Character
from app.models.student import Student
from enum import Enum

class PurchaseType(Enum):
    EQUIPMENT = 'equipment'
    ABILITY = 'ability'
    SHOP = 'shop'  # Added to support shop purchases

class ShopPurchase(Base):
    """Model for tracking purchases made in the game shop."""
    
    __tablename__ = 'shop_purchases'
    
    id = db.Column(db.Integer, primary_key=True)
    character_id = db.Column(db.Integer, db.ForeignKey('characters.id', ondelete='CASCADE'), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id', ondelete='CASCADE'), nullable=False)
    gold_spent = db.Column(db.Integer, nullable=False)
    purchase_type = db.Column(db.String(20), nullable=False)  # 'equipment' or 'ability'
    item_id = db.Column(db.Integer, nullable=False)  # ID of the purchased equipment or ability
    purchase_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    
    # Relationships
    character = db.relationship('Character', back_populates='purchases')
    student = db.relationship('Student', back_populates='purchases')
    
    @validates('purchase_type')
    def validate_purchase_type(self, key, value):
        """Validate that purchase_type is either 'equipment' or 'ability'."""
        if isinstance(value, PurchaseType):
            value = value.value
        if value not in [PurchaseType.EQUIPMENT.value, PurchaseType.ABILITY.value, PurchaseType.SHOP.value]:
            raise ValueError("purchase_type must be either 'equipment', 'ability', or 'shop'")
        return value
    
    @validates('gold_spent')
    def validate_gold_spent(self, key, value):
        """Validate that gold_spent is a positive integer."""
        if not isinstance(value, int) or value <= 0:
            raise ValueError("gold_spent must be a positive integer")
        return value
    
    def get_purchased_item(self):
        """Get the purchased item (equipment or ability) based on purchase_type."""
        if self.purchase_type == 'equipment':
            from app.models.equipment import Equipment
            return Equipment.get_by_id(self.item_id)
        else:  # ability
            from app.models.ability import Ability
            return Ability.get_by_id(self.item_id)
    
    @classmethod
    def get_character_purchases(cls, character_id, purchase_type=None):
        """Get all purchases made by a character, optionally filtered by purchase_type."""
        query = cls.query.filter_by(character_id=character_id)
        if purchase_type is not None:
            query = query.filter_by(purchase_type=purchase_type)
        return query.order_by(cls.purchase_date.desc()).all()
    
    @classmethod
    def get_recent_purchases(cls, limit=10):
        """Get the most recent purchases across all characters."""
        return cls.query.order_by(cls.purchase_date.desc()).limit(limit).all()

# At the end of the file, after both classes are defined:
from app.models.character import Character
from app.models.student import Student
ShopPurchase.character = db.relationship('Character', back_populates='purchases')
ShopPurchase.student = db.relationship('Student', back_populates='purchases')
Character.purchases = db.relationship('ShopPurchase', back_populates='character', cascade='all, delete-orphan')
Student.purchases = db.relationship('ShopPurchase', back_populates='student', cascade='all, delete-orphan') 