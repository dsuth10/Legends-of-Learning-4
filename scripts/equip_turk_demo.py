from app import db
from app.models.user import User
from app.models.character import Character
from app.models.equipment import Equipment, EquipmentType, EquipmentSlot, Inventory

user = User.query.filter_by(username='turk').first()
if not user:
    print("No user 'turk' found.")
    exit(1)
character = Character.query.filter_by(student_id=user.id, is_active=True).first()
if not character:
    print("No active character found for 'turk'.")
    exit(1)

# Create or get test equipment
weapon = Equipment.query.filter_by(name='Test Sword').first()
if not weapon:
    weapon = Equipment(
        name='Test Sword',
        description='A sharp blade for testing.',
        type=EquipmentType.WEAPON,
        slot=EquipmentSlot.MAIN_HAND,
        level_requirement=1,
        health_bonus=0,
        power_bonus=5,
        defense_bonus=0,
        cost=0
    )
    db.session.add(weapon)

armor = Equipment.query.filter_by(name='Test Armor').first()
if not armor:
    armor = Equipment(
        name='Test Armor',
        description='Sturdy armor for testing.',
        type=EquipmentType.ARMOR,
        slot=EquipmentSlot.CHEST,
        level_requirement=1,
        health_bonus=20,
        power_bonus=0,
        defense_bonus=5,
        cost=0
    )
    db.session.add(armor)

accessory = Equipment.query.filter_by(name='Test Ring').first()
if not accessory:
    accessory = Equipment(
        name='Test Ring',
        description='A magical ring for testing.',
        type=EquipmentType.ACCESSORY,
        slot=EquipmentSlot.RING,
        level_requirement=1,
        health_bonus=5,
        power_bonus=2,
        defense_bonus=2,
        cost=0
    )
    db.session.add(accessory)

db.session.commit()

def add_and_equip(equipment):
    inv = Inventory.query.filter_by(character_id=character.id, equipment_id=equipment.id).first()
    if not inv:
        inv = Inventory(character_id=character.id, equipment_id=equipment.id, is_equipped=True)
        db.session.add(inv)
    else:
        inv.is_equipped = True
    db.session.commit()
    inv.equip()

add_and_equip(weapon)
add_and_equip(armor)
add_and_equip(accessory)

print("Test equipment added and equipped to turk!") 