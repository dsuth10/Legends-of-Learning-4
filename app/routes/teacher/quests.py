from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from app.models import db
from app.models.quest import Quest, QuestType, Reward, RewardType
from app.models.student import Student
from app.models.character import Character
from app.models.clan import Clan
from app.models.classroom import Classroom
from app.models.quest import QuestLog, QuestStatus
from app.models.user import User
from app.models.audit import AuditLog, EventType
from app.models.equipment import Inventory
from app.models.ability import CharacterAbility
from app.services.quest_map_utils import find_available_coordinates
from app.routes.teacher.blueprint import teacher_required
from datetime import datetime
import json
import logging

logger = logging.getLogger(__name__)

teacher_quests_bp = Blueprint('teacher_quests', __name__, url_prefix='/teacher/quests')

@teacher_quests_bp.route('/', methods=['GET'])
@login_required
def list_quests():
    db.session.expire_all()  # Force session to reload from DB
    quests = Quest.query.order_by(Quest.id.desc()).all()
    # Get classes for the teacher to populate dropdown (fallback if JS fails)
    classes = Classroom.query.filter_by(teacher_id=current_user.id, is_active=True).all()
    return render_template('teacher/quests.html', quests=quests, classes=classes)

@teacher_quests_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create_quest():
    if request.method == 'POST':
        try:
            title = request.form['title']
            description = request.form['description']
            quest_type = request.form['type']
            gold_reward = request.form.get('gold_reward', type=int, default=0)
            xp_reward = request.form.get('xp_reward', type=int, default=0)
            
            # Advanced fields
            level_requirement = request.form.get('level_requirement', type=int, default=1)
            start_date_str = request.form.get('start_date', '').strip()
            end_date_str = request.form.get('end_date', '').strip()
            time_limit_hours = request.form.get('time_limit_hours', type=int) or None
            parent_quest_id = request.form.get('parent_quest_id', type=int) or None
            requirements_str = request.form.get('requirements', '{}').strip()
            completion_criteria_str = request.form.get('completion_criteria', '{}').strip()
            
            # Parse dates (datetime-local returns naive datetime, we need to treat as UTC)
            from app.utils.date_utils import get_utc_now
            from datetime import timezone
            start_date = None
            if start_date_str:
                try:
                    # datetime-local returns naive datetime, assume UTC
                    naive_dt = datetime.fromisoformat(start_date_str)
                    start_date = naive_dt.replace(tzinfo=timezone.utc)
                except ValueError:
                    flash('Invalid start date format', 'error')
                    return redirect(url_for('teacher_quests.create_quest'))
            
            end_date = None
            if end_date_str:
                try:
                    # datetime-local returns naive datetime, assume UTC
                    naive_dt = datetime.fromisoformat(end_date_str)
                    end_date = naive_dt.replace(tzinfo=timezone.utc)
                except ValueError:
                    flash('Invalid end date format', 'error')
                    return redirect(url_for('teacher_quests.create_quest'))
            
            # Validate date range
            if start_date and end_date and start_date >= end_date:
                flash('End date must be after start date', 'error')
                return redirect(url_for('teacher_quests.create_quest'))
            
            # Validate parent quest
            if parent_quest_id:
                parent_quest = Quest.query.get(parent_quest_id)
                if not parent_quest:
                    flash('Selected prerequisite quest does not exist', 'error')
                    return redirect(url_for('teacher_quests.create_quest'))
                # Prevent circular dependencies (basic check)
                if parent_quest.parent_quest_id == parent_quest_id:
                    flash('Cannot create circular quest dependencies', 'error')
                    return redirect(url_for('teacher_quests.create_quest'))
            
            # Parse JSON fields
            try:
                requirements = json.loads(requirements_str) if requirements_str else {}
            except json.JSONDecodeError as e:
                flash(f'Invalid requirements JSON: {str(e)}', 'error')
                return redirect(url_for('teacher_quests.create_quest'))
            
            try:
                completion_criteria = json.loads(completion_criteria_str) if completion_criteria_str else {}
            except json.JSONDecodeError as e:
                flash(f'Invalid completion criteria JSON: {str(e)}', 'error')
                return redirect(url_for('teacher_quests.create_quest'))
            
            new_quest = Quest(
                title=title,
                description=description,
                type=quest_type,
                level_requirement=level_requirement,
                start_date=start_date,
                end_date=end_date,
                time_limit_hours=time_limit_hours,
                parent_quest_id=parent_quest_id,
                requirements=requirements,
                completion_criteria=completion_criteria
            )
            db.session.add(new_quest)
            db.session.flush()  # Get new_quest.id before adding rewards
            
            if gold_reward and gold_reward > 0:
                gold = Reward(quest_id=new_quest.id, type=RewardType.GOLD, amount=gold_reward)
                db.session.add(gold)
            if xp_reward and xp_reward > 0:
                xp = Reward(quest_id=new_quest.id, type=RewardType.EXPERIENCE, amount=xp_reward)
                db.session.add(xp)
            
            db.session.commit()
            flash('Quest created!', 'success')
            return redirect(url_for('teacher_quests.list_quests'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating quest: {str(e)}', 'error')
            return redirect(url_for('teacher_quests.create_quest'))
    
    # GET request - get available quests for prerequisite dropdown
    available_quests = Quest.query.order_by(Quest.title).all()
    return render_template('teacher/quest_form.html', quest=None, available_quests=available_quests)

@teacher_quests_bp.route('/edit/<int:quest_id>', methods=['GET', 'POST'])
@login_required
def edit_quest(quest_id):
    quest = Quest.query.get_or_404(quest_id)
    if request.method == 'POST':
        try:
            quest.title = request.form['title']
            quest.description = request.form['description']
            quest.type = request.form['type']
            gold_reward = request.form.get('gold_reward', type=int, default=0)
            xp_reward = request.form.get('xp_reward', type=int, default=0)
            
            # Advanced fields
            quest.level_requirement = request.form.get('level_requirement', type=int, default=1)
            start_date_str = request.form.get('start_date', '').strip()
            end_date_str = request.form.get('end_date', '').strip()
            time_limit_hours = request.form.get('time_limit_hours', type=int) or None
            parent_quest_id = request.form.get('parent_quest_id', type=int) or None
            requirements_str = request.form.get('requirements', '{}').strip()
            completion_criteria_str = request.form.get('completion_criteria', '{}').strip()
            
            # Parse dates (datetime-local returns naive datetime, we need to treat as UTC)
            from app.utils.date_utils import get_utc_now
            from datetime import timezone
            start_date = None
            if start_date_str:
                try:
                    # datetime-local returns naive datetime, assume UTC
                    naive_dt = datetime.fromisoformat(start_date_str)
                    start_date = naive_dt.replace(tzinfo=timezone.utc)
                except ValueError:
                    flash('Invalid start date format', 'error')
                    return redirect(url_for('teacher_quests.edit_quest', quest_id=quest_id))
            quest.start_date = start_date
            
            end_date = None
            if end_date_str:
                try:
                    # datetime-local returns naive datetime, assume UTC
                    naive_dt = datetime.fromisoformat(end_date_str)
                    end_date = naive_dt.replace(tzinfo=timezone.utc)
                except ValueError:
                    flash('Invalid end date format', 'error')
                    return redirect(url_for('teacher_quests.edit_quest', quest_id=quest_id))
            quest.end_date = end_date
            
            # Validate date range
            if quest.start_date and quest.end_date and quest.start_date >= quest.end_date:
                flash('End date must be after start date', 'error')
                return redirect(url_for('teacher_quests.edit_quest', quest_id=quest_id))
            
            quest.time_limit_hours = time_limit_hours
            
            # Validate parent quest (prevent self-reference and circular dependencies)
            if parent_quest_id:
                if parent_quest_id == quest_id:
                    flash('Quest cannot be its own prerequisite', 'error')
                    return redirect(url_for('teacher_quests.edit_quest', quest_id=quest_id))
                
                parent_quest = Quest.query.get(parent_quest_id)
                if not parent_quest:
                    flash('Selected prerequisite quest does not exist', 'error')
                    return redirect(url_for('teacher_quests.edit_quest', quest_id=quest_id))
                
                # Check for circular dependencies (prevent A -> B -> A)
                def check_circular(child_id, target_id, visited=None):
                    if visited is None:
                        visited = set()
                    if child_id in visited:
                        return False
                    visited.add(child_id)
                    child = Quest.query.get(child_id)
                    if not child or not child.parent_quest_id:
                        return False
                    if child.parent_quest_id == target_id:
                        return True
                    return check_circular(child.parent_quest_id, target_id, visited)
                
                if check_circular(parent_quest_id, quest_id):
                    flash('Cannot create circular quest dependencies', 'error')
                    return redirect(url_for('teacher_quests.edit_quest', quest_id=quest_id))
            
            quest.parent_quest_id = parent_quest_id
            
            # Parse JSON fields
            try:
                quest.requirements = json.loads(requirements_str) if requirements_str else {}
            except json.JSONDecodeError as e:
                flash(f'Invalid requirements JSON: {str(e)}', 'error')
                return redirect(url_for('teacher_quests.edit_quest', quest_id=quest_id))
            
            try:
                quest.completion_criteria = json.loads(completion_criteria_str) if completion_criteria_str else {}
            except json.JSONDecodeError as e:
                flash(f'Invalid completion criteria JSON: {str(e)}', 'error')
                return redirect(url_for('teacher_quests.edit_quest', quest_id=quest_id))
            
            # Remove existing gold/xp rewards
            for reward in quest.rewards.filter(Reward.type.in_([RewardType.GOLD, RewardType.EXPERIENCE])):
                db.session.delete(reward)
            
            if gold_reward and gold_reward > 0:
                gold = Reward(quest_id=quest.id, type=RewardType.GOLD, amount=gold_reward)
                db.session.add(gold)
            if xp_reward and xp_reward > 0:
                xp = Reward(quest_id=quest.id, type=RewardType.EXPERIENCE, amount=xp_reward)
                db.session.add(xp)
            
            db.session.commit()
            flash('Quest updated!', 'success')
            return redirect(url_for('teacher_quests.list_quests'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating quest: {str(e)}', 'error')
            return redirect(url_for('teacher_quests.edit_quest', quest_id=quest_id))
    
    # GET request - get current values and available quests for prerequisite dropdown
    gold_reward = quest.rewards.filter_by(type=RewardType.GOLD).first().amount if quest.rewards.filter_by(type=RewardType.GOLD).first() else 0
    xp_reward = quest.rewards.filter_by(type=RewardType.EXPERIENCE).first().amount if quest.rewards.filter_by(type=RewardType.EXPERIENCE).first() else 0
    available_quests = Quest.query.filter(Quest.id != quest_id).order_by(Quest.title).all()
    # Get parent quest if exists
    parent_quest = Quest.query.get(quest.parent_quest_id) if quest.parent_quest_id else None
    return render_template('teacher/quest_form.html', quest=quest, gold_reward=gold_reward, xp_reward=xp_reward, available_quests=available_quests, parent_quest=parent_quest)

@teacher_quests_bp.route('/delete/<int:quest_id>', methods=['POST'])
@login_required
def delete_quest(quest_id):
    quest = Quest.query.get_or_404(quest_id)
    db.session.delete(quest)
    db.session.commit()
    flash('Quest deleted!', 'info')
    return redirect(url_for('teacher_quests.list_quests'))

@teacher_quests_bp.route('/assign', methods=['POST'])
@login_required
def assign_quest():
    quest_id = int(request.form['quest_id'])
    class_id = int(request.form['class_id'])
    target_type = request.form['target_type']
    target_ids = request.form.getlist('target_ids')  # List of selected clan or student IDs
    auto_assign = request.form.get('auto_assign') == '1'  # Checkbox value

    # Determine the list of character IDs to assign the quest to
    character_ids = []

    if target_type == 'class':
        # Assign to all students with active characters in the class
        characters = Character.query.join(Student).filter(
            Character.is_active == True,
            Student.class_id == class_id
        ).all()
        character_ids = [c.id for c in characters]
    elif target_type == 'clan':
        # Assign to all students with active characters in the selected clans
        if target_ids:
            characters = Character.query.filter(
                Character.is_active == True,
                Character.clan_id.in_(target_ids)
            ).all()
            character_ids = [c.id for c in characters]
    elif target_type == 'student':
        # Assign to the selected character IDs directly
        character_ids = [int(cid) for cid in target_ids]

    # Remove duplicates
    character_ids = list(set(character_ids))

    # Determine initial status and started_at based on auto_assign
    from app.utils.date_utils import get_utc_now
    initial_status = QuestStatus.IN_PROGRESS if auto_assign else QuestStatus.NOT_STARTED
    started_at = get_utc_now() if auto_assign else None

    # Assign the quest to each character
    assigned = 0
    skipped = 0
    errors = []
    for char_id in character_ids:
        # Check if QuestLog already exists
        existing = QuestLog.query.filter_by(character_id=char_id, quest_id=quest_id).first()
        if existing:
            skipped += 1
            continue
        # Assign coordinates
        coords = find_available_coordinates(char_id, db.session)
        if not coords:
            errors.append(f"No available coordinates for character {char_id}")
            continue
        new_log = QuestLog(
            character_id=char_id,
            quest_id=quest_id,
            status=initial_status,
            x_coordinate=coords[0],
            y_coordinate=coords[1],
            started_at=started_at
        )
        db.session.add(new_log)
        assigned += 1
    db.session.commit()
    assignment_type = "Auto-assigned" if auto_assign else "Assigned"
    msg = f"{assignment_type} quest to {assigned} character(s)."
    if skipped:
        msg += f" Skipped {skipped} already assigned."
    if errors:
        msg += " Errors: " + "; ".join(errors)
    flash(msg, 'info' if assigned else 'warning')
    return redirect(url_for('teacher_quests.list_quests'))

@teacher_quests_bp.route('/assignment_data', methods=['GET'])
@login_required
def assignment_data():
    class_id = request.args.get('class_id', type=int)
    # Get all active classes for this teacher
    classes = Classroom.query.filter_by(teacher_id=current_user.id, is_active=True).all()
    classes_data = [{'id': c.id, 'name': c.name} for c in classes]
    result = {'classes': classes_data}
    if class_id:
        # Get clans in this class
        clans = Clan.query.filter_by(class_id=class_id, is_active=True).all()
        clans_data = [{'id': clan.id, 'name': clan.name} for clan in clans]
        # Get students with active characters in this class
        students_query = db.session.query(Student, Character).\
            join(Character, (Character.student_id == Student.id) & (Character.is_active == True)).\
            filter(Student.class_id == class_id)
        students_data = [
            {
                'id': student.id,
                'name': student.user.display_name if hasattr(student, 'user') and student.user else f'Student {student.id}',
                'character_id': character.id,
                'character_name': character.name
            }
            for student, character in students_query.all()
        ]
        result['clans'] = clans_data
        result['students'] = students_data
    return jsonify(result)

@teacher_quests_bp.route('/chain/<int:quest_id>', methods=['GET'])
@login_required
def view_quest_chain(quest_id):
    """View quest chain visualization showing parent/child relationships."""
    quest = Quest.query.get_or_404(quest_id)
    
    # Build chain: find all ancestors (parents, grandparents, etc.)
    ancestors = []
    current = quest
    visited = set()  # Prevent infinite loops
    while current and current.parent_quest_id and current.parent_quest_id not in visited:
        visited.add(current.parent_quest_id)
        parent = Quest.query.get(current.parent_quest_id)
        if parent:
            ancestors.append(parent)
            current = parent
        else:
            break
    
    ancestors.reverse()  # Show from root to current
    
    # Find all children (quests that have this quest as parent)
    children = Quest.query.filter_by(parent_quest_id=quest_id).order_by(Quest.title).all()
    
    # Find all descendants (children, grandchildren, etc.)
    def get_descendants(quest_id, visited=None):
        if visited is None:
            visited = set()
        if quest_id in visited:
            return []
        visited.add(quest_id)
        direct_children = Quest.query.filter_by(parent_quest_id=quest_id).all()
        descendants = list(direct_children)
        for child in direct_children:
            descendants.extend(get_descendants(child.id, visited))
        return descendants
    
    all_descendants = get_descendants(quest_id)
    
    return render_template('teacher/quest_chain.html', 
                         quest=quest, 
                         ancestors=ancestors, 
                         children=children,
                         all_descendants=all_descendants)

@teacher_quests_bp.route('/progress', methods=['GET'])
@login_required
@teacher_required
def quest_progress():
    """View student quest progress with filtering options."""
    # Get filter parameters
    class_id = request.args.get('class_id', type=int)
    quest_id = request.args.get('quest_id', type=int)
    chain_quest_id = request.args.get('chain_quest_id', type=int)  # Show all quests in this chain
    
    # Get all classes for the teacher
    classes = Classroom.query.filter_by(teacher_id=current_user.id, is_active=True).all()
    selected_class = None
    
    # Get all quests for filtering
    all_quests = Quest.query.order_by(Quest.title).all()
    
    # Build query for quest logs
    query = db.session.query(QuestLog, Quest, Character, Student, User, Classroom).\
        join(Quest, QuestLog.quest_id == Quest.id).\
        join(Character, QuestLog.character_id == Character.id).\
        join(Student, Character.student_id == Student.id).\
        join(User, Student.user_id == User.id).\
        join(Classroom, Student.class_id == Classroom.id).\
        filter(Classroom.teacher_id == current_user.id)
    
    # Apply filters
    if class_id:
        query = query.filter(Student.class_id == class_id)
        selected_class = Classroom.query.filter_by(id=class_id, teacher_id=current_user.id).first()
    
    if quest_id:
        query = query.filter(Quest.id == quest_id)
    
    if chain_quest_id:
        # Get all quests in the chain
        chain_quest = Quest.query.get(chain_quest_id)
        if chain_quest:
            chain_context = chain_quest.get_quest_chain_context()
            chain_quest_ids = [q.id for q in chain_context['ancestors']]
            chain_quest_ids.append(chain_quest.id)
            chain_quest_ids.extend([q.id for q in chain_context['all_descendants']])
            query = query.filter(Quest.id.in_(chain_quest_ids))
    
    # Execute query and group by quest
    results = query.order_by(Quest.title, User.display_name).all()
    
    # Group results by quest
    quest_groups = {}
    for quest_log, quest, character, student, user, classroom in results:
        if quest.id not in quest_groups:
            quest_groups[quest.id] = {
                'quest': quest,
                'students': []
            }
        
        quest_groups[quest.id]['students'].append({
            'quest_log': quest_log,
            'character': character,
            'student': student,
            'user': user,
            'classroom': classroom
        })
    
    # Get chain context for navigation if viewing a specific quest
    chain_context = None
    if quest_id:
        quest = Quest.query.get(quest_id)
        if quest:
            chain_context = quest.get_quest_chain_context()
    
    return render_template('teacher/quest_progress.html',
                         quest_groups=quest_groups,
                         classes=classes,
                         selected_class=selected_class,
                         all_quests=all_quests,
                         selected_quest_id=quest_id,
                         selected_chain_quest_id=chain_quest_id,
                         chain_context=chain_context)

@teacher_quests_bp.route('/start/<int:quest_log_id>', methods=['POST'])
@login_required
@teacher_required
def start_quest_for_student(quest_log_id):
    """Start a quest for a student (move from NOT_STARTED to IN_PROGRESS)."""
    logger.info(f"Quest start request received for quest_log_id={quest_log_id} by user={current_user.id}")
    try:
        # Get quest log with all necessary relationships
        quest_log = QuestLog.query.get_or_404(quest_log_id)
        character = Character.query.get_or_404(quest_log.character_id)
        student = Student.query.get_or_404(character.student_id)
        classroom = Classroom.query.get_or_404(student.class_id)
        quest = Quest.query.get_or_404(quest_log.quest_id)
        
        # Permission check: ensure teacher owns this student's class
        if classroom.teacher_id != current_user.id:
            return jsonify({'success': False, 'error': 'Unauthorized access'}), 403
        
        # Validate quest status
        if quest_log.status != QuestStatus.NOT_STARTED:
            return jsonify({
                'success': False,
                'error': f'Quest must be NOT_STARTED to start. Current status: {quest_log.status.value}'
            }), 400
        
        # Start the quest (sets status to IN_PROGRESS and started_at timestamp)
        quest_log.start_quest()
        db.session.commit()
        
        logger.info(f"Quest {quest.id} started successfully for character {character.id}")
        
        return jsonify({
            'success': True,
            'message': f'Quest "{quest.title}" started successfully for {student.user.display_name if hasattr(student, "user") and student.user else "student"}!',
            'quest_log_id': quest_log.id,
            'new_status': quest_log.status.value,
            'started_at': quest_log.started_at.isoformat() if quest_log.started_at else None
        })
        
    except ValueError as e:
        db.session.rollback()
        logger.warning(f"ValueError starting quest {quest_log_id}: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error starting quest {quest_log_id}: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': f'Error starting quest: {str(e)}'
        }), 500

@teacher_quests_bp.route('/complete/<int:quest_log_id>', methods=['POST'])
@login_required
@teacher_required
def complete_quest_for_student(quest_log_id):
    """Mark a quest as completed for a student and unlock next quest in chain."""
    logger.info(f"Quest completion request received for quest_log_id={quest_log_id} by user={current_user.id}")
    try:
        # Get quest log with all necessary relationships
        quest_log = QuestLog.query.get_or_404(quest_log_id)
        character = Character.query.get_or_404(quest_log.character_id)
        student = Student.query.get_or_404(character.student_id)
        classroom = Classroom.query.get_or_404(student.class_id)
        quest = Quest.query.get_or_404(quest_log.quest_id)
        
        # Permission check: ensure teacher owns this student's class
        if classroom.teacher_id != current_user.id:
            return jsonify({'success': False, 'error': 'Unauthorized access'}), 403
        
        # Validate quest status
        if quest_log.status != QuestStatus.IN_PROGRESS:
            return jsonify({
                'success': False,
                'error': f'Quest must be IN_PROGRESS to complete. Current status: {quest_log.status.value}'
            }), 400
        
        # Import models needed for reward tracking
        from app.models.equipment import Equipment
        from app.models.ability import Ability
        
        # Capture character state before completion
        old_gold = character.gold
        old_experience = character.experience
        old_level = character.level
        
        # Get current equipment IDs
        old_equipment_ids = set(
            inv.item_id for inv in Inventory.query.filter_by(character_id=character.id).all()
        )
        
        # Get current ability IDs
        old_ability_ids = set(
            ca.ability_id for ca in CharacterAbility.query.filter_by(character_id=character.id).all()
        )
        
        # Complete the quest (this awards rewards)
        quest_log.complete_quest()
        
        # Refresh character to get updated values
        db.session.refresh(character)
        
        # Calculate rewards distributed
        gold_gained = character.gold - old_gold
        xp_gained = character.experience - old_experience
        levels_gained = character.level - old_level
        
        # Get new equipment IDs
        new_equipment_ids = set(
            inv.item_id for inv in Inventory.query.filter_by(character_id=character.id).all()
        )
        equipment_awarded_ids = list(new_equipment_ids - old_equipment_ids)
        
        # Get equipment names for awarded items
        equipment_awarded = []
        for item_id in equipment_awarded_ids:
            item = Equipment.query.get(item_id)
            if item:
                equipment_awarded.append({'id': item_id, 'name': item.name})
        
        # Get new ability IDs
        new_ability_ids = set(
            ca.ability_id for ca in CharacterAbility.query.filter_by(character_id=character.id).all()
        )
        abilities_awarded_ids = list(new_ability_ids - old_ability_ids)
        
        # Get ability names for awarded abilities
        abilities_awarded = []
        for ability_id in abilities_awarded_ids:
            ability = Ability.query.get(ability_id)
            if ability:
                abilities_awarded.append({'id': ability_id, 'name': ability.name})
        
        # Collect reward details from quest.rewards
        rewards_detail = []
        for reward in quest.rewards:
            reward_info = {
                'type': reward.type.value,
                'amount': reward.amount
            }
            if reward.type == RewardType.EQUIPMENT and reward.item_id:
                item = Equipment.query.get(reward.item_id)
                if item:
                    reward_info['item_id'] = reward.item_id
                    reward_info['item_name'] = item.name
            elif reward.type == RewardType.ABILITY and reward.ability_id:
                ability = Ability.query.get(reward.ability_id)
                if ability:
                    reward_info['ability_id'] = reward.ability_id
                    reward_info['ability_name'] = ability.name
            rewards_detail.append(reward_info)
        
        # Unlock next quests in chain
        next_quests = quest.get_next_quests_in_chain()
        unlocked_quests = []
        
        for next_quest in next_quests:
            # Check if already assigned
            existing = QuestLog.query.filter_by(
                character_id=character.id,
                quest_id=next_quest.id
            ).first()
            
            if not existing:
                try:
                    # Assign next quest with available coordinates
                    coords = find_available_coordinates(character.id, db.session)
                    new_log = QuestLog(
                        character_id=character.id,
                        quest_id=next_quest.id,
                        status=QuestStatus.NOT_STARTED,
                        x_coordinate=coords[0],
                        y_coordinate=coords[1]
                    )
                    db.session.add(new_log)
                    unlocked_quests.append({
                        'id': next_quest.id,
                        'title': next_quest.title
                    })
                except ValueError as e:
                    # No coordinates available - log but don't fail
                    logger.warning(f"Could not assign next quest {next_quest.id} to character {character.id}: {str(e)}")
        
        # Create audit log entry
        event_data = {
            'quest_id': quest.id,
            'quest_title': quest.title,
            'student_id': student.id,
            'student_name': student.user.get_display_name() if student.user else 'Unknown',
            'character_id': character.id,
            'character_name': character.name,
            'rewards_distributed': {
                'gold': gold_gained,
                'experience': xp_gained,
                'levels_gained': levels_gained,
                'equipment': equipment_awarded,
                'abilities': abilities_awarded
            },
            'rewards_detail': rewards_detail,
            'completed_at': quest_log.completed_at.isoformat() if quest_log.completed_at else None,
            'unlocked_quests': unlocked_quests,
            'marked_complete_by': {
                'user_id': current_user.id,
                'user_name': current_user.get_display_name() if hasattr(current_user, 'get_display_name') else current_user.username
            }
        }
        
        AuditLog.log_event(
            event_type=EventType.QUEST_COMPLETE,
            event_data=event_data,
            user_id=current_user.id,
            character_id=character.id
        )
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Quest "{quest.title}" completed successfully!',
            'unlocked_quests': unlocked_quests,
            'quest_log_id': quest_log.id,
            'new_status': quest_log.status.value
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error completing quest {quest_log_id}: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': f'Error completing quest: {str(e)}'
        }), 500 