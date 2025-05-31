from app import create_app
from app.models import db
from app.models.achievement_badge import AchievementBadge

app = create_app()

with app.app_context():
    # Delete all existing badges
    AchievementBadge.query.delete()
    db.session.commit()
    # Seed new badges
    badge_data = [
        {"name": f"Achievement {i}", "description": f"Achievement {i} unlocked!", "icon": f"/static/images/badges/achieve{i}.png", "is_clan": True, "is_student": False}
        for i in range(1, 7)
    ]
    for b in badge_data:
        db.session.add(AchievementBadge(**b))
    db.session.commit()
    print("Badges seeded!") 