import pytest
from datetime import datetime
from app.models import db
from app.models.user import User, UserRole
from app.models.classroom import Class
from app.models.character import Character
from app.models.clan import Clan
from app.models.equipment import Equipment, EquipmentType, EquipmentSlot, Inventory
from app.models.ability import Ability, AbilityType, CharacterAbility
from sqlalchemy.exc import IntegrityError

@pytest.fixture
def student_user(db_session):
    """Create a test student user."""
    student = User(
        username='teststudent',
        email='student@test.com',
        role=UserRole.STUDENT,
        password='password123'
    )
    student.save()
    return student

@pytest.fixture
def teacher_user(db_session):
    """Create a test teacher user."""
    teacher = User(
        username='testteacher',
        email='teacher@test.com',
        role=UserRole.TEACHER,
        password='password123'
    )
    teacher.save()
    return teacher

@pytest.fixture
def test_class(db_session, teacher_user):
    """Create a test class."""
    class_ = Class(
        name='Test Class',
        teacher_id=teacher_user.id,
        join_code='TEST123'
    )
    class_.save()
    return class_

@pytest.fixture
def test_character(db_session, student_user):
    """Create a test character."""
    character = Character(
        name='Test Character',
        student_id=student_user.id
    )
    character.save()
    return character

@pytest.fixture
def test_clan(db_session, test_class):
    """Create a test clan."""
    clan = Clan(
        name='Test Clan',
        class_id=test_class.id,
        description='A test clan'
    )
    clan.save()
    return clan

@pytest.fixture
def test_equipment(db_session):
    """Create test equipment."""
    equipment = Equipment(
        name='Test Sword',
        type=EquipmentType.WEAPON,
        slot=EquipmentSlot.MAIN_HAND,
        strength_bonus=5
    )
    equipment.save()
    return equipment

@pytest.fixture
def test_ability(db_session):
    """Create a test ability."""
    ability = Ability(
        name='Test Ability',
        type=AbilityType.ATTACK,
        power=15,
        cooldown=2
    )
    ability.save()
    return ability

def test_character_creation(test_character):
    """Test basic character creation and attributes."""
    assert test_character.id is not None
    assert test_character.level == 1
    assert test_character.experience == 0
    assert test_character.health == 100
    assert test_character.max_health == 100
    assert test_character.strength == 10
    assert test_character.defense == 10
    assert test_character.is_active is True

def test_character_experience_and_leveling(test_character):
    """Test character experience gain and leveling up."""
    initial_health = test_character.max_health
    initial_strength = test_character.strength
    initial_defense = test_character.defense
    
    # Gain enough XP for level 2
    test_character.gain_experience(1000)
    assert test_character.level == 2
    assert test_character.max_health == initial_health + 10
    assert test_character.strength == initial_strength + 2
    assert test_character.defense == initial_defense + 2
    assert test_character.health == test_character.max_health  # Should heal on level up

def test_clan_management(test_clan, test_character):
    """Test clan membership operations."""
    # Add character to clan
    test_clan.add_member(test_character)
    assert test_character in test_clan.members.all()
    assert test_clan == test_character.clan
    
    # Set character as leader
    test_clan.set_leader(test_character)
    assert test_clan.leader == test_character
    
    # Remove character from clan
    test_clan.remove_member(test_character)
    assert test_character not in test_clan.members.all()
    assert test_character.clan is None
    assert test_clan.leader is None

def test_equipment_and_inventory(test_character, test_equipment):
    """Test equipment management and inventory system."""
    # Add equipment to character's inventory
    inventory_item = Inventory(
        character_id=test_character.id,
        equipment_id=test_equipment.id
    )
    inventory_item.save()
    
    assert inventory_item in test_character.inventory_items.all()
    assert not inventory_item.is_equipped
    
    # Equip the item
    inventory_item.equip()
    assert inventory_item.is_equipped
    
    # Create and equip another item in same slot
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
    
    # Original item should be unequipped
    inventory_item.refresh_from_db()
    assert not inventory_item.is_equipped
    assert another_inventory.is_equipped

def test_ability_system(test_character, test_ability):
    """Test ability learning and management."""
    # Learn the ability
    char_ability = CharacterAbility(
        character_id=test_character.id,
        ability_id=test_ability.id
    )
    char_ability.save()
    
    assert char_ability in test_character.learned_abilities.all()
    assert not char_ability.is_equipped
    assert char_ability.level == 1
    
    # Level up the ability
    char_ability.level_up()
    assert char_ability.level == 2
    
    # Equip the ability
    char_ability.equip()
    assert char_ability.is_equipped
    
    # Try to equip more than 4 abilities
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
        
        if i < 3:  # First 3 should succeed
            char_ability.equip()
            assert char_ability.is_equipped
        else:  # Fourth one should fail
            with pytest.raises(ValueError, match="Cannot equip more than 4 abilities"):
                char_ability.equip()

def test_character_combat_mechanics(test_character):
    """Test basic combat-related mechanics."""
    # Test damage taking
    initial_health = test_character.health
    damage = 30
    test_character.take_damage(damage)
    assert test_character.health == initial_health - damage
    
    # Test healing
    heal_amount = 20
    test_character.heal(heal_amount)
    assert test_character.health == initial_health - damage + heal_amount
    
    # Test healing cap at max_health
    test_character.heal(1000)
    assert test_character.health == test_character.max_health

def test_clan_experience_system(test_clan):
    """Test clan experience and leveling system."""
    initial_level = test_clan.level
    
    # Gain clan experience
    test_clan.gain_experience(5000)  # Should level up once
    assert test_clan.level == initial_level + 1
    
    # Gain more experience
    test_clan.gain_experience(5000)  # Should level up again
    assert test_clan.level == initial_level + 2 