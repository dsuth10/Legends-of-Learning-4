from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user
from .teacher import student_required
from app.models import db
from app.models.character import Character
from app.models.equipment import Inventory, Equipment, EquipmentType, EquipmentSlot, TEST_ARMOR_IMAGE, TEST_RING_IMAGE, TEST_SWORD_IMAGE
from app.models.student import Student
from app.models.ability import Ability, CharacterAbility
from app.models.shop import ShopPurchase, PurchaseType
from app.models.quest import Quest, QuestLog, QuestStatus, RewardType
from app.models.audit import AuditLog, EventType
from app.models.achievement_badge import AchievementBadge
from app.models.shop_config import ShopItemOverride
from datetime import datetime, timedelta
from collections import defaultdict
import time
import logging

logger = logging.getLogger(__name__)

student_bp = Blueprint('student', __name__, url_prefix='/student')

@student_bp.route('/profile')
@login_required
@student_required
def profile():
    try:
        return render_template('student/profile.html', student=current_user)
    except Exception as e:
        logger.error(f"Error loading profile page: {str(e)}", exc_info=True)
        flash('An error occurred while loading your profile. Please try again.', 'danger')
        return redirect(url_for('student.character'))

@student_bp.route('/quests')
@login_required
@student_required
def quests():
    try:
        logger.info(f"Quest page accessed by user {current_user.id}")
        student_profile = Student.query.filter_by(user_id=current_user.id).first()
        if not student_profile:
            logger.warning(f"No student profile found for user {current_user.id}")
            flash('No student profile found. Please contact your administrator.', 'warning')
            return redirect(url_for('student.character'))
        logger.debug(f"Student profile found: {student_profile.id}")
        main_char = student_profile.characters.filter_by(is_active=True).first()
        assigned_quests = []
        equipped_abilities = []
        ability_targets = []
        
        if main_char:
            # quest_logs is lazy='dynamic', so we need to call .all()
            for log in main_char.quest_logs.all():
                logger.debug(f"Quest log: quest_id={log.quest_id}, status={log.status}, log_id={log.id}")
                quest = log.quest
                if not quest:
                    logger.warning(f"Quest log {log.id} references non-existent quest {log.quest_id}, skipping")
                    continue
                
                # Parse objectives from completion_criteria
                objectives = []
                completion_criteria = quest.completion_criteria or {}
                progress_data = log.progress_data or {}
                
                # Try to extract objectives from completion_criteria
                if isinstance(completion_criteria, dict):
                    # Check for objectives list
                    if 'objectives' in completion_criteria:
                        objectives = completion_criteria['objectives']
                    # Or create objectives from criteria keys
                    elif completion_criteria:
                        obj_num = 1
                        for key, value in completion_criteria.items():
                            if key not in ['progress', 'min_score_percent']:
                                objectives.append({
                                    'id': obj_num,
                                    'text': f"{key.replace('_', ' ').title()}: {value}",
                                    'completed': progress_data.get(key, False) or progress_data.get('progress', 0) >= (value if isinstance(value, (int, float)) else 0)
                                })
                                obj_num += 1
                
                # If no objectives found, create default ones
                if not objectives:
                    objectives = [
                        {'id': 1, 'text': 'Complete quest requirements', 'completed': log.status == QuestStatus.COMPLETED}
                    ]
                
                # Calculate progress percentage
                completed_count = sum(1 for obj in objectives if obj.get('completed', False))
                total_count = len(objectives) if objectives else 1
                progress_percent = int((completed_count / total_count * 100)) if total_count > 0 else 0
                
                # Get rewards breakdown
                rewards_xp = 0
                rewards_gold = 0
                rewards_items = []
                # quest.rewards is lazy='dynamic', so we need to call .all()
                for reward in quest.rewards.all():
                    # Handle enum comparison - reward.type is a RewardType enum
                    reward_type_value = reward.type.value if hasattr(reward.type, 'value') else str(reward.type)
                    
                    if reward_type_value == 'experience' or reward_type_value == 'xp':
                        rewards_xp += reward.amount
                    elif reward_type_value == 'gold':
                        rewards_gold += reward.amount
                    elif reward_type_value == 'equipment' or reward_type_value == 'item':
                        # Add item_name for template display
                        reward_data = {
                            'reward': reward,
                            'item_name': 'Quest Item'  # Default fallback
                        }
                        # Try to get equipment name if it's an equipment reward
                        if reward_type_value == 'equipment' and reward.item_id:
                            equipment = reward.equipment
                            if equipment:
                                reward_data['item_name'] = equipment.name
                            else:
                                # Fallback: query directly if relationship not loaded
                                equipment = Equipment.query.get(reward.item_id)
                                if equipment:
                                    reward_data['item_name'] = equipment.name
                        # Try to get ability name if it's an ability reward
                        elif reward_type_value == 'ability' and reward.ability_id:
                            ability = reward.ability
                            if ability:
                                reward_data['item_name'] = ability.name
                            else:
                                # Fallback: query directly if relationship not loaded
                                ability = Ability.query.get(reward.ability_id)
                                if ability:
                                    reward_data['item_name'] = ability.name
                        rewards_items.append(reward_data)
                
                # Calculate time remaining if deadline exists
                time_remaining = None
                if quest.end_date:
                    from datetime import datetime
                    now = datetime.utcnow()
                    if quest.end_date > now:
                        delta = quest.end_date - now
                        days = delta.days
                        hours = delta.seconds // 3600
                        if days > 0:
                            time_remaining = f"{days} day{'s' if days != 1 else ''} remaining"
                        elif hours > 0:
                            time_remaining = f"{hours} hour{'s' if hours != 1 else ''} remaining"
                        else:
                            time_remaining = "Less than 1 hour remaining"
                
                # Get quest type display name
                quest_type_display = quest.type.value.title() if hasattr(quest.type, 'value') else str(quest.type).title()
                if quest_type_display == 'Story':
                    quest_type_display = 'Story Quest'
                
                assigned_quests.append({
                    'quest': quest,
                    'status': log.status,
                    'x': log.x_coordinate,
                    'y': log.y_coordinate,
                    'log': log,
                    'objectives': objectives,
                    'progress_percent': progress_percent,
                    'rewards_xp': rewards_xp,
                    'rewards_gold': rewards_gold,
                    'rewards_items': rewards_items,
                    'time_remaining': time_remaining,
                    'quest_type_display': quest_type_display
                })
            
            # Get equipped abilities for quest context
            equipped_abilities = []
            for ca in main_char.abilities.filter_by(is_equipped=True).all():
                # Ensure ability relationship is loaded
                if ca.ability:
                    equipped_abilities.append({
                        'id': ca.ability.id,
                        'name': ca.ability.name,
                        'type': ca.ability.type,
                        'description': ca.ability.description,
                        'power': ca.ability.power,
                        'cooldown': ca.ability.cooldown,
                        'duration': ca.ability.duration,
                        'last_used_at': ca.last_used_at.isoformat() if ca.last_used_at else None,
                    })
                else:
                    # Fallback: query ability directly if relationship not loaded
                    ability = Ability.query.get(ca.ability_id)
                    if ability:
                        equipped_abilities.append({
                            'id': ability.id,
                            'name': ability.name,
                            'type': ability.type,
                            'description': ability.description,
                            'power': ability.power,
                            'cooldown': ability.cooldown,
                            'duration': ability.duration,
                            'last_used_at': ca.last_used_at.isoformat() if ca.last_used_at else None,
                        })
            # Get ability targets (clanmates)
            if main_char.clan:
                ability_targets = [
                    {'id': member.id, 'name': member.name, 'character_class': member.character_class}
                    for member in main_char.clan.members if member.id != main_char.id
                ]
        # Eager load classroom and teacher for template
        if student_profile and student_profile.classroom:
            # Access teacher relationship to ensure it's loaded
            _ = student_profile.classroom.teacher
        
        now = int(time.time())
        logger.info(f"Rendering quests_new.html template for user {current_user.id} with {len(assigned_quests)} quests")
        logger.debug(f"Quest data: assigned_quests={len(assigned_quests)}, equipped_abilities={len(equipped_abilities)}, ability_targets={len(ability_targets)}")
        return render_template('student/quests_new.html', student=current_user, student_profile=student_profile, assigned_quests=assigned_quests, equipped_abilities=equipped_abilities, ability_targets=ability_targets, main_character=main_char, now=now)
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        logger.error(f"Error loading quests page: {str(e)}\n{error_details}", exc_info=True)
        flash(f'An error occurred while loading quests: {str(e)}. Please try again.', 'danger')
        return redirect(url_for('student.character'))

@student_bp.route('/quests/start/<int:quest_id>', methods=['POST'])
@login_required
@student_required
def start_quest(quest_id):
    try:
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
                logger.debug(f"Quest started: quest_id={quest.id}, character_id={main_char.id}, status={existing_log.status}")
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
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error starting quest {quest_id}: {str(e)}", exc_info=True)
        flash('An error occurred while starting the quest. Please try again.', 'danger')
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
        logger.info(f"Completing quest: quest_id={quest_id}, character_id={main_char.id}, current_gold={main_char.gold}, current_level={main_char.level}, current_xp={main_char.experience}")
        
        # Ensure character and quest_log are in session before completing quest
        db.session.add(main_char)
        db.session.add(quest_log)
        
        # Complete quest - this distributes rewards and commits in a single transaction
        quest_log.complete_quest()  # This calls self.save() which commits all changes
        
        # Character is already refreshed in complete_quest(), but refresh again to be safe
        db.session.refresh(main_char)
        
        logger.info(f"Quest completed successfully: quest_id={quest_id}, character_id={main_char.id}, gold={main_char.gold}, level={main_char.level}, experience={main_char.experience}")
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
    try:
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
        
        # Ensure student_profile is available for template
        if not student_profile:
            student_profile = Student.query.filter_by(user_id=current_user.id).first()
        
        # Eager load classroom and teacher for template
        if student_profile and student_profile.classroom:
            # Access teacher relationship to ensure it's loaded
            _ = student_profile.classroom.teacher
        
        return render_template('student/character_new.html', 
                             student=current_user, 
                             main_character=main_character, 
                             equipped_abilities=equipped_abilities, 
                             now=now, 
                             ability_targets=ability_targets, 
                             active_status_effects=active_status_effects, 
                             student_profile=student_profile)
    except Exception as e:
        logger.error(f"Error loading character page: {str(e)}", exc_info=True)
        flash('An error occurred while loading your character. Please try again.', 'danger')
        return redirect(url_for('student.character'))

@student_bp.route('/shop')
@login_required
@student_required
def shop():
    try:
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
        logger.debug(f"Shop route: Equipment count={len(items)}, Ability count={len(ability_items)}")
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

        # Calculate total spent gold
        total_spent = 0
        if main_character:
            purchases = ShopPurchase.query.filter_by(character_id=main_character.id).all()
            total_spent = sum(p.gold_spent for p in purchases)
        
        # Rarity mapping
        RARITY_MAP = {
            1: {'name': 'Common', 'class': 'rarity-common'},
            2: {'name': 'Rare', 'class': 'rarity-rare'},
            3: {'name': 'Epic', 'class': 'rarity-epic'},
            4: {'name': 'Legendary', 'class': 'rarity-legendary'},
            5: {'name': 'Legendary', 'class': 'rarity-legendary'}  # Handle 5 as legendary too
        }
        
        items_list = []
        logger.debug(f"Shop route: Processing {len(items)} equipment items")
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
            
            # Determine item type for filtering
            item_type = 'weapon'
            if eq.slot in ['CHEST', 'HEAD', 'LEGS', 'FEET']:
                item_type = 'armor'
            elif eq.slot in ['NECK', 'RING']:
                item_type = 'accessory'
            elif eq.type and eq.type.lower() in ['armor', 'accessory']:
                item_type = eq.type.lower()
            
            # Build stats dict
            stats = {}
            if eq.health_bonus:
                stats['health_bonus'] = eq.health_bonus
            if eq.power_bonus:
                stats['power_bonus'] = eq.power_bonus
            if eq.defense_bonus:
                stats['defense_bonus'] = eq.defense_bonus
            # Also add direct fields for template fallback
            health_bonus = eq.health_bonus
            power_bonus = eq.power_bonus
            defense_bonus = eq.defense_bonus
            
            rarity_info = RARITY_MAP.get(eq.rarity, RARITY_MAP[1])
            
            items_list.append({
                'id': eq.id,
                'name': eq.name,
                'price': effective_cost,
                'original_price': eq.cost if effective_cost != eq.cost else None,
                'image': eq.image_url or '/static/images/default_item.png',
                'category': 'equipment',
                'item_type': item_type,  # For filtering: weapon/armor/accessory
                'slot': eq.slot,
                'type': eq.type,  # Original equipment type
                'tier': eq.rarity,
                'rarity_name': rarity_info['name'],
                'rarity_class': rarity_info['class'],
                'description': eq.description or '',
                'level_requirement': effective_level,
                'original_level_requirement': getattr(eq, 'level_requirement', 1) if effective_level != getattr(eq, 'level_requirement', 1) else None,
                'class_restriction': getattr(eq, 'class_restriction', None),
                'stats': stats,
                'health_bonus': health_bonus,  # Direct field for template fallback
                'power_bonus': power_bonus,
                'defense_bonus': defense_bonus,
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
            
            # Abilities are typically considered as "accessory" type for filtering
            item_type = 'accessory'
            
            # Build stats dict for abilities
            stats = {}
            if hasattr(ab, 'power'):
                stats['power_bonus'] = ab.power
            
            rarity_info = RARITY_MAP.get(getattr(ab, 'tier', 1), RARITY_MAP[1])
            
            items_list.append({
                'id': ab.id,
                'name': ab.name,
                'price': effective_cost,
                'original_price': ab.cost if effective_cost != ab.cost else None,
                'image': '/static/images/default_item.png',
                'category': 'ability',
                'item_type': item_type,  # For filtering
                'slot': None,  # Abilities don't have slots
                'type': 'ability',
                'tier': getattr(ab, 'tier', 1),
                'rarity_name': rarity_info['name'],
                'rarity_class': rarity_info['class'],
                'description': ab.description or '',
                'level_requirement': effective_level,
                'original_level_requirement': getattr(ab, 'level_requirement', 1) if effective_level != getattr(ab, 'level_requirement', 1) else None,
                'class_restriction': None,
                'stats': stats,
                'owned': owned,
                'can_afford': can_afford,
                'unlocked': unlocked,
                'can_buy': can_buy,
            })
        
        return render_template('student/shop_new.html', student=current_user, student_profile=student_profile, main_character=main_character, items=items_list, total_spent=total_spent)
    except Exception as e:
        logger.error(f"Error loading shop page: {str(e)}", exc_info=True)
        flash('An error occurred while loading the shop. Please try again.', 'danger')
        return redirect(url_for('student.character'))

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
        "Warrior":   {"health": 120, "max_health": 120, "power": 15, "defense": 15, "gold": 0},
        "Sorcerer":  {"health": 80,  "max_health": 80,  "power": 20, "defense": 8,  "gold": 0},
        "Druid":     {"health": 100, "max_health": 100, "power": 12, "defense": 12, "gold": 0},
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
            return redirect(url_for('student.character'))
        # Create character
        new_character = Character(
            name=name,
            character_class=character_class,
            gender=gender,
            avatar_url=avatar_url,
            student_id=student_profile.id,
            health=base_stats["health"],
            max_health=base_stats["max_health"],
            power=base_stats["power"],
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
        return redirect(url_for('student.character'))
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

@student_bp.route('/equipment')
@login_required
@student_required
def equipment():
    """Equipment management page."""
    try:
        student_profile = Student.query.filter_by(user_id=current_user.id).first()
        main_character = None
        inventory_items = []
        equipped_items = {}
        stat_changes = {'attack': 0, 'defense': 0}
        
        if student_profile:
            main_character = student_profile.characters.filter_by(is_active=True).first()
            if main_character:
                # Get all inventory items (unequipped)
                inventory_items = main_character.inventory_items.filter_by(is_equipped=False).all()
                
                # Get equipped items grouped by slot
                equipped = main_character.inventory_items.filter_by(is_equipped=True).all()
                for inv_item in equipped:
                    slot = inv_item.equipment.slot if inv_item.equipment else None
                    if slot:
                        equipped_items[slot] = inv_item
                
                # Calculate stat changes from equipped items
                for inv_item in equipped:
                    if inv_item.equipment:
                        stat_changes['attack'] += inv_item.equipment.power_bonus or 0
                        stat_changes['defense'] += inv_item.equipment.defense_bonus or 0
        
        # Eager load classroom and teacher for template
        if student_profile and student_profile.classroom:
            # Access teacher relationship to ensure it's loaded
            _ = student_profile.classroom.teacher
        
        return render_template(
            'student/equipment_new.html',
            student=current_user,
            student_profile=student_profile,
            main_character=main_character,
            inventory_items=inventory_items,
            equipped_items=equipped_items,
            stat_changes=stat_changes
        )
    except Exception as e:
        logger.error(f"Error loading equipment page: {str(e)}", exc_info=True)
        flash('An error occurred while loading the equipment page. Please try again.', 'danger')
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
        # characters relationship is lazy='dynamic', so we need to call filter_by on the query object
        character = student_profile.characters.filter_by(is_active=True).first()
        if not character:
            return jsonify({'success': False, 'message': 'No active character found.'}), 404
        logger.info(f"Character found: id={character.id}, name={character.name}, gold={character.gold}, level={character.level}")
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
        if not purchase_type:
            return jsonify({'success': False, 'message': 'Could not determine item type.'}), 400
        # Check ownership
        if purchase_type == PurchaseType.EQUIPMENT.value:
            already_owned = Inventory.query.filter_by(character_id=character.id, item_id=item.id).first()
        else:
            already_owned = CharacterAbility.query.filter_by(character_id=character.id, ability_id=item.id).first()
        if already_owned:
            return jsonify({'success': False, 'message': 'Item already owned.'}), 400
        # Check for overrides
        # Student has a direct classroom relationship (singular), not classes
        active_class = student_profile.classroom
        effective_cost = getattr(item, 'cost', 0)
        effective_level_req = getattr(item, 'level_requirement', 1)
        
        if active_class:
            try:
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
            except Exception as e:
                # Handle case where shop_item_overrides table doesn't exist yet
                # This can happen if migrations haven't been run
                logger.warning(f"Could not query shop item overrides: {e}")
                # Continue with default values

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
        # Convert and validate gold_spent before creating ShopPurchase
        try:
            gold_spent = int(effective_cost)
        except (TypeError, ValueError):
            return jsonify({'success': False, 'message': 'Invalid item cost. Please contact your teacher/admin.'}), 400

        if gold_spent <= 0:
            return jsonify({'success': False, 'message': 'Item has no cost set. Please contact your teacher/admin.'}), 400
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
        # Refresh character to get updated gold after commit
        db.session.refresh(character)
        logger.info(f"Shop purchase successful: character={character.id}, item={item_id}, gold_spent={gold_spent}, remaining_gold={character.gold}")
        
        # Prepare updated info
        # inventory_items relationship is lazy='dynamic', so we need to call .all() on it
        inventory = [
            {'item_id': inv.item_id, 'is_equipped': inv.is_equipped}
            for inv in character.inventory_items.all()
        ]
        # abilities relationship is lazy='dynamic', so we need to call .all() on it
        character_abilities = getattr(character, 'abilities', None)
        if character_abilities is not None:
            abilities = [
                {'ability_id': ab.ability_id, 'level': ab.level}
                for ab in character_abilities.all()
            ]
        else:
            abilities = []
        
        # Return consistent JSON response with all necessary data
        return jsonify({
            'success': True,
            'message': 'Item purchased successfully.',
            'character': {
                'id': character.id,
                'gold': character.gold,  # Refreshed from database
                'level': character.level,
                'character_class': character.character_class
            },
            'item': {
                'id': item.id,
                'name': item.name,
                'type': purchase_type
            },
            'inventory': inventory,
            'abilities': abilities
        })
    except ValueError as ve:
        # Handle validation errors specifically
        db.session.rollback()
        logger.error(f"Shop purchase validation error: user={current_user.id}, item_id={item_id}, error={str(ve)}", exc_info=True)
        return jsonify({
            'success': False,
            'message': f'Purchase validation failed: {str(ve)}',
            'error_type': 'ValidationError',
            'error_code': 'VALIDATION_ERROR'
        }), 400
    except Exception as e:
        db.session.rollback()
        import traceback
        error_traceback = traceback.format_exc()
        logger.error(f"Shop purchase error: user={current_user.id}, item_id={item_id}, error={str(e)}\n{error_traceback}", exc_info=True)
        return jsonify({
            'success': False,
            'message': f'An error occurred while processing your purchase. Please try again.',
            'error_type': type(e).__name__,
            'error_code': 'INTERNAL_ERROR'
        }), 500 