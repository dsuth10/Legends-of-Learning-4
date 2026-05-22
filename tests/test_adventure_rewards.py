"""Foundational tests for atomic adventure reward and consequence application."""



import uuid



import pytest



from app.models.adventure import AdventureRewardType, NodeConsequence, NodeReward, NodeType
from app.models.adventure_progress import NodeProgressStatus
from app.models.equipment import Equipment, EquipmentSlot, EquipmentType
from app.services.adventure_graph import recompute_unlocks_for_character
from app.services.adventure_rewards import (
    apply_node_consequence_row,
    distribute_node_rewards,
)
from tests.fixtures.adventure_factories import add_node, create_adventure, seed_node_progress





@pytest.fixture

def teacher_user(db_session):

    from app.models.user import User, UserRole



    unique = uuid.uuid4().hex[:8]

    user = User(

        username=f"rew_teacher_{unique}",

        email=f"rew_teacher_{unique}@test.com",

        role=UserRole.TEACHER,

        password="password123",

    )

    db_session.add(user)

    db_session.commit()

    return user





@pytest.fixture

def student_character(db_session):

    from app.models.character import Character

    from app.models.classroom import Classroom

    from app.models.student import Student

    from app.models.user import User, UserRole



    unique = uuid.uuid4().hex[:8]

    teacher = User(

        username=f"rwteacher_{unique}",

        email=f"rwteacher_{unique}@test.com",

        role=UserRole.TEACHER,

        password="password123",

    )

    db_session.add(teacher)

    db_session.commit()

    classroom = Classroom(name=f"RWClass_{unique}", teacher_id=teacher.id, join_code=f"RW{unique}")

    db_session.add(classroom)

    db_session.commit()

    user = User(

        username=f"rwstudent_{unique}",

        email=f"rwstudent_{unique}@test.com",

        role=UserRole.STUDENT,

        password="password123",

    )

    db_session.add(user)

    db_session.commit()

    student = Student(user_id=user.id, class_id=classroom.id)

    db_session.add(student)

    db_session.commit()

    character = Character(

        name="RewardHero",

        student_id=student.id,

        character_class="Warrior",

        gold=100,

        experience=0,

    )

    db_session.add(character)

    db_session.commit()

    return character





def test_distribute_xp_and_gold_without_commit(db_session, teacher_user, student_character):

    adventure = create_adventure(teacher_user)

    node = add_node(adventure, "reward", NodeType.REWARD)

    db_session.add(

        NodeReward(node_id=node.id, type=AdventureRewardType.EXPERIENCE.value, amount=250)

    )

    db_session.add(

        NodeReward(node_id=node.id, type=AdventureRewardType.GOLD.value, amount=40)

    )

    db_session.commit()



    initial_gold = student_character.gold

    distributed = distribute_node_rewards(

        student_character, node, session=db_session, commit=False

    )

    assert len(distributed) == 2

    assert student_character.experience == 250

    assert student_character.gold == initial_gold + 40



    db_session.rollback()

    db_session.refresh(student_character)

    assert student_character.experience == 0

    assert student_character.gold == initial_gold





def test_conditional_reward_skipped(db_session, teacher_user, student_character):

    adventure = create_adventure(teacher_user)

    node = add_node(adventure, "quiz_reward", NodeType.QUIZ)

    db_session.add(

        NodeReward(

            node_id=node.id,

            type=AdventureRewardType.GOLD.value,

            amount=100,

            is_conditional=True,

            condition_json={"min_score_percent": 90},

        )

    )

    db_session.commit()



    distributed = distribute_node_rewards(

        student_character, node, score=80, session=db_session, commit=False

    )

    assert distributed == []

    assert student_character.gold == 100



    distributed = distribute_node_rewards(

        student_character, node, score=95, session=db_session, commit=False

    )

    assert len(distributed) == 1

    assert student_character.gold == 200





def test_apply_consequences_without_commit(db_session, teacher_user, student_character):

    adventure = create_adventure(teacher_user)

    node = add_node(adventure, "fail", NodeType.QUIZ)

    student_character.experience = 100

    student_character.gold = 50

    student_character.health = 80

    db_session.commit()



    consequence = NodeConsequence(

        node_id=node.id,

        xp_penalty=30,

        gold_penalty=20,

        hp_penalty=10,

        description="Failed the quiz",

    )

    db_session.add(consequence)

    db_session.commit()



    apply_node_consequence_row(student_character, consequence, session=db_session, commit=False)

    assert student_character.experience == 70

    assert student_character.gold == 30

    assert student_character.health == 70



    db_session.rollback()

    db_session.refresh(student_character)

    assert student_character.experience == 100

    assert student_character.gold == 50

    assert student_character.health == 80





def test_equipment_reward_adds_inventory(db_session, teacher_user, student_character):

    adventure = create_adventure(teacher_user)

    node = add_node(adventure, "gear", NodeType.REWARD)

    equipment = Equipment(

        name="Test Sword",

        description="A sword",

        type=EquipmentType.WEAPON.value,

        slot=EquipmentSlot.MAIN_HAND.value,

        level_requirement=1,

        cost=10,

    )

    db_session.add(equipment)

    db_session.flush()

    db_session.add(

        NodeReward(

            node_id=node.id,

            type=AdventureRewardType.EQUIPMENT.value,

            amount=0,

            item_id=equipment.id,

        )

    )

    db_session.commit()



    from app.models.equipment import Inventory



    before = Inventory.query.filter_by(character_id=student_character.id).count()

    distribute_node_rewards(student_character, node, session=db_session, commit=True)

    after = Inventory.query.filter_by(character_id=student_character.id).count()

    assert after == before + 1


def test_ability_reward(db_session, teacher_user, student_character):
    from app.models.ability import Ability, CharacterAbility

    adventure = create_adventure(teacher_user)
    node = add_node(adventure, "ability_node", NodeType.REWARD)
    ability = Ability(
        name="Test Strike",
        description="Hits hard",
        type="attack",
        target_type="self",
        power=5,
        cooldown=0,
        duration=0,
    )
    db_session.add(ability)
    db_session.flush()
    db_session.add(
        NodeReward(
            node_id=node.id,
            type=AdventureRewardType.ABILITY.value,
            amount=0,
            ability_id=ability.id,
        )
    )
    db_session.commit()

    before = CharacterAbility.query.filter_by(character_id=student_character.id).count()
    distribute_node_rewards(student_character, node, session=db_session, commit=True)
    after = CharacterAbility.query.filter_by(character_id=student_character.id).count()
    assert after == before + 1


def test_clan_xp_reward(db_session, teacher_user, student_character):
    from app.models.clan import Clan

    clan = Clan(name="Reward Clan", class_id=student_character.student.class_id)
    db_session.add(clan)
    db_session.flush()
    student_character.clan_id = clan.id
    db_session.commit()

    adventure = create_adventure(teacher_user)
    node = add_node(adventure, "clan_xp", NodeType.REWARD)
    db_session.add(
        NodeReward(
            node_id=node.id,
            type=AdventureRewardType.CLAN_EXPERIENCE.value,
            amount=120,
        )
    )
    db_session.commit()

    old_xp = clan.experience
    distribute_node_rewards(student_character, node, session=db_session, commit=True)
    db_session.refresh(clan)
    assert clan.experience == old_xp + 120


def test_badge_reward(db_session, teacher_user, student_character):
    from app.models.achievement_badge import AchievementBadge, character_badges

    adventure = create_adventure(teacher_user)
    node = add_node(adventure, "badge_node", NodeType.REWARD)
    badge = AchievementBadge(name="Explorer", description="Explored", icon="/static/x.png")
    db_session.add(badge)
    db_session.flush()
    db_session.add(
        NodeReward(
            node_id=node.id,
            type=AdventureRewardType.BADGE.value,
            amount=0,
            badge_id=badge.id,
        )
    )
    db_session.commit()

    distribute_node_rewards(student_character, node, session=db_session, commit=True)
    link = db_session.execute(
        character_badges.select().where(
            character_badges.c.character_id == student_character.id,
            character_badges.c.badge_id == badge.id,
        )
    ).first()
    assert link is not None


def test_special_currency_reward(db_session, teacher_user, student_character):
    adventure = create_adventure(teacher_user)
    node = add_node(adventure, "currency", NodeType.REWARD)
    db_session.add(
        NodeReward(
            node_id=node.id,
            type=AdventureRewardType.SPECIAL_CURRENCY.value,
            amount=75,
        )
    )
    db_session.commit()

    old_gold = student_character.student.gold
    distribute_node_rewards(student_character, node, session=db_session, commit=True)
    db_session.refresh(student_character.student)
    assert student_character.student.gold == old_gold + 75


def test_optional_node_rewards_when_completed(db_session, teacher_user, student_character):
    from tests.fixtures.adventure_factories import build_branching_adventure

    adventure, nodes = build_branching_adventure(teacher_user)
    db_session.add(
        NodeReward(
            node_id=nodes["side_bonus"].id,
            type=AdventureRewardType.GOLD.value,
            amount=25,
        )
    )
    db_session.commit()

    initial_gold = student_character.gold
    seed_node_progress(
        student_character,
        nodes["left_path"],
        NodeProgressStatus.COMPLETED,
    )
    recompute_unlocks_for_character(student_character, adventure)
    db_session.commit()

    distributed = distribute_node_rewards(
        student_character, nodes["side_bonus"], session=db_session, commit=True
    )
    assert len(distributed) == 1
    assert student_character.gold == initial_gold + 25


def test_adventure_complete_without_optional_rewards(
    db_session, teacher_user, student_character
):
    from app.services.adventure_graph import (
        evaluate_adventure_complete,
        mark_unvisited_optional_nodes_skipped,
    )
    from tests.fixtures.adventure_factories import build_branching_adventure

    adventure, nodes = build_branching_adventure(teacher_user)
    db_session.add(
        NodeReward(
            node_id=nodes["side_bonus"].id,
            type=AdventureRewardType.GOLD.value,
            amount=50,
        )
    )
    db_session.commit()

    initial_gold = student_character.gold
    seed_node_progress(
        student_character, nodes["start"], NodeProgressStatus.COMPLETED
    )
    seed_node_progress(
        student_character, nodes["choice"], NodeProgressStatus.COMPLETED, choice_made="right"
    )
    seed_node_progress(
        student_character, nodes["right_path"], NodeProgressStatus.COMPLETED
    )
    seed_node_progress(
        student_character, nodes["merge"], NodeProgressStatus.COMPLETED
    )
    seed_node_progress(
        student_character, nodes["end"], NodeProgressStatus.COMPLETED
    )
    assert evaluate_adventure_complete(adventure, student_character)
    mark_unvisited_optional_nodes_skipped(
        student_character, adventure, session=db_session
    )
    db_session.commit()
    assert student_character.gold == initial_gold


