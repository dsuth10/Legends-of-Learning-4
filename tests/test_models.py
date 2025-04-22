import pytest
from app.models import db
from app.models.user import User, UserRole
from app.models.classroom import Class
from sqlalchemy.exc import IntegrityError
from datetime import datetime

@pytest.fixture
def app(app):
    """Create application for the tests."""
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    return app

@pytest.fixture
def db_session(app):
    """Create database and tables for the tests."""
    with app.app_context():
        db.create_all()
        yield db
        db.session.remove()
        db.drop_all()

@pytest.fixture
def teacher(db_session):
    """Create a test teacher."""
    teacher = User(
        username='teacher',
        email='teacher@example.com',
        role=UserRole.TEACHER,
        password='password123'
    )
    teacher.save()
    return teacher

@pytest.fixture
def student(db_session):
    """Create a test student."""
    student = User(
        username='student',
        email='student@example.com',
        role=UserRole.STUDENT,
        password='password123'
    )
    student.save()
    return student

def test_user_creation(db_session):
    """Test basic user creation."""
    user = User(
        username='testuser',
        email='test@example.com',
        role=UserRole.STUDENT,
        password='password123'
    )
    user.save()
    
    assert user.id is not None
    assert user.created_at is not None
    assert user.updated_at is not None
    assert user.is_active is True
    assert user.role == UserRole.STUDENT

def test_user_password(db_session):
    """Test password hashing and verification."""
    user = User(
        username='testuser',
        email='test@example.com',
        role=UserRole.STUDENT,
        password='password123'
    )
    
    assert user.password_hash is not None
    assert user.check_password('password123') is True
    assert user.check_password('wrongpassword') is False

def test_unique_username_email(db_session):
    """Test that usernames and emails must be unique."""
    user1 = User(
        username='testuser',
        email='test@example.com',
        role=UserRole.STUDENT,
        password='password123'
    )
    user1.save()
    
    # Try to create user with same username
    with pytest.raises(IntegrityError):
        user2 = User(
            username='testuser',
            email='different@example.com',
            role=UserRole.STUDENT,
            password='password123'
        )
        user2.save()
    
    db_session.session.rollback()
    
    # Try to create user with same email
    with pytest.raises(IntegrityError):
        user3 = User(
            username='different',
            email='test@example.com',
            role=UserRole.STUDENT,
            password='password123'
        )
        user3.save()

def test_class_creation(db_session, teacher):
    """Test basic class creation."""
    class_ = Class(
        name='Test Class',
        teacher_id=teacher.id,
        join_code='ABC123'
    )
    class_.save()
    
    assert class_.id is not None
    assert class_.created_at is not None
    assert class_.teacher_id == teacher.id
    assert class_.is_active is True
    assert class_.max_students == 30  # Default value
    assert class_.max_clans == 6  # Default value

def test_class_student_relationship(db_session, teacher, student):
    """Test adding and removing students from a class."""
    class_ = Class(
        name='Test Class',
        teacher_id=teacher.id,
        join_code='ABC123'
    )
    class_.save()
    
    # Add student to class
    class_.add_student(student)
    assert student in class_.students.all()
    assert class_ in student.enrolled_classes.all()
    
    # Try to add same student again
    class_.add_student(student)  # Should not raise error but also not duplicate
    assert class_.students.count() == 1
    
    # Remove student from class
    class_.remove_student(student)
    assert student not in class_.students.all()
    assert class_ not in student.enrolled_classes.all()

def test_class_capacity(db_session, teacher):
    """Test class capacity limits."""
    class_ = Class(
        name='Test Class',
        teacher_id=teacher.id,
        join_code='ABC123',
        max_students=2  # Set small max for testing
    )
    class_.save()
    
    # Add max number of students
    for i in range(2):
        student = User(
            username=f'student{i}',
            email=f'student{i}@example.com',
            role=UserRole.STUDENT,
            password='password123'
        )
        student.save()
        class_.add_student(student)
    
    # Try to add one more student
    extra_student = User(
        username='extrastudent',
        email='extra@example.com',
        role=UserRole.STUDENT,
        password='password123'
    )
    extra_student.save()
    
    with pytest.raises(ValueError, match="Class is at maximum capacity"):
        class_.add_student(extra_student)

def test_get_by_join_code(db_session, teacher):
    """Test finding a class by join code."""
    class_ = Class(
        name='Test Class',
        teacher_id=teacher.id,
        join_code='ABC123'
    )
    class_.save()
    
    found_class = Class.get_by_join_code('ABC123')
    assert found_class is not None
    assert found_class.id == class_.id
    
    # Test with inactive class
    class_.is_active = False
    class_.save()
    assert Class.get_by_join_code('ABC123') is None

def test_teacher_classes(db_session, teacher):
    """Test getting a teacher's classes."""
    # Create some active and inactive classes
    class1 = Class(name='Class 1', teacher_id=teacher.id, join_code='ABC123')
    class2 = Class(name='Class 2', teacher_id=teacher.id, join_code='DEF456')
    class3 = Class(name='Class 3', teacher_id=teacher.id, join_code='GHI789', is_active=False)
    
    class1.save()
    class2.save()
    class3.save()
    
    active_classes = Class.get_active_by_teacher(teacher.id)
    assert len(active_classes) == 2
    assert class3 not in active_classes 