
import sys
import os

# Add the project directory to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.models import db, Base
from app.models.quest import Quest, QuestLog, QuestType, QuestStatus
from app.models.education import QuestionSet, Question
from app.models.battle import Battle, BattleStatus, Monster
from app.models.student import Student
from app.models.character import Character
from app.models.user import User
from app.models.classroom import Classroom
from app.models.student import Student
from app.models.character import Character
from app.models.user import User, UserRole
from app.models.classroom import Classroom
from app.models.clan import Clan
from app.models.teacher import Teacher
from app.models.equipment import Equipment
from app.models.ability import Ability
from app.models.audit import AuditLog

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime

# Setup in-memory DB
engine = create_engine('sqlite:///:memory:')
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)
session = Session()

# Mock DB session in models (since they import db.session or rely on request context usually, but we are hacking it for this script)
# However, the models use `db.Column` which are bound to `db`.
# To make this work without Flask app context, we might need a minimal Flask app.
# Or we can patch `db.session` if the methods rely on it.
# The `check_completion` method uses `Battle.query`. This requires a Flask app context with SQLA setup.

from flask import Flask
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# We need to initialize db with app
# But db is already imported from app.models
from app.models import db
db.init_app(app)

with app.app_context():
    db.create_all()
    
    # 1. Setup Student and Character
    user = User(username='test_student', email='test@example.com', role=UserRole.STUDENT, password_hash='dummy')
    db.session.add(user)
    db.session.commit()
    
    student = Student(user_id=user.id)
    db.session.add(student)
    db.session.commit()
    
    character = Character(name='Hero', student_id=student.id)
    db.session.add(character)
    db.session.commit()
    
    # 2. Setup Question Set and Monster
    teacher_user = User(username='teacher', email='t@t.com', role=UserRole.TEACHER, password_hash='dummy')
    db.session.add(teacher_user)
    db.session.commit()
    
    # Need a teacher model? Yes
    from app.models.teacher import Teacher
    teacher = Teacher(user_id=teacher_user.id)
    db.session.add(teacher)
    db.session.commit()
    
    qset = QuestionSet(title='Algebra Quiz', teacher_id=teacher.id)
    db.session.add(qset)
    
    monster = Monster(name='Goblin', health=100)
    db.session.add(monster)
    db.session.commit()
    
    # 3. Create Quests
    # Quest A: Defeat 1 Goblin
    quest_monster = Quest(
        title='Slayer',
        description='Kill a goblin',
        type=QuestType.DAILY,
        requirements={'level': 1},
        completion_criteria={'count': 1}
    )
    quest_monster.monster_id = monster.id
    db.session.add(quest_monster)
    
    # Quest B: Pass Algebra Quiz (> 50%)
    quest_quiz = Quest(
        title='Math Whiz',
        description='Pass the quiz',
        type=QuestType.STORY,
        requirements={'level': 1},
        completion_criteria={'min_score_percent': 50}
    )
    quest_quiz.question_set_id = qset.id
    db.session.add(quest_quiz)
    
    db.session.commit()
    
    # 4. Assign Quests
    log_monster = QuestLog(character_id=character.id, quest_id=quest_monster.id, status=QuestStatus.IN_PROGRESS)
    log_quiz = QuestLog(character_id=character.id, quest_id=quest_quiz.id, status=QuestStatus.IN_PROGRESS)
    
    db.session.add(log_monster)
    db.session.add(log_quiz)
    db.session.commit()
    
    print("Initial Checks:")
    print(f"Monster Quest Complete? {log_monster.check_completion()}")
    print(f"Quiz Quest Complete? {log_quiz.check_completion()}")
    
    # 5. Simulate Battle (Monster) - WON
    battle1 = Battle(
        student_id=student.id,
        monster_id=monster.id,
        player_health=100, player_max_health=100, monster_health=0, monster_max_health=100,
        status=BattleStatus.WON,
        turn_log=[{'action': 'attack'}]
    )
    db.session.add(battle1)
    db.session.commit()
    
    print("\nAfter Monster Battle (WON):")
    is_complete = log_monster.check_completion()
    print(f"Monster Quest Complete? {is_complete}")
    if not is_complete:
        print("FAIL: Monster quest should be complete")
        
    # 6. Simulate Battle (Quiz) - FAILED Score (0%)
    battle2 = Battle(
        student_id=student.id,
        monster_id=monster.id, # Any monster
        question_set_id=qset.id,
        player_health=100, player_max_health=100, monster_health=100, monster_max_health=100,
        status=BattleStatus.WON, # Even if won battle, score matters? Logic says status=WON AND score
        turn_log=[{'correct': False}, {'correct': False}]
    )
    db.session.add(battle2)
    db.session.commit()
    
    print("\nAfter Quiz Battle (0% score):")
    print(f"Quiz Quest Complete? {log_quiz.check_completion()}")
    
    # 7. Simulate Battle (Quiz) - PASS Score (100%)
    battle3 = Battle(
        student_id=student.id,
        monster_id=monster.id,
        question_set_id=qset.id,
        player_health=100, player_max_health=100, monster_health=0, monster_max_health=100,
        status=BattleStatus.WON,
        turn_log=[{'correct': True}, {'correct': True}]
    )
    db.session.add(battle3)
    db.session.commit()
    
    print("\nAfter Quiz Battle (100% score):")
    is_complete_quiz = log_quiz.check_completion()
    print(f"Quiz Quest Complete? {is_complete_quiz}")
    if not is_complete_quiz:
        print("FAIL: Quiz quest should be complete")

