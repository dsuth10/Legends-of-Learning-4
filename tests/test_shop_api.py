import pytest
from flask import url_for
from sqlalchemy import text

@pytest.fixture
def test_equipment(db_session):
    from app.models.equipment import Equipment
    eq = db_session.query(Equipment).first()
    if eq is None:
        eq = Equipment(name='Test Sword', type='weapon', slot='main_hand', cost=100)
        db_session.add(eq)
        db_session.commit()
    return eq

@pytest.fixture
def test_weapon(db_session):
    from app.models.equipment import Equipment
    weapon = db_session.query(Equipment).filter_by(name='Test Sword').first()
    if weapon is None:
        weapon = Equipment(name='Test Sword', type='weapon', slot='main_hand', cost=100, class_restriction='Warrior', level_requirement=1)
        db_session.add(weapon)
        db_session.commit()
    return weapon

@pytest.fixture
def test_armor(db_session):
    from app.models.equipment import Equipment
    armor = db_session.query(Equipment).filter_by(type='armor').first()
    if armor is None:
        armor = Equipment(name='Test Armor', type='armor', slot='chest', cost=50)
        db_session.add(armor)
        db_session.commit()
    return armor

@pytest.fixture
def test_accessory(db_session):
    from app.models.equipment import Equipment
    accessory = db_session.query(Equipment).filter_by(type='accessory').first()
    if accessory is None:
        accessory = Equipment(name='Test Ring', type='accessory', slot='ring', cost=25)
        db_session.add(accessory)
        db_session.commit()
    return accessory

# --- DEBUG: Print inventories table schema ---
def test_print_inventories_schema(db_session):
    result = db_session.execute(text("SELECT sql FROM sqlite_master WHERE type='table' AND name='inventories';"))
    print("\n[DEBUG] inventories CREATE TABLE SQL:\n", result.fetchone()[0])

# --- Shop Listing ---
def test_shop_listing(client, db_session, test_user, test_character, test_weapon):
    test_character.gold = 200
    test_character.level = 10
    test_character.character_class = 'Warrior'
    db_session.commit()
    with client:
        client.post('/auth/login', data={'username': test_user.username, 'password': 'password'}, follow_redirects=True)
        response = client.get('/student/shop')
        assert response.status_code == 200
        assert test_weapon.name.encode() in response.data

# --- Purchase Success ---
def test_purchase_success(client, db_session, test_user, test_character, test_weapon):
    db_session.rollback()
    test_character.gold = 200
    test_character.level = 10
    test_character.character_class = 'Warrior'
    db_session.commit()
    with client:
        client.post('/auth/login', data={'username': test_user.username, 'password': 'password'}, follow_redirects=True)
        response = client.post('/student/shop/buy', json={
            "item_id": test_weapon.id,
            "item_type": "equipment"
        })
    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    db_session.refresh(test_character)
    assert test_character.gold == 100

# --- Purchase: Insufficient Gold ---
def test_purchase_insufficient_gold(client, db_session, test_user, test_character, test_weapon):
    test_character.gold = 50
    db_session.commit()
    with client:
        client.post('/auth/login', data={'username': test_user.username, 'password': 'password'}, follow_redirects=True)
        response = client.post('/student/shop/buy', json={
            "item_id": test_weapon.id,
            "item_type": "equipment"
        })
    assert response.status_code == 400
    assert b"not enough gold" in response.data.lower()

# --- Purchase: Already Owned ---
def test_purchase_already_owned(client, db_session, test_user, test_character, test_weapon):
    from app.models.equipment import Inventory
    db_session.refresh(test_character)
    db_session.refresh(test_weapon)
    # Add equipment to inventory to simulate already owned
    inv = Inventory(character_id=test_character.id, item_id=test_weapon.id)
    db_session.add(inv)
    db_session.commit()
    test_character.gold = 200
    db_session.commit()
    with client:
        client.post('/auth/login', data={'username': test_user.username, 'password': 'password'}, follow_redirects=True)
        response = client.post('/student/shop/buy', json={
            "item_id": test_weapon.id,
            "item_type": "equipment"
        })
    assert response.status_code == 400
    assert b"already owned" in response.data.lower()

# --- Purchase: Level Restriction ---
def test_purchase_level_restriction(client, db_session, test_user, test_character, test_weapon):
    test_weapon.level_requirement = 10
    db_session.commit()
    test_character.level = 1
    test_character.gold = 200
    db_session.commit()
    with client:
        client.post('/auth/login', data={'username': test_user.username, 'password': 'password'}, follow_redirects=True)
        response = client.post('/student/shop/buy', json={
            "item_id": test_weapon.id,
            "item_type": "equipment"
        })
    assert response.status_code == 400
    assert b"level" in response.data.lower()

# --- Purchase: Class Restriction ---
def test_purchase_class_restriction(client, db_session, test_user, test_character, test_weapon):
    test_weapon.class_restriction = "Sorcerer"
    db_session.commit()
    test_character.character_class = "Warrior"
    test_character.level = test_weapon.level_requirement
    test_character.gold = 200
    db_session.commit()
    with client:
        client.post('/auth/login', data={'username': test_user.username, 'password': 'password'}, follow_redirects=True)
        response = client.post('/student/shop/buy', json={
            "item_id": test_weapon.id,
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
def test_equip_item(client, db_session, test_user, test_character, test_weapon):
    from app.models.equipment import Inventory
    test_character.character_class = 'Warrior'
    test_character.level = 10
    db_session.commit()
    db_session.refresh(test_character)
    db_session.refresh(test_weapon)
    inv = Inventory(character_id=test_character.id, item_id=test_weapon.id)
    db_session.add(inv)
    db_session.commit()
    with client:
        client.post('/auth/login', data={'username': test_user.username, 'password': 'password'}, follow_redirects=True)
        response = client.patch('/student/equipment/equip', json={
            "inventory_id": inv.id,
            "slot": test_weapon.slot
        })
    assert response.status_code == 200
    db_session.refresh(inv)
    assert inv.is_equipped is True

# --- Unequip Item ---
def test_unequip_item(client, db_session, test_user, test_character, test_weapon):
    from app.models.equipment import Inventory
    db_session.refresh(test_character)
    db_session.refresh(test_weapon)
    inv = Inventory(character_id=test_character.id, item_id=test_weapon.id, is_equipped=True)
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
def test_equip_item_not_in_inventory(client, db_session, test_user, test_character, test_weapon):
    with client:
        client.post('/auth/login', data={'username': test_user.username, 'password': 'password'}, follow_redirects=True)
        response = client.patch('/student/equipment/equip', json={
            "inventory_id": 99999,
            "slot": "main_hand"
        })
    assert response.status_code == 404
    assert b"item not found" in response.data.lower()

# --- Equip Two Items in Same Slot (should unequip previous) ---
def test_equip_two_items_same_slot(client, db_session, test_user, test_character, test_weapon):
    from app.models.equipment import Equipment, Inventory, EquipmentType, EquipmentSlot
    test_character.character_class = 'Warrior'
    test_character.level = 10
    db_session.commit()
    db_session.refresh(test_character)
    db_session.refresh(test_weapon)
    # Create two weapons
    weapon1 = test_weapon
    weapon2 = Equipment(
        name='Test Sword 2',
        type=EquipmentType.WEAPON.value,
        slot=EquipmentSlot.MAIN_HAND.value,
        cost=50,
        class_restriction='Warrior',
        level_requirement=1
    )
    db_session.add(weapon2)
    db_session.commit()
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
            "slot": weapon2.slot
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
# def test_teacher_purchase_log(client, db_session, teacher_user, test_student, test_weapon):
#     from app.models.shop import ShopPurchase
#     purchase = ShopPurchase(student_id=test_student.id, character_id=1, item_id=test_weapon.id, gold_spent=100)
#     db_session.add(purchase)
#     db_session.commit()
#     client.post('/login', data={'username': teacher_user.username, 'password': 'password'})
#     response = client.get('/teacher/purchases')
#     assert response.status_code == 200
#     assert b"Test Sword" in response.data 

# --- Unequip Weapon ---
def test_unequip_weapon(client, db_session, test_user, test_character, test_weapon):
    db_session.rollback()
    from app.models.equipment import Inventory, EquipmentType, EquipmentSlot
    # Equip a weapon for the character
    inv = Inventory(character_id=test_character.id, item_id=test_weapon.id, is_equipped=True)
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
def test_unequip_armor(client, db_session, test_user, test_character, test_armor):
    db_session.rollback()
    from app.models.equipment import Equipment, EquipmentType, EquipmentSlot, Inventory
    # Create and equip an armor
    armor = test_armor
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
def test_unequip_accessory(client, db_session, test_user, test_character, test_accessory):
    db_session.rollback()
    from app.models.equipment import Equipment, EquipmentType, EquipmentSlot, Inventory
    # Create and equip an accessory
    accessory = test_accessory
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