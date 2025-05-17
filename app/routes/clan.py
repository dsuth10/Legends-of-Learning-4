from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, current_user
from app.models.clan import Clan
from app.models.clan_progress import ClanProgressHistory
from app.services.clan_metrics import calculate_clan_metrics, calculate_percentile_rankings
from app import db
from datetime import datetime, timedelta

clan_api = Blueprint('clan_api', __name__)

@clan_api.route('/clans/<int:clan_id>/metrics', methods=['GET'])
@jwt_required()
def get_clan_metrics(clan_id):
    metrics = calculate_clan_metrics(clan_id)
    if not metrics:
        return jsonify({'error': 'Clan not found'}), 404
    return jsonify(metrics)

@clan_api.route('/clans/<int:clan_id>/history', methods=['GET'])
@jwt_required()
def get_clan_history(clan_id):
    days = request.args.get('days', 30, type=int)
    cutoff = datetime.utcnow() - timedelta(days=days)
    history = ClanProgressHistory.query.filter(
        ClanProgressHistory.clan_id == clan_id,
        ClanProgressHistory.timestamp >= cutoff
    ).order_by(ClanProgressHistory.timestamp).all()
    return jsonify([
        {
            'timestamp': h.timestamp.isoformat(),
            'avg_completion_rate': h.avg_completion_rate,
            'total_points': h.total_points,
            'active_members': h.active_members,
            'avg_daily_points': h.avg_daily_points,
            'quest_completion_rate': h.quest_completion_rate,
            'avg_member_level': h.avg_member_level,
            'percentile_rank': h.percentile_rank
        } for h in history
    ])

@clan_api.route('/classes/<int:class_id>/clan-leaderboard', methods=['GET'])
@jwt_required()
def get_clan_leaderboard_for_class(class_id):
    # Optionally: check current_user has access to this class
    percentiles = calculate_percentile_rankings(class_id=class_id)
    clans = Clan.query.filter_by(class_id=class_id).all()
    leaderboard = []
    for clan in clans:
        metrics = calculate_clan_metrics(clan.id)
        latest = ClanProgressHistory.query.filter_by(clan_id=clan.id).order_by(ClanProgressHistory.timestamp.desc()).first()
        leaderboard.append({
            'id': clan.id,
            'name': clan.name,
            'total_points': metrics['total_points'] if metrics else 0,
            'avg_completion_rate': metrics['avg_completion_rate'] if metrics else 0,
            'percentile_rank': percentiles.get(clan.id, 0),
            'rank': None  # Will be set after sorting
        })
    # Sort by total_points descending
    leaderboard.sort(key=lambda x: x['total_points'], reverse=True)
    for idx, entry in enumerate(leaderboard):
        entry['rank'] = idx + 1
    return jsonify({'clans': leaderboard})

@clan_api.route('/clans/<int:clan_id>/trend-data', methods=['GET'])
@jwt_required()
def get_clan_trend_data(clan_id):
    days = request.args.get('days', 30, type=int)
    metric = request.args.get('metric', 'total_points')
    cutoff = datetime.utcnow() - timedelta(days=days)
    history = ClanProgressHistory.query.filter(
        ClanProgressHistory.clan_id == clan_id,
        ClanProgressHistory.timestamp >= cutoff
    ).order_by(ClanProgressHistory.timestamp).all()
    return jsonify({
        'labels': [h.timestamp.strftime('%Y-%m-%d') for h in history],
        'data': [getattr(h, metric, None) for h in history]
    })

# To use: register clan_api blueprint in your app factory or main app
# from app.routes.clan import clan_api
# app.register_blueprint(clan_api) 