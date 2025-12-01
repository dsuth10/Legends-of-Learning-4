import os
import pytest
from flask import current_app
import uuid

def test_teacher_signup_with_valid_access_code(client, db_session):
    from app.models.user import User
    access_code = current_app.config['TEACHER_ACCESS_CODE']
    unique = uuid.uuid4().hex
    username = 'newteacher' + unique
    email = 'teacher' + unique + '@example.com'
    response = client.post('/auth/signup', data={
        'username': username,
        'email': email,
        'password': 'securepassword',
        'confirm_password': 'securepassword',
        'access_code': access_code
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b'Account created successfully' in response.data
    user = User.query.filter_by(username=username).first()
    assert user is not None
    assert user.role.value == 'teacher'

def test_teacher_signup_with_invalid_access_code(client, db_session):
    from app.models.user import User
    unique = uuid.uuid4().hex
    username = 'badteacher' + unique
    email = 'badteacher' + unique + '@example.com'
    response = client.post('/auth/signup', data={
        'username': username,
        'email': email,
        'password': 'securepassword',
        'confirm_password': 'securepassword',
        'access_code': 'wrong-code'
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b'Invalid access code' in response.data
    user = User.query.filter_by(username=username).first()
    assert user is None

def test_teacher_signup_duplicate_username_email(client, db_session):
    from app.models.user import User
    access_code = current_app.config['TEACHER_ACCESS_CODE']
    unique = uuid.uuid4().hex
    username = 'dupeuser' + unique
    email = 'dupe' + unique + '@example.com'
    # First signup
    client.post('/auth/signup', data={
        'username': username,
        'email': email,
        'password': 'securepassword',
        'confirm_password': 'securepassword',
        'access_code': access_code
    }, follow_redirects=True)
    # Attempt duplicate username
    response = client.post('/auth/signup', data={
        'username': username,
        'email': 'other' + unique + '@example.com',
        'password': 'securepassword',
        'confirm_password': 'securepassword',
        'access_code': access_code
    }, follow_redirects=True)
    assert b'Username already exists.' in response.data
    # Attempt duplicate email
    response = client.post('/auth/signup', data={
        'username': 'otheruser' + unique,
        'email': email,
        'password': 'securepassword',
        'confirm_password': 'securepassword',
        'access_code': access_code
    }, follow_redirects=True)
    assert b'Email already exists.' in response.data

def test_teacher_login_flow(client, db_session):
    from app.models.user import User
    from flask import current_app
    access_code = current_app.config['TEACHER_ACCESS_CODE']
    unique = uuid.uuid4().hex
    username = 'loginuser' + unique
    email = 'loginuser' + unique + '@example.com'
    password = 'securepassword'
    # Sign up
    response = client.post('/auth/signup', data={
        'username': username,
        'email': email,
        'password': password,
        'confirm_password': password,
        'access_code': access_code
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b'Account created successfully' in response.data
    # Log out
    client.get('/auth/logout', follow_redirects=True)
    # Attempt login
    response = client.post('/auth/login', data={
        'username': username,
        'password': password
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b'Logged in successfully' in response.data or b'Teacher Dashboard' in response.data or b'teacher dashboard' in response.data
    user = User.query.filter_by(username=username).first()
    assert user is not None
    assert user.role.value == 'teacher' 