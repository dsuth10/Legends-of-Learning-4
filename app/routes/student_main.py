from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user
from .teacher import student_required
from app.models import db
from app.models.character import Character
from app.models.equipment import Inventory, Equipment, EquipmentType, EquipmentSlot, TEST_ARMOR_IMAGE, TEST_RING_IMAGE, TEST_SWORD_IMAGE
from app.models.student import Student
from app.models.ability import Ability, CharacterAbility
from app.models.shop import ShopPurchase, PurchaseType
from app.models.quest import Quest, QuestLog, QuestStatus
from app.models.audit import AuditLog, EventType
from app.models.achievement_badge import AchievementBadge
from app.models.shop_config import ShopItemOverride
from datetime import datetime, timedelta
from collections import defaultdict
import time
import logging

logger = logging.getLogger(__name__)

student_bp = Blueprint('student', __name__, url_prefix='/student')

@student_bp.route('/dashboard')
@login_required
@student_required
def dashboard():
    """Student dashboard main view."""
    student_profile = Student.query.filter_by(user_id=current_user.id).first()
    classes = list(getattr(current_user, 'classes', []))
    main_character = None
    if student_profile:
        main_character = student_profile.characters.filter_by(is_active=True).first()
    clan = main_character.clan if main_character and main_character.clan else None
    active_quests = main_character.quest_logs.filter_by(status='in_progress').all() if main_character else []
    try:
        recent_activities = list(current_user.audit_logs.order_by(db.desc('event_timestamp')).limit(10))
    except Exception as e:
        # Handle case where audit_log table doesn't exist yet
        logger.warning(f"Could not query audit logs: {e}")
        recent_activities = []
    return render_template(
        'student/dashboard.html',
        student=current_user,
        student_profile=student_profile,
        classes=classes,
        main_character=main_character,
        clan=clan,
        active_quests=active_quests,
        recent_activities=recent_activities
    )

@student_bp.route('/profile')
@login_required
@student_required
def profile():
    return render_template('student/profile.html', student=current_user)

@student_bp.route('/quests')
@login_required
@student_required
def quests():
    student_profile = Student.query.filter_by(user_id=current_user.id).first()
    main_char = student_profile.characters.filter_by(is_active=True).first() if student_profile else None
    assigned_quests = []
    equipped_abilities = []
    ability_targets = []
    if main_char:
        for log in main_char.quest_logs:
            print("DEBUG QUESTLOG:", log.quest_id, log.status, type(log.status), log.id)
            quest = log.quest
            assigned_quests.append({
                'quest': quest,
                'status': log.status,
                'x': log.x_coordinate,
                'y': log.y_coordinate,
                'log': log
            })
        # Get equipped abilities for quest context
        equipped_abilities = [
            {
                'id': ca.ability.id,
                'name': ca.ability.name,
                'type': ca.ability.type,
                'description': ca.ability.description,
                'power': ca.ability.power,
                'cooldown': ca.ability.cooldown,
                'duration': ca.ability.duration,
                'last_used_at': ca.last_used_at.isoformat() if ca.last_used_at else None,
            }
            for ca in main_char.abilities.filter_by(is_equipped=True).all()
        ]
        # Get ability targets (clanmates)
        if main_char.clan:
            ability_targets = [
                {'id': member.id, 'name': member.name, 'character_class': member.character_class}
                for member in main_char.clan.members if member.id != main_char.id
            ]
    now = int(time.time())
    return render_template('student/quests.html', student=current_user, assigned_quests=assigned_quests, equipped_abilities=equipped_abilities, ability_targets=ability_targets, main_character=main_char, now=now)

@student_bp.route('/quests/start/<int:quest_id>', methods=['POST'])
@login_required
@student_required
def start_quest(quest_id):
    student_profile = Student.query.filter_by(user_id=current_user.id).first()
    main_char = student_profile.characters.filter_by(is_active=True).first() if student_profile else None
    quest = Quest.query.get_or_404(quest_id)
    if not main_char:
        flash('No active character found.', 'danger')
        return redirect(url_for('student.quests'))
    existing_log = QuestLog.query.filter_by(character_id=main_char.id, quest_id=quest.id).first()
    if existing_log:
        if existing_log.status == QuestStatus.NOT_STARTED:
            existing_log.status = QuestStatus.IN_PROGRESS
            db.session.commit()
            db.session.refresh(existing_log)
            print("AFTER REFRESH:", existing_log.status)
            print("DEBUG: All quest logs for character after start_quest:")
            for log in QuestLog.query.filter_by(character_id=main_char.id).all():
                print(log.quest_id, log.status, type(log.status), log.id)
            flash('Quest started!', 'success')
        elif existing_log.status == QuestStatus.IN_PROGRESS:
            flash('You have already started this quest.', 'info')
        elif existing_log.status == QuestStatus.COMPLETED:
            flash('You have already completed this quest.', 'info')
        else:
            flash('Quest already in progress or completed.', 'info')
        return redirect(url_for('student.quests'))
    # If no log exists, create a new one (should not happen with current assign flow)
    new_log = QuestLog(character_id=main_char.id, quest_id=quest.id, status=QuestStatus.IN_PROGRESS)
    db.session.add(new_log)
    db.session.commit()
    flash('Quest accepted!', 'success')
    return redirect(url_for('student.quests'))

@student_bp.route('/quests/complete/<int:quest_id>', methods=['POST'])
@login_required
@student_required
def complete_quest(quest_id):
    student_profile = Student.query.filter_by(user_id=current_user.id).first()
    main_char = student_profile.characters.filter_by(is_active=True).first() if student_profile else None
    if not main_char:
        flash('No active character found.', 'danger')
        return redirect(url_for('student.quests'))
    quest_log = QuestLog.query.filter_by(character_id=main_char.id, quest_id=quest_id).first()
    if not quest_log or quest_log.status != QuestStatus.IN_PROGRESS:
        flash('Quest not in progress or already completed.', 'warning')
        return redirect(url_for('student.quests'))
    try:
        logger.info(f"Completing quest: quest_id={quest_id}, character_id={main_char.id}")
        quest_log.complete_quest()
        # Refresh character to get updated gold/XP
        db.session.refresh(main_char)
        logger.info(f"Quest completed successfully: quest_id={quest_id}, character_id={main_char.id}, gold={main_char.gold}, level={main_char.level}")
        flash('Quest completed! Rewards granted.', 'success')
    except Exception as e:
        db.session.rollback()
        logger.error(f"Quest completion error: quest_id={quest_id}, character_id={main_char.id if main_char else None}, error={str(e)}", exc_info=True)
        flash(f'Error completing quest: {str(e)}', 'danger')
    return redirect(url_for('student.quests'))

@student_bp.route('/clan')
@login_required
@student_required
def clan():
    return render_template('student/clan.html', student=current_user)

@student_bp.route('/character')
@login_required
@student_required
def character():
    from datetime import datetime, timezone
    from app.models.character import StatusEffect
    
    student_profile = Student.query.filter_by(user_id=current_user.id).first()
    main_character = None
    equipped_abilities = []
    active_status_effects = []
    if student_profile:
        main_character = student_profile.characters.filter_by(is_active=True).first()
        if main_character:
            equipped_abilities = [
                {
                    'id': ca.ability.id,
                    'name': ca.ability.name,
                    'type': ca.ability.type,
                    'description': ca.ability.description,
                    'power': ca.ability.power,
                    'cooldown': ca.ability.cooldown,
                    'duration': ca.ability.duration,
                    'last_used_at': ca.last_used_at.isoformat() if ca.last_used_at else None,
                    'is_equipped': ca.is_equipped
                }
                for ca in main_character.abilities.filter_by(is_equipped=True).all()
            ]
            # Get active status effects
            now = datetime.now(timezone.utc).replace(tzinfo=None)
            active_effects = main_character.status_effects.filter(StatusEffect.expires_at > now).all()
            active_status_effects = [
                {
                    'effect_type': effect.effect_type,
                    'stat_affected': effect.stat_affected,
                    'amount': effect.amount,
                    'source': effect.source,
                    'expires_at': effect.expires_at,
                    'remaining_minutes': max(0, int((effect.expires_at - now).total_seconds() / 60))
                }
                for effect in active_effects
            ]
    now = int(time.time())
    ability_targets = []
    if main_character and main_character.clan:
        ability_targets = [
            {'id': member.id, 'name': member.name, 'character_class': member.character_class}
            for member in main_character.clan.members if member.id != main_character.id
        ]
    return render_template('student/character.html', student=current_user, main_character=main_character, equipped_abilities=equipped_abilities, now=now, ability_targets=ability_targets, active_status_effects=active_status_effects)

@student_bp.route('/shop')
@login_required
@student_required
def shop():
    student_profile = Student.query.filter_by(user_id=current_user.id).first()
    main_character = None
    owned_item_ids = set()
    owned_ability_ids = set()
    if student_profile:
        main_character = student_profile.characters.filter_by(is_active=True).first()
        if main_character:
            # Get owned item IDs
            owned_item_ids = set(inv.item_id for inv in main_character.inventory_items)
            # Get owned ability IDs
            if hasattr(main_character, 'abilities'):
                owned_ability_ids = set(a.ability_id for a in main_character.abilities)
    # Always define these, even if main_character is None
    char_gold = main_character.gold if main_character else 0
    char_level = main_character.level if main_character else 1
    char_class = main_character.character_class if main_character else ''
    # Query all items and abilities for the shop
    items = Equipment.query.all()
    ability_items = Ability.query.all()
    print(f"[DEBUG] Shop route: Equipment.query.all() count = {len(items)}")
    print(f"[DEBUG] Shop route: Ability.query.all() count = {len(ability_items)}")
    # Query overrides for the student's active classroom
    overrides_map = {}
    if main_character and student_profile:
        # Student has a direct relationship to one classroom via class_id
        # Use student_profile.classroom (singular) instead of classes
        active_class = student_profile.classroom
        if active_class and active_class.is_active:
            try:
                overrides = ShopItemOverride.query.filter_by(classroom_id=active_class.id).all()
                for ov in overrides:
                    overrides_map[(ov.item_type, ov.item_id)] = ov
            except Exception as e:
                # Handle case where shop_item_overrides table doesn't exist yet
                # This can happen if migrations haven't been run
                logger.warning(f"Could not query shop item overrides: {e}")
                overrides_map = {}

    items_list = []
    print(f"[DEBUG] Shop route: Equipment.query.all() count = {len(items)}")
    for eq in items:
        # Apply Overrides
        override = overrides_map.get(('equipment', eq.id))
        effective_cost = override.override_cost if override and override.override_cost is not None else eq.cost
        effective_level = override.override_level_req if override and override.override_level_req is not None else getattr(eq, 'level_requirement', 1)
        visible = override.is_visible if override else True
        
        if not visible:
            continue

        owned = eq.id in owned_item_ids
        can_afford = char_gold >= effective_cost
        unlocked = (char_level >= effective_level) and (not eq.class_restriction or eq.class_restriction.lower() == char_class.lower())
        can_buy = (not owned) and can_afford and unlocked
        
        items_list.append({
            'id': eq.id,
            'name': eq.name,
            'price': effective_cost,
            'original_price': eq.cost if effective_cost != eq.cost else None,
            'image': eq.image_url or '/static/images/default_item.png',
            'category': 'equipment',
            'tier': getattr(eq, 'rarity', 1),
            'description': eq.description or '',
            'level_requirement': effective_level,
            'original_level_requirement': getattr(eq, 'level_requirement', 1) if effective_level != getattr(eq, 'level_requirement', 1) else None,
            'class_restriction': getattr(eq, 'class_restriction', None),
            'owned': owned,
            'can_afford': can_afford,
            'unlocked': unlocked,
            'can_buy': can_buy,
        })
    
    for ab in ability_items:
        # Apply Overrides
        override = overrides_map.get(('ability', ab.id))
        effective_cost = override.override_cost if override and override.override_cost is not None else ab.cost
        effective_level = override.override_level_req if override and override.override_level_req is not None else getattr(ab, 'level_requirement', 1)
        visible = override.is_visible if override else True
        
        if not visible:
            continue

        owned = ab.id in owned_ability_ids
        can_afford = char_gold >= effective_cost
        unlocked = (char_level >= effective_level)
        can_buy = (not owned) and can_afford and unlocked
        
        items_list.append({
            'id': ab.id,
            'name': ab.name,
            'price': effective_cost,
            'original_price': ab.cost if effective_cost != ab.cost else None,
            'image': '/static/images/default_item.png',
            'category': 'ability',
            'tier': getattr(ab, 'tier', 1),
            'description': ab.description or '',
            'level_requirement': effective_level,
            'original_level_requirement': getattr(ab, 'level_requirement', 1) if effective_level != getattr(ab, 'level_requirement', 1) else None,
            'class_restriction': None,
            'owned': owned,
            'can_afford': can_afford,
            'unlocked': unlocked,
            'can_buy': can_buy,
        })
    return render_template('student/shop.html', student=current_user, main_character=main_character, items=items_list)

@student_bp.route('/progress')
@login_required
@student_required
def progress():
    """Student progress page with charts and statistics."""
    student_profile = Student.query.filter_by(user_id=current_user.id).first()
    main_character = None
    if student_profile:
        main_character = student_profile.characters.filter_by(is_active=True).first()
    
    # If no character, return empty data
    if not main_character:
        return render_template(
            'student/progress.html',
            student=current_user,
            main_character=None,
            summary_stats={},
            xp_chart_data={'dates': [], 'xp': []},
            level_chart_data={'dates': [], 'levels': []},
            gold_chart_data={'dates': [], 'earned': [], 'spent': []},
            quest_stats={},
            badges=[],
            recent_activities=[]
        )
    
    # Get date range (last 90 days)
    since = datetime.utcnow() - timedelta(days=90)
    
    # Summary statistics
    summary_stats = {
        'current_level': main_character.level,
        'total_xp': main_character.experience,
        'current_gold': main_character.gold,
        'total_quests_completed': main_character.quest_logs.filter_by(status=QuestStatus.COMPLETED).count()
    }
    
    # XP Progression Chart Data
    try:
        xp_events = AuditLog.query.filter(
            AuditLog.character_id == main_character.id,
            AuditLog.event_type == EventType.XP_GAIN.value,
            AuditLog.event_timestamp >= since
        ).order_by(AuditLog.event_timestamp.asc()).all()
        
        xp_by_date = defaultdict(int)
        cumulative_xp = 0
        for event in xp_events:
            try:
                event_date = event.event_timestamp.date() if event.event_timestamp else datetime.utcnow().date()
                amount = event.event_data.get('amount', 0) if isinstance(event.event_data, dict) else 0
                cumulative_xp += amount
                xp_by_date[event_date] = cumulative_xp
            except (AttributeError, TypeError):
                continue
        
        # Ensure we have initial state
        if main_character.created_at:
            try:
                initial_date = main_character.created_at.date()
                if initial_date not in xp_by_date:
                    xp_by_date[initial_date] = 0
            except (AttributeError, TypeError):
                pass
        
        # Add current XP if not in history
        today = datetime.utcnow().date()
        if today not in xp_by_date:
            xp_by_date[today] = main_character.experience
        
        xp_dates = sorted(xp_by_date.keys())
        xp_values = [xp_by_date[d] for d in xp_dates]
        
        xp_chart_data = {
            'dates': [d.strftime('%Y-%m-%d') for d in xp_dates],
            'xp': xp_values
        }
    except Exception as e:
        logger.error(f"Error processing XP chart data: {str(e)}", exc_info=True)
        xp_chart_data = {'dates': [], 'xp': []}
    
    # Level Progression Timeline
    try:
        level_events = AuditLog.query.filter(
            AuditLog.character_id == main_character.id,
            AuditLog.event_type == EventType.LEVEL_UP.value
        ).order_by(AuditLog.event_timestamp.asc()).all()
        
        level_by_date = {}
        # Add initial level at character creation
        if main_character.created_at:
            try:
                level_by_date[main_character.created_at.date()] = 1
            except (AttributeError, TypeError):
                pass
        
        for event in level_events:
            try:
                event_date = event.event_timestamp.date() if event.event_timestamp else datetime.utcnow().date()
                level = event.event_data.get('level', main_character.level) if isinstance(event.event_data, dict) else main_character.level
                level_by_date[event_date] = level
            except (AttributeError, TypeError):
                continue
        
        # Add current level
        today = datetime.utcnow().date()
        if today not in level_by_date:
            level_by_date[today] = main_character.level
        
        level_dates = sorted(level_by_date.keys())
        level_values = [level_by_date[d] for d in level_dates]
        
        level_chart_data = {
            'dates': [d.strftime('%Y-%m-%d') for d in level_dates],
            'levels': level_values
        }
    except Exception as e:
        logger.error(f"Error processing level chart data: {str(e)}", exc_info=True)
        level_chart_data = {'dates': [], 'levels': []}
    
    # Gold Earned/Spent Chart Data
    try:
        gold_earned_events = AuditLog.query.filter(
            AuditLog.character_id == main_character.id,
            AuditLog.event_type == EventType.GOLD_TRANSACTION.value,
            AuditLog.event_timestamp >= since
        ).order_by(AuditLog.event_timestamp.asc()).all()
        
        gold_earned_by_date = defaultdict(int)
        for event in gold_earned_events:
            try:
                event_date = event.event_timestamp.date() if event.event_timestamp else datetime.utcnow().date()
                amount = event.event_data.get('amount', 0) if isinstance(event.event_data, dict) else 0
                if amount > 0:  # Only count positive amounts as earned
                    gold_earned_by_date[event_date] += amount
            except (AttributeError, TypeError):
                continue
        
        # Gold spent from ShopPurchase
        purchases = ShopPurchase.query.filter(
            ShopPurchase.character_id == main_character.id,
            ShopPurchase.purchase_date >= since
        ).order_by(ShopPurchase.purchase_date.asc()).all()
        
        gold_spent_by_date = defaultdict(int)
        for purchase in purchases:
            try:
                purchase_date = purchase.purchase_date.date() if purchase.purchase_date else datetime.utcnow().date()
                gold_spent_by_date[purchase_date] += purchase.gold_spent
            except (AttributeError, TypeError):
                continue
        
        # Combine all dates for gold chart
        all_gold_dates = set(gold_earned_by_date.keys()) | set(gold_spent_by_date.keys())
        if all_gold_dates:
            gold_dates = sorted(all_gold_dates)
            gold_earned_values = [gold_earned_by_date.get(d, 0) for d in gold_dates]
            gold_spent_values = [gold_spent_by_date.get(d, 0) for d in gold_dates]
        else:
            gold_dates = []
            gold_earned_values = []
            gold_spent_values = []
        
        gold_chart_data = {
            'dates': [d.strftime('%Y-%m-%d') for d in gold_dates],
            'earned': gold_earned_values,
            'spent': gold_spent_values
        }
    except Exception as e:
        logger.error(f"Error processing gold chart data: {str(e)}", exc_info=True)
        gold_chart_data = {'dates': [], 'earned': [], 'spent': []}
    
    # Quest Completion Statistics
    try:
        completed_quests = main_character.quest_logs.filter_by(status=QuestStatus.COMPLETED).all()
        total_quests = main_character.quest_logs.count()
        quest_completion_rate = (len(completed_quests) / total_quests * 100) if total_quests > 0 else 0
        
        # Quest completion timeline
        quest_completion_by_date = defaultdict(int)
        for quest_log in completed_quests:
            if quest_log.completed_at:
                try:
                    completion_date = quest_log.completed_at.date()
                    quest_completion_by_date[completion_date] += 1
                except (AttributeError, TypeError):
                    continue
        
        quest_dates = sorted(quest_completion_by_date.keys())
        quest_counts = [quest_completion_by_date[d] for d in quest_dates]
        
        quest_stats = {
            'total_completed': len(completed_quests),
            'total_quests': total_quests,
            'completion_rate': round(quest_completion_rate, 1),
            'completion_timeline': {
                'dates': [d.strftime('%Y-%m-%d') for d in quest_dates] if quest_dates else [],
                'counts': quest_counts if quest_dates else []
            }
        }
    except Exception as e:
        logger.error(f"Error processing quest stats: {str(e)}", exc_info=True)
        quest_stats = {
            'total_completed': 0,
            'total_quests': 0,
            'completion_rate': 0,
            'completion_timeline': {
                'dates': [],
                'counts': []
            }
        }
    
    # Achievement Badges
    try:
        badges = list(main_character.badges) if hasattr(main_character, 'badges') and main_character.badges else []
    except Exception as e:
        logger.error(f"Error fetching badges: {str(e)}", exc_info=True)
        badges = []
    
    # Recent Activity Feed
    try:
        recent_activities = AuditLog.query.filter(
            AuditLog.character_id == main_character.id
        ).order_by(AuditLog.event_timestamp.desc()).limit(15).all()
        
        activity_feed = []
        for activity in recent_activities:
            try:
                activity_feed.append({
                    'type': AuditLog.EVENT_TYPES.get(activity.event_type, activity.event_type),
                    'timestamp': activity.event_timestamp,
                    'description': activity.event_data.get('description', '') if isinstance(activity.event_data, dict) else ''
                })
            except (AttributeError, TypeError) as e:
                logger.warning(f"Error processing activity log entry: {str(e)}")
                continue
    except Exception as e:
        logger.error(f"Error fetching recent activities: {str(e)}", exc_info=True)
        activity_feed = []
    
    return render_template(
        'student/progress.html',
        student=current_user,
        main_character=main_character,
        summary_stats=summary_stats,
        xp_chart_data=xp_chart_data,
        level_chart_data=level_chart_data,
        gold_chart_data=gold_chart_data,
        quest_stats=quest_stats,
        badges=badges,
        recent_activities=activity_feed
    )

@student_bp.route('/character/create', methods=['GET', 'POST'])
@login_required
@student_required
def character_create():
    from flask import request, redirect, url_for, flash
    from app.models.character import Character
    # Class base stats mapping
    CLASS_BASE_STATS = {
        "Warrior":   {"health": 120, "max_health": 120, "strength": 15, "defense": 15, "gold": 0},
        "Sorcerer":  {"health": 80,  "max_health": 80,  "strength": 20, "defense": 8,  "gold": 0},
        "Druid":     {"health": 100, "max_health": 100, "strength": 12, "defense": 12, "gold": 0},
    }
    # Get the correct student_id from the Student table
    student_profile = Student.query.filter_by(user_id=current_user.id).first()
    if student_profile and student_profile.characters.filter_by(is_active=True).first():
        flash('You already have a character.', 'info')
        return redirect(url_for('student.character'))

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        character_class = request.form.get('character_class', '').strip()
        gender = request.form.get('gender', '').strip()
        avatar_url = request.form.get('avatar_url', '').strip()
        # Basic validation
        if not name or not character_class or not gender:
            flash('Please fill out all required fields.', 'danger')
            return render_template('student/character_create.html', student=current_user, form=request.form)
        # Set base stats based on class
        base_stats = CLASS_BASE_STATS.get(character_class, CLASS_BASE_STATS["Warrior"])
        if not student_profile:
            flash('Student profile not found. Please contact your teacher or admin.', 'danger')
            return redirect(url_for('student.dashboard'))
        # Create character
        new_character = Character(
            name=name,
            character_class=character_class,
            gender=gender,
            avatar_url=avatar_url,
            student_id=student_profile.id,
            health=base_stats["health"],
            max_health=base_stats["max_health"],
            strength=base_stats["strength"],
            defense=base_stats["defense"],
            gold=base_stats["gold"]
        )
        db.session.add(new_character)
        db.session.commit()
        flash('Character created successfully!', 'success')
        return redirect(url_for('student.character'))
    # GET: Render form
    class_options = ['Warrior', 'Sorcerer', 'Druid']
    gender_options = ['Male', 'Female', 'Other']
    avatar_options = [
        '/static/avatars/warrior_m.png',
        '/static/avatars/warrior_f.png',
        '/static/avatars/sorcerer_m.png',
        '/static/avatars/sorcerer_f.png',
        '/static/avatars/druid_m.png',
        '/static/avatars/druid_f.png',
    ]
    return render_template('student/character_create.html', student=current_user, class_options=class_options, gender_options=gender_options, avatar_options=avatar_options, form={})

@student_bp.route('/character/gain_xp', methods=['POST'])
@login_required
@student_required
def gain_xp():
    from flask import redirect, url_for, flash
    from app.models.character import Character
    student_profile = Student.query.filter_by(user_id=current_user.id).first()
    if not student_profile:
        flash('No student profile found.', 'danger')
        return redirect(url_for('student.dashboard'))
    main_character = student_profile.characters.filter_by(is_active=True).first()
    if not main_character:
        flash('No character found.', 'danger')
        return redirect(url_for('student.character'))
    main_character.gain_experience(500)
    db.session.commit()
    flash('Gained 500 XP!','success')
    return redirect(url_for('student.character'))

@student_bp.route('/character/unequip_weapon', methods=['POST'])
@login_required
@student_required
def unequip_weapon():
    from flask import redirect, url_for, flash
    from app.models.character import Character
    from app.models.equipment import EquipmentType
    student_profile = Student.query.filter_by(user_id=current_user.id).first()
    if not student_profile:
        flash('No student profile found.', 'warning')
        return redirect(url_for('student.character'))
    main_character = student_profile.characters.filter_by(is_active=True).first()
    if not main_character:
        flash('No character found.', 'warning')
        return redirect(url_for('student.character'))
    equipped_weapon = main_character.equipped_weapon
    if not equipped_weapon:
        flash('No weapon equipped.', 'warning')
        return redirect(url_for('student.character'))
    equipped_weapon.is_equipped = False
    db.session.commit()
    flash('Weapon unequipped and moved to inventory.', 'success')
    return redirect(url_for('student.character'))

@student_bp.route('/character/unequip_armor', methods=['POST'])
@login_required
@student_required
def unequip_armor():
    from flask import redirect, url_for, flash
    from app.models.character import Character
    from app.models.equipment import EquipmentType
    student_profile = Student.query.filter_by(user_id=current_user.id).first()
    if not student_profile:
        flash('No student profile found.', 'warning')
        return redirect(url_for('student.character'))
    main_character = student_profile.characters.filter_by(is_active=True).first()
    if not main_character:
        flash('No character found.', 'warning')
        return redirect(url_for('student.character'))
    equipped_armor = main_character.equipped_armor
    if not equipped_armor:
        flash('No armor equipped.', 'warning')
        return redirect(url_for('student.character'))
    equipped_armor.is_equipped = False
    db.session.commit()
    flash('Armor unequipped and moved to inventory.', 'success')
    return redirect(url_for('student.character'))

@student_bp.route('/character/unequip_accessory', methods=['POST'])
@login_required
@student_required
def unequip_accessory():
    from flask import redirect, url_for, flash
    from app.models.character import Character
    from app.models.equipment import EquipmentType
    student_profile = Student.query.filter_by(user_id=current_user.id).first()
    if not student_profile:
        flash('No student profile found.', 'warning')
        return redirect(url_for('student.character'))
    main_character = student_profile.characters.filter_by(is_active=True).first()
    if not main_character:
        flash('No character found.', 'warning')
        return redirect(url_for('student.character'))
    equipped_accessory = main_character.equipped_accessory
    if not equipped_accessory:
        flash('No accessory equipped.', 'warning')
        return redirect(url_for('student.character'))
    equipped_accessory.is_equipped = False
    db.session.commit()
    flash('Accessory unequipped and moved to inventory.', 'success')
    return redirect(url_for('student.character'))

@student_bp.route('/equipment/equip', methods=['PATCH'])
@login_required
@student_required
def api_equip_item():
    data = request.get_json()
    inventory_id = data.get('inventory_id')
    slot = data.get('slot')
    student_profile = Student.query.filter_by(user_id=current_user.id).first()
    if not student_profile:
        return jsonify({'success': False, 'message': 'No student profile found.'}), 404
    main_character = student_profile.characters.filter_by(is_active=True).first()
    if not main_character:
        return jsonify({'success': False, 'message': 'No character found.'}), 404
    item = Inventory.query.filter_by(id=inventory_id, character_id=main_character.id).first()
    if not item:
        return jsonify({'success': False, 'message': 'Item not found.'}), 404
    # Validate slot directly
    if item.equipment.slot != slot:
        return jsonify({'success': False, 'message': f'Cannot equip {item.equipment.type} in {slot} slot.'}), 400
    # Unequip any currently equipped item in the same slot
    for inv in main_character.inventory_items:
        if inv.is_equipped and inv.equipment.slot == item.equipment.slot:
            inv.is_equipped = False
    item.is_equipped = True
    db.session.commit()
    return jsonify({'success': True})

@student_bp.route('/equipment/unequip', methods=['PATCH'])
@login_required
@student_required
def api_unequip_item():
    data = request.get_json()
    inventory_id = data.get('inventory_id')
    student_profile = Student.query.filter_by(user_id=current_user.id).first()
    if not student_profile:
        return jsonify({'success': False, 'message': 'No student profile found.'}), 404
    main_character = student_profile.characters.filter_by(is_active=True).first()
    if not main_character:
        return jsonify({'success': False, 'message': 'No character found.'}), 404
    item = Inventory.query.filter_by(id=inventory_id, character_id=main_character.id).first()
    if not item or not item.is_equipped:
        return jsonify({'success': False, 'message': 'Item not equipped or not found.'}), 404
    item.is_equipped = False
    db.session.commit()
    return jsonify({'success': True})

@student_bp.route('/api/clan', methods=['GET'])
@login_required
@student_required
def api_get_student_clan():
    student_profile = Student.query.filter_by(user_id=current_user.id).first()
    if not student_profile:
        return jsonify({"clan": None}), 200
    main_character = student_profile.characters.filter_by(is_active=True).first()
    if not main_character or not main_character.clan:
        return jsonify({"clan": None}), 200
    clan = main_character.clan
    clan_data = clan.to_dict(include_members=True, include_metrics=True)
    clan_data["badges"] = [
        {"id": b.id, "name": b.name, "description": b.description, "icon": b.icon}
        for b in clan.badges
    ]
    return jsonify({"clan": clan_data})

@student_bp.route('/shop/buy', methods=['POST'])
@login_required
@student_required
def shop_buy():
    from flask import request
    from app.models.equipment import Equipment, Inventory
    from app.models.ability import Ability, CharacterAbility
    from app.models.shop import ShopPurchase, PurchaseType
    from app.models.shop_config import ShopItemOverride
    item_id = None  # Initialize before try block to avoid UnboundLocalError
    try:
        data = request.get_json()
        item_id = data.get('item_id') if data else None
        item_type = data.get('item_type') if data else None  # 'equipment' or 'ability', optional
        logger.info(f"Shop purchase attempt: user={current_user.id}, item_id={item_id}, item_type={item_type}")
        
        if not item_id:
            return jsonify({'success': False, 'message': 'Missing item_id.'}), 400
        # Get current student's active character
        student_profile = Student.query.filter_by(user_id=current_user.id).first()
        if not student_profile:
            return jsonify({'success': False, 'message': 'No student profile found.'}), 404
        character = student_profile.characters.filter_by(is_active=True).first()
        if not character:
            return jsonify({'success': False, 'message': 'No active character found.'}), 404
        # Determine item type and fetch item
        item = None
        purchase_type = None
        if item_type == 'equipment' or item_type is None:
            item = Equipment.query.filter_by(id=item_id).first()
            if item:
                purchase_type = PurchaseType.EQUIPMENT.value
        if not item and (item_type == 'ability' or item_type is None):
            item = Ability.query.filter_by(id=item_id).first()
            if item:
                purchase_type = PurchaseType.ABILITY.value
        if not item:
            return jsonify({'success': False, 'message': 'Item not found.'}), 404
        # Check ownership
        if purchase_type == PurchaseType.EQUIPMENT.value:
            already_owned = Inventory.query.filter_by(character_id=character.id, item_id=item.id).first()
        else:
            already_owned = CharacterAbility.query.filter_by(character_id=character.id, ability_id=item.id).first()
        if already_owned:
            return jsonify({'success': False, 'message': 'Item already owned.'}), 400
        # Check for overrides
        active_class = next((c for c in student_profile.classes), None)
        effective_cost = getattr(item, 'cost', 0)
        effective_level_req = getattr(item, 'level_requirement', 1)
        
        if active_class:
            override = ShopItemOverride.query.filter_by(
                classroom_id=active_class.id,
                item_type='equipment' if purchase_type == PurchaseType.EQUIPMENT.value else 'ability',
                item_id=item.id
            ).first()
            if override:
                if not override.is_visible:
                    return jsonify({'success': False, 'message': 'Item is not available.'}), 400
                if override.override_cost is not None:
                    effective_cost = override.override_cost
                if override.override_level_req is not None:
                    effective_level_req = override.override_level_req

        # Validate gold
        if character.gold < effective_cost:
            return jsonify({'success': False, 'message': 'Not enough gold.'}), 400
        # Validate level
        if character.level < effective_level_req:
            return jsonify({'success': False, 'message': f'Level {effective_level_req} required.'}), 400
        # Validate class restriction (equipment only)
        class_restr = getattr(item, 'class_restriction', None)
        if purchase_type == PurchaseType.EQUIPMENT.value and class_restr and class_restr.lower() != character.character_class.lower():
            return jsonify({'success': False, 'message': f'Class restriction: {class_restr}.'}), 400
        # Deduct gold
        character.gold -= effective_cost
        # Set gold_spent to the item's price (or gold deducted)
        gold_spent = effective_cost

        if gold_spent is None:
            return jsonify({'success': False, 'message': 'Item has no cost set. Please contact your teacher/admin.'}), 400
        if gold_spent <= 0:
            return jsonify({'success': False, 'message': 'Invalid gold_spent value.'}), 400
        # Add to inventory or abilities
        if purchase_type == PurchaseType.EQUIPMENT.value:
            new_inv = Inventory(character_id=character.id, item_id=item.id, is_equipped=False)
            db.session.add(new_inv)
        else:
            new_ability = CharacterAbility(character_id=character.id, ability_id=item.id)
            db.session.add(new_ability)
        # Log purchase
        purchase = ShopPurchase(
            character_id=character.id,
            item_id=item.id,
            gold_spent=gold_spent,
            purchase_type=purchase_type,
            student_id=student_profile.id,
        )
        db.session.add(purchase)
        db.session.commit()
        # Refresh character to get updated gold
        db.session.refresh(character)
        logger.info(f"Shop purchase successful: character={character.id}, item={item_id}, gold_spent={gold_spent}, remaining_gold={character.gold}")
        
        # Prepare updated info
        inventory = [
            {'item_id': inv.item_id, 'is_equipped': inv.is_equipped}
            for inv in character.inventory_items
        ]
        abilities = [
            {'ability_id': ab.ability_id, 'level': ab.level}
            for ab in getattr(character, 'abilities', [])
        ]
        return jsonify({
            'success': True,
            'message': 'Item purchased successfully.',
            'character': {
                'id': character.id,
                'gold': character.gold,  # Now refreshed
                'level': character.level,
                'character_class': character.character_class
            },
            'inventory': inventory,
            'abilities': abilities
        })
    except Exception as e:
        db.session.rollback()
        logger.error(f"Shop purchase error: user={current_user.id}, item_id={item_id}, error={str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        }), 500 