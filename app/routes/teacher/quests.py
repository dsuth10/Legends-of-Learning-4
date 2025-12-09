from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from app.models import db
from app.models.quest import Quest, QuestType, Reward, RewardType
from app.models.student import Student
from app.models.character import Character
from app.models.clan import Clan
from app.models.classroom import Classroom
from app.models.quest import QuestLog, QuestStatus
from app.services.quest_map_utils import find_available_coordinates
from datetime import datetime
import json

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
            status='NOT_STARTED',
            x_coordinate=coords[0],
            y_coordinate=coords[1]
        )
        db.session.add(new_log)
        assigned += 1
    db.session.commit()
    msg = f"Assigned quest to {assigned} character(s)."
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