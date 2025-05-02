import os
import pytest
from app.models.user import User
from flask import current_app

def test_teacher_signup_with_valid_access_code(client, db_session):
    """Test teacher signup with valid access code."""
    access_code = current_app.config['TEACHER_ACCESS_CODE']
    response = client.post('/auth/signup', data={
        'username': 'newteacher',
        'email': 'teacher@example.com',
        'password': 'securepassword',
        'confirm_password': 'securepassword',
        'access_code': access_code
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b'Account created successfully' in response.data
    user = User.query.filter_by(username='newteacher').first()
    assert user is not None
    assert user.role.value == 'teacher'

def test_teacher_signup_with_invalid_access_code(client, db_session):
    """Test teacher signup with invalid access code."""
    response = client.post('/auth/signup', data={
        'username': 'badteacher',
        'email': 'badteacher@example.com',
        'password': 'securepassword',
        'confirm_password': 'securepassword',
        'access_code': 'wrong-code'
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b'Invalid access code' in response.data
    user = User.query.filter_by(username='badteacher').first()
    assert user is None

def test_teacher_signup_duplicate_username_email(client, db_session):
    """Test teacher signup fails with duplicate username or email."""
    access_code = current_app.config['TEACHER_ACCESS_CODE']
    # First signup
    client.post('/auth/signup', data={
        'username': 'dupeuser',
        'email': 'dupe@example.com',
        'password': 'securepassword',
        'confirm_password': 'securepassword',
        'access_code': access_code
    }, follow_redirects=True)
    # Attempt duplicate username
    response = client.post('/auth/signup', data={
        'username': 'dupeuser',
        'email': 'other@example.com',
        'password': 'securepassword',
        'confirm_password': 'securepassword',
        'access_code': access_code
    }, follow_redirects=True)
    assert b'Username or email already exists' in response.data
    # Attempt duplicate email
    response = client.post('/auth/signup', data={
        'username': 'otheruser',
        'email': 'dupe@example.com',
        'password': 'securepassword',
        'confirm_password': 'securepassword',
        'access_code': access_code
    }, follow_redirects=True)
    assert b'Username or email already exists' in response.data 