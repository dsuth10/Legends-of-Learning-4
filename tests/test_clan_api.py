import pytest
from datetime import datetime, timedelta
import uuid
from flask_jwt_extended import create_access_token

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
def test_clan(db_session, test_classroom):
    from app.models.clan import Clan
    unique_id = uuid.uuid4().hex
    clan = Clan(name=f'Test Clan {unique_id}', class_id=test_classroom.id)
    db_session.add(clan)
    db_session.commit()
    return clan

@pytest.fixture(autouse=True)
def setup_clan_progress(db_session, test_clan):
    from app.models.clan_progress import ClanProgressHistory
    now = datetime.utcnow()
    for i in range(5):
        h = ClanProgressHistory(
            clan_id=test_clan.id,
            timestamp=now - timedelta(days=i),
            avg_completion_rate=0.8,
            total_points=100 + i * 10,
            active_members=5,
            avg_daily_points=20.0 + i,
            quest_completion_rate=0.7,
            avg_member_level=3.5,
            percentile_rank=90
        )
        db_session.add(h)
    db_session.commit()

@pytest.fixture
def auth_headers(test_user):
    token = create_access_token(identity=str(test_user.id))
    return {'Authorization': f'Bearer {token}'}

@pytest.fixture
def test_clan_with_member(db_session, test_clan, test_classroom, setup_clan_progress):
    from app.models.student import Student
    from app.models.user import User, UserRole
    from app.models.character import Character
    from app.models.audit import AuditLog
    from app.models.clan_progress import ClanProgressHistory
    import uuid
    from datetime import datetime
    unique = uuid.uuid4().hex[:8]
    # Create a student user
    student_user = User(
        username=f'student_{unique}',
        email=f'student_{unique}@example.com',
        role=UserRole.STUDENT,
        first_name='Test',
        last_name='Student'
    )
    student_user.set_password('password')
    db_session.add(student_user)
    db_session.commit()
    # Create a student profile
    student = Student(
        user_id=student_user.id,
        class_id=test_classroom.id,
        clan_id=test_clan.id,
        level=1,
        gold=0,
        xp=0,
        health=100,
        power=10,
        last_activity=datetime.utcnow()
    )
    db_session.add(student)
    db_session.commit()
    # Create a character for the student
    character = Character(
        name='TestChar',
        student_id=student.id,
        clan_id=test_clan.id,
        character_class='Warrior',
        level=1,
        experience=0,
        health=100,
        max_health=100,
        is_active=True
    )
    db_session.add(character)
    db_session.commit()
    # Add a dummy QuestAssignment or QuestLog for the character
    try:
        from app.models.quest_assignment import QuestAssignment
        quest = QuestAssignment(character_id=character.id, status='completed')
        db_session.add(quest)
        db_session.commit()
    except ImportError:
        from app.models.quest import Quest, QuestLog
        # Create a dummy quest
        quest_obj = Quest(
            title='Test Quest Title',
            type='STORY',
            description='Dummy quest',
            level_requirement=1
        )
        db_session.add(quest_obj)
        db_session.commit()
        quest = QuestLog(character_id=character.id, quest_id=quest_obj.id, status='completed')
        db_session.add(quest)
        db_session.commit()
    # Add a dummy AuditLog for XP_GAIN
    audit = AuditLog(
        event_type='XP_GAIN',
        character_id=character.id,
        event_data={'amount': 10},
        event_timestamp=datetime.utcnow()
    )
    db_session.add(audit)
    db_session.commit()
    # Add a ClanProgressHistory record for the clan
    progress = ClanProgressHistory(
        clan_id=test_clan.id,
        timestamp=datetime.utcnow(),
        avg_completion_rate=1.0,
        total_points=100,
        active_members=1
    )
    db_session.add(progress)
    db_session.commit()
    return test_clan

def test_get_clan_metrics(client, test_clan_with_member, auth_headers):
    response = client.get(f'/clans/{test_clan_with_member.id}/metrics', headers=auth_headers)
    assert response.status_code == 200
    data = response.get_json()
    assert 'avg_completion_rate' in data
    assert 'total_points' in data
    assert 'active_members' in data

def test_get_clan_history(client, test_clan_with_member, auth_headers):
    response = client.get(f'/clans/{test_clan_with_member.id}/history', headers=auth_headers)
    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, list)
    assert len(data) >= 1

def test_get_clan_leaderboard(client, test_classroom, auth_headers):
    response = client.get(f'/classes/{test_classroom.id}/clan-leaderboard', headers=auth_headers)
    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, dict)
    assert 'clans' in data
    assert isinstance(data['clans'], list)

def test_get_clan_trend_data(client, test_clan_with_member, auth_headers):
    response = client.get(f'/clans/{test_clan_with_member.id}/trend-data', headers=auth_headers)
    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, dict)
    assert 'labels' in data
    assert 'data' in data
    assert isinstance(data['labels'], list)
    assert isinstance(data['data'], list) 