from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app.models import db
from app.models.quest import Quest, QuestType, Reward, RewardType

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