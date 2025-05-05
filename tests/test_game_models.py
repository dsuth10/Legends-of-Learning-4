import pytest
from datetime import datetime
from sqlalchemy.exc import IntegrityError
import uuid

@pytest.fixture
def student_user(db_session):
    from app.models.user import User, UserRole
    unique = uuid.uuid4().hex[:8]
    student = User(
        username=f'teststudent_{unique}',
        email=f'student_{unique}@test.com',
        role=UserRole.STUDENT,
        password='password123'
    )
    student.save()
    return student

@pytest.fixture
def teacher_user(db_session):
    from app.models.user import User, UserRole
    unique = uuid.uuid4().hex[:8]
    teacher = User(
        username=f'testteacher_{unique}',
        email=f'teacher_{unique}@test.com',
        role=UserRole.TEACHER,
        password='password123'
    )
    teacher.save()
    return teacher

@pytest.fixture
def test_class(db_session, teacher_user):
    from app.models.classroom import Classroom
    unique = uuid.uuid4().hex[:8]
    class_ = Classroom(
        name=f'Test Class {unique}',
        teacher_id=teacher_user.id,
        join_code=f'TEST{unique[:5]}'
    )
    class_.save()
    return class_

@pytest.fixture
def test_character(db_session, student_user):
    from app.models.character import Character
    character = Character(
        name='Test Character',
        student_id=student_user.id
    )
    character.health = 100
    character.max_health = 100
    character.strength = 10
    character.defense = 10
    character.save()
    return character

@pytest.fixture
def test_clan(db_session, test_class):
    from app.models.clan import Clan
    clan = Clan(
        name='Test Clan',
        class_id=test_class.id,
        description='A test clan'
    )
    clan.save()
    return clan

@pytest.fixture
def test_equipment(db_session):
    from app.models.equipment import Equipment, EquipmentType, EquipmentSlot
    equipment = Equipment(
        name='Test Sword',
        type=EquipmentType.WEAPON,
        slot=EquipmentSlot.MAIN_HAND,
        strength_bonus=5,
        cost=100
    )
    equipment.save()
    return equipment

@pytest.fixture
def test_ability(db_session):
    from app.models.ability import Ability, AbilityType
    ability = Ability(
        name='Test Ability',
        type=AbilityType.ATTACK,
        power=15,
        cooldown=2,
        cost=50
    )
    ability.save()
    return ability

def test_character_creation(test_character):
    assert test_character.id is not None
    assert test_character.level == 1
    assert test_character.experience == 0
    assert test_character.health == 100
    assert test_character.max_health == 100
    assert test_character.strength == 10
    assert test_character.defense == 10
    assert test_character.is_active is True

def test_character_experience_and_leveling(test_character):
    initial_health = test_character.max_health
    initial_strength = test_character.strength
    initial_defense = test_character.defense
    test_character.gain_experience(1000)
    assert test_character.level == 2
    assert test_character.max_health == initial_health + 10
    assert test_character.strength == initial_strength + 2
    assert test_character.defense == initial_defense + 2
    assert test_character.health == test_character.max_health

def test_clan_management(test_clan, test_character):
    test_clan.add_member(test_character)
    assert test_character in test_clan.members.all()
    assert test_clan == test_character.clan
    test_clan.set_leader(test_character)
    assert test_clan.leader == test_character
    test_clan.remove_member(test_character)
    assert test_character not in test_clan.members.all()
    assert test_character.clan is None
    assert test_clan.leader is None

def test_equipment_and_inventory(test_character, test_equipment):
    from app.models.equipment import Inventory, Equipment, EquipmentType, EquipmentSlot
    from app.models import db
    # Debug: print equipment table columns
    import sqlite3
    engine = db.get_engine()
    conn = engine.raw_connection()
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(equipment);")
    columns = cursor.fetchall()
    print("[DEBUG] equipment table columns before test:", columns)
    conn.close()
    inventory_item = Inventory(
        character_id=test_character.id,
        equipment_id=test_equipment.id
    )
    inventory_item.save()
    assert inventory_item in test_character.inventory_items.all()
    assert not inventory_item.is_equipped
    inventory_item.equip()
    assert inventory_item.is_equipped
    another_weapon = Equipment(
        name='Another Sword',
        type=EquipmentType.WEAPON,
        slot=EquipmentSlot.MAIN_HAND
    )
    another_weapon.save()
    another_inventory = Inventory(
        character_id=test_character.id,
        equipment_id=another_weapon.id
    )
    another_inventory.save()
    another_inventory.equip()
    db.session.refresh(inventory_item)
    assert not inventory_item.is_equipped
    assert another_inventory.is_equipped

def test_ability_system(test_character, test_ability):
    from app.models.ability import Ability, AbilityType, CharacterAbility
    char_ability = CharacterAbility(
        character_id=test_character.id,
        ability_id=test_ability.id
    )
    char_ability.save()
    assert char_ability in test_character.learned_abilities.all()
    assert not char_ability.is_equipped
    assert char_ability.level == 1
    char_ability.level_up()
    assert char_ability.level == 2
    char_ability.equip()
    assert char_ability.is_equipped
    for i in range(4):
        ability = Ability(
            name=f'Extra Ability {i}',
            type=AbilityType.ATTACK
        )
        ability.save()
        char_ability = CharacterAbility(
            character_id=test_character.id,
            ability_id=ability.id
        )
        char_ability.save()
        if i < 3:
            char_ability.equip()
            assert char_ability.is_equipped
        else:
            with pytest.raises(ValueError, match="Cannot equip more than 4 abilities"):
                char_ability.equip()

def test_character_combat_mechanics(test_character):
    initial_health = test_character.health
    damage = 30
    test_character.take_damage(damage)
    assert test_character.health == initial_health - damage
    heal_amount = 20
    test_character.heal(heal_amount)
    assert test_character.health == initial_health - damage + heal_amount
    test_character.heal(1000)
    assert test_character.health == test_character.max_health

def test_clan_experience_system(test_clan):
    initial_level = test_clan.level
    test_clan.gain_experience(5000)
    assert test_clan.level == initial_level + 1
    test_clan.gain_experience(5000)
    assert test_clan.level == initial_level + 2 