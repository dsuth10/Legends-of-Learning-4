"""Create, list, and authorise classroom, clan, and character adventure assignments."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from flask import url_for

from app.models import db
from app.models.adventure import Adventure, AdventureStatus
from app.models.adventure_progress import (
    AdventureAssignment,
    CharacterAdventureProgress,
)
from app.models.character import Character
from app.models.clan import Clan
from app.models.classroom import Classroom
from app.models.student import Student
from app.models.user import User
from app.services.adventure_graph import (
    AssignmentError,
    AuthorizationError,
    require_teacher_classroom,
)
from app.utils.date_utils import get_utc_now

EMPTY_CLAN_WARNING = (
    "This clan has no members yet, so no students will see the adventure "
    "until someone joins."
)


def assignment_target_type(assignment: AdventureAssignment) -> str:
    if assignment.classroom_id:
        return "classroom"
    if assignment.clan_id:
        return "clan"
    return "character"


def _student_display_name(student: Optional[Student]) -> str:
    if student is None:
        return ""
    user = student.user
    if user is None:
        return ""
    return user.get_display_name() if hasattr(user, "get_display_name") else (
        user.display_name or user.username
    )


def assignment_target_label(assignment: AdventureAssignment) -> str:
    if assignment.classroom_id:
        classroom = db.session.get(Classroom, assignment.classroom_id)
        return classroom.name if classroom else f"Class #{assignment.classroom_id}"
    if assignment.clan_id:
        clan = db.session.get(Clan, assignment.clan_id)
        return clan.name if clan else f"Clan #{assignment.clan_id}"
    if assignment.character_id:
        character = db.session.get(Character, assignment.character_id)
        if character:
            student_name = _student_display_name(character.student)
            if student_name and student_name != character.name:
                return f"{character.name} ({student_name})"
            return character.name
        return f"Character #{assignment.character_id}"
    return "Unknown"


def clan_member_count(clan_id: int) -> int:
    return Character.query.filter_by(clan_id=clan_id, is_active=True).count()


def assignment_progress_url(assignment: AdventureAssignment) -> str:
    if assignment.classroom_id:
        return url_for(
            "adventures_teacher.adventure_progress",
            adventure_id=assignment.adventure_id,
            classroom_id=assignment.classroom_id,
        )
    return url_for(
        "adventures_teacher.adventure_progress",
        adventure_id=assignment.adventure_id,
        assignment_id=assignment.id,
    )


def _require_clan_owned_by_teacher(teacher: User, clan_id: int) -> Clan:
    clan = db.session.get(Clan, clan_id)
    if clan is None:
        raise AuthorizationError("NOT_FOUND", "Clan not found.")
    require_teacher_classroom(teacher, clan.class_id)
    return clan


def _require_character_owned_by_teacher(teacher: User, character_id: int) -> Character:
    character = db.session.get(Character, character_id)
    if character is None or character.student is None:
        raise AuthorizationError("NOT_FOUND", "Character not found.")
    class_id = character.student.class_id
    if not class_id:
        raise AuthorizationError("FORBIDDEN", "You do not own this student's class.")
    require_teacher_classroom(teacher, class_id)
    return character


def _existing_active(
    adventure_id: int,
    *,
    classroom_id: Optional[int] = None,
    clan_id: Optional[int] = None,
    character_id: Optional[int] = None,
) -> Optional[AdventureAssignment]:
    query = AdventureAssignment.query.filter_by(
        adventure_id=adventure_id,
        is_active=True,
    )
    if classroom_id is not None:
        query = query.filter_by(classroom_id=classroom_id)
    elif clan_id is not None:
        query = query.filter_by(clan_id=clan_id)
    elif character_id is not None:
        query = query.filter_by(character_id=character_id)
    else:
        return None
    return query.first()


def create_adventure_assignment(
    adventure: Adventure,
    teacher: User,
    *,
    classroom_id: Optional[int] = None,
    clan_id: Optional[int] = None,
    character_id: Optional[int] = None,
    starts_at=None,
    ends_at=None,
) -> Tuple[AdventureAssignment, List[str]]:
    """Create one active assignment. Returns (assignment, warnings)."""
    if adventure.status != AdventureStatus.PUBLISHED.value:
        raise AssignmentError("CONFLICT", "Only published adventures can be assigned.")

    targets = [classroom_id, clan_id, character_id]
    if sum(1 for t in targets if t is not None) != 1:
        raise AssignmentError(
            "VALIDATION_ERROR",
            "exactly one of classroom_id, clan_id, character_id is required",
        )

    warnings: List[str] = []
    if classroom_id is not None:
        require_teacher_classroom(teacher, classroom_id)
        if _existing_active(adventure.id, classroom_id=classroom_id):
            raise AssignmentError(
                "CONFLICT",
                "This adventure is already assigned to that classroom.",
            )
    elif clan_id is not None:
        clan = _require_clan_owned_by_teacher(teacher, clan_id)
        if _existing_active(adventure.id, clan_id=clan_id):
            raise AssignmentError(
                "CONFLICT",
                "This adventure is already assigned to that clan.",
            )
        if clan_member_count(clan.id) == 0:
            warnings.append(EMPTY_CLAN_WARNING)
    else:
        _require_character_owned_by_teacher(teacher, character_id)
        if _existing_active(adventure.id, character_id=character_id):
            raise AssignmentError(
                "CONFLICT",
                "This adventure is already assigned to that student.",
            )

    assignment = AdventureAssignment(
        adventure_id=adventure.id,
        adventure_version=adventure.version,
        classroom_id=classroom_id,
        clan_id=clan_id,
        character_id=character_id,
        assigned_by_user_id=teacher.id,
        starts_at=starts_at,
        ends_at=ends_at,
        is_active=True,
    )
    db.session.add(assignment)
    db.session.commit()
    return assignment, warnings


def list_active_assignments(adventure: Adventure) -> List[AdventureAssignment]:
    return (
        AdventureAssignment.query.filter_by(
            adventure_id=adventure.id,
            is_active=True,
        )
        .order_by(AdventureAssignment.id.asc())
        .all()
    )


def get_assignment_for_adventure(
    adventure: Adventure, assignment_id: int
) -> Optional[AdventureAssignment]:
    return AdventureAssignment.query.filter_by(
        id=assignment_id,
        adventure_id=adventure.id,
    ).first()


def list_assignment_targets(teacher: User, adventure: Adventure) -> Dict[str, Any]:
    classrooms = Classroom.query.filter_by(teacher_id=teacher.id, is_active=True).all()
    class_ids = [c.id for c in classrooms]
    active = list_active_assignments(adventure)
    assigned_class = {a.classroom_id for a in active if a.classroom_id}
    assigned_clan = {a.clan_id for a in active if a.clan_id}
    assigned_char = {a.character_id for a in active if a.character_id}

    clans = []
    if class_ids:
        for clan in Clan.query.filter(Clan.class_id.in_(class_ids)).all():
            classroom = db.session.get(Classroom, clan.class_id)
            clans.append(
                {
                    "id": clan.id,
                    "name": clan.name,
                    "class_id": clan.class_id,
                    "class_name": classroom.name if classroom else "",
                    "member_count": clan_member_count(clan.id),
                    "already_assigned": clan.id in assigned_clan,
                }
            )

    characters = []
    if class_ids:
        students = Student.query.filter(Student.class_id.in_(class_ids)).all()
        student_by_id = {s.id: s for s in students}
        student_ids = list(student_by_id)
        if student_ids:
            for character in Character.query.filter(
                Character.student_id.in_(student_ids),
                Character.is_active.is_(True),
            ).all():
                student = student_by_id.get(character.student_id)
                classroom = db.session.get(Classroom, student.class_id) if student else None
                characters.append(
                    {
                        "id": character.id,
                        "name": character.name,
                        "student_name": _student_display_name(student),
                        "class_id": student.class_id if student else None,
                        "class_name": classroom.name if classroom else "",
                        "already_assigned": character.id in assigned_char,
                    }
                )

    return {
        "classrooms": [
            {
                "id": c.id,
                "name": c.name,
                "already_assigned": c.id in assigned_class,
            }
            for c in classrooms
        ],
        "clans": clans,
        "characters": characters,
    }


def started_assignment_still_active(
    character, adventure_id: int
) -> Optional[AdventureAssignment]:
    """Return the pinned assignment if the student already started and it is still active."""
    progress = CharacterAdventureProgress.query.filter_by(
        character_id=character.id,
        adventure_id=adventure_id,
    ).first()
    if progress is None or not progress.assignment_id:
        return None
    assignment = db.session.get(AdventureAssignment, progress.assignment_id)
    if assignment is None or not assignment.is_active:
        return None
    if assignment.adventure_id != adventure_id:
        return None
    now = get_utc_now()
    if assignment.starts_at and now < assignment.starts_at:
        return None
    if assignment.ends_at and now > assignment.ends_at:
        return None
    return assignment
