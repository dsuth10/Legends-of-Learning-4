"""Legacy quest UI is retired; routes send people to Adventures."""

import uuid

from app.models.classroom import Classroom
from app.models.user import User, UserRole


def _teacher(db_session):
    unique = uuid.uuid4().hex[:8]
    user = User(
        username=f"retire_t_{unique}",
        email=f"retire_t_{unique}@example.com",
        role=UserRole.TEACHER,
    )
    user.set_password("password")
    db_session.add(user)
    db_session.commit()
    classroom = Classroom(
        name=f"Retire {unique[:4]}",
        teacher_id=user.id,
        join_code=f"R{unique[:6]}",
    )
    db_session.add(classroom)
    db_session.commit()
    return user


def test_teacher_quest_pages_redirect_to_adventures(client, db_session):
    teacher = _teacher(db_session)
    client.post(
        "/auth/login",
        data={"username": teacher.username, "password": "password"},
        follow_redirects=True,
    )
    resp = client.get("/teacher/quests/", follow_redirects=False)
    assert resp.status_code in (301, 302)
    assert "/teacher/adventures" in (resp.headers.get("Location") or "")


def test_student_quest_page_redirects_to_adventures(client, db_session):
    from app.models.student import Student

    unique = uuid.uuid4().hex[:8]
    teacher = _teacher(db_session)
    user = User(
        username=f"retire_s_{unique}",
        email=f"retire_s_{unique}@example.com",
        role=UserRole.STUDENT,
    )
    user.set_password("password")
    db_session.add(user)
    db_session.flush()
    db_session.add(Student(user_id=user.id, class_id=Classroom.query.filter_by(teacher_id=teacher.id).first().id))
    db_session.commit()
    client.post(
        "/auth/login",
        data={"username": user.username, "password": "password"},
        follow_redirects=True,
    )
    resp = client.get("/student/quests", follow_redirects=False)
    assert resp.status_code in (301, 302)
    assert "/student/adventures" in (resp.headers.get("Location") or "")
