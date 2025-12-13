from datetime import datetime
from app.utils.date_utils import get_utc_now
from enum import Enum
from typing import List, Optional
from sqlalchemy import String, Integer, Float, DateTime, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from pydantic import BaseModel, Field
import logging

from app.models import db
from app.models.base import Base
from app.models.equipment import Equipment
from app.models.ability import Ability
from app.models.audit import AuditLog, EventType

logger = logging.getLogger(__name__)

class QuestStatus(str, Enum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"

class QuestType(str, Enum):
    STORY = "story"
    DAILY = "daily"
    WEEKLY = "weekly"
    ACHIEVEMENT = "achievement"
    EVENT = "event"

class RewardType(str, Enum):
    EXPERIENCE = "experience"
    GOLD = "gold"
    EQUIPMENT = "equipment"
    ABILITY = "ability"
    CLAN_EXPERIENCE = "clan_experience"
    SPECIAL_CURRENCY = "special_currency"

class Quest(Base):
    """Quest model representing available quests in the game."""
    
    __tablename__ = 'quests'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(128), nullable=False)
    description = db.Column(db.Text, nullable=False)
    type = db.Column(db.Enum(QuestType), nullable=False)
    level_requirement = db.Column(db.Integer, default=1, nullable=False)
    
    # Quest requirements and completion criteria stored as JSON
    requirements = db.Column(JSON, nullable=False, default=dict)
    completion_criteria = db.Column(JSON, nullable=False, default=dict)
    
    # Time constraints (optional)
    start_date = db.Column(db.DateTime, nullable=True)
    end_date = db.Column(db.DateTime, nullable=True)
    time_limit_hours = db.Column(db.Integer, nullable=True)  # Time limit once started
    
    # Quest chain/prerequisites
    # Quest chain/prerequisites
    parent_quest_id = db.Column(db.Integer, db.ForeignKey('quests.id', ondelete='SET NULL'), nullable=True)
    
    # Verification Links
    question_set_id = db.Column(db.Integer, db.ForeignKey('question_sets.id', ondelete='SET NULL'), nullable=True)
    monster_id = db.Column(db.Integer, db.ForeignKey('monsters.id', ondelete='SET NULL'), nullable=True)
    
    # Relationships
    rewards = db.relationship('Reward', backref='quest', lazy='dynamic', cascade='all, delete-orphan')
    consequences = db.relationship('Consequence', backref='quest', lazy='dynamic', cascade='all, delete-orphan')
    quest_logs = db.relationship('QuestLog', backref='quest', lazy='dynamic', cascade='all, delete-orphan')
    
    # New Relationships for verification
    question_set = db.relationship('QuestionSet', backref='linked_quests')
    monster = db.relationship('Monster', backref='linked_quests')
    
    __table_args__ = (
        db.Index('idx_quest_type', 'type'),  # For filtering quests by type
        db.Index('idx_quest_level', 'level_requirement'),  # For level-appropriate quests
        db.Index('idx_quest_dates', 'start_date', 'end_date'),  # For active quests
    )
    
    def __init__(self, title, description, type, **kwargs):
        super().__init__(**kwargs)
        self.title = title
        self.description = description
        self.type = type
    
    def is_available(self, character):
        """Check if quest is available for a character."""
        if self.level_requirement > character.level:
            return False
        
        if self.start_date and get_utc_now() < self.start_date:
            return False
        
        if self.end_date and get_utc_now() > self.end_date:
            return False
        
        # Check if prerequisite quest is completed
        if self.parent_quest_id:
            parent_log = QuestLog.query.filter_by(
                quest_id=self.parent_quest_id,
                character_id=character.id,
                status=QuestStatus.COMPLETED
            ).first()
            if not parent_log:
                return False
        
        return True
    
    def get_next_quests_in_chain(self):
        """Get all quests that have this quest as their parent (next in chain)."""
        return Quest.query.filter_by(parent_quest_id=self.id).all()
    
    def get_quest_chain_context(self):
        """Get full quest chain context: ancestors, current, and descendants."""
        # Build ancestors (parents, grandparents, etc.)
        ancestors = []
        current = self
        visited = set()
        while current and current.parent_quest_id and current.parent_quest_id not in visited:
            visited.add(current.parent_quest_id)
            parent = Quest.query.get(current.parent_quest_id)
            if parent:
                ancestors.append(parent)
                current = parent
            else:
                break
        ancestors.reverse()  # Show from root to current
        
        # Get direct children
        children = Quest.query.filter_by(parent_quest_id=self.id).order_by(Quest.title).all()
        
        # Get all descendants recursively
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
        
        all_descendants = get_descendants(self.id)
        
        return {
            'ancestors': ancestors,
            'current': self,
            'children': children,
            'all_descendants': all_descendants
        }
    
    def __repr__(self):
        return f'<Quest {self.title} ({self.type.value})>'

class QuestLog(Base):
    """Model for tracking character progress on quests."""
    
    __tablename__ = 'quest_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    character_id = db.Column(db.Integer, db.ForeignKey('characters.id', ondelete='CASCADE'), nullable=False)
    quest_id = db.Column(db.Integer, db.ForeignKey('quests.id', ondelete='CASCADE'), nullable=False)
    status = db.Column(db.Enum(QuestStatus), default=QuestStatus.NOT_STARTED, nullable=False)
    
    # Progress tracking
    progress_data = db.Column(JSON, nullable=False, default=dict)  # Store progress details
    started_at = db.Column(db.DateTime, nullable=True)
    completed_at = db.Column(db.DateTime, nullable=True)

    # Map coordinates for quest placement
    x_coordinate = db.Column(db.Integer, nullable=True)
    y_coordinate = db.Column(db.Integer, nullable=True)
    
    # Relationships
    character = db.relationship('Character', backref=db.backref('quest_logs', lazy='dynamic'))
    
    __table_args__ = (
        db.Index('idx_questlog_character', 'character_id'),  # For character's quests
        db.Index('idx_questlog_status', 'character_id', 'status'),  # For filtering by status
        db.UniqueConstraint('character_id', 'quest_id', name='uq_character_quest'),  # One log per quest
        db.UniqueConstraint('character_id', 'x_coordinate', 'y_coordinate', name='uq_character_questlog_map_coord'),  # No overlapping quests on map
    )
    
    def start_quest(self):
        """Start the quest."""
        if self.status != QuestStatus.NOT_STARTED:
            raise ValueError("Quest has already been started")
        
        self.status = QuestStatus.IN_PROGRESS
        self.started_at = get_utc_now()
        self.save()
    
    def update_progress(self, progress_data):
        """Update quest progress."""
        self.progress_data.update(progress_data)
        self.save()
        
    def check_completion(self):
        """
        Verify if the quest completion criteria are partially or fully met.
        Returns True if the quest is ready to be completed.
        """
        if self.status == QuestStatus.COMPLETED:
            return True
        
        is_complete = False
        
        # 1. Check Monster Criteria
        if self.quest.monster_id:
            from app.models.battle import Battle, BattleStatus
            # QuestLog matches to Character, but Battle matches to Student.
            # Character has student_id.
            if not self.character:
                return False # Should not happen if constraint holds
                
            student_id = self.character.student_id
            
            won_battles = Battle.query.filter_by(
                student_id=student_id,
                monster_id=self.quest.monster_id,
                status=BattleStatus.WON
            ).count()
            
            required_count = self.quest.completion_criteria.get('count', 1)
            if won_battles >= required_count:
                is_complete = True
            else:
                return False # Failed monster requirement

        # 2. Check Question Set Criteria
        if self.quest.question_set_id:
            from app.models.battle import Battle, BattleStatus
            
            if not self.character:
                return False
                
            student_id = self.character.student_id
            
            # Find battles with this question set
            battles = Battle.query.filter_by(
                student_id=student_id,
                question_set_id=self.quest.question_set_id,
                status=BattleStatus.WON # Must win the battle? Or just pass the quiz?
                # Usually "Complete the Algebra Quiz" implies passing it.
            ).all()
            
            min_score = self.quest.completion_criteria.get('min_score_percent', 0)
            passed = False
            
            for battle in battles:
                # Calculate score from turn_log
                # turn_log example: [{correct: true}, {correct: false}]
                if not battle.turn_log:
                    continue
                    
                total_questions = len(battle.turn_log)
                if total_questions == 0:
                    continue
                    
                correct_answers = sum(1 for turn in battle.turn_log if turn.get('correct'))
                score_percent = (correct_answers / total_questions) * 100
                
                if score_percent >= min_score:
                    passed = True
                    break
            
            if passed:
                is_complete = True
            else:
                return False

        # If we have no specific linked criteria but are in progress, 
        # check manual progress metrics (existing behavior support)
        if not self.quest.monster_id and not self.quest.question_set_id:
            # Fallback to existing manual progress checks if any
            required_progress = self.quest.completion_criteria.get('progress', 100)
            current_progress = self.progress_data.get('progress', 0)
            if current_progress >= required_progress:
                is_complete = True
                
        return is_complete

    def complete_quest(self):
        """Mark quest as completed and distribute rewards.
        
        This method distributes all rewards in a single transaction to ensure
        atomicity and prevent race conditions. All changes are committed together.
        """
        if self.status != QuestStatus.IN_PROGRESS:
            raise ValueError("Quest must be in progress to complete")
        
        # Ensure character is in session before modifying
        from app.models import db
        db.session.add(self.character)
        
        self.status = QuestStatus.COMPLETED
        self.completed_at = get_utc_now()
        
        # Distribute all rewards in a single transaction (no commits in distribute)
        for reward in self.quest.rewards:
            reward.distribute(self.character, commit=False)
        
        # Single commit for all changes (quest status, rewards, character updates)
        self.save()
        
        # Refresh character to ensure we have the latest values from database
        db.session.refresh(self.character)
    
    def fail_quest(self):
        """Mark quest as failed and apply consequences."""
        self.status = QuestStatus.FAILED
        self.completed_at = get_utc_now()
        
        # Apply all consequences in a single transaction
        for consequence in self.quest.consequences:
            consequence.apply(self.character, commit=False)
        
        # Single commit for all changes
        self.save()
    
    def __repr__(self):
        return f'<QuestLog {self.quest.title} - {self.status.value}>'

class Reward(Base):
    """Model for quest rewards."""
    
    __tablename__ = 'rewards'
    
    id = db.Column(db.Integer, primary_key=True)
    quest_id = db.Column(db.Integer, db.ForeignKey('quests.id', ondelete='CASCADE'), nullable=False)
    type = db.Column(db.Enum(RewardType), nullable=False)
    amount = db.Column(db.Integer, nullable=False, default=0)  # For XP, gold, etc.
    
    # Optional foreign keys for specific rewards
    item_id = db.Column(db.Integer, db.ForeignKey('equipment.id', ondelete='SET NULL'), nullable=True)
    ability_id = db.Column(db.Integer, db.ForeignKey('abilities.id', ondelete='SET NULL'), nullable=True)
    
    def distribute(self, character, session=None, commit=False):
        """Distribute reward to character.
        
        Args:
            character: Character to receive reward
            session: Database session (defaults to db.session)
            commit: Whether to commit after distribution (default: False)
        """
        from app.models import db
        if session is None:
            session = db.session
        
        logger.info(f"Distributing {self.type.value} reward of {self.amount} to character {character.id}")
        
        if self.type == RewardType.EXPERIENCE:
            # Ensure character is in session before modifying
            session.add(character)
            
            # Manually handle experience and level up to avoid premature commit
            # This maintains the single transaction guarantee
            old_level = character.level
            old_experience = character.experience
            character.experience += self.amount
            logger.debug(f"Character {character.id} gained {self.amount} XP")
            
            # Log XP gain to AuditLog for progress tracking
            # Add to session without committing (will be committed with quest completion)
            try:
                user_id = character.student.user_id if character.student and character.student.user_id else None
                audit_log = AuditLog(
                    event_type=EventType.XP_GAIN.value,
                    event_data={
                        'amount': self.amount,
                        'old_experience': old_experience,
                        'new_experience': character.experience,
                        'source': 'quest_reward',
                        'quest_id': self.quest_id
                    },
                    user_id=user_id,
                    character_id=character.id
                )
                session.add(audit_log)
            except Exception as e:
                logger.warning(f"Failed to log XP gain to AuditLog: {str(e)}", exc_info=True)
            
            # Calculate new level (level = experience // 1000 + 1)
            new_level = (character.experience // 1000) + 1
            if new_level > character.level:
                # Handle level up manually without calling level_up() which commits
                levels_gained = new_level - character.level
                character.level = new_level
                # Increase stats with each level (same logic as level_up())
                character.max_health += 10 * levels_gained
                character.health = character.max_health  # Heal to full on level up
                character.strength += 2 * levels_gained
                character.defense += 2 * levels_gained
                logger.debug(f"Character {character.id} leveled up to {character.level} (gained {levels_gained} levels)")
                
                # Log level up to AuditLog
                # Add to session without committing (will be committed with quest completion)
                try:
                    user_id = character.student.user_id if character.student and character.student.user_id else None
                    audit_log = AuditLog(
                        event_type=EventType.LEVEL_UP.value,
                        event_data={
                            'old_level': old_level,
                            'new_level': character.level,
                            'levels_gained': levels_gained,
                            'source': 'quest_reward',
                            'quest_id': self.quest_id
                        },
                        user_id=user_id,
                        character_id=character.id
                    )
                    session.add(audit_log)
                except Exception as e:
                    logger.warning(f"Failed to log level up to AuditLog: {str(e)}", exc_info=True)
        elif self.type == RewardType.GOLD:
            # Ensure character is in session before modifying
            session.add(character)
            old_gold = character.gold
            character.gold += self.amount
            logger.debug(f"Character {character.id} gold: {old_gold} -> {character.gold}")
            
            # Log gold transaction to AuditLog for progress tracking
            # Add to session without committing (will be committed with quest completion)
            try:
                user_id = character.student.user_id if character.student and character.student.user_id else None
                audit_log = AuditLog(
                    event_type=EventType.GOLD_TRANSACTION.value,
                    event_data={
                        'amount': self.amount,
                        'old_gold': old_gold,
                        'new_gold': character.gold,
                        'source': 'quest_reward',
                        'quest_id': self.quest_id
                    },
                    user_id=user_id,
                    character_id=character.id
                )
                session.add(audit_log)
            except Exception as e:
                logger.warning(f"Failed to log gold transaction to AuditLog: {str(e)}", exc_info=True)
        elif self.type == RewardType.EQUIPMENT and self.item_id:
            from app.models.equipment import Inventory
            inventory = Inventory(
                character_id=character.id,
                item_id=self.item_id
            )
            session.add(inventory)
            logger.debug(f"Added equipment {self.item_id} to character {character.id} inventory")
        elif self.type == RewardType.ABILITY and self.ability_id:
            from app.models.ability import CharacterAbility
            char_ability = CharacterAbility(
                character_id=character.id,
                ability_id=self.ability_id
            )
            session.add(char_ability)
            logger.debug(f"Added ability {self.ability_id} to character {character.id}")
        elif self.type == RewardType.CLAN_EXPERIENCE and hasattr(character, 'clan') and character.clan:
            clan = character.clan
            # Ensure clan is in session before modifying
            session.add(clan)
            
            # Manually handle experience and level up to avoid premature commit
            # This maintains the single transaction guarantee
            old_clan_level = clan.level
            clan.experience += self.amount
            logger.debug(f"Clan {clan.id} gained {self.amount} XP")
            
            # Calculate new level (level = experience // 5000 + 1)
            new_clan_level = (clan.experience // 5000) + 1
            if new_clan_level > clan.level:
                clan.level = new_clan_level
                logger.debug(f"Clan {clan.id} leveled up to {clan.level}")
        
        if commit:
            session.commit()
            logger.info(f"Reward distribution committed for character {character.id}")
    
    def __repr__(self):
        return f'<Reward {self.type.value} ({self.amount})>'

class Consequence(Base):
    """Model for quest failure consequences."""
    
    __tablename__ = 'consequences'
    
    id = db.Column(db.Integer, primary_key=True)
    quest_id = db.Column(db.Integer, db.ForeignKey('quests.id', ondelete='CASCADE'), nullable=False)
    description = db.Column(db.Text, nullable=False)
    
    # Penalty values
    experience_penalty = db.Column(db.Integer, default=0)
    gold_penalty = db.Column(db.Integer, default=0)
    health_penalty = db.Column(db.Integer, default=0)
    
    def apply(self, character, session=None, commit=False):
        """Apply the consequence to a character.
        
        Args:
            character: Character to apply consequence to
            session: Database session (defaults to db.session)
            commit: Whether to commit after applying (default: False)
        """
        from app.models import db
        if session is None:
            session = db.session
        
        logger.info(f"Applying consequence to character {character.id}: XP={self.experience_penalty}, Gold={self.gold_penalty}, Health={self.health_penalty}")
        
        # Ensure character is in session before modifying
        session.add(character)
        
        if self.experience_penalty > 0:
            old_experience = character.experience
            character.experience = max(0, character.experience - self.experience_penalty)
            logger.debug(f"Character {character.id} experience: {old_experience} -> {character.experience}")
        
        if self.gold_penalty > 0:
            old_gold = character.gold
            character.gold = max(0, character.gold - self.gold_penalty)
            logger.debug(f"Character {character.id} gold: {old_gold} -> {character.gold}")
        
        if self.health_penalty > 0:
            # Manually apply damage to avoid premature commit from take_damage()
            old_health = character.health
            character.health = max(0, character.health - self.health_penalty)
            logger.debug(f"Character {character.id} health: {old_health} -> {character.health}")
        
        if commit:
            session.commit()
            logger.info(f"Consequence applied and committed for character {character.id}")
    
    def __repr__(self):
        return f'<Consequence for {self.quest.title}>'

# Pydantic models for validation
class QuestBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=128)
    description: str = Field(..., min_length=1)
    type: QuestType
    level_requirement: int = Field(default=1, ge=1)
    requirements: dict = Field(default_factory=dict)
    completion_criteria: dict = Field(default_factory=dict)
    time_limit_hours: Optional[int] = Field(None, ge=0)

class QuestCreate(QuestBase):
    pass

class QuestUpdate(QuestBase):
    pass

class QuestRead(QuestBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

Reward.equipment = db.relationship('Equipment')
Reward.ability = db.relationship('Ability') 