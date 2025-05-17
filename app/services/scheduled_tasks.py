from app import db, celery
from app.models.clan import Clan
from app.models.clan_progress import ClanProgressHistory
from app.services.clan_metrics import calculate_clan_metrics, calculate_percentile_rankings
from datetime import datetime

@celery.task
def update_clan_metrics():
    """Daily job to calculate and store clan metrics for all clans."""
    clans = Clan.query.all()
    for clan in clans:
        metrics = calculate_clan_metrics(clan.id)
        if not metrics:
            continue
        history = ClanProgressHistory(
            clan_id=clan.id,
            timestamp=datetime.utcnow(),
            avg_completion_rate=metrics['avg_completion_rate'],
            total_points=metrics['total_points'],
            active_members=metrics['active_members'],
            avg_daily_points=metrics['avg_daily_points'],
            quest_completion_rate=metrics['quest_completion_rate'],
            avg_member_level=metrics['avg_member_level']
        )
        db.session.add(history)
    # Update percentile rankings
    class_percentiles = calculate_percentile_rankings()
    for clan_id, percentile in class_percentiles.items():
        latest_history = ClanProgressHistory.query.filter_by(clan_id=clan_id).order_by(ClanProgressHistory.timestamp.desc()).first()
        if latest_history:
            latest_history.percentile_rank = percentile
    db.session.commit()

# To schedule this task daily, add to your Celery beat schedule (example):
# CELERY_BEAT_SCHEDULE = {
#     'update-clan-metrics-daily': {
#         'task': 'app.services.scheduled_tasks.update_clan_metrics',
#         'schedule': crontab(hour=0, minute=0),
#     },
# } 