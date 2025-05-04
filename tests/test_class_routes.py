import pytest
from app.models.user import User, UserRole
from app.models.classroom import Classroom
from app import db

TEACHER_USERNAME = 'testteacher'
TEACHER_EMAIL = 'testteacher@example.com'
TEACHER_PASSWORD = 'password123'

@pytest.fixture
def teacher_user(db_session):
    user = User(
        username=TEACHER_USERNAME,
        email=TEACHER_EMAIL,
        role=UserRole.TEACHER
    )
    user.set_password(TEACHER_PASSWORD)
    db.session.add(user)
    db.session.commit()
    return user

def login(client, username, password):
    return client.post('/auth/login', data={
        'username': username,
        'password': password
    }, follow_redirects=True)

def test_class_crud_and_archive(client, db_session, teacher_user):
    # Log in as teacher
    resp = login(client, TEACHER_USERNAME, TEACHER_PASSWORD)
    assert b'Logged in successfully.' in resp.data

    # Create a class
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

    # Edit the class
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

    # Archive the class
    resp = client.post(f'/teacher/classes/{class_obj.id}/archive', follow_redirects=True)
    assert b'Class archived successfully.' in resp.data
    class_obj = Classroom.query.get(class_obj.id)
    assert class_obj.is_active is False

    # Delete the class
    resp = client.post(f'/teacher/classes/{class_obj.id}/delete', follow_redirects=True)
    assert b'Class deleted permanently.' in resp.data
    class_obj = Classroom.query.get(class_obj.id)
    assert class_obj is None

def test_edit_class_empty_name(client, db_session, teacher_user):
    # Log in and create a class
    login(client, TEACHER_USERNAME, TEACHER_PASSWORD)
    client.post('/teacher/classes', data={
        'name': 'Class to Edit',
        'description': 'desc',
        'max_students': 10
    }, follow_redirects=True)
    class_obj = Classroom.query.filter_by(name='Class to Edit').first()
    # Try to edit with empty name
    resp = client.post(f'/teacher/classes/{class_obj.id}/edit', data={
        'name': '',
        'description': 'desc',
        'max_students': 10
    }, follow_redirects=True)
    assert b'Class name is required.' in resp.data
    # Ensure name did not change
    class_obj = Classroom.query.get(class_obj.id)
    assert class_obj.name == 'Class to Edit'

def test_unauthenticated_redirects(client, db_session, teacher_user):
    # Create a class as teacher
    login(client, TEACHER_USERNAME, TEACHER_PASSWORD)
    client.post('/teacher/classes', data={
        'name': 'Class for Auth',
        'description': 'desc',
        'max_students': 10
    }, follow_redirects=True)
    class_obj = Classroom.query.filter_by(name='Class for Auth').first()
    # Log out
    client.get('/auth/logout', follow_redirects=True)
    # Try to access all class management routes
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
        # Should redirect to login
        assert resp.status_code in (302, 401)
        assert '/auth/login' in resp.headers.get('Location', '') or resp.status_code == 401

def test_archived_class_not_in_list(client, db_session, teacher_user):
    # Log in and create a class
    login(client, TEACHER_USERNAME, TEACHER_PASSWORD)
    client.post('/teacher/classes', data={
        'name': 'Class to Archive',
        'description': 'desc',
        'max_students': 10
    }, follow_redirects=True)
    class_obj = Classroom.query.filter_by(name='Class to Archive').first()
    # Archive the class
    client.post(f'/teacher/classes/{class_obj.id}/archive', follow_redirects=True)
    # Get the classes list page
    resp = client.get('/teacher/classes')
    # Archived class should not appear
    assert b'Class to Archive' not in resp.data 