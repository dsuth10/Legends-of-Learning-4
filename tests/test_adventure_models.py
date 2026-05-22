"""Foundational tests for Adventures ORM models and constraints."""



import uuid



import pytest

from sqlalchemy.exc import IntegrityError



from app.models.adventure import (

    Adventure,

    AdventureEdge,

    AdventureNode,

    AdventureRewardType,

    AdventureStatus,

    NodeReward,

    NodeType,

)

from app.models.adventure_progress import (

    AdventureAssignment,

    AdventureProgressStatus,

    CharacterAdventureProgress,

    CharacterNodeProgress,

    NodeProgressStatus,

)

from tests.fixtures.adventure_factories import (

    add_edge,

    add_node,

    assign_to_classroom,

    build_linear_adventure,

    create_adventure,

)





@pytest.fixture

def teacher_user(db_session):

    from app.models.user import User, UserRole



    unique = uuid.uuid4().hex[:8]

    user = User(

        username=f"adv_teacher_{unique}",

        email=f"adv_teacher_{unique}@test.com",

        role=UserRole.TEACHER,

        password="password123",

    )

    db_session.add(user)

    db_session.commit()

    return user





@pytest.fixture

def classroom(db_session, teacher_user):

    from app.models.classroom import Classroom



    unique = uuid.uuid4().hex[:8]

    classroom = Classroom(

        name=f"AdvClass_{unique}",

        teacher_id=teacher_user.id,

        join_code=f"AC{unique}",

    )

    db_session.add(classroom)

    db_session.commit()

    return classroom





@pytest.fixture

def student_character(db_session, classroom):

    from app.models.character import Character

    from app.models.student import Student

    from app.models.user import User, UserRole



    unique = uuid.uuid4().hex[:8]

    user = User(

        username=f"adv_student_{unique}",

        email=f"adv_student_{unique}@test.com",

        role=UserRole.STUDENT,

        password="password123",

    )

    db_session.add(user)

    db_session.commit()

    student = Student(user_id=user.id, class_id=classroom.id)

    db_session.add(student)

    db_session.commit()

    character = Character(name="AdvHero", student_id=student.id, character_class="Warrior")

    db_session.add(character)

    db_session.commit()

    return character





def test_adventure_node_slug_unique_per_adventure(db_session, teacher_user):

    adventure = create_adventure(teacher_user)

    add_node(adventure, "alpha", NodeType.START, is_start=True)

    with pytest.raises(IntegrityError):

        add_node(adventure, "alpha", NodeType.END)

    db_session.rollback()





def test_adventure_edge_no_self_loop(db_session, teacher_user):

    adventure = create_adventure(teacher_user)

    node = add_node(adventure, "solo", NodeType.STORY)

    db_session.commit()

    edge = AdventureEdge(

        adventure_id=adventure.id,

        from_node_id=node.id,

        to_node_id=node.id,

        condition_data={},

    )

    db_session.add(edge)

    with pytest.raises(IntegrityError):

        db_session.flush()

    db_session.rollback()





def test_adventure_edge_unique_pair(db_session, teacher_user):

    adventure = create_adventure(teacher_user)

    a = add_node(adventure, "a", NodeType.START, is_start=True)

    b = add_node(adventure, "b", NodeType.END, is_end=True)

    add_edge(adventure, a, b)

    with pytest.raises(IntegrityError):

        add_edge(adventure, a, b)

    db_session.rollback()





def test_assignment_requires_exactly_one_target(db_session, teacher_user, classroom):

    adventure = create_adventure(teacher_user)

    db_session.commit()

    bad = AdventureAssignment(

        adventure_id=adventure.id,

        adventure_version=1,

        classroom_id=classroom.id,

        character_id=1,

        is_active=True,

    )

    db_session.add(bad)

    with pytest.raises(IntegrityError):

        db_session.flush()

    db_session.rollback()





def test_character_adventure_progress_unique(db_session, teacher_user, student_character):

    adventure = create_adventure(teacher_user)

    db_session.commit()

    db_session.add(

        CharacterAdventureProgress(

            character_id=student_character.id,

            adventure_id=adventure.id,

            status=AdventureProgressStatus.NOT_STARTED.value,

        )

    )

    db_session.commit()

    db_session.add(

        CharacterAdventureProgress(

            character_id=student_character.id,

            adventure_id=adventure.id,

            status=AdventureProgressStatus.IN_PROGRESS.value,

        )

    )

    with pytest.raises(IntegrityError):

        db_session.flush()

    db_session.rollback()





def test_character_node_progress_unique(db_session, teacher_user, student_character):

    adventure = create_adventure(teacher_user)

    node = add_node(adventure, "n1", NodeType.STORY)

    db_session.commit()

    db_session.add(

        CharacterNodeProgress(

            character_id=student_character.id,

            node_id=node.id,

            status=NodeProgressStatus.LOCKED.value,

        )

    )

    db_session.commit()

    db_session.add(

        CharacterNodeProgress(

            character_id=student_character.id,

            node_id=node.id,

            status=NodeProgressStatus.AVAILABLE.value,

        )

    )

    with pytest.raises(IntegrityError):

        db_session.flush()

    db_session.rollback()





def test_cascade_delete_adventure_removes_nodes(db_session, teacher_user):

    adventure, nodes = build_linear_adventure(teacher_user)

    node_ids = [n.id for n in nodes]

    db_session.delete(adventure)

    db_session.commit()

    assert AdventureNode.query.filter(AdventureNode.id.in_(node_ids)).count() == 0





def test_node_reward_relationship(db_session, teacher_user):

    adventure = create_adventure(teacher_user)

    node = add_node(adventure, "reward_node", NodeType.REWARD)

    db_session.add(

        NodeReward(

            node_id=node.id,

            type=AdventureRewardType.GOLD.value,

            amount=50,

        )

    )

    db_session.commit()

    assert node.rewards.count() == 1

    assert node.rewards.first().amount == 50





def test_published_adventure_status(db_session, teacher_user):

    adventure = create_adventure(teacher_user, status=AdventureStatus.PUBLISHED)

    db_session.commit()

    loaded = db_session.get(Adventure, adventure.id)

    assert loaded.status == AdventureStatus.PUBLISHED.value





def test_valid_assignment_to_classroom(db_session, teacher_user, classroom):

    adventure = create_adventure(teacher_user, status=AdventureStatus.PUBLISHED)

    db_session.commit()

    assignment = assign_to_classroom(adventure, classroom.id, teacher_user)

    assert assignment.classroom_id == classroom.id

    assert assignment.adventure_version == adventure.version


