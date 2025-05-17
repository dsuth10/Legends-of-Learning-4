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
    token = create_access_token(identity=test_user.id)
    return {'Authorization': f'Bearer {token}'}

def test_get_clan_metrics(client, test_clan, auth_headers):
    response = client.get(f'/clans/{test_clan.id}/metrics', headers=auth_headers)
    assert response.status_code == 200
    data = response.get_json()
    assert 'avg_completion_rate' in data
    assert 'total_points' in data
    assert 'active_members' in data

def test_get_clan_history(client, test_clan, auth_headers):
    response = client.get(f'/clans/{test_clan.id}/history', headers=auth_headers)
    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, list)
    assert len(data) >= 1

def test_get_clan_leaderboard(client, test_classroom, auth_headers):
    response = client.get(f'/classes/{test_classroom.id}/clan-leaderboard', headers=auth_headers)
    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, list)

def test_get_clan_trend_data(client, test_clan, auth_headers):
    response = client.get(f'/clans/{test_clan.id}/trend-data', headers=auth_headers)
    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, list) 