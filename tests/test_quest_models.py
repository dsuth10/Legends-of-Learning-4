import pytest
from datetime import datetime, timedelta
from sqlalchemy.exc import IntegrityError
import uuid

# Model and db imports moved inside fixtures and test functions

@pytest.fixture
def user(db_session):
    from app.models.user import User, UserRole
    unique = uuid.uuid4().hex[:8]
    user = User(
        username=f"testuser_{unique}",
        email=f"test_{unique}@example.com",
        password="testpass123",
        role=UserRole.STUDENT
    )
    db_session.add(user)
    db_session.commit()
    return user

@pytest.fixture
def character(db_session, user):
    from app.models.character import Character
    character = Character(
        name="TestCharacter",
        student_id=user.id,
        character_class="Warrior",
        level=1,
        gold=100
    )
    character.health = 100
    character.max_health = 100
    character.strength = 10
    character.defense = 10
    db_session.add(character)
    db_session.commit()
    return character

@pytest.fixture
def clan(db_session, classroom):
    from app.models.clan import Clan
    clan = Clan(
        name="TestClan",
        description="A test clan",
        level=1,
        experience=0,
        class_id=classroom.id
    )
    db_session.add(clan)
    db_session.commit()
    return clan

@pytest.fixture
def teacher(db_session):
    from app.models.user import User, UserRole
    unique = uuid.uuid4().hex[:8]
    teacher = User(
        username=f"teacher_{unique}",
        email=f"teacher_{unique}@example.com",
        role=UserRole.TEACHER,
        password="testpass123"
    )
    db_session.add(teacher)
    db_session.commit()
    return teacher

@pytest.fixture
def classroom(db_session, teacher):
    from app.models.classroom import Classroom
    unique = uuid.uuid4().hex[:8]
    classroom = Classroom(
        name=f"TestClass_{unique}",
        teacher_id=teacher.id,
        join_code=f"JC{unique}"
    )
    db_session.add(classroom)
    db_session.commit()
    return classroom

@pytest.fixture
def equipment(db_session):
    from app.models.equipment import Equipment, EquipmentType, EquipmentSlot
    equipment = Equipment(
        name="TestSword",
        description="A test sword",
        type=EquipmentType.WEAPON,
        slot=EquipmentSlot.MAIN_HAND,
        cost=100
    )
    equipment.stats = {"attack": 10}
    db_session.add(equipment)
    db_session.commit()
    return equipment

@pytest.fixture
def ability(db_session):
    from app.models.ability import Ability, AbilityType
    ability = Ability(
        name="TestAbility",
        description="A test ability",
        type=AbilityType.ATTACK.value,
        cost=50
    )
    ability.effects = {"damage": 20}
    db_session.add(ability)
    db_session.commit()
    return ability

@pytest.fixture
def quest(db_session):
    from app.models.quest import Quest, QuestType
    quest = Quest(
        title="Test Quest",
        description="A test quest",
        type=QuestType.STORY,
        level_requirement=1,
        requirements={"item": "test_item"},
        completion_criteria={"kill_count": 5}
    )
    db_session.add(quest)
    db_session.commit()
    return quest

@pytest.fixture
def quest_with_rewards(db_session, quest, equipment, ability):
    from app.models.quest import Reward, RewardType
    rewards = [
        Reward(quest_id=quest.id, type=RewardType.EXPERIENCE, amount=100),
        Reward(quest_id=quest.id, type=RewardType.GOLD, amount=50),
        Reward(quest_id=quest.id, type=RewardType.EQUIPMENT, equipment_id=equipment.id),
        Reward(quest_id=quest.id, type=RewardType.ABILITY, ability_id=ability.id),
        Reward(quest_id=quest.id, type=RewardType.CLAN_EXPERIENCE, amount=75)
    ]
    db_session.add_all(rewards)
    db_session.commit()
    return quest

@pytest.fixture
def quest_with_consequences(db_session, quest):
    from app.models.quest import Consequence
    consequence = Consequence(
        quest_id=quest.id,
        description="Test consequence",
        experience_penalty=50,
        gold_penalty=25,
        health_penalty=10
    )
    db_session.add(consequence)
    db_session.commit()
    return quest

class TestQuest:
    def test_create_quest(self, db_session):
        from app.models.quest import Quest, QuestType
        quest = Quest(
            title="Test Quest",
            description="A test quest",
            type=QuestType.STORY,
            level_requirement=1
        )
        db_session.add(quest)
        db_session.commit()
        
        assert quest.id is not None
        assert quest.title == "Test Quest"
        assert quest.type == QuestType.STORY
    
    def test_quest_availability(self, quest, character):
        # Test level requirement
        assert quest.is_available(character) == True
        character.level = 0
        assert quest.is_available(character) == False
        
        # Test date constraints
        character.level = 1
        quest.start_date = datetime.utcnow() + timedelta(days=1)
        assert quest.is_available(character) == False
        
        quest.start_date = datetime.utcnow() - timedelta(days=1)
        quest.end_date = datetime.utcnow() + timedelta(days=1)
        assert quest.is_available(character) == True
        
        quest.end_date = datetime.utcnow() - timedelta(hours=1)
        assert quest.is_available(character) == False
    
    def test_quest_prerequisites(self, db_session, quest, character):
        from app.models.quest import Quest, QuestType, QuestLog, QuestStatus
        # Create a prerequisite quest
        prereq_quest = Quest(
            title="Prerequisite Quest",
            description="Must complete this first",
            type=QuestType.STORY
        )
        db_session.add(prereq_quest)
        db_session.commit()
        
        quest.parent_quest_id = prereq_quest.id
        assert quest.is_available(character) == False
        
        # Complete prerequisite quest
        prereq_log = QuestLog(
            character_id=character.id,
            quest_id=prereq_quest.id,
            status=QuestStatus.COMPLETED
        )
        db_session.add(prereq_log)
        db_session.commit()
        
        assert quest.is_available(character) == True

class TestQuestLog:
    def test_quest_log_creation(self, db_session, quest, character):
        from app.models.quest import QuestLog, QuestStatus
        quest_log = QuestLog(
            character_id=character.id,
            quest_id=quest.id
        )
        db_session.add(quest_log)
        db_session.commit()
        
        assert quest_log.id is not None
        assert quest_log.status == QuestStatus.NOT_STARTED
        assert quest_log.progress_data == {}
    
    def test_quest_log_unique_constraint(self, db_session, quest, character):
        from app.models.quest import QuestLog
        quest_log1 = QuestLog(
            character_id=character.id,
            quest_id=quest.id
        )
        db_session.add(quest_log1)
        db_session.commit()
        
        # Try to create duplicate log
        with pytest.raises(IntegrityError):
            quest_log2 = QuestLog(
                character_id=character.id,
                quest_id=quest.id
            )
            db_session.add(quest_log2)
            db_session.commit()
        db_session.rollback()
    
    def test_quest_progression(self, db_session, quest, character):
        from app.models.quest import QuestLog, QuestStatus
        quest_log = QuestLog(
            character_id=character.id,
            quest_id=quest.id
        )
        db_session.add(quest_log)
        db_session.commit()
        
        # Start quest
        quest_log.start_quest()
        assert quest_log.status == QuestStatus.IN_PROGRESS
        assert quest_log.started_at is not None
        
        # Update progress
        quest_log.update_progress({"kill_count": 3})
        quest_log.progress_data = {"kill_count": 3}
        assert quest_log.progress_data == {"kill_count": 3}
        
        # Complete quest
        quest_log.complete_quest()
        assert quest_log.status == QuestStatus.COMPLETED
        assert quest_log.completed_at is not None
    
    def test_quest_failure(self, db_session, quest_with_consequences, character):
        from app.models.quest import QuestLog, QuestStatus
        quest_log = QuestLog(
            character_id=character.id,
            quest_id=quest_with_consequences.id,
            status=QuestStatus.IN_PROGRESS
        )
        db_session.add(quest_log)
        db_session.commit()
        
        character.experience = 100  # Set before initial_exp
        initial_exp = character.experience
        initial_gold = character.gold
        initial_health = character.health
        
        quest_log.fail_quest()
        
        assert quest_log.status == QuestStatus.FAILED
        assert quest_log.completed_at is not None
        assert character.experience < initial_exp
        assert character.gold < initial_gold
        assert character.health < initial_health

class TestReward:
    def test_experience_reward(self, db_session, quest, character):
        from app.models.quest import Reward, RewardType
        reward = Reward(
            quest_id=quest.id,
            type=RewardType.EXPERIENCE,
            amount=100
        )
        db_session.add(reward)
        db_session.commit()
        initial_exp = character.experience
        reward.distribute(character, session=db_session)
        db_session.refresh(character)
        assert character.experience == initial_exp + 100
    
    def test_gold_reward(self, db_session, quest, character):
        from app.models.quest import Reward, RewardType
        reward = Reward(
            quest_id=quest.id,
            type=RewardType.GOLD,
            amount=50
        )
        db_session.add(reward)
        db_session.commit()
        initial_gold = character.gold
        reward.distribute(character, session=db_session)
        db_session.refresh(character)
        assert character.gold == initial_gold + 50
    
    def test_equipment_reward(self, db_session, quest, character, equipment):
        from app.models.quest import Reward, RewardType
        reward = Reward(
            quest_id=quest.id,
            type=RewardType.EQUIPMENT,
            equipment_id=equipment.id
        )
        db_session.add(reward)
        db_session.commit()
        # print(f"reward.equipment: {reward.equipment}")
        initial_inventory_count = character.inventory_items.count()
        reward.distribute(character, session=db_session)
        db_session.refresh(character)
        from app.models.equipment import Inventory
        inventory_count = db_session.query(Inventory).filter_by(character_id=character.id).count()
        assert inventory_count == initial_inventory_count + 1
    
    def test_ability_reward(self, db_session, quest, character, ability):
        from app.models.quest import Reward, RewardType
        reward = Reward(
            quest_id=quest.id,
            type=RewardType.ABILITY,
            ability_id=ability.id
        )
        db_session.add(reward)
        db_session.commit()
        initial_ability_count = character.abilities.count()
        reward.distribute(character, session=db_session)
        db_session.refresh(character)
        assert character.abilities.count() == initial_ability_count + 1
    
    def test_clan_experience_reward(self, db_session, quest, character, clan):
        from app.models.quest import Reward, RewardType
        character.clan = clan
        db_session.commit()
        reward = Reward(
            quest_id=quest.id,
            type=RewardType.CLAN_EXPERIENCE,
            amount=75
        )
        db_session.add(reward)
        db_session.commit()
        initial_clan_exp = clan.experience
        reward.distribute(character, session=db_session)
        db_session.refresh(character)
        db_session.refresh(clan)
        assert clan.experience == initial_clan_exp + 75

class TestConsequence:
    def test_apply_consequences(self, db_session, quest, character):
        from app.models.quest import Consequence
        consequence = Consequence(
            quest_id=quest.id,
            description="Test consequence",
            experience_penalty=50,
            gold_penalty=25,
            health_penalty=10
        )
        db_session.add(consequence)
        db_session.commit()
        
        initial_exp = character.experience = 100
        initial_gold = character.gold = 100
        initial_health = character.health = 100
        db_session.commit()
        
        consequence.apply(character)
        
        assert character.experience == initial_exp - 50
        assert character.gold == initial_gold - 25
        assert character.health == initial_health - 10
    
    def test_minimum_values(self, db_session, quest, character):
        from app.models.quest import Consequence
        consequence = Consequence(
            quest_id=quest.id,
            description="Test consequence",
            experience_penalty=200,  # More than current experience
            gold_penalty=200,  # More than current gold
            health_penalty=200  # More than current health
        )
        db_session.add(consequence)
        db_session.commit()
        
        character.experience = 100
        character.gold = 100
        character.health = 100
        db_session.commit()
        
        consequence.apply(character)
        
        assert character.experience == 0  # Can't go below 0
        assert character.gold == 0  # Can't go below 0
        assert character.health == 0  # Can't go below 0 