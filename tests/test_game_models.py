import pytest
from datetime import datetime, timedelta
from sqlalchemy.exc import IntegrityError
import uuid
import json
from app.models.character import Character, StatusEffect
from app.models.ability import Ability, CharacterAbility
from app import db

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
def student_user(client, db_session):
    from app.models.user import User, UserRole
    from app.models.classroom import Classroom
    from app.models.student import Student
    # Create a classroom for the student
    classroom = Classroom(name='TestClass', teacher_id=1, join_code='TEST1234')
    db.session.add(classroom)
    db.session.commit()
    # Create the user
    u = User(username='student1', email='student1@example.com', role=UserRole.STUDENT)
    u.set_password('testpass')
    db.session.add(u)
    db.session.commit()
    # Create the student linked to the user and classroom
    s = Student(user_id=u.id, class_id=classroom.id, level=1, gold=0, xp=0, health=100, power=10)
    db.session.add(s)
    db.session.commit()
    return u

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
def test_character(db_session, test_clan):
    from app.models.character import Character
    from app.models.student import Student
    # Create a student for the character
    student = Student(user_id=1, class_id=test_clan.class_id, level=1, gold=0, xp=0, health=100, power=10)
    db_session.add(student)
    db_session.commit()
    character = Character(name='Test Character', student_id=student.id, character_class='Warrior')
    db_session.add(character)
    db_session.commit()
    return character

@pytest.fixture
def test_clan(db_session, test_classroom):
    from app.models.clan import Clan
    unique_id = uuid.uuid4().hex
    clan = Clan(name=f'Test Clan {unique_id}', class_id=test_classroom.id)
    db_session.add(clan)
    db_session.commit()
    return clan

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

@pytest.fixture
def test_user(db_session):
    from app.models.user import User, UserRole
    unique_id = uuid.uuid4().hex
    user = User(username=f'testuser_{unique_id}', email=f'test_{unique_id}@example.com', role=UserRole.TEACHER)
    user.set_password('password')
    db_session.add(user)
    db_session.commit()
    return user

@pytest.fixture
def test_classroom(db_session, test_user):
    from app.models.classroom import Classroom
    unique_id = uuid.uuid4().hex
    classroom = Classroom(name=f'Test Class {unique_id}', teacher_id=test_user.id, join_code=f'TEST1234_{unique_id}')
    db_session.add(classroom)
    db_session.commit()
    return classroom

@pytest.fixture
def test_weapon(db_session):
    from app.models.equipment import Equipment
    weapon = db_session.query(Equipment).filter_by(type='weapon').first()
    if weapon is None:
        weapon = Equipment(name='Test Sword', type='weapon', slot='main_hand', cost=100)
        db_session.add(weapon)
        db_session.commit()
    return weapon

@pytest.fixture
def student_character(db_session, student_user):
    c = Character(name='StudentChar', student_id=1, health=80, max_health=100, strength=10, defense=10)
    db.session.add(c)
    db.session.commit()
    return c

@pytest.fixture
def student_ability(db_session):
    a = Ability(name='Heal', type='heal', power=20, cooldown=5, duration=1)
    db.session.add(a)
    db.session.commit()
    return a

@pytest.fixture
def student_char_ability(db_session, student_character, student_ability):
    ca = CharacterAbility(character_id=student_character.id, ability_id=student_ability.id, is_equipped=True)
    db.session.add(ca)
    db.session.commit()
    return ca

@pytest.fixture
def clanmate(db_session):
    c = Character(name='Clanmate', student_id=2, health=60, max_health=100, strength=8, defense=8)
    db.session.add(c)
    db.session.commit()
    return c

@pytest.fixture
def login_student(client, student_user):
    client.post('/auth/login', data={'username': 'student1', 'password': 'testpass'}, follow_redirects=True)
    return True

@pytest.fixture
def api_buff_ability(db_session):
    a = Ability(name='APIBuff', type='buff', power=5, cooldown=2, duration=2)
    db.session.add(a)
    db.session.commit()
    return a

@pytest.fixture
def api_debuff_ability(db_session):
    a = Ability(name='APIDebuff', type='debuff', power=3, cooldown=2, duration=2)
    db.session.add(a)
    db.session.commit()
    return a

@pytest.fixture
def api_protect_ability(db_session):
    a = Ability(name='APIProtect', type='defense', power=4, cooldown=2, duration=2)
    db.session.add(a)
    db.session.commit()
    return a

@pytest.fixture
def api_buff_char_ability(db_session, student_character, api_buff_ability):
    ca = CharacterAbility(character_id=student_character.id, ability_id=api_buff_ability.id, is_equipped=True)
    db.session.add(ca)
    db.session.commit()
    return ca

@pytest.fixture
def api_debuff_char_ability(db_session, student_character, api_debuff_ability):
    ca = CharacterAbility(character_id=student_character.id, ability_id=api_debuff_ability.id, is_equipped=True)
    db.session.add(ca)
    db.session.commit()
    return ca

@pytest.fixture
def api_protect_char_ability(db_session, student_character, api_protect_ability):
    ca = CharacterAbility(character_id=student_character.id, ability_id=api_protect_ability.id, is_equipped=True)
    db.session.add(ca)
    db.session.commit()
    return ca

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
    # Character should not be in a clan initially
    assert test_character.clan_id is None
    # Add character to clan
    test_clan.add_member(test_character)
    assert test_character.clan_id == test_clan.id
    # Remove character from clan
    test_clan.remove_member(test_character)
    assert test_character.clan_id is None
    # Debug print if assertion fails
    if test_character.clan_id is not None:
        print('[DEBUG] Character clan_id after removal:', test_character.clan_id)

def test_equipment_and_inventory(test_character, test_weapon):
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
        item_id=test_weapon.id
    )
    inventory_item.save()
    assert inventory_item in test_character.inventory_items.all()
    assert not inventory_item.is_equipped
    inventory_item.equip()
    assert inventory_item.is_equipped
    another_weapon = Equipment(
        name='Another Sword',
        type=EquipmentType.WEAPON.value,
        slot=EquipmentSlot.MAIN_HAND.value
    )
    db.session.add(another_weapon)
    db.session.commit()
    another_inventory = Inventory(
        character_id=test_character.id,
        item_id=another_weapon.id
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

def test_game_model_logic(db_session, test_clan, test_character):
    from app.models.clan_progress import ClanProgressHistory
    # ... rest of the test ... 

def test_api_use_ability_on_self(client, db_session, login_student, student_character, student_ability, student_char_ability):
    # Use ability on self
    resp = client.post('/student/abilities/use', json={
        'ability_id': student_ability.id,
        'target_id': student_character.id,
        'context': 'general'
    })
    data = resp.get_json()
    assert resp.status_code == 200
    assert data['success']
    assert 'Healed' in data['message']

def test_api_use_ability_on_clanmate(client, db_session, login_student, student_character, student_ability, student_char_ability, clanmate):
    # Use ability on clanmate
    resp = client.post('/student/abilities/use', json={
        'ability_id': student_ability.id,
        'target_id': clanmate.id,
        'context': 'general'
    })
    data = resp.get_json()
    assert resp.status_code == 200
    assert data['success']
    assert 'Healed' in data['message']

def test_api_ability_on_cooldown(client, db_session, login_student, student_character, student_ability, student_char_ability):
    # Use ability once
    resp1 = client.post('/student/abilities/use', json={
        'ability_id': student_ability.id,
        'target_id': student_character.id,
        'context': 'general'
    })
    assert resp1.get_json()['success']
    # Use again immediately (should be on cooldown)
    resp2 = client.post('/student/abilities/use', json={
        'ability_id': student_ability.id,
        'target_id': student_character.id,
        'context': 'general'
    })
    data2 = resp2.get_json()
    assert not data2['success'] or 'cooldown' in data2['message'].lower()

def test_api_ability_not_equipped(client, db_session, login_student, student_character, student_ability):
    # Not equipped
    resp = client.post('/student/abilities/use', json={
        'ability_id': student_ability.id,
        'target_id': student_character.id,
        'context': 'general'
    })
    data = resp.get_json()
    assert not data['success']
    assert 'equipped' in data['message']

def test_api_ability_invalid_target(client, db_session, login_student, student_character, student_ability, student_char_ability):
    # Use ability on invalid target
    resp = client.post('/student/abilities/use', json={
        'ability_id': student_ability.id,
        'target_id': 999999,
        'context': 'general'
    })
    data = resp.get_json()
    assert not data['success']
    assert 'Target not found' in data['message']

def test_api_buff_ability(client, db_session, login_student, student_character, api_buff_ability, api_buff_char_ability):
    # Use buff ability on self
    resp = client.post('/student/abilities/use', json={
        'ability_id': api_buff_ability.id,
        'target_id': student_character.id,
        'context': 'general'
    })
    data = resp.get_json()
    assert resp.status_code == 200
    assert data['success']
    assert 'Buffed' in data['message']
    # Stat should be increased
    assert student_character.total_strength == student_character.strength + api_buff_ability.power
    # StatusEffect should exist
    effects = student_character.status_effects.all()
    assert any(e.effect_type == 'buff' for e in effects)

def test_api_debuff_ability(client, db_session, login_student, student_character, api_debuff_ability, api_debuff_char_ability, clanmate):
    # Use debuff ability on clanmate
    resp = client.post('/student/abilities/use', json={
        'ability_id': api_debuff_ability.id,
        'target_id': clanmate.id,
        'context': 'general'
    })
    data = resp.get_json()
    assert resp.status_code == 200
    assert data['success']
    assert 'Debuffed' in data['message']
    # Stat should be decreased
    assert clanmate.total_strength == clanmate.strength - api_debuff_ability.power
    # StatusEffect should exist
    effects = clanmate.status_effects.all()
    assert any(e.effect_type == 'debuff' for e in effects)

def test_api_protect_ability(client, db_session, login_student, student_character, api_protect_ability, api_protect_char_ability):
    # Use protect ability on self
    resp = client.post('/student/abilities/use', json={
        'ability_id': api_protect_ability.id,
        'target_id': student_character.id,
        'context': 'general'
    })
    data = resp.get_json()
    assert resp.status_code == 200
    assert data['success']
    assert 'Protected' in data['message']
    # Stat should be increased
    assert student_character.total_defense == student_character.defense + api_protect_ability.power
    # StatusEffect should exist
    effects = student_character.status_effects.all()
    assert any(e.effect_type == 'protect' for e in effects)

def test_api_buff_stack_and_expire(client, db_session, login_student, student_character, api_buff_ability, api_buff_char_ability):
    # Use buff ability twice (stack)
    resp1 = client.post('/student/abilities/use', json={
        'ability_id': api_buff_ability.id,
        'target_id': student_character.id,
        'context': 'general'
    })
    assert resp1.get_json()['success']
    # Simulate cooldown expiry
    ca = CharacterAbility.query.filter_by(character_id=student_character.id, ability_id=api_buff_ability.id).first()
    ca.last_used_at = datetime.utcnow() - timedelta(seconds=api_buff_ability.cooldown + 1)
    db.session.commit()
    resp2 = client.post('/student/abilities/use', json={
        'ability_id': api_buff_ability.id,
        'target_id': student_character.id,
        'context': 'general'
    })
    assert resp2.get_json()['success']
    # Stat should reflect both buffs
    total_buff = sum(e.amount for e in student_character.status_effects.filter_by(effect_type='buff'))
    assert student_character.total_strength == student_character.strength + total_buff
    # Expire all buffs
    for effect in student_character.status_effects:
        effect.expires_at = datetime.utcnow() - timedelta(seconds=1)
    db.session.commit()
    assert student_character.total_strength == student_character.strength

def test_api_invalid_buff_target(client, db_session, login_student, api_buff_ability, api_buff_char_ability):
    # Use buff ability on invalid target
    resp = client.post('/student/abilities/use', json={
        'ability_id': api_buff_ability.id,
        'target_id': 999999,
        'context': 'general'
    })
    data = resp.get_json()
    assert not data['success']
    assert 'Target not found' in data['message'] 