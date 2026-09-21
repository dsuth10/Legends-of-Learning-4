"""HTML chrome contracts for the shared student shell (spec 004)."""
import uuid

from app.models.ability import Ability, CharacterAbility
from app.models.character import Character
from app.models.classroom import Classroom
from app.models.clan import Clan
from app.models.student import Student
from app.models.user import User, UserRole
from app.services.student_chrome import power_icon_for_ability


DESTINATIONS = [
    b"Character",
    b"Quests",
    b"Shop",
    b"Equipment",
    b"Adventures",
    b"Progress",
    b"Powers",
]

CHROME_PAGES = [
    ("/student/character", "student.character"),
    ("/student/quests", "student.quests"),
    ("/student/shop", "student.shop"),
    ("/student/equipment", "student.equipment"),
    ("/student/adventures/", "adventures_student.list_adventures"),
    ("/student/progress", "student.progress"),
    ("/student/powers", "student.powers"),
    ("/student/clan", "student.clan"),
    ("/student/profile", "student.profile"),
]

FORBIDDEN_ACTIONS = [
    b"Special Offer",
    b"Auto Equip",
    b"Save Loadout",
    b"Filter Quests",
    b"Click to Rotate",
]


def _login(client, username, password="password"):
    return client.post(
        "/auth/login",
        data={"username": username, "password": password},
        follow_redirects=True,
    )


def _make_teacher(db_session):
    unique = uuid.uuid4().hex[:8]
    teacher = User(
        username=f"shell_t_{unique}",
        email=f"shell_t_{unique}@example.com",
        role=UserRole.TEACHER,
        first_name="Shell",
        last_name="Teacher",
    )
    teacher.set_password("password")
    db_session.add(teacher)
    db_session.flush()
    classroom = Classroom(
        name=f"Arcane Hall {unique[:4]}",
        teacher_id=teacher.id,
        join_code=f"SH{unique[:6]}",
    )
    db_session.add(classroom)
    db_session.commit()
    return teacher, classroom


def _make_student(db_session, classroom, name="ShellStudent", with_character=True, clan=None):
    unique = uuid.uuid4().hex[:8]
    user = User(
        username=f"{name.lower()}_{unique}",
        email=f"{name.lower()}_{unique}@example.com",
        role=UserRole.STUDENT,
        first_name=name,
        last_name="Test",
    )
    user.set_password("password")
    db_session.add(user)
    db_session.flush()
    profile = Student(user_id=user.id, class_id=classroom.id, level=1, gold=50)
    db_session.add(profile)
    db_session.flush()
    character = None
    if with_character:
        character = Character(
            name=f"{name} Hero",
            student_id=profile.id,
            character_class="Warrior",
            level=2,
            experience=250,
            health=80,
            max_health=100,
            power=6,
            max_power=10,
            power_points=3,
            gold=42,
            defense=10,
            is_active=True,
            clan_id=clan.id if clan else None,
        )
        db_session.add(character)
        db_session.flush()
    db_session.commit()
    return user, profile, character


def test_power_icon_map_uses_type_and_special_effect():
    assert power_icon_for_ability({"type": "attack"}) == "swords"
    assert power_icon_for_ability({"type": "heal", "special_effect": "revive"}) == "emergency"
    assert power_icon_for_ability({"type": "heal", "special_effect": "cheat_death"}) == "health_and_safety"
    assert power_icon_for_ability({"type": "utility"}) == "auto_fix"


def test_in_scope_pages_include_shared_chrome(client, db_session):
    teacher, classroom = _make_teacher(db_session)
    clan = Clan(name="Oak Guard", class_id=classroom.id)
    db_session.add(clan)
    db_session.commit()
    user, _profile, _character = _make_student(
        db_session, classroom, name="Chrome", clan=clan
    )
    _login(client, user.username)

    for path, endpoint in CHROME_PAGES:
        response = client.get(path)
        assert response.status_code == 200, path
        html = response.data
        for label in DESTINATIONS:
            assert label in html, f"{path} missing {label!r}"
        assert b'data-student-chrome="identity"' in html
        assert b'data-student-chrome="strip"' in html
        assert b'data-student-chrome="stats"' in html
        assert b'data-student-chrome="destinations"' in html
        assert b"HP" in html
        assert b"Power" in html
        assert b"Gold" in html or b"GP" in html
        assert classroom.name.encode() in html
        assert b"Oak Guard" in html
        assert b'aria-current="page"' in html
        if endpoint in (
            "student.character",
            "student.quests",
            "student.shop",
            "student.equipment",
            "adventures_student.list_adventures",
            "student.progress",
            "student.powers",
        ):
            assert html.count(b'aria-current="page"') >= 1


def test_clanless_student_gets_classroom_strip_and_single_tab(client, db_session):
    _teacher, classroom = _make_teacher(db_session)
    user, _profile, character = _make_student(
        db_session, classroom, name="Solo", clan=None
    )
    _login(client, user.username)
    response = client.get("/student/character")
    assert response.status_code == 200
    html = response.data
    assert classroom.name.encode() in html
    assert html.count(b'data-clan-tab="current"') == 1
    assert b'data-clan-tab="mate"' not in html
    assert character.name.encode() in html
    assert b'data-student-chrome="party"' not in html


def test_create_character_has_visual_language_without_fabricated_hp(client, db_session):
    _teacher, classroom = _make_teacher(db_session)
    user, _profile, _character = _make_student(
        db_session, classroom, name="Newcomer", with_character=False
    )
    _login(client, user.username)
    response = client.get("/student/character/create")
    assert response.status_code == 200
    html = response.data
    assert b"Create" in html
    assert classroom.name.encode() in html
    assert b'data-student-chrome="identity"' in html
    assert b'data-student-chrome="stats"' not in html
    assert b'data-clan-tab=' not in html


def test_forbidden_placeholder_actions_are_absent(client, db_session):
    _teacher, classroom = _make_teacher(db_session)
    user, _profile, _character = _make_student(db_session, classroom, name="Honest")
    _login(client, user.username)
    for path in (
        "/student/character",
        "/student/quests",
        "/student/shop",
        "/student/equipment",
    ):
        html = client.get(path).data
        for forbidden in FORBIDDEN_ACTIONS:
            assert forbidden not in html, f"{path} still contains {forbidden!r}"
        assert b">article<" not in html


def test_character_identity_powers_and_no_solo_party(client, db_session):
    _teacher, classroom = _make_teacher(db_session)
    clan = Clan(name="Twin Stars", class_id=classroom.id)
    db_session.add(clan)
    db_session.commit()
    user, _profile, character = _make_student(
        db_session, classroom, name="Caster", clan=clan
    )
    ability = Ability(
        name="Oakbolt",
        type="attack",
        description="A test attack",
        power=8,
        cost=1,
        tier="basic",
    )
    db_session.add(ability)
    db_session.flush()
    link = CharacterAbility(
        character_id=character.id, ability_id=ability.id, is_equipped=True
    )
    db_session.add(link)
    db_session.commit()

    _login(client, user.username)
    html = client.get("/student/character").data
    assert classroom.name.encode() in html
    assert b"Twin Stars" in html
    assert b"Oakbolt" in html
    assert b"swords" in html
    assert b"Empty" in html
    assert b'data-student-chrome="party"' not in html
    identity_start = html.find(b'data-student-chrome="identity"')
    identity_end = html.find(b'data-student-chrome="strip"')
    identity = html[identity_start:identity_end]
    assert classroom.name.encode() in identity
    assert b"Twin Stars" in identity
    assert b", " not in identity
