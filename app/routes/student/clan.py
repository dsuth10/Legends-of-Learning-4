from app.models.achievement_badge import AchievementBadge

# In the endpoint that returns the clan object, add:
    clan_data = clan.to_dict(include_members=True, include_metrics=True)
    clan_data["badges"] = [
        {"id": b.id, "name": b.name, "description": b.description, "icon": b.icon}
        for b in clan.badges
    ]
    return jsonify({"success": True, "clan": clan_data}) 