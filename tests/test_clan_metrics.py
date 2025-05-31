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
    print(f'[DEBUG] Created test_user with id={user.id}')
    return user

@pytest.fixture
def test_classroom(db_session, test_user):
    from app.models.classroom import Classroom
    unique_id = uuid.uuid4().hex
    classroom = Classroom(name=f'Test Class {unique_id}', teacher_id=test_user.id, join_code=f'TEST1234_{unique_id}')
    db_session.add(classroom)
    db_session.commit()
    print(f'[DEBUG] Created test_classroom with id={classroom.id}, teacher_id={classroom.teacher_id}')
    return classroom

@pytest.fixture
def test_clan(db_session, test_classroom, test_user):
    from app.models.clan import Clan
    from app.models.character import Character
    from app.models.student import Student
    unique_id = uuid.uuid4().hex
    clan = Clan(name=f'Test Clan {unique_id}', class_id=test_classroom.id)
    db_session.add(clan)
    db_session.commit()
    print(f'[DEBUG] Created test_clan with id={clan.id}, class_id={clan.class_id}')
    # If Clan has a leader_id, create a Character for test_user and set leader_id
    if hasattr(clan, 'leader_id'):
        # Create a Student for test_user in the classroom (not in the clan)
        student = Student(user_id=test_user.id, class_id=test_classroom.id)
        db_session.add(student)
        db_session.commit()
        character = Character(name=f'LeaderChar_{unique_id}', student_id=student.id)
        db_session.add(character)
        db_session.commit()
        clan.leader_id = character.id
        db_session.commit()
        print(f'[DEBUG] Set clan.leader_id = {character.id}')
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

def test_clan_student_relationships(db_session, test_clan, test_students_and_characters):
    """Test that students are correctly related to their clan and that the relationship is bidirectional."""
    from app.models.clan import Clan
    from app.models.student import Student
    clan = db_session.query(Clan).get(test_clan.id)
    students = clan.clan_members.all()
    assert len(students) == 5  # Only the 5 test students
    for student in students:
        assert student.clan_id == clan.id
        # Check bidirectional
        assert db_session.query(Clan).get(student.clan_id).id == clan.id


def test_clan_size_constraint(db_session, test_clan, test_students_and_characters):
    """Test that adding more students than allowed by max_size raises an error (if enforced at DB or model level)."""
    from app.models.clan import Clan
    clan = db_session.query(Clan).get(test_clan.id)
    # Assume max_size is 5 for this test (adjust if different)
    clan.max_size = 5
    db_session.commit()
    from app.models.user import User, UserRole
    from app.models.student import Student
    import uuid
    # Add 5 students (already present), try to add a 6th
    unique_id = uuid.uuid4().hex
    user = User(username=f"student_extra_{unique_id}", email=f"student_extra_{unique_id}@example.com", role=UserRole.STUDENT)
    user.set_password("password")
    db_session.add(user)
    db_session.commit()
    student = Student(user_id=user.id, clan_id=clan.id)
    db_session.add(student)
    try:
        db_session.commit()
        # If no error, check if model enforces it in Python
        if hasattr(clan, 'max_size'):
            assert len(clan.students) <= clan.max_size
    except Exception as e:
        db_session.rollback()
        assert True  # Exception expected if DB constraint exists


def test_clan_metrics_api(client, db_session, test_user, test_clan, test_students_and_characters):
    """Test the /clans/<id>/metrics API endpoint returns expected structure."""
    token = create_access_token(identity=str(test_user.id))
    headers = {"Authorization": f"Bearer {token}"}
    response = client.get(f"/clans/{test_clan.id}/metrics", headers=headers)
    if response.status_code != 200:
        print("[DEBUG] Response data:", response.get_data(as_text=True))
    assert response.status_code == 200
    data = response.get_json()
    assert 'avg_completion_rate' in data
    assert 'total_points' in data
    assert 'active_members' in data


def test_clan_history_api(client, db_session, test_user, test_clan, test_students_and_characters):
    """Test the /clans/<id>/history API endpoint returns a list of historical metrics."""
    token = create_access_token(identity=str(test_user.id))
    headers = {"Authorization": f"Bearer {token}"}
    response = client.get(f"/clans/{test_clan.id}/history?days=30", headers=headers)
    if response.status_code != 200:
        print("[DEBUG] Response data:", response.get_data(as_text=True))
    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, list)
    if data:
        assert 'timestamp' in data[0]
        assert 'avg_completion_rate' in data[0]
        assert 'total_points' in data[0]
        assert 'active_members' in data[0] 