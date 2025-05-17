import pytest
from datetime import datetime, timedelta
import uuid

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

@pytest.fixture
def test_student(db_session, test_classroom):
    from app.models.student import Student
    student = Student(user_id=1, class_id=test_classroom.id)
    db_session.add(student)
    db_session.commit()
    return student

@pytest.fixture
def test_students_and_characters(db_session, test_clan):
    from app.models.user import User, UserRole
    from app.models.student import Student
    from app.models.character import Character
    students = []
    characters = []
    now = datetime.utcnow()
    for i in range(5):
        unique_id = uuid.uuid4().hex
        user = User(username=f"student{i}_{unique_id}", email=f"student{i}_{unique_id}@example.com", role=UserRole.STUDENT)
        user.set_password("password")
        db_session.add(user)
        db_session.commit()
        student = Student(user_id=user.id, clan_id=test_clan.id, last_activity=now if i < 3 else now - timedelta(days=10))
        db_session.add(student)
        db_session.commit()
        character = Character(name=f"Char{i}_{unique_id}", student_id=student.id, experience=100 * i, level=i+1)
        db_session.add(character)
        db_session.commit()
        students.append(student)
        characters.append(character)
    return students, characters

@pytest.fixture
def test_clan2(db_session, test_classroom):
    from app.models.clan import Clan
    unique_id = uuid.uuid4().hex
    clan = Clan(name=f"Phoenix Riders {unique_id}", class_id=test_classroom.id)
    db_session.add(clan)
    db_session.commit()
    return clan

@pytest.fixture
def test_students2(db_session, test_clan2):
    from app.models.user import User, UserRole
    from app.models.student import Student
    from app.models.character import Character
    students = []
    now = datetime.utcnow()
    for i in range(5):
        unique_id = uuid.uuid4().hex
        user = User(username=f"student{i+5}_{unique_id}", email=f"student{i+5}_{unique_id}@example.com", role=UserRole.STUDENT)
        user.set_password("password")
        db_session.add(user)
        db_session.commit()
        student = Student(user_id=user.id, clan_id=test_clan2.id, last_activity=now)
        db_session.add(student)
        db_session.commit()
        character = Character(name=f"Char{i+5}_{unique_id}", student_id=student.id, experience=200 * i, level=i+2)
        db_session.add(character)
        db_session.commit()
        students.append(student)
    return students

@pytest.fixture
def clan_metrics_services():
    from app.services.clan_metrics import (
        calculate_avg_completion_rate,
        calculate_total_points,
        calculate_active_members,
        calculate_clan_metrics,
        calculate_percentile_rankings
    )
    return {
        'calculate_avg_completion_rate': calculate_avg_completion_rate,
        'calculate_total_points': calculate_total_points,
        'calculate_active_members': calculate_active_members,
        'calculate_clan_metrics': calculate_clan_metrics,
        'calculate_percentile_rankings': calculate_percentile_rankings
    }

def test_avg_completion_rate(db_session, test_clan, test_students_and_characters, clan_metrics_services):
    rate = clan_metrics_services['calculate_avg_completion_rate'](test_clan)
    assert isinstance(rate, float)

def test_total_points(db_session, test_clan, test_students_and_characters, clan_metrics_services):
    points = clan_metrics_services['calculate_total_points'](test_clan)
    assert isinstance(points, int)

def test_active_members(db_session, test_clan, test_students_and_characters, clan_metrics_services):
    active = clan_metrics_services['calculate_active_members'](test_clan)
    assert active == 3

def test_clan_metrics(db_session, test_clan, test_students_and_characters, clan_metrics_services):
    metrics = clan_metrics_services['calculate_clan_metrics'](test_clan.id)
    assert isinstance(metrics, dict)
    assert 'avg_completion_rate' in metrics
    assert 'total_points' in metrics
    assert 'active_members' in metrics

def test_percentile_rankings(db_session, test_clan, test_students_and_characters, test_clan2, test_students2, clan_metrics_services):
    percentiles = clan_metrics_services['calculate_percentile_rankings']()
    assert isinstance(percentiles, dict)

def test_clan_metrics_logic(db_session, test_clan, test_student):
    from app.models.clan import Clan
    from app.models.student import Student
    from app.services.clan_metrics import calculate_clan_metrics
    # Setup: Add students to clan and assign points/metrics
    # ... add your test logic here ...
    metrics = calculate_clan_metrics(test_clan.id)
    assert metrics is not None, '[DEBUG] Clan metrics should not be None.'
    # ... more assertions and debug prints as needed ... 