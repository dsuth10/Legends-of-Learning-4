import pytest
from flask import url_for
from sqlalchemy import text

# --- DEBUG: Print inventories table schema ---
def test_print_inventories_schema(db_session):
    result = db_session.execute(text("SELECT sql FROM sqlite_master WHERE type='table' AND name='inventories';"))
    print("\n[DEBUG] inventories CREATE TABLE SQL:\n", result.fetchone()[0])

# --- Shop Listing ---
def test_shop_listing(client, db_session, test_user, test_character, test_equipment):
    with client:
        client.post('/auth/login', data={'username': test_user.username, 'password': 'password'}, follow_redirects=True)
        response = client.get('/student/shop')
        assert response.status_code == 200
        assert b"Test Sword" in response.data  # or check for JSON if API

# --- Purchase Success ---
def test_purchase_success(client, db_session, test_user, test_character, test_equipment):
    db_session.rollback()
    test_character.gold = 200
    db_session.commit()
    with client:
        client.post('/auth/login', data={'username': test_user.username, 'password': 'password'}, follow_redirects=True)
        response = client.post('/student/shop/buy', json={
            "item_id": test_equipment.id,
            "item_type": "equipment"
        })
    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    db_session.refresh(test_character)
    assert test_character.gold == 100

# --- Purchase: Insufficient Gold ---
def test_purchase_insufficient_gold(client, db_session, test_user, test_character, test_equipment):
    test_character.gold = 50
    db_session.commit()
    with client:
        client.post('/auth/login', data={'username': test_user.username, 'password': 'password'}, follow_redirects=True)
        response = client.post('/student/shop/buy', json={
            "item_id": test_equipment.id,
            "item_type": "equipment"
        })
    assert response.status_code == 400
    assert b"not enough gold" in response.data.lower()

# --- Purchase: Already Owned ---
def test_purchase_already_owned(client, db_session, test_user, test_character, test_equipment, test_item):
    from app.models.equipment import Inventory
    db_session.refresh(test_character)
    db_session.refresh(test_equipment)
    # Use test_equipment.id for item_id, which matches a valid Item
    inv = Inventory(character_id=test_character.id, item_id=test_equipment.id)
    db_session.add(inv)
    db_session.commit()
    test_character.gold = 200
    db_session.commit()
    with client:
        client.post('/auth/login', data={'username': test_user.username, 'password': 'password'}, follow_redirects=True)
        response = client.post('/student/shop/buy', json={
            "item_id": test_equipment.id,
            "item_type": "equipment"
        })
    assert response.status_code == 400
    assert b"already owned" in response.data.lower()

# --- Purchase: Level Restriction ---
def test_purchase_level_restriction(client, db_session, test_user, test_character, test_equipment):
    test_equipment.level_requirement = 10
    db_session.commit()
    test_character.level = 1
    test_character.gold = 200
    db_session.commit()
    with client:
        client.post('/auth/login', data={'username': test_user.username, 'password': 'password'}, follow_redirects=True)
        response = client.post('/student/shop/buy', json={
            "item_id": test_equipment.id,
            "item_type": "equipment"
        })
    assert response.status_code == 400
    assert b"level" in response.data.lower()

# --- Purchase: Class Restriction ---
def test_purchase_class_restriction(client, db_session, test_user, test_character, test_equipment):
    test_equipment.class_restriction = "Sorcerer"
    db_session.commit()
    test_character.character_class = "Warrior"
    test_character.gold = 200
    db_session.commit()
    with client:
        client.post('/auth/login', data={'username': test_user.username, 'password': 'password'}, follow_redirects=True)
        response = client.post('/student/shop/buy', json={
            "item_id": test_equipment.id,
            "item_type": "equipment"
        })
    assert response.status_code == 400
    assert b"class restriction" in response.data.lower()

# --- Purchase: Invalid Item ID ---
def test_purchase_invalid_item_id(client, db_session, test_user, test_character):
    test_character.gold = 200
    db_session.commit()
    with client:
        client.post('/auth/login', data={'username': test_user.username, 'password': 'password'}, follow_redirects=True)
        response = client.post('/student/shop/buy', json={
            "item_id": 99999,
            "item_type": "equipment"
        })
    assert response.status_code == 404
    assert b"item not found" in response.data.lower()

# --- Equip Item ---
def test_equip_item(client, db_session, test_user, test_character, equipment_with_item):
    from app.models.equipment import Inventory
    db_session.refresh(test_character)
    db_session.refresh(equipment_with_item)
    inv = Inventory(character_id=test_character.id, item_id=equipment_with_item.id)
    db_session.add(inv)
    db_session.commit()
    with client:
        client.post('/auth/login', data={'username': test_user.username, 'password': 'password'}, follow_redirects=True)
        response = client.patch('/student/equipment/equip', json={
            "inventory_id": inv.id,
            "slot": "weapon"
        })
    assert response.status_code == 200
    db_session.refresh(inv)
    assert inv.is_equipped is True

# --- Unequip Item ---
def test_unequip_item(client, db_session, test_user, test_character, test_equipment):
    from app.models.equipment import Inventory
    db_session.refresh(test_character)
    db_session.refresh(test_equipment)
    inv = Inventory(character_id=test_character.id, item_id=test_equipment.id, is_equipped=True)
    db_session.add(inv)
    db_session.commit()
    with client:
        client.post('/auth/login', data={'username': test_user.username, 'password': 'password'}, follow_redirects=True)
        response = client.patch('/student/equipment/unequip', json={
            "inventory_id": inv.id
        })
    assert response.status_code == 200
    db_session.refresh(inv)
    assert inv.is_equipped is False

# --- Equip Item Not in Inventory ---
def test_equip_item_not_in_inventory(client, db_session, test_user, test_character, test_equipment):
    with client:
        client.post('/auth/login', data={'username': test_user.username, 'password': 'password'}, follow_redirects=True)
        response = client.patch('/student/equipment/equip', json={
            "inventory_id": 99999,
            "slot": "weapon"
        })
    assert response.status_code == 404
    assert b"item not found" in response.data.lower()

# --- Equip Two Items in Same Slot (should unequip previous) ---
def test_equip_two_items_same_slot(client, db_session, test_user, test_character, test_equipment, test_item):
    from app.models.equipment import Equipment, Inventory, EquipmentType, EquipmentSlot
    from app.models.item import Item
    db_session.refresh(test_character)
    db_session.refresh(test_equipment)
    # Create two items and two weapons
    item1 = test_item
    weapon1 = test_equipment
    # Ensure Item exists for weapon1 (should already exist via fixture)
    # Create a second weapon and matching item with a unique ID
    weapon2 = Equipment(
        name='Test Sword 2',
        type=EquipmentType.WEAPON,
        slot=EquipmentSlot.MAIN_HAND,
        cost=50
    )
    db_session.add(weapon2)
    db_session.commit()
    # Only create Item if it doesn't exist
    existing_item = Item.query.get(weapon2.id)
    if not existing_item:
        item2 = Item(
            id=weapon2.id,
            name="Test Sword 2",
            description="A second test sword.",
            type="weapon",
            tier=1,
            slot="main_hand",
            class_restriction=None,
            level_requirement=1,
            price=50,
            image_path=None
        )
        db_session.add(item2)
        db_session.commit()
    # Now proceed with the rest of the test logic
    # Add both to inventory
    inv1 = Inventory(character_id=test_character.id, item_id=weapon1.id, is_equipped=True)
    inv2 = Inventory(character_id=test_character.id, item_id=weapon2.id, is_equipped=False)
    db_session.add_all([inv1, inv2])
    db_session.commit()
    with client:
        client.post('/auth/login', data={'username': test_user.username, 'password': 'password'}, follow_redirects=True)
        # Equip second weapon
        response = client.patch('/student/equipment/equip', json={
            "inventory_id": inv2.id,
            "slot": "weapon"
        })
    assert response.status_code == 200
    db_session.refresh(inv1)
    db_session.refresh(inv2)
    assert inv1.is_equipped is False
    assert inv2.is_equipped is True

# --- Purchase: Missing Payload ---
def test_purchase_missing_payload(client, db_session, test_user, test_character):
    test_character.gold = 200
    db_session.commit()
    with client:
        client.post('/auth/login', data={'username': test_user.username, 'password': 'password'}, follow_redirects=True)
        response = client.post('/student/shop/buy', json={})
    assert response.status_code == 400
    assert b"missing item_id" in response.data.lower()

# --- Teacher Purchase Log (if endpoint exists) ---
# Uncomment and adjust if you have a /teacher/purchases endpoint and teacher_user fixture
# def test_teacher_purchase_log(client, db_session, teacher_user, test_student, test_equipment):
#     from app.models.shop import ShopPurchase
#     purchase = ShopPurchase(student_id=test_student.id, character_id=1, item_id=test_equipment.id, gold_spent=100)
#     db_session.add(purchase)
#     db_session.commit()
#     client.post('/login', data={'username': teacher_user.username, 'password': 'password'})
#     response = client.get('/teacher/purchases')
#     assert response.status_code == 200
#     assert b"Test Sword" in response.data 

# --- Unequip Weapon ---
def test_unequip_weapon(client, db_session, test_user, test_character, test_equipment):
    db_session.rollback()
    from app.models.equipment import Inventory, EquipmentType, EquipmentSlot
    # Equip a weapon for the character
    inv = Inventory(character_id=test_character.id, item_id=test_equipment.id, is_equipped=True)
    db_session.add(inv)
    db_session.commit()
    with client:
        client.post('/auth/login', data={'username': test_user.username, 'password': 'password'}, follow_redirects=True)
        response = client.post('/student/character/unequip_weapon', data={
            "character_id": test_character.id
        }, follow_redirects=True)
    assert response.status_code == 200
    db_session.refresh(test_character)
    assert test_character.equipped_weapon is None

# --- Unequip Armor ---
def test_unequip_armor(client, db_session, test_user, test_character, test_equipment):
    db_session.rollback()
    from app.models.equipment import Equipment, EquipmentType, EquipmentSlot, Inventory
    from app.models.item import Item
    # Create and equip an armor
    armor = Equipment(
        name="Test Armor",
        type=EquipmentType.ARMOR,
        slot=EquipmentSlot.CHEST,
        cost=50
    )
    db_session.add(armor)
    db_session.commit()
    # Create a matching Item for the armor if it doesn't exist
    existing_item = Item.query.get(armor.id)
    if not existing_item:
        item = Item(
            id=armor.id,
            name="Test Armor",
            description="A test armor.",
            type="armor",
            tier=1,
            slot="chest",
            class_restriction=None,
            level_requirement=1,
            price=50,
            image_path=None
        )
        db_session.add(item)
        db_session.commit()
    inv = Inventory(character_id=test_character.id, item_id=armor.id, is_equipped=True)
    db_session.add(inv)
    db_session.commit()
    with client:
        client.post('/auth/login', data={'username': test_user.username, 'password': 'password'}, follow_redirects=True)
        response = client.post('/student/character/unequip_armor', data={
            "character_id": test_character.id
        }, follow_redirects=True)
    assert response.status_code == 200
    db_session.refresh(test_character)
    assert test_character.equipped_armor is None

# --- Unequip Accessory ---
def test_unequip_accessory(client, db_session, test_user, test_character, test_equipment):
    db_session.rollback()
    from app.models.equipment import Equipment, EquipmentType, EquipmentSlot, Inventory
    from app.models import db
    # Create and equip an accessory
    accessory = Equipment(
        name="Test Ring",
        type=EquipmentType.ACCESSORY,
        slot=EquipmentSlot.RING,
        cost=25
    )
    db_session.add(accessory)
    db_session.commit()
    item_table = db.Table('items', db.metadata, autoload_with=db.engine)
    db_session.execute(item_table.insert().values(
        id=accessory.id,
        name="Test Ring",
        description="A test ring.",
        type="accessory",
        tier=1,
        slot="ring",
        class_restriction=None,
        price=25
    ))
    db_session.commit()
    inv = Inventory(character_id=test_character.id, item_id=accessory.id, is_equipped=True)
    db_session.add(inv)
    db_session.commit()
    with client:
        client.post('/auth/login', data={'username': test_user.username, 'password': 'password'}, follow_redirects=True)
        response = client.post('/student/character/unequip_accessory', data={
            "character_id": test_character.id
        }, follow_redirects=True)
    assert response.status_code == 200
    db_session.refresh(test_character)
    assert test_character.equipped_accessory is None

@pytest.fixture
def equipment_with_item(db_session):
    from app.models.equipment import Equipment, EquipmentType, EquipmentSlot
    from app.models.item import Item
    equipment = Equipment(
        name='Test Sword',
        type=EquipmentType.WEAPON,
        slot=EquipmentSlot.MAIN_HAND,
        cost=100,
        level_requirement=1
    )
    db_session.add(equipment)
    db_session.commit()
    # Create a matching Item row with the same ID if it doesn't exist
    if not Item.query.get(equipment.id):
        item = Item(
            id=equipment.id,
            name=equipment.name,
            description="A test sword.",
            type="weapon",
            tier=1,
            slot="main_hand",
            class_restriction=None,
            level_requirement=1,
            price=equipment.cost,
            image_path=None
        )
        db_session.add(item)
        db_session.commit()
    return equipment 