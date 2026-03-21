"""Tests for JWT clan API access control helpers."""
import uuid

import pytest

from app.utils.jwt_access import user_can_access_clan, user_can_access_class_for_clan_api


@pytest.fixture
def teacher_and_class(db_session):
    from app.models.user import User, UserRole
    from app.models.classroom import Classroom

    u = User(
        username=f"t_{uuid.uuid4().hex[:8]}",
        email=f"t_{uuid.uuid4().hex[:8]}@example.com",
        role=UserRole.TEACHER,
    )
    u.set_password("pw")
    db_session.add(u)
    db_session.commit()
    c = Classroom(
        name="JWT class",
        teacher_id=u.id,
        join_code=f"JC{uuid.uuid4().hex[:6]}",
    )
    db_session.add(c)
    db_session.commit()
    return u, c


def test_teacher_can_access_own_class_clan(db_session, teacher_and_class):
    from app.models.clan import Clan

    teacher, classroom = teacher_and_class
    clan = Clan(name="C", class_id=classroom.id)
    db_session.add(clan)
    db_session.commit()
    assert user_can_access_clan(teacher.id, clan.id) is True
    assert user_can_access_class_for_clan_api(teacher.id, classroom.id) is True


def test_teacher_cannot_access_other_class(db_session, teacher_and_class):
    from app.models.user import User, UserRole
    from app.models.classroom import Classroom
    from app.models.clan import Clan

    teacher, _ = teacher_and_class
    other = User(
        username=f"o_{uuid.uuid4().hex[:8]}",
        email=f"o_{uuid.uuid4().hex[:8]}@example.com",
        role=UserRole.TEACHER,
    )
    other.set_password("pw")
    db_session.add(other)
    db_session.commit()
    oc = Classroom(
        name="Other",
        teacher_id=other.id,
        join_code=f"OC{uuid.uuid4().hex[:6]}",
    )
    db_session.add(oc)
    db_session.commit()
    clan = Clan(name="Other clan", class_id=oc.id)
    db_session.add(clan)
    db_session.commit()
    assert user_can_access_clan(teacher.id, clan.id) is False
