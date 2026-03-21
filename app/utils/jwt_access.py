"""Authorization helpers for JWT-authenticated API routes."""
from __future__ import annotations

from app.models import db
from app.models.clan import Clan
from app.models.classroom import Classroom
from app.models.student import Student
from app.models.user import User, UserRole


def user_can_access_clan(user_id: int, clan_id: int) -> bool:
    """True if the user may read clan metrics/history (teacher of class or student in class)."""
    user = db.session.get(User, user_id)
    clan = db.session.get(Clan, clan_id)
    if not user or not clan:
        return False
    classroom = clan.class_
    if not classroom:
        return False
    if user.role == UserRole.TEACHER and classroom.teacher_id == user.id:
        return True
    if user.role == UserRole.STUDENT:
        student = Student.query.filter_by(user_id=user.id).first()
        return bool(student and student.class_id == classroom.id)
    if user.role == UserRole.ADMIN:
        return True
    return False


def user_can_access_class_for_clan_api(user_id: int, class_id: int) -> bool:
    """True if user may access class-level clan leaderboard data."""
    user = db.session.get(User, user_id)
    if not user:
        return False
    classroom = db.session.get(Classroom, class_id)
    if not classroom:
        return False
    if user.role == UserRole.TEACHER and classroom.teacher_id == user.id:
        return True
    if user.role == UserRole.STUDENT:
        student = Student.query.filter_by(user_id=user.id).first()
        return bool(student and student.class_id == class_id)
    if user.role == UserRole.ADMIN:
        return True
    return False


# Whitelist for trend / history metric column names on ClanProgressHistory
CLAN_HISTORY_METRIC_FIELDS = frozenset({
    'avg_completion_rate',
    'total_points',
    'active_members',
    'avg_daily_points',
    'quest_completion_rate',
    'avg_member_level',
    'percentile_rank',
})


def clamp_history_days(days: int | None, default: int = 30, max_days: int = 366) -> int:
    if days is None:
        return default
    try:
        d = int(days)
    except (TypeError, ValueError):
        return default
    return max(1, min(d, max_days))
