import pytest

def login(client, username, password):
    return client.post('/auth/login', data={'username': username, 'password': password}, follow_redirects=True)

def create_teacher_and_class(db_session):
    from app.models.user import User, UserRole
    from app.models.classroom import Classroom
    teacher = User(
        username='teachertest',
        email='teachertest@example.com',
        role=UserRole.TEACHER,
        first_name='Teacher',
        last_name='Test'
    )
    teacher.set_password('password123')
    db_session.add(teacher)
    db_session.commit()
    classroom = Classroom(name='Test Class', teacher_id=teacher.id, join_code='TEST123')
    db_session.add(classroom)
    db_session.commit()
    return teacher, classroom

def create_student_with_character(db_session, class_id, name='Student1', char_name='Hero', char_class='Warrior'):
    from app.models.user import User, UserRole
    from app.models.student import Student
    from app.models.character import Character
    student = User(
        username=f'{name.lower()}_user',
        email=f'{name.lower()}@example.com',
        role=UserRole.STUDENT,
        first_name=name,
        last_name='Test'
    )
    student.set_password('password123')
    db_session.add(student)
    db_session.commit()
    student_profile = Student(user_id=student.id, class_id=class_id, level=2, gold=100, xp=500, health=90, power=80)
    db_session.add(student_profile)
    db_session.commit()
    character = Character(name=char_name, student_id=student_profile.id, character_class=char_class, level=2, experience=500, health=90, max_health=100, is_active=True)
    db_session.add(character)
    db_session.commit()
    return student, student_profile, character

def test_character_management_navigation_and_display(client, db_session):
    # Setup
    teacher, classroom = create_teacher_and_class(db_session)
    student, student_profile, character = create_student_with_character(db_session, classroom.id)
    login(client, teacher.username, 'password123')

    # 1. Students page loads and has Character Management button
    resp = client.get(f'/teacher/students?class_id={classroom.id}')
    assert b'Character Management' in resp.data
    assert f'/teacher/students/{classroom.id}/characters'.encode() in resp.data

    # 2. Character Management page loads
    resp = client.get(f'/teacher/students/{classroom.id}/characters')
    assert resp.status_code == 200
    assert b'Character Management' in resp.data
    assert character.name.encode() in resp.data
    assert f"{student.first_name} {student.last_name}".encode() in resp.data
    assert b'Equipped Items' in resp.data

    # 3. Edge case: no students with characters
    from app.models.classroom import Classroom
    empty_class = Classroom(name='Empty Class', teacher_id=teacher.id, join_code='EMPTY123')
    db_session.add(empty_class)
    db_session.commit()
    resp = client.get(f'/teacher/students/{empty_class.id}/characters')
    assert b'No students with characters found in this class.' in resp.data

def test_character_management_permission(client, db_session):
    # Setup: teacher1 owns class, teacher2 does not
    teacher1, classroom = create_teacher_and_class(db_session)
    from app.models.user import User, UserRole
    teacher2 = User(username='otherteacher', email='otherteacher@example.com', role=UserRole.TEACHER)
    teacher2.set_password('password123')
    db_session.add(teacher2)
    db_session.commit()
    login(client, teacher2.username, 'password123')
    # Should not be able to access teacher1's class
    resp = client.get(f'/teacher/students/{classroom.id}/characters', follow_redirects=True)
    assert b'Class not found or you do not have permission.' in resp.data or resp.status_code in (302, 403)

def test_batch_reset_health(client, db_session):
    from app.models.user import User
    from app.models.character import Character
    from app.models.audit import AuditLog, EventType
    # Setup
    teacher, classroom = create_teacher_and_class(db_session)
    student1, student_profile1, character1 = create_student_with_character(db_session, classroom.id, name='StudentA', char_name='HeroA')
    student2, student_profile2, character2 = create_student_with_character(db_session, classroom.id, name='StudentB', char_name='HeroB')
    login(client, teacher.username, 'password123')
    # Set health to non-max
    character1.health = 10
    character2.health = 20
    db_session.commit()
    # Perform batch reset-health
    resp = client.post('/teacher/api/teacher/characters/batch-action', json={
        'action': 'reset-health',
        'character_ids': [character1.id, character2.id]
    })
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['success']
    assert str(character1.id) in data['results']
    assert str(character2.id) in data['results']
    db_session.refresh(character1)
    db_session.refresh(character2)
    assert character1.health == character1.max_health
    assert character2.health == character2.max_health
    # Check audit log
    logs = AuditLog.query.filter_by(event_type=EventType.CHARACTER_UPDATE.value).order_by(AuditLog.event_timestamp.desc()).all()
    assert any('batch-reset-health' in (log.event_data.get('action') or '') for log in logs)

def test_batch_grant_item(client, db_session):
    from app.models.user import User
    from app.models.character import Character
    from app.models.audit import AuditLog, EventType
    from app.models.equipment import Equipment, EquipmentType, EquipmentSlot, Inventory
    # Setup
    teacher, classroom = create_teacher_and_class(db_session)
    student1, student_profile1, character1 = create_student_with_character(db_session, classroom.id, name='StudentA', char_name='HeroA')
    student2, student_profile2, character2 = create_student_with_character(db_session, classroom.id, name='StudentB', char_name='HeroB')
    # Create equipment item
    equipment = Equipment(
        name='Test Sword',
        type=EquipmentType.WEAPON,
        slot=EquipmentSlot.MAIN_HAND,
        cost=100
    )
    db_session.add(equipment)
    db_session.commit()
    login(client, teacher.username, 'password123')
    # Perform batch grant-item
    resp = client.post('/teacher/api/teacher/characters/batch-action', json={
        'action': 'grant-item',
        'character_ids': [character1.id, character2.id],
        'item_id': equipment.id
    })
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['success']
    assert str(character1.id) in data['results']
    assert str(character2.id) in data['results']
    # Check inventory for both characters
    inv1 = Inventory.query.filter_by(character_id=character1.id, equipment_id=equipment.id).first()
    inv2 = Inventory.query.filter_by(character_id=character2.id, equipment_id=equipment.id).first()
    assert inv1 is not None
    assert inv2 is not None
    # Check audit log
    logs = AuditLog.query.filter_by(event_type=EventType.EQUIPMENT_CHANGE.value).order_by(AuditLog.event_timestamp.desc()).all()
    assert any('batch-grant-item' in (log.event_data.get('action') or '') for log in logs) 