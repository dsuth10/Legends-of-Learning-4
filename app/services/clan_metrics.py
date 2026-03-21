from datetime import datetime, timedelta
from sqlalchemy import func, case
from app.models.clan import Clan
from app.models.student import Student
from app.models.character import Character
from app.models.clan_progress import ClanProgressHistory
# Quest assignment tracking uses QuestLog (no separate QuestAssignment model in repo)
from app.models.quest import QuestLog as QuestAssignment, QuestStatus
from app.models import db
from app.models.audit import AuditLog
from sqlalchemy import and_

# Registry for custom metrics
CUSTOM_METRICS = {}

def register_custom_metric(name, calculation_func, description=None):
    """Register a custom clan metric"""
    CUSTOM_METRICS[name] = {
        'func': calculation_func,
        'description': description or f"Custom metric: {name}"
    }

def _is_quest_completed(status):
    if status == QuestStatus.COMPLETED:
        return True
    val = getattr(status, 'value', status)
    return val == 'completed'


def calculate_avg_completion_rate(clan):
    """Calculate the average quest completion rate for clan members"""
    members = Student.query.filter_by(clan_id=clan.id).all()
    if not members:
        return 0.0
    student_ids = [m.id for m in members]
    characters = Character.query.filter(Character.student_id.in_(student_ids)).all()
    if not characters:
        return 0.0
    char_ids = [c.id for c in characters]
    rows = (
        db.session.query(
            QuestAssignment.character_id,
            func.count(QuestAssignment.id).label('total'),
            func.sum(
                case((QuestAssignment.status == QuestStatus.COMPLETED, 1), else_=0)
            ).label('done'),
        )
        .filter(QuestAssignment.character_id.in_(char_ids))
        .group_by(QuestAssignment.character_id)
        .all()
    )
    agg = {r.character_id: (r.done or 0, r.total or 0) for r in rows}
    completion_rates = []
    for char in characters:
        done, total = agg.get(char.id, (0, 0))
        if total == 0:
            continue
        completion_rates.append(done / total)
    return sum(completion_rates) / len(completion_rates) if completion_rates else 0.0

def calculate_total_points(clan):
    """Calculate total points earned by all clan members"""
    return (db.session.query(func.sum(Character.experience))
        .join(Student, Student.id == Character.student_id)
        .filter(Student.clan_id == clan.id)
        .scalar() or 0)

def calculate_active_members(clan, days=7):
    """Count members with activity in the last N days"""
    cutoff = datetime.utcnow() - timedelta(days=days)
    return (db.session.query(func.count(Student.id))
        .filter(Student.clan_id == clan.id, Student.last_activity >= cutoff)
        .scalar() or 0)

def calculate_avg_daily_points(clan, days=7):
    """Calculate average daily points earned by clan in the last N days using AuditLog XP_GAIN events."""
    cutoff = datetime.utcnow() - timedelta(days=days)
    # Get all character IDs in the clan
    character_ids = [char.id for char in clan.members]
    if not character_ids:
        return 0.0
    # Query all XP_GAIN events for these characters in the time window
    logs = (
        AuditLog.query
        .filter(
            AuditLog.event_type == 'XP_GAIN',
            AuditLog.character_id.in_(character_ids),
            AuditLog.event_timestamp >= cutoff
        )
        .all()
    )
    # Sum XP gained from event_data (assume event_data['amount'] or event_data['xp'])
    total_xp = 0
    for log in logs:
        data = log.event_data
        if isinstance(data, dict):
            if 'amount' in data:
                total_xp += data['amount']
            elif 'xp' in data:
                total_xp += data['xp']
    return total_xp / days if days > 0 else 0.0

def calculate_quest_completion_rate(clan):
    """Calculate the ratio of completed quests to assigned quests"""
    members = Student.query.filter_by(clan_id=clan.id).all()
    if not members:
        return 0.0
    student_ids = [m.id for m in members]
    char_ids = [
        c.id
        for c in Character.query.filter(Character.student_id.in_(student_ids)).all()
    ]
    if not char_ids:
        return 0.0
    assignments = QuestAssignment.query.filter(QuestAssignment.character_id.in_(char_ids)).all()
    if not assignments:
        return 0.0
    completed = sum(1 for a in assignments if _is_quest_completed(a.status))
    return completed / len(assignments)

def calculate_avg_member_level(clan):
    """Calculate average level of clan members"""
    levels = db.session.query(Character.level).join(
        Student, Student.id == Character.student_id
    ).filter(Student.clan_id == clan.id).all()
    if not levels:
        return 0.0
    return sum(level[0] for level in levels) / len(levels)

def calculate_clan_metrics(clan_id, include_custom=True):
    """Calculate all metrics for a specific clan"""
    clan = Clan.query.get(clan_id)
    if not clan:
        return None
    metrics = {
        'avg_completion_rate': calculate_avg_completion_rate(clan),
        'total_points': calculate_total_points(clan),
        'active_members': calculate_active_members(clan),
        'avg_daily_points': calculate_avg_daily_points(clan),
        'quest_completion_rate': calculate_quest_completion_rate(clan),
        'avg_member_level': calculate_avg_member_level(clan)
    }
    if include_custom:
        for name, metric_info in CUSTOM_METRICS.items():
            metrics[name] = metric_info['func'](clan_id)
    return metrics

def calculate_percentile_rankings(class_id=None, school_id=None):
    """Calculate percentile rankings for clans within a class or school"""
    if school_id:
        # Student model has no school_id; extend when multi-school support exists
        return {}
    query = (
        db.session.query(
            Clan.id,
            func.sum(Character.experience).label('total_points'),
        )
        .select_from(Clan)
        .join(Student, Student.clan_id == Clan.id)
        .join(Character, Character.student_id == Student.id)
        .group_by(Clan.id)
    )
    if class_id is not None:
        query = query.filter(Clan.class_id == class_id)
    results = query.all()
    sorted_clans = sorted(results, key=lambda x: x.total_points or 0, reverse=True)
    total_clans = len(sorted_clans)
    if total_clans == 0:
        return {}
    percentiles = {}
    for i, clan_data in enumerate(sorted_clans):
        percentile = 100 - int((i / total_clans) * 100)
        percentiles[clan_data.id] = percentile
    return percentiles 