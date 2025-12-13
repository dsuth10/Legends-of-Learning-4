"""Analytics service for aggregating and processing analytics data."""

from app.models import db
from app.models.classroom import Classroom
from app.models.student import Student
from app.models.character import Character
from app.models.quest import QuestLog, QuestStatus
from app.models.audit import AuditLog, EventType
from app.models.shop import ShopPurchase
from datetime import datetime, timedelta
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)


def get_student_performance_data(classroom_id, student_id=None, days=90):
    """Get performance data for students in a classroom.
    
    Args:
        classroom_id: ID of the classroom
        student_id: Optional specific student ID, otherwise all students
        days: Number of days to look back
        
    Returns:
        dict: Performance data including XP progression, quest completion, etc.
    """
    since = datetime.utcnow() - timedelta(days=days)
    
    # Get students
    if student_id:
        students = Student.query.filter_by(id=student_id, class_id=classroom_id).all()
    else:
        students = Student.query.filter_by(class_id=classroom_id).all()
    
    if not students:
        return {'students': [], 'class_average': {}}
    
    student_data = []
    total_xp = 0
    total_quests_completed = 0
    total_quests_assigned = 0
    total_gold_earned = 0
    total_gold_spent = 0
    total_logins = 0
    
    for student in students:
        character = student.characters.filter_by(is_active=True).first()
        if not character:
            continue
        
        # XP progression over time
        xp_events = AuditLog.query.filter(
            AuditLog.character_id == character.id,
            AuditLog.event_type.in_([EventType.XP_GAIN.value, EventType.XP_TRANSACTION.value]),
            AuditLog.event_timestamp >= since
        ).order_by(AuditLog.event_timestamp.asc()).all()
        
        xp_by_date = defaultdict(int)
        for event in xp_events:
            event_date = event.event_timestamp.date()
            amount = event.event_data.get('amount', 0) if isinstance(event.event_data, dict) else 0
            xp_by_date[event_date] += amount
        
        # Quest completion stats
        quest_logs = character.quest_logs.all()
        completed_quests = [q for q in quest_logs if q.status == QuestStatus.COMPLETED]
        total_quests = len(quest_logs)
        
        # Gold transactions
        gold_earned_events = AuditLog.query.filter(
            AuditLog.character_id == character.id,
            AuditLog.event_type == EventType.GOLD_TRANSACTION.value,
            AuditLog.event_timestamp >= since
        ).all()
        
        gold_earned = sum(
            event.event_data.get('amount', 0) 
            for event in gold_earned_events 
            if isinstance(event.event_data, dict) and event.event_data.get('amount', 0) > 0
        )
        
        gold_spent = ShopPurchase.query.filter(
            ShopPurchase.character_id == character.id,
            ShopPurchase.purchase_date >= since
        ).with_entities(db.func.sum(ShopPurchase.gold_spent)).scalar() or 0
        
        # Login frequency
        login_events = AuditLog.query.filter(
            AuditLog.user_id == student.user_id,
            AuditLog.event_type.in_([EventType.LOGIN.value, EventType.USER_LOGIN.value]),
            AuditLog.event_timestamp >= since
        ).count()
        
        student_data.append({
            'student_id': student.id,
            'user_id': student.user_id,
            'character_id': character.id,
            'name': character.name if character else f"Student {student.id}",
            'level': character.level,
            'experience': character.experience,
            'gold': character.gold,
            'quests_completed': len(completed_quests),
            'quests_total': total_quests,
            'quest_completion_rate': (len(completed_quests) / total_quests * 100) if total_quests > 0 else 0,
            'gold_earned': gold_earned,
            'gold_spent': gold_spent,
            'login_count': login_events,
            'xp_progression': {
                'dates': sorted(xp_by_date.keys()),
                'xp_values': [xp_by_date[d] for d in sorted(xp_by_date.keys())]
            }
        })
        
        total_xp += character.experience
        total_quests_completed += len(completed_quests)
        total_quests_assigned += total_quests
        total_gold_earned += gold_earned
        total_gold_spent += gold_spent
        total_logins += login_events
    
    num_students = len(student_data)
    if num_students == 0:
        return {'students': [], 'class_average': {}}
    
    class_average = {
        'avg_level': total_xp / num_students / 1000 + 1 if total_xp > 0 else 1,  # Approximate level from XP
        'avg_quest_completion_rate': (total_quests_completed / total_quests_assigned * 100) if total_quests_assigned > 0 else 0,
        'avg_gold_earned': total_gold_earned / num_students,
        'avg_gold_spent': total_gold_spent / num_students,
        'avg_logins': total_logins / num_students,
        'total_students': num_students
    }
    
    return {
        'students': student_data,
        'class_average': class_average
    }


def get_engagement_metrics(classroom_id, days=30):
    """Get engagement metrics for a classroom.
    
    Args:
        classroom_id: ID of the classroom
        days: Number of days to analyze
        
    Returns:
        dict: Engagement metrics including activity patterns
    """
    since = datetime.utcnow() - timedelta(days=days)
    
    students = Student.query.filter_by(class_id=classroom_id).all()
    if not students:
        return {'daily_activity': [], 'event_types': {}}
    
    # Get all audit logs for students in this class
    user_ids = [s.user_id for s in students]
    character_ids = []
    for student in students:
        character = student.characters.filter_by(is_active=True).first()
        if character:
            character_ids.append(character.id)
    
    # Daily activity
    daily_activity = defaultdict(int)
    event_types = defaultdict(int)
    
    audit_logs = AuditLog.query.filter(
        db.or_(
            AuditLog.user_id.in_(user_ids),
            AuditLog.character_id.in_(character_ids)
        ),
        AuditLog.event_timestamp >= since
    ).all()
    
    for log in audit_logs:
        event_date = log.event_timestamp.date()
        daily_activity[event_date] += 1
        event_types[log.event_type] += 1
    
    return {
        'daily_activity': [
            {'date': str(date), 'count': count}
            for date, count in sorted(daily_activity.items())
        ],
        'event_types': dict(event_types)
    }


def get_quest_completion_analytics(classroom_id, days=90):
    """Get quest completion analytics for a classroom.
    
    Args:
        classroom_id: ID of the classroom
        days: Number of days to look back
        
    Returns:
        dict: Quest completion statistics
    """
    since = datetime.utcnow() - timedelta(days=days)
    
    students = Student.query.filter_by(class_id=classroom_id).all()
    if not students:
        return {'quest_stats': [], 'completion_timeline': []}
    
    character_ids = []
    for student in students:
        character = student.characters.filter_by(is_active=True).first()
        if character:
            character_ids.append(character.id)
    
    if not character_ids:
        return {'quest_stats': [], 'completion_timeline': []}
    
    # Quest completion timeline
    completed_quests = QuestLog.query.filter(
        QuestLog.character_id.in_(character_ids),
        QuestLog.status == QuestStatus.COMPLETED,
        QuestLog.completed_at >= since
    ).all()
    
    completion_by_date = defaultdict(int)
    for quest_log in completed_quests:
        if quest_log.completed_at:
            completion_date = quest_log.completed_at.date()
            completion_by_date[completion_date] += 1
    
    return {
        'completion_timeline': [
            {'date': str(date), 'count': count}
            for date, count in sorted(completion_by_date.items())
        ],
        'total_completed': len(completed_quests)
    }

