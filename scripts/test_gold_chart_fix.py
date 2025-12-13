"""
Test script to verify the gold chart fix.

This script:
1. Creates a new student with a character
2. Creates a quest with a gold reward
3. Completes the quest
4. Verifies AuditLog entries are created
5. Tests the progress page to verify gold chart data
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db
from app.models.user import User, UserRole
from app.models.student import Student
from app.models.character import Character
from app.models.classroom import Classroom
from app.models.quest import Quest, QuestLog, QuestStatus, Reward, RewardType
from app.models.audit import AuditLog, EventType
from flask_login import login_user
from datetime import datetime
import uuid

def test_gold_chart_fix():
    """Test that gold rewards from quests are logged to AuditLog."""
    
    app = create_app()
    
    with app.app_context():
        # Clean up any existing test data (optional - comment out if you want to keep test data)
        # test_user = User.query.filter_by(username='test_gold_student').first()
        # if test_user:
        #     db.session.delete(test_user)
        #     db.session.commit()
        
        # 1. Create a test teacher and classroom
        unique_id = uuid.uuid4().hex[:8]
        teacher = User(
            username=f'test_teacher_{unique_id}',
            email=f'teacher_{unique_id}@test.com',
            role=UserRole.TEACHER
        )
        teacher.set_password('password123')
        db.session.add(teacher)
        db.session.commit()
        
        classroom = Classroom(
            name=f'Test Class {unique_id}',
            teacher_id=teacher.id,
            join_code=f'TEST{unique_id[:5]}'
        )
        db.session.add(classroom)
        db.session.commit()
        
        # 2. Create a test student with character
        student_user = User(
            username=f'test_gold_student_{unique_id}',
            email=f'student_{unique_id}@test.com',
            role=UserRole.STUDENT
        )
        student_user.set_password('password123')
        db.session.add(student_user)
        db.session.commit()
        
        student_profile = Student(
            user_id=student_user.id,
            class_id=classroom.id,
            level=1,
            gold=0,  # Start with 0 gold
            xp=0
        )
        db.session.add(student_profile)
        db.session.commit()
        
        character = Character(
            name='Test Hero',
            student_id=student_profile.id,
            character_class='Warrior',
            level=1,
            experience=0,
            gold=0,  # Start with 0 gold
            health=100,
            max_health=100,
            power=10,
            defense=10,
            is_active=True
        )
        db.session.add(character)
        db.session.commit()
        
        print(f"[OK] Created test student: {student_user.username}")
        print(f"[OK] Created test character: {character.name} (ID: {character.id})")
        print(f"  Initial gold: {character.gold}")
        
        # 3. Create a quest with a gold reward
        quest = Quest(
            title='Test Gold Quest',
            description='Complete this quest to earn gold',
            type='story',
            level_requirement=1
        )
        db.session.add(quest)
        db.session.commit()
        
        # Add gold reward
        gold_reward = Reward(
            quest_id=quest.id,
            type=RewardType.GOLD,
            amount=150  # Award 150 gold
        )
        db.session.add(gold_reward)
        db.session.commit()
        
        print(f"[OK] Created quest: {quest.title} (ID: {quest.id})")
        print(f"[OK] Added gold reward: {gold_reward.amount} gold")
        
        # 4. Create a QuestLog and complete the quest
        quest_log = QuestLog(
            character_id=character.id,
            quest_id=quest.id,
            status=QuestStatus.IN_PROGRESS
        )
        db.session.add(quest_log)
        db.session.commit()
        
        print(f"[OK] Created QuestLog (ID: {quest_log.id})")
        
        # Get initial gold count
        initial_gold = character.gold
        initial_audit_count = AuditLog.query.filter_by(
            character_id=character.id,
            event_type=EventType.GOLD_TRANSACTION.value
        ).count()
        
        print(f"\nBefore quest completion:")
        print(f"  Character gold: {initial_gold}")
        print(f"  Existing GOLD_TRANSACTION audit logs: {initial_audit_count}")
        
        # Complete the quest
        print(f"\nCompleting quest...")
        quest_log.complete_quest()
        
        # Refresh character to get updated values
        db.session.refresh(character)
        
        # 5. Verify the results
        final_gold = character.gold
        gold_earned = final_gold - initial_gold
        
        # Check AuditLog entries
        gold_audit_logs = AuditLog.query.filter_by(
            character_id=character.id,
            event_type=EventType.GOLD_TRANSACTION.value
        ).order_by(AuditLog.event_timestamp.desc()).all()
        
        new_gold_logs = gold_audit_logs[:len(gold_audit_logs) - initial_audit_count] if initial_audit_count > 0 else gold_audit_logs
        
        print(f"\nAfter quest completion:")
        print(f"  Character gold: {final_gold} (earned: {gold_earned})")
        print(f"  Total GOLD_TRANSACTION audit logs: {len(gold_audit_logs)}")
        print(f"  New GOLD_TRANSACTION audit logs: {len(new_gold_logs)}")
        
        # Verify the fix
        success = True
        issues = []
        
        if gold_earned != gold_reward.amount:
            success = False
            issues.append(f"Gold earned ({gold_earned}) doesn't match reward amount ({gold_reward.amount})")
        
        if len(new_gold_logs) == 0:
            success = False
            issues.append("No new GOLD_TRANSACTION audit logs were created!")
        else:
            latest_log = new_gold_logs[0]
            log_data = latest_log.event_data
            if log_data.get('amount') != gold_reward.amount:
                success = False
                issues.append(f"AuditLog amount ({log_data.get('amount')}) doesn't match reward amount ({gold_reward.amount})")
            if log_data.get('source') != 'quest_reward':
                success = False
                issues.append(f"AuditLog source is '{log_data.get('source')}', expected 'quest_reward'")
            if log_data.get('quest_id') != quest.id:
                success = False
                issues.append(f"AuditLog quest_id ({log_data.get('quest_id')}) doesn't match quest.id ({quest.id})")
        
        # 6. Verify progress page data can be queried
        print(f"\n{'='*60}")
        print("Verifying progress page data query...")
        print(f"{'='*60}")
        
        # Simulate the progress page query logic
        from collections import defaultdict
        from datetime import datetime, timedelta
        
        # Get gold earned events (from AuditLog)
        gold_earned_events = AuditLog.query.filter_by(
            character_id=character.id,
            event_type=EventType.GOLD_TRANSACTION.value
        ).all()
        
        gold_earned_by_date = defaultdict(int)
        for event in gold_earned_events:
            event_date = event.event_timestamp.date()
            amount = event.event_data.get('amount', 0)
            gold_earned_by_date[event_date] += amount
        
        # Get gold spent events (from ShopPurchase)
        from app.models.shop import ShopPurchase
        purchases = ShopPurchase.query.filter_by(character_id=character.id).all()
        gold_spent_by_date = defaultdict(int)
        for purchase in purchases:
            purchase_date = purchase.purchased_at.date()
            gold_spent_by_date[purchase_date] += purchase.gold_spent
        
        # Combine all dates
        all_gold_dates = set(gold_earned_by_date.keys()) | set(gold_spent_by_date.keys())
        
        if all_gold_dates:
            gold_dates = sorted(all_gold_dates)
            gold_earned_values = [gold_earned_by_date.get(d, 0) for d in gold_dates]
            gold_spent_values = [gold_spent_by_date.get(d, 0) for d in gold_dates]
            print(f"[OK] Gold chart data can be generated:")
            print(f"  - Dates with transactions: {len(gold_dates)}")
            print(f"  - Total gold earned: {sum(gold_earned_values)}")
            print(f"  - Total gold spent: {sum(gold_spent_values)}")
            if gold_earned_values:
                print(f"  - Latest earned: {gold_earned_values[-1]} on {gold_dates[-1]}")
        else:
            print("[WARN] No gold transaction dates found (this is expected if no purchases made)")
        
        # Final summary
        print(f"\n{'='*60}")
        print("TEST SUMMARY")
        print(f"{'='*60}")
        
        if success:
            print("[SUCCESS] Gold chart fix is working correctly!")
            print(f"\nDetails:")
            print(f"  - Gold reward distributed: {gold_reward.amount} gold")
            print(f"  - Character gold updated: {initial_gold} -> {final_gold}")
            print(f"  - AuditLog entry created: YES")
            if new_gold_logs:
                print(f"  - AuditLog details:")
                log = new_gold_logs[0]
                print(f"    * Event Type: {log.event_type}")
                print(f"    * Amount: {log.event_data.get('amount')}")
                print(f"    * Action: {log.event_data.get('action')}")
                print(f"    * Quest ID: {log.event_data.get('quest_id')}")
                print(f"    * Timestamp: {log.event_timestamp}")
        else:
            print("[FAILURE] Issues found with gold chart fix!")
            print(f"\nIssues:")
            for issue in issues:
                print(f"  - {issue}")
        
        print(f"\n{'='*60}")
        print("Test student credentials:")
        print(f"  Username: {student_user.username}")
        print(f"  Password: password123")
        print(f"  Character: {character.name} (ID: {character.id})")
        print(f"  Current Gold: {character.gold}")
        print(f"{'='*60}\n")
        
        return success

if __name__ == '__main__':
    try:
        success = test_gold_chart_fix()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n[ERROR] Test failed with exception:")
        print(f"   {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

