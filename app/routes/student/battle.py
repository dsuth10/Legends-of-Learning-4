from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from app.models import db
from app.models.battle import Monster, Battle, BattleStatus
from app.models.education import QuestionSet, Question
from app.models.student import Student
from app.models.character import Character
from app.routes.student_main import student_required
import random
import json
import time

student_battle_bp = Blueprint('student_battle', __name__, url_prefix='/student/battle')

@student_battle_bp.route('/', methods=['GET'])
@login_required
@student_required
def arena():
    """Battle arena dashboard - select monster and question set."""
    student_profile = Student.query.filter_by(user_id=current_user.id).first()
    if not student_profile:
        flash('Student profile not found.', 'danger')
        return redirect(url_for('student.character'))
    
    character = student_profile.characters.filter_by(is_active=True).first()
    if not character:
        flash('You need to create a character first.', 'warning')
        return redirect(url_for('student.character_create'))
    
    # Get all monsters
    monsters = Monster.query.all()
    
    # Get active question sets
    question_sets = QuestionSet.query.filter_by(is_active=True).all()
    
    # Get active battles for this student
    active_battles = Battle.query.filter_by(
        student_id=student_profile.id,
        status=BattleStatus.ACTIVE
    ).all()
    
    return render_template('student/battle/arena.html', 
                         character=character,
                         monsters=monsters,
                         question_sets=question_sets,
                         active_battles=active_battles,
                         active_page='battle')

@student_battle_bp.route('/start', methods=['POST'])
@login_required
@student_required
def start_battle():
    """Initialize a new battle."""
    student_profile = Student.query.filter_by(user_id=current_user.id).first()
    if not student_profile:
        flash('Student profile not found.', 'danger')
        return redirect(url_for('student.character'))
    
    character = student_profile.characters.filter_by(is_active=True).first()
    if not character:
        flash('You need to create a character first.', 'warning')
        return redirect(url_for('student.character_create'))
    
    monster_id = request.form.get('monster_id', type=int)
    question_set_id = request.form.get('question_set_id', type=int)
    
    if not monster_id or not question_set_id:
        flash('Please select both a monster and a question set.', 'danger')
        return redirect(url_for('student_battle.arena'))
    
    monster = Monster.query.get_or_404(monster_id)
    question_set = QuestionSet.query.get_or_404(question_set_id)
    
    # Check if question set has questions
    if question_set.questions.count() == 0:
        flash('This question set has no questions yet.', 'warning')
        return redirect(url_for('student_battle.arena'))
    
    # Create new battle
    new_battle = Battle(
        student_id=student_profile.id,
        monster_id=monster.id,
        question_set_id=question_set.id,
        player_health=character.health,
        player_max_health=character.max_health,
        monster_health=monster.health,
        monster_max_health=monster.health,
        status=BattleStatus.ACTIVE,
        turn_log=[]
    )
    db.session.add(new_battle)
    db.session.commit()
    
    flash(f'Battle started against {monster.name}!', 'success')
    return redirect(url_for('student_battle.fight', battle_id=new_battle.id))

@student_battle_bp.route('/<int:battle_id>', methods=['GET'])
@login_required
@student_required
def fight(battle_id):
    """Battle interface - show current battle state and question."""
    student_profile = Student.query.filter_by(user_id=current_user.id).first()
    if not student_profile:
        flash('Student profile not found.', 'danger')
        return redirect(url_for('student.character'))
    
    battle = Battle.query.filter_by(id=battle_id, student_id=student_profile.id).first_or_404()
    
    # If battle is over, redirect to results
    if battle.status != BattleStatus.ACTIVE:
        return redirect(url_for('student_battle.results', battle_id=battle.id))
    
    # Get a random question from the set
    questions = battle.question_set.questions.all()
    if not questions:
        flash('No questions available in this set.', 'danger')
        return redirect(url_for('student_battle.arena'))
    
    current_question = random.choice(questions)
    
    # Get equipped abilities for battle context
    equipped_abilities = []
    if character:
        from app.models.ability import CharacterAbility
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
            for ca in character.abilities.filter_by(is_equipped=True).all()
        ]
    
    now = int(time.time())
    return render_template('student/battle/fight.html',
                         battle=battle,
                         question=current_question,
                         character=character,
                         equipped_abilities=equipped_abilities,
                         now=now,
                         active_page='battle')

@student_battle_bp.route('/<int:battle_id>/attack', methods=['POST'])
@login_required
@student_required
def attack(battle_id):
    """Process answer and calculate damage."""
    student_profile = Student.query.filter_by(user_id=current_user.id).first()
    if not student_profile:
        return jsonify({'success': False, 'message': 'Student profile not found'}), 400
    
    character = student_profile.characters.filter_by(is_active=True).first()
    battle = Battle.query.filter_by(id=battle_id, student_id=student_profile.id).first_or_404()
    
    if battle.status != BattleStatus.ACTIVE:
        return jsonify({'success': False, 'message': 'Battle is not active'}), 400
    
    # Get submitted answer
    submitted_answer = request.form.get('answer', '').strip()
    question_id = request.form.get('question_id', type=int)
    
    question = Question.query.get_or_404(question_id)
    
    # Check if answer is correct
    is_correct = submitted_answer == question.correct_answer
    
    # Calculate damage
    base_damage = character.power
    if is_correct:
        # Player attacks monster
        damage = base_damage + (question.difficulty * 5)  # Bonus for difficulty
        battle.monster_health -= damage
        turn_result = {
            'turn': len(battle.turn_log) + 1,
            'correct': True,
            'damage_dealt': damage,
            'damage_taken': 0,
            'question': question.text,
            'player_answer': submitted_answer
        }
    else:
        # Monster attacks player
        monster_damage = battle.monster.attack
        battle.player_health -= monster_damage
        turn_result = {
            'turn': len(battle.turn_log) + 1,
            'correct': False,
            'damage_dealt': 0,
            'damage_taken': monster_damage,
            'question': question.text,
            'player_answer': submitted_answer,
            'correct_answer': question.correct_answer
        }
    
    # Update turn log
    turn_log = battle.turn_log if battle.turn_log else []
    turn_log.append(turn_result)
    battle.turn_log = turn_log
    
    # Check for battle end
    battle_ended = False
    if battle.monster_health <= 0:
        battle.status = BattleStatus.WON
        battle.monster_health = 0
        battle_ended = True
        
        # Award rewards
        character.experience += battle.monster.xp_reward
        character.gold += battle.monster.gold_reward
        
        # Check for level up
        xp_needed = character.level * 100
        if character.experience >= xp_needed:
            character.level_up()
        
    elif battle.player_health <= 0:
        battle.status = BattleStatus.LOST
        battle.player_health = 0
        battle_ended = True
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'correct': is_correct,
        'battle_ended': battle_ended,
        'battle_status': battle.status.value if battle_ended else 'active',
        'player_health': battle.player_health,
        'player_max_health': battle.player_max_health,
        'monster_health': battle.monster_health,
        'monster_max_health': battle.monster_max_health,
        'turn_result': turn_result,
        'redirect_url': url_for('student_battle.results', battle_id=battle.id) if battle_ended else None
    })

@student_battle_bp.route('/<int:battle_id>/flee', methods=['POST'])
@login_required
@student_required
def flee(battle_id):
    """Flee from battle."""
    student_profile = Student.query.filter_by(user_id=current_user.id).first()
    battle = Battle.query.filter_by(id=battle_id, student_id=student_profile.id).first_or_404()
    
    if battle.status == BattleStatus.ACTIVE:
        battle.status = BattleStatus.FLED
        db.session.commit()
        flash('You fled from the battle!', 'warning')
    
    return redirect(url_for('student_battle.arena'))

@student_battle_bp.route('/<int:battle_id>/results', methods=['GET'])
@login_required
@student_required
def results(battle_id):
    """Show battle results."""
    student_profile = Student.query.filter_by(user_id=current_user.id).first()
    battle = Battle.query.filter_by(id=battle_id, student_id=student_profile.id).first_or_404()
    
    return render_template('student/battle/results.html',
                         battle=battle,
                         active_page='battle')
