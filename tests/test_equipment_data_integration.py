import pytest
from app.models.equipment import Equipment, EquipmentType, EquipmentSlot
from app.models.equipment_data import EQUIPMENT_DATA

def test_equipment_data_populated(db_session):
    """Ensure all items from EQUIPMENT_DATA exist in the Equipment table."""
    for item in EQUIPMENT_DATA:
        type_value = item['type'].value if hasattr(item['type'], 'value') else item['type']
        slot_value = item['slot'].value if hasattr(item['slot'], 'value') else item['slot']
        eq = db_session.query(Equipment).filter_by(
            name=item['name'],
            type=type_value,
            slot=slot_value,
            # If your model has class_restriction, include it:
            # class_restriction=item.get('class_restriction')
        ).first()
        assert eq is not None, f"Missing equipment: {item['name']}"
        assert eq.cost == item['cost']
        assert eq.level_requirement == item['level_requirement']
        assert eq.health_bonus == item['health_bonus']
        assert eq.power_bonus == item['power_bonus']
        assert eq.defense_bonus == item['defense_bonus']
        assert eq.rarity == item['rarity']
        assert eq.image_url == item['image_url']
        assert eq.class_restriction == item.get('class_restriction')

def test_shop_items_for_class(client, db_session, test_user, test_character):
    # Set the test character to a high level to unlock all items
    test_character.level = 99
    db_session.commit()
    db_session.refresh(test_character)
    print(f"[DEBUG TEST] test_character: class={test_character.character_class}, level={test_character.level}, gold={test_character.gold}")
    all_eq = db_session.query(Equipment).all()
    print("[DEBUG TEST] Equipment table before shop call:")
    for eq in all_eq:
        print(f"  - id={eq.id}, name={eq.name}, type={eq.type}, slot={eq.slot}, class_restriction={eq.class_restriction}")
    with client:
        client.post('/auth/login', data={'username': test_user.username, 'password': 'password'}, follow_redirects=True)
        response = client.get('/student/shop')
        assert response.status_code == 200
        html = response.get_data(as_text=True)
        # All equipment for the class should be visible
        for item in db_session.query(Equipment).filter_by(class_restriction=test_character.character_class).all():
            assert item.name in html

def test_purchase_and_equip_hardcoded_item(client, db_session, test_user, test_character):
    # Set the test character to a high level to unlock all items
    test_character.level = 99
    test_character.gold = 9999  # Ensure enough gold
    db_session.commit()
    db_session.refresh(test_character)
    with client:
        client.post('/auth/login', data={'username': test_user.username, 'password': 'password'}, follow_redirects=True)
        # Find a purchasable item for the character's class (case-insensitive)
        class_restr = test_character.character_class.lower()
        item = db_session.query(Equipment).filter_by(class_restriction=class_restr).first()
        assert item is not None
        response = client.post('/student/shop/buy', json={'item_id': item.id, 'item_type': 'equipment'})
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        # Check inventory
        from app.models.equipment import Inventory
        inv = db_session.query(Inventory).filter_by(character_id=test_character.id, item_id=item.id).first()
        assert inv is not None
        assert inv.is_equipped is False 