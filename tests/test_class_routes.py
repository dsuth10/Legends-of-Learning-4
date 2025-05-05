import pytest
import uuid
from flask import template_rendered

TEACHER_PASSWORD = 'password123'

@pytest.fixture(autouse=True)
def add_csrf_token(app):
    @app.context_processor
    def inject_csrf_token():
        return dict(csrf_token=lambda: "test-csrf-token")

@pytest.fixture
def teacher_user(db_session):
    from app.models.user import User, UserRole
    from app import db
    unique = uuid.uuid4().hex[:8]
    username = f'teacher_{unique}'
    email = f'testteacher_{unique}@example.com'
    user = User(
        username=username,
        email=email,
        role=UserRole.TEACHER
    )
    user.set_password(TEACHER_PASSWORD)
    db.session.add(user)
    db.session.commit()
    return user

def login(client, username, password):
    response = client.post('/auth/login', data={
        'username': username,
        'password': password
    }, follow_redirects=True)
    return response

def test_class_crud_and_archive(client, db_session, teacher_user):
    from app.models.classroom import Classroom
    from app import db
    resp = login(client, teacher_user.username, TEACHER_PASSWORD)
    assert b'Logged in successfully.' in resp.data
    resp = client.post('/teacher/classes', data={
        'name': 'Integration Test Class',
        'description': 'A class for integration testing.',
        'max_students': 42
    }, follow_redirects=True)
    assert b'Class created successfully!' in resp.data
    class_obj = Classroom.query.filter_by(name='Integration Test Class').first()
    assert class_obj is not None
    assert class_obj.description == 'A class for integration testing.'
    assert class_obj.max_students == 42
    assert class_obj.is_active is True
    resp = client.post(f'/teacher/classes/{class_obj.id}/edit', data={
        'name': 'Integration Test Class Edited',
        'description': 'Edited description.',
        'max_students': 99
    }, follow_redirects=True)
    assert b'Class updated successfully!' in resp.data
    class_obj = Classroom.query.get(class_obj.id)
    assert class_obj.name == 'Integration Test Class Edited'
    assert class_obj.description == 'Edited description.'
    assert class_obj.max_students == 99
    resp = client.post(f'/teacher/classes/{class_obj.id}/archive', follow_redirects=True)
    assert b'Class archived successfully.' in resp.data
    class_obj = Classroom.query.get(class_obj.id)
    assert class_obj.is_active is False
    resp = client.post(f'/teacher/classes/{class_obj.id}/delete', follow_redirects=True)
    assert b'Class deleted permanently.' in resp.data
    class_obj = Classroom.query.get(class_obj.id)
    assert class_obj is None

def test_edit_class_empty_name(client, db_session, teacher_user):
    from app.models.classroom import Classroom
    login(client, teacher_user.username, TEACHER_PASSWORD)
    client.post('/teacher/classes', data={
        'name': 'Class to Edit',
        'description': 'desc',
        'max_students': 10
    }, follow_redirects=True)
    class_obj = Classroom.query.filter_by(name='Class to Edit').first()
    resp = client.post(f'/teacher/classes/{class_obj.id}/edit', data={
        'name': '',
        'description': 'desc',
        'max_students': 10
    }, follow_redirects=True)
    if b'Class name is required.' not in resp.data:
        print('[DEBUG] Response HTML for empty name validation:', resp.data.decode())
    assert b'Class name is required.' in resp.data
    class_obj = Classroom.query.get(class_obj.id)
    assert class_obj.name == 'Class to Edit'

def test_unauthenticated_redirects(client, db_session, teacher_user):
    from app.models.classroom import Classroom
    login(client, teacher_user.username, TEACHER_PASSWORD)
    client.post('/teacher/classes', data={
        'name': 'Class for Auth',
        'description': 'desc',
        'max_students': 10
    }, follow_redirects=True)
    class_obj = Classroom.query.filter_by(name='Class for Auth').first()
    client.get('/auth/logout', follow_redirects=True)
    endpoints = [
        ('get', '/teacher/classes'),
        ('post', '/teacher/classes'),
        ('get', f'/teacher/classes/{class_obj.id}/edit'),
        ('post', f'/teacher/classes/{class_obj.id}/edit'),
        ('post', f'/teacher/classes/{class_obj.id}/archive'),
        ('post', f'/teacher/classes/{class_obj.id}/delete'),
    ]
    for method, url in endpoints:
        resp = getattr(client, method)(url, follow_redirects=False)
        assert resp.status_code in (302, 401)
        assert '/auth/login' in resp.headers.get('Location', '') or resp.status_code == 401

def test_archived_class_not_in_list(client, db_session, teacher_user):
    from app.models.classroom import Classroom
    login(client, teacher_user.username, TEACHER_PASSWORD)
    client.post('/teacher/classes', data={
        'name': 'Class to Archive',
        'description': 'desc',
        'max_students': 10
    }, follow_redirects=True)
    class_obj = Classroom.query.filter_by(name='Class to Archive').first()
    client.post(f'/teacher/classes/{class_obj.id}/archive', follow_redirects=True)
    resp = client.get('/teacher/classes')
    if b'Class to Archive' in resp.data:
        print('[DEBUG] Response HTML for archived class filtering:', resp.data.decode())
    assert b'Class to Archive' not in resp.data

def test_student_roster_listing_filtering_sorting(client, db_session, teacher_user):
    from app.models.classroom import Classroom
    from app.models.clan import Clan
    from app.models.student import Student
    from app import db
    login(client, teacher_user.username, TEACHER_PASSWORD)
    resp = client.post('/teacher/classes', data={
        'name': 'Roster Test Class',
        'description': 'Class for roster testing.',
        'max_students': 10
    }, follow_redirects=True)
    assert b'Class created successfully!' in resp.data
    class_obj = Classroom.query.filter_by(name='Roster Test Class').first()
    assert class_obj is not None
    unique1 = uuid.uuid4().hex[:8]
    unique2 = uuid.uuid4().hex[:8]
    clan1 = Clan(name=f'Alpha_{unique1}', class_id=class_obj.id)
    clan2 = Clan(name=f'Beta_{unique2}', class_id=class_obj.id)
    db.session.add_all([clan1, clan2])
    db.session.commit()
    students = []
    bob_email = None
    for i, (name, level, gold, xp, health, power, clan, char_class) in enumerate([
        ('Alice', 2, 100, 500, 90, 80, clan1, 'Warrior'),
        ('Bob', 3, 200, 1500, 100, 90, clan2, 'Mage'),
        ('Charlie', 1, 50, 200, 70, 60, None, 'Druid'),
    ]):
        unique = uuid.uuid4().hex[:8]
        email = f'user{i}_{unique}@example.com'
        user = __import__('app.models.user', fromlist=['User', 'UserRole']).User(
            username=f'user{i}_{unique}',
            email=email,
            role=__import__('app.models.user', fromlist=['User', 'UserRole']).UserRole.STUDENT,
            first_name=name,
            last_name="Test"
        )
        user.set_password('password123')
        db.session.add(user)
        db.session.commit()
        if name == "Bob":
            bob_email = email
        student = Student(
            user_id=user.id,
            class_id=class_obj.id,
            clan_id=clan.id if clan else None,
            level=level,
            gold=gold,
            xp=xp,
            health=health,
            power=power
        )
        db.session.add(student)
        db.session.commit()
        Character = __import__('app.models.character', fromlist=['Character']).Character
        character = Character(
            name=char_class,
            student_id=user.id,
            level=level,
            experience=xp,
            health=health,
            max_health=health,
            is_active=True
        )
        db.session.add(character)
        db.session.commit()
        students.append((user, student, character, clan))
    resp = client.get(f'/teacher/students?class_id={class_obj.id}')
    assert b'Alice' in resp.data and b'Bob' in resp.data and b'Charlie' in resp.data

    # Filter by name
    resp = client.get(f'/teacher/students?class_id={class_obj.id}&search=Alice')
    assert b'Alice' in resp.data and b'Bob' not in resp.data and b'Charlie' not in resp.data

    # Filter by email
    resp = client.get(f'/teacher/students?class_id={class_obj.id}&search={bob_email}')
    assert b'Bob' in resp.data and b'Alice' not in resp.data and b'Charlie' not in resp.data

    # Filter by level
    resp = client.get(f'/teacher/students?class_id={class_obj.id}&level=3')
    assert b'Bob' in resp.data and b'Alice' not in resp.data and b'Charlie' not in resp.data

    # Filter by gold
    resp = client.get(f'/teacher/students?class_id={class_obj.id}&gold=50')
    assert b'Charlie' in resp.data and b'Alice' not in resp.data and b'Bob' not in resp.data

    # Filter by xp
    resp = client.get(f'/teacher/students?class_id={class_obj.id}&xp=500')
    assert b'Alice' in resp.data and b'Bob' not in resp.data and b'Charlie' not in resp.data

    # Filter by health
    resp = client.get(f'/teacher/students?class_id={class_obj.id}&health=70')
    assert b'Charlie' in resp.data and b'Alice' not in resp.data and b'Bob' not in resp.data

    # Filter by power
    resp = client.get(f'/teacher/students?class_id={class_obj.id}&power=90')
    assert b'Bob' in resp.data and b'Alice' not in resp.data and b'Charlie' not in resp.data

    # Filter by clan
    resp = client.get(f'/teacher/students?class_id={class_obj.id}&clan_id={clan1.id}')
    assert b'Alice' in resp.data and b'Bob' not in resp.data and b'Charlie' not in resp.data

    # Filter by character class
    resp = client.get(f'/teacher/students?class_id={class_obj.id}&character_class=Mage')
    assert b'Bob' in resp.data and b'Alice' not in resp.data and b'Charlie' not in resp.data

    # Sorting by level desc
    resp = client.get(f'/teacher/students?class_id={class_obj.id}&sort=level&direction=desc')
    assert resp.data.find(b'Bob') < resp.data.find(b'Alice') < resp.data.find(b'Charlie')

    # Sorting by gold asc
    resp = client.get(f'/teacher/students?class_id={class_obj.id}&sort=gold&direction=asc')
    assert resp.data.find(b'Charlie') < resp.data.find(b'Alice') < resp.data.find(b'Bob')

    # Edge case: no students
    empty_class = Classroom(name='Empty Class', teacher_id=teacher_user.id, join_code='EMPTY123')
    db.session.add(empty_class)
    db.session.commit()
    resp = client.get(f'/teacher/students?class_id={empty_class.id}')
    assert b'No students found in this class.' in resp.data

    # Edge case: filter matches no students
    resp = client.get(f'/teacher/students?class_id={class_obj.id}&search=Nonexistent')
    assert b'No students found in this class.' in resp.data 