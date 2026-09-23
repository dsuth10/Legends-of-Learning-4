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

def _run_equipment_sync(app, *args):
    return app.test_cli_runner().invoke(args=['sync-equipment', *args])


def test_sync_equipment_fresh_catalogue_is_complete_and_idempotent(app, db_session):
    db_session.query(Equipment).delete()
    db_session.commit()

    first = _run_equipment_sync(app)
    assert first.exit_code == 0, first.output
    assert db_session.query(Equipment).count() == len(EQUIPMENT_DATA)
    assert {row.catalogue_key for row in db_session.query(Equipment)} == {
        item['catalogue_key'] for item in EQUIPMENT_DATA
    }
    second = _run_equipment_sync(app)
    assert second.exit_code == 0, second.output
    assert '0 insert(s), 0 update(s)' in second.output
    assert db_session.query(Equipment).count() == len(EQUIPMENT_DATA)


def test_sync_equipment_repairs_legacy_cloaks_and_leaves_custom_items(app, db_session, test_character):
    # Simulate an old database that has the tier-1 cloak under the shared legacy
    # name and path, lacks the tier-2 cloak, and contains a teacher-created item.
    for row in db_session.query(Equipment).all():
        row.catalogue_key = None
    tier1 = db_session.query(Equipment).filter_by(
        image_url='/static/images/equipment/sorcerer/sorcerer_1_armor_cloak2.png'
    ).one()
    stable_id = tier1.id
    tier1.name = 'Sorcerer Cloak II'
    tier1.image_url = '/static/images/equipment/Sorcerer Cloak II.png'
    tier2 = db_session.query(Equipment).filter_by(
        image_url='/static/images/equipment/sorcerer/sorcerer_2_armor_cloak.png'
    ).one()
    db_session.delete(tier2)
    custom = Equipment(
        # The teacher reuses the catalogue art and matching slot/level/class,
        # but a distinct display name keeps this custom row out of sync.
        name='Teacher Winter Robe', type='armor', slot='chest', cost=777,
        level_requirement=11,
        image_url='/static/images/equipment/sorcerer/sorcerer_2_armor_cloak.png',
        class_restriction='sorcerer',
    )
    db_session.add(custom)
    from app.models.equipment import Inventory
    inventory = Inventory(character_id=test_character.id, item_id=tier1.id, is_equipped=True)
    db_session.add(inventory)
    db_session.commit()
    custom_id = custom.id
    inventory_id = inventory.id

    dry_run = _run_equipment_sync(app, '--dry-run')
    assert dry_run.exit_code == 0, dry_run.output
    assert 'Dry run: no changes written.' in dry_run.output
    assert tier1.catalogue_key is None
    assert tier1.image_url.endswith('Sorcerer Cloak II.png')

    result = _run_equipment_sync(app)
    assert result.exit_code == 0, result.output
    db_session.expire_all()
    tier1 = db_session.get(Equipment, stable_id)
    assert tier1.catalogue_key == 'sorcerer_1_armor_cloak2'
    assert tier1.name == 'Sorcerer Cloak I'
    assert tier1.image_url == '/static/images/equipment/sorcerer/sorcerer_1_armor_cloak2.png'
    preserved_inventory = db_session.get(Inventory, inventory_id)
    assert preserved_inventory.item_id == stable_id
    assert preserved_inventory.is_equipped is True
    assert db_session.query(Equipment).filter_by(catalogue_key='sorcerer_2_armor_cloak').count() == 1
    custom = db_session.get(Equipment, custom_id)
    assert custom.name == 'Teacher Winter Robe'
    assert custom.image_url == '/static/images/equipment/sorcerer/sorcerer_2_armor_cloak.png'
    assert custom.catalogue_key is None


def test_sync_equipment_partially_synced_database_only_updates_missing_keys(app, db_session):
    first_data = EQUIPMENT_DATA[0]
    first_row = db_session.query(Equipment).filter_by(image_url=first_data['image_url']).one()
    original_id = first_row.id
    first_row.catalogue_key = first_data['catalogue_key']
    first_row.cost += 1
    first_row.health_bonus += 2
    first_row.power_bonus += 3
    first_row.defense_bonus += 4
    first_row.level_requirement += 1
    first_row.rarity = 5
    preserved_balance = {
        field: getattr(first_row, field)
        for field in (
            'cost', 'health_bonus', 'power_bonus', 'defense_bonus',
            'level_requirement', 'rarity',
        )
    }
    db_session.commit()

    result = _run_equipment_sync(app)
    assert result.exit_code == 0, result.output
    db_session.expire_all()
    repaired = db_session.get(Equipment, original_id)
    assert repaired.catalogue_key == first_data['catalogue_key']
    assert {
        field: getattr(repaired, field) for field in preserved_balance
    } == preserved_balance
    assert db_session.query(Equipment).count() == len(EQUIPMENT_DATA)
    second = _run_equipment_sync(app)
    assert second.exit_code == 0, second.output
    assert '0 insert(s), 0 update(s)' in second.output


def test_seed_db_populates_catalogue_keys_on_migrated_database(app, db_session):
    db_session.query(Equipment).delete()
    db_session.commit()

    result = app.test_cli_runner().invoke(args=['seed-db'])
    assert result.exit_code == 0, result.output
    rows = db_session.query(Equipment).all()
    assert len(rows) == len(EQUIPMENT_DATA)
    assert {row.catalogue_key for row in rows} == {
        item['catalogue_key'] for item in EQUIPMENT_DATA
    }


def test_sync_equipment_fails_when_catalogue_key_migration_is_missing(app, monkeypatch):
    from app import commands

    real_inspect = commands.sa_inspect

    class InspectorWithoutCatalogueKey:
        def get_table_names(self):
            return real_inspect(commands.db.engine).get_table_names()

        def get_columns(self, table_name):
            columns = real_inspect(commands.db.engine).get_columns(table_name)
            if table_name == 'equipment':
                return [column for column in columns if column['name'] != 'catalogue_key']
            return columns

    monkeypatch.setattr(commands, 'sa_inspect', lambda _engine: InspectorWithoutCatalogueKey())
    result = _run_equipment_sync(app)

    assert result.exit_code != 0
    assert 'catalogue-key migration is required' in result.output


def test_sync_equipment_reports_runtime_failures_as_nonzero(app, monkeypatch):
    from app import commands

    def fail_inspection(_engine):
        raise RuntimeError('simulated inspection failure')

    monkeypatch.setattr(commands, 'sa_inspect', fail_inspection)
    result = _run_equipment_sync(app)

    assert result.exit_code != 0
    assert 'Error syncing equipment: simulated inspection failure' in result.output
