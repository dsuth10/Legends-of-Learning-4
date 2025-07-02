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

teacher_quests_bp = Blueprint('teacher_quests', __name__, url_prefix='/teacher/quests')

@teacher_quests_bp.route('/', methods=['GET'])
@login_required
def list_quests():
    db.session.expire_all()  # Force session to reload from DB
    quests = Quest.query.order_by(Quest.id.desc()).all()
    return render_template('teacher/quests.html', quests=quests)

@teacher_quests_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create_quest():
    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        quest_type = request.form['type']
        gold_reward = request.form.get('gold_reward', type=int, default=0)
        xp_reward = request.form.get('xp_reward', type=int, default=0)
        new_quest = Quest(
            title=title,
            description=description,
            type=quest_type
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
    return render_template('teacher/quest_form.html', quest=None)

@teacher_quests_bp.route('/edit/<int:quest_id>', methods=['GET', 'POST'])
@login_required
def edit_quest(quest_id):
    quest = Quest.query.get_or_404(quest_id)
    if request.method == 'POST':
        quest.title = request.form['title']
        quest.description = request.form['description']
        quest.type = request.form['type']
        gold_reward = request.form.get('gold_reward', type=int, default=0)
        xp_reward = request.form.get('xp_reward', type=int, default=0)
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
    # Get current gold/xp rewards for form
    gold_reward = quest.rewards.filter_by(type=RewardType.GOLD).first().amount if quest.rewards.filter_by(type=RewardType.GOLD).first() else 0
    xp_reward = quest.rewards.filter_by(type=RewardType.EXPERIENCE).first().amount if quest.rewards.filter_by(type=RewardType.EXPERIENCE).first() else 0
    return render_template('teacher/quest_form.html', quest=quest, gold_reward=gold_reward, xp_reward=xp_reward)

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
        characters = Character.query.join('student').filter(
            Character.is_active == True,
            Character.student.has(class_id=class_id)
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