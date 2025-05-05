import pytest
from sqlalchemy.exc import IntegrityError
from datetime import datetime
import uuid

@pytest.fixture
def teacher(db_session):
    from app.models.user import User, UserRole
    unique = uuid.uuid4().hex[:8]
    teacher = User(
        username=f'teacher_{unique}',
        email=f'teacher_{unique}@example.com',
        role=UserRole.TEACHER,
        password='password123'
    )
    teacher.save()
    return teacher

@pytest.fixture
def student(db_session):
    from app.models.user import User, UserRole
    unique = uuid.uuid4().hex[:8]
    student = User(
        username=f'student_{unique}',
        email=f'student_{unique}@example.com',
        role=UserRole.STUDENT,
        password='password123'
    )
    student.save()
    return student

def test_user_creation(db_session):
    from app.models.user import User, UserRole
    unique = uuid.uuid4().hex[:8]
    user = User(
        username=f'testuser_{unique}',
        email=f'test_{unique}@example.com',
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
    from app.models.user import User, UserRole
    unique = uuid.uuid4().hex[:8]
    user = User(
        username=f'testuser_{unique}',
        email=f'test_{unique}@example.com',
        role=UserRole.STUDENT,
        password='password123'
    )
    assert user.password_hash is not None
    assert user.check_password('password123') is True
    assert user.check_password('wrongpassword') is False

def test_unique_username_email(db_session):
    from app.models.user import User, UserRole
    unique = uuid.uuid4().hex[:8]
    user1 = User(
        username=f'testuser_{unique}',
        email=f'test_{unique}@example.com',
        role=UserRole.STUDENT,
        password='password123'
    )
    user1.save()
    # Try to create user with same username
    with pytest.raises(IntegrityError):
        user2 = User(
            username=f'testuser_{unique}',
            email=f'different_{unique}@example.com',
            role=UserRole.STUDENT,
            password='password123'
        )
        user2.save()
    db_session.rollback()
    # Try to create user with same email
    with pytest.raises(IntegrityError):
        user3 = User(
            username=f'different_{unique}',
            email=f'test_{unique}@example.com',
            role=UserRole.STUDENT,
            password='password123'
        )
        user3.save()

def test_class_creation(db_session, teacher):
    from app.models.classroom import Classroom
    unique = uuid.uuid4().hex[:8]
    class_ = Classroom(
        name=f'Test Class {unique}',
        teacher_id=teacher.id,
        join_code=f'ABC{unique[:5]}'
    )
    class_.save()
    assert class_.id is not None
    assert class_.created_at is not None
    assert class_.teacher_id == teacher.id
    assert class_.is_active is True
    assert class_.max_students == 30  # Default value
    assert class_.max_clans == 6  # Default value

def test_class_student_relationship(db_session, teacher, student):
    from app.models.classroom import Classroom
    unique = uuid.uuid4().hex[:8]
    class_ = Classroom(
        name=f'Test Class {unique}',
        teacher_id=teacher.id,
        join_code=f'ABC{unique[:5]}'
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
    from app.models.classroom import Classroom
    from app.models.user import User, UserRole
    unique = uuid.uuid4().hex[:8]
    class_ = Classroom(
        name=f'Test Class {unique}',
        teacher_id=teacher.id,
        join_code=f'ABC{unique[:5]}',
        max_students=2  # Set small max for testing
    )
    class_.save()
    # Add max number of students
    for i in range(2):
        s_unique = uuid.uuid4().hex[:8]
        student = User(
            username=f'student{i}_{s_unique}',
            email=f'student{i}_{s_unique}@example.com',
            role=UserRole.STUDENT,
            password='password123'
        )
        student.save()
        class_.add_student(student)
    # Try to add one more student
    extra_unique = uuid.uuid4().hex[:8]
    extra_student = User(
        username=f'extrastudent_{extra_unique}',
        email=f'extra_{extra_unique}@example.com',
        role=UserRole.STUDENT,
        password='password123'
    )
    extra_student.save()
    with pytest.raises(ValueError, match="Classroom is at maximum capacity"):
        class_.add_student(extra_student)

def test_get_by_join_code(db_session, teacher):
    from app.models.classroom import Classroom
    unique = uuid.uuid4().hex[:8]
    join_code = f'ABC{unique[:5]}'
    class_ = Classroom(
        name=f'Test Class {unique}',
        teacher_id=teacher.id,
        join_code=join_code
    )
    class_.save()
    found_class = Classroom.get_by_join_code(join_code)
    assert found_class is not None
    assert found_class.id == class_.id
    # Test with inactive class
    class_.is_active = False
    class_.save()
    assert Classroom.get_by_join_code(join_code) is None

def test_teacher_classes(db_session, teacher):
    from app.models.classroom import Classroom
    unique1 = uuid.uuid4().hex[:8]
    unique2 = uuid.uuid4().hex[:8]
    unique3 = uuid.uuid4().hex[:8]
    class1 = Classroom(name=f'Class 1_{unique1}', teacher_id=teacher.id, join_code=f'ABC{unique1[:5]}')
    class2 = Classroom(name=f'Class 2_{unique2}', teacher_id=teacher.id, join_code=f'DEF{unique2[:5]}')
    class3 = Classroom(name=f'Class 3_{unique3}', teacher_id=teacher.id, join_code=f'GHI{unique3[:5]}', is_active=False)
    class1.save()
    class2.save()
    class3.save()
    active_classes = Classroom.get_active_by_teacher(teacher.id)
    assert len(active_classes) == 2
    assert class3 not in active_classes 