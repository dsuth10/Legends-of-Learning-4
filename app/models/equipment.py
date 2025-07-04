from app.models.base import Base
from datetime import datetime
from enum import Enum

class EquipmentType(Enum):
    WEAPON = 'weapon'
    ARMOR = 'armor'
    ACCESSORY = 'accessory'

class EquipmentSlot(Enum):
    MAIN_HAND = 'main_hand'
    OFF_HAND = 'off_hand'
    HEAD = 'head'
    CHEST = 'chest'
    LEGS = 'legs'
    FEET = 'feet'
    NECK = 'neck'
    RING = 'ring'

class Equipment(Base):
    """Equipment model for items that can be equipped by characters."""
    
    __tablename__ = 'equipment'
    
    from app.models import db
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), nullable=False)
    description = db.Column(db.Text)
    type = db.Column(db.String(16), nullable=False)
    slot = db.Column(db.String(16), nullable=False)
    level_requirement = db.Column(db.Integer, default=1, nullable=False)
    
    # Stats
    health_bonus = db.Column(db.Integer, default=0, nullable=False)
    strength_bonus = db.Column(db.Integer, default=0, nullable=False)
    defense_bonus = db.Column(db.Integer, default=0, nullable=False)
    
    # Metadata
    rarity = db.Column(db.Integer, default=1, nullable=False)  # 1=common, 2=uncommon, 3=rare, 4=epic, 5=legendary
    is_tradeable = db.Column(db.Boolean, default=True, nullable=False)
    cost = db.Column(db.Integer, default=0, nullable=False)  # Cost in gold to purchase
    image_url = db.Column(db.String(256), nullable=True)
    class_restriction = db.Column(db.String(32), nullable=True)
    
    def __init__(self, name, type, slot, cost=0, **kwargs):
        super().__init__(**kwargs)
        self.name = name
        self.type = type
        self.slot = slot
        self.cost = cost
    
    def __repr__(self):
        return f'<Equipment {self.name} ({self.type})>'

class Inventory(Base):
    """Inventory model for tracking character equipment ownership."""
    
    __tablename__ = 'inventories'
    
    from app.models import db
    id = db.Column(db.Integer, primary_key=True)
    character_id = db.Column(db.Integer, db.ForeignKey('characters.id', ondelete='CASCADE'), nullable=False)
    item_id = db.Column(db.Integer, db.ForeignKey('equipment.id', ondelete='CASCADE'), nullable=False)
    is_equipped = db.Column(db.Boolean, default=False, nullable=False)
    acquired_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    
    # Relationships
    character = db.relationship('Character', backref=db.backref('inventory_items', lazy='dynamic', cascade='all, delete-orphan'))
    item = db.relationship('Equipment')
    equipment = db.relationship('Equipment', primaryjoin='Inventory.item_id == Equipment.id', foreign_keys='Inventory.item_id', overlaps="item")
    
    __table_args__ = (
        db.Index('idx_inventory_character', 'character_id'),  # For looking up character's inventory
        db.Index('idx_inventory_equipped', 'character_id', 'is_equipped'),  # For equipped items
    )
    
    def __init__(self, character_id, item_id, **kwargs):
        super().__init__(**kwargs)
        self.character_id = character_id
        self.item_id = item_id
    
    @classmethod
    def get_equipped_items(cls, character_id):
        """Get all equipped items for a character."""
        return cls.query.filter_by(character_id=character_id, is_equipped=True).all()
    
    def equip(self):
        """Equip this item, unequipping any item in the same slot."""
        from app.models import db
        if not self.is_equipped:
            # Unequip any item in the same slot
            current_equipped = Inventory.query.join(Equipment).filter(
                Inventory.character_id == self.character_id,
                Inventory.is_equipped == True,
                Equipment.slot == self.item.slot
            ).first()
            
            if current_equipped:
                current_equipped.is_equipped = False
                current_equipped.save()
            
            self.is_equipped = True
            self.save()
    
    def unequip(self):
        """Unequip this item."""
        from app.models import db
        if self.is_equipped:
            self.is_equipped = False
            self.save()
    
    def __repr__(self):
        status = "equipped" if self.is_equipped else "in inventory"
        return f'<Inventory {self.item.name} ({status})>'

# Default image filenames for test items
TEST_ARMOR_IMAGE = '/static/images/test_armor.png'
TEST_RING_IMAGE = '/static/images/test_ring.png'
TEST_SWORD_IMAGE = '/static/images/test_sword.png' 