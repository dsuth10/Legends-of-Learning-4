import pytest
from datetime import datetime, timedelta
from sqlalchemy.exc import IntegrityError
from app.models import (
    User, Character, Equipment, Ability, ShopPurchase, AuditLog,
    PurchaseType, EventType, ModelException
)

@pytest.fixture
def test_user(db_session):
    user = User(username='test_user', email='test@example.com')
    user.password = 'testpass'
    db_session.add(user)
    db_session.commit()
    return user

@pytest.fixture
def test_character(db_session, test_user):
    character = Character(
        user=test_user,
        name='TestChar',
        character_class='Warrior',
        level=1,
        gold=1000,
        health=100,
        power=50
    )
    db_session.add(character)
    db_session.commit()
    return character

@pytest.fixture
def test_equipment(db_session):
    equipment = Equipment(
        name='Test Sword',
        type='weapon',
        tier=1,
        cost=100,
        min_level=1,
        health_bonus=10,
        power_bonus=5
    )
    db_session.add(equipment)
    db_session.commit()
    return equipment

@pytest.fixture
def test_ability(db_session):
    ability = Ability(
        name='Test Ability',
        type='active',
        tier=1,
        cost=200,
        min_level=1,
        power_cost=20,
        cooldown=60
    )
    db_session.add(ability)
    db_session.commit()
    return ability

class TestShopPurchase:
    def test_equipment_purchase_creation(self, db_session, test_character, test_equipment):
        purchase = ShopPurchase(
            character=test_character,
            purchase_type=PurchaseType.EQUIPMENT,
            item_id=test_equipment.id,
            gold_spent=test_equipment.cost
        )
        db_session.add(purchase)
        db_session.commit()

        saved_purchase = ShopPurchase.query.first()
        assert saved_purchase is not None
        assert saved_purchase.character_id == test_character.id
        assert saved_purchase.purchase_type == PurchaseType.EQUIPMENT
        assert saved_purchase.item_id == test_equipment.id
        assert saved_purchase.gold_spent == test_equipment.cost

    def test_ability_purchase_creation(self, db_session, test_character, test_ability):
        purchase = ShopPurchase(
            character=test_character,
            purchase_type=PurchaseType.ABILITY,
            item_id=test_ability.id,
            gold_spent=test_ability.cost
        )
        db_session.add(purchase)
        db_session.commit()

        saved_purchase = ShopPurchase.query.first()
        assert saved_purchase is not None
        assert saved_purchase.purchase_type == PurchaseType.ABILITY
        assert saved_purchase.item_id == test_ability.id

    def test_invalid_purchase_type(self, db_session, test_character, test_equipment):
        with pytest.raises(ValueError):
            purchase = ShopPurchase(
                character=test_character,
                purchase_type='INVALID',
                item_id=test_equipment.id,
                gold_spent=100
            )
            db_session.add(purchase)
            db_session.commit()

    def test_negative_gold_spent(self, db_session, test_character, test_equipment):
        with pytest.raises(ValueError):
            purchase = ShopPurchase(
                character=test_character,
                purchase_type=PurchaseType.EQUIPMENT,
                item_id=test_equipment.id,
                gold_spent=-50
            )
            db_session.add(purchase)
            db_session.commit()

    def test_get_character_purchases(self, db_session, test_character, test_equipment, test_ability):
        # Create multiple purchases
        purchases = [
            ShopPurchase(
                character=test_character,
                purchase_type=PurchaseType.EQUIPMENT,
                item_id=test_equipment.id,
                gold_spent=100
            ),
            ShopPurchase(
                character=test_character,
                purchase_type=PurchaseType.ABILITY,
                item_id=test_ability.id,
                gold_spent=200
            )
        ]
        db_session.add_all(purchases)
        db_session.commit()

        # Test retrieving all purchases
        character_purchases = ShopPurchase.get_character_purchases(test_character.id)
        assert len(character_purchases) == 2

        # Test filtering by purchase type
        equipment_purchases = ShopPurchase.get_character_purchases(
            test_character.id, purchase_type=PurchaseType.EQUIPMENT
        )
        assert len(equipment_purchases) == 1
        assert equipment_purchases[0].purchase_type == PurchaseType.EQUIPMENT

class TestAuditLog:
    def test_audit_log_creation(self, db_session, test_user, test_character):
        log = AuditLog(
            event_type=EventType.CHARACTER_CREATED,
            user=test_user,
            character=test_character,
            event_data={'name': 'TestChar', 'class': 'Warrior'},
            ip_address='127.0.0.1'
        )
        db_session.add(log)
        db_session.commit()

        saved_log = AuditLog.query.first()
        assert saved_log is not None
        assert saved_log.event_type == EventType.CHARACTER_CREATED
        assert saved_log.user_id == test_user.id
        assert saved_log.character_id == test_character.id
        assert saved_log.event_data == {'name': 'TestChar', 'class': 'Warrior'}
        assert saved_log.ip_address == '127.0.0.1'

    def test_invalid_event_type(self, db_session, test_user):
        with pytest.raises(ValueError):
            log = AuditLog(
                event_type='INVALID_EVENT',
                user=test_user,
                event_data={},
                ip_address='127.0.0.1'
            )
            db_session.add(log)
            db_session.commit()

    def test_get_user_events(self, db_session, test_user):
        # Create multiple events
        events = [
            AuditLog(
                event_type=EventType.USER_LOGIN,
                user=test_user,
                event_data={},
                ip_address='127.0.0.1'
            ),
            AuditLog(
                event_type=EventType.USER_LOGOUT,
                user=test_user,
                event_data={},
                ip_address='127.0.0.1'
            )
        ]
        db_session.add_all(events)
        db_session.commit()

        # Test retrieving all user events
        user_events = AuditLog.get_user_events(test_user.id)
        assert len(user_events) == 2

        # Test filtering by event type
        login_events = AuditLog.get_user_events(
            test_user.id, event_type=EventType.USER_LOGIN
        )
        assert len(login_events) == 1
        assert login_events[0].event_type == EventType.USER_LOGIN

    def test_get_character_events(self, db_session, test_character):
        # Create multiple character events
        events = [
            AuditLog(
                event_type=EventType.XP_EARNED,
                user=test_character.user,
                character=test_character,
                event_data={'xp': 100},
                ip_address='127.0.0.1'
            ),
            AuditLog(
                event_type=EventType.GOLD_EARNED,
                user=test_character.user,
                character=test_character,
                event_data={'gold': 50},
                ip_address='127.0.0.1'
            )
        ]
        db_session.add_all(events)
        db_session.commit()

        # Test retrieving all character events
        character_events = AuditLog.get_character_events(test_character.id)
        assert len(character_events) == 2

        # Test filtering by event type
        xp_events = AuditLog.get_character_events(
            test_character.id, event_type=EventType.XP_EARNED
        )
        assert len(xp_events) == 1
        assert xp_events[0].event_type == EventType.XP_EARNED

    def test_get_recent_events(self, db_session, test_user):
        # Create events with different timestamps
        now = datetime.utcnow()
        events = [
            AuditLog(
                event_type=EventType.USER_LOGIN,
                user=test_user,
                event_data={},
                ip_address='127.0.0.1',
                event_timestamp=now - timedelta(hours=2)
            ),
            AuditLog(
                event_type=EventType.USER_LOGOUT,
                user=test_user,
                event_data={},
                ip_address='127.0.0.1',
                event_timestamp=now - timedelta(hours=1)
            )
        ]
        db_session.add_all(events)
        db_session.commit()

        # Test retrieving recent events
        recent_events = AuditLog.get_recent_events(hours=1.5)
        assert len(recent_events) == 1
        assert recent_events[0].event_type == EventType.USER_LOGOUT

        # Test with pagination
        all_events = AuditLog.get_recent_events(hours=3, page=1, per_page=1)
        assert len(all_events) == 1

        # Test with event type filter
        login_events = AuditLog.get_recent_events(
            hours=3, event_type=EventType.USER_LOGIN
        )
        assert len(login_events) == 1
        assert login_events[0].event_type == EventType.USER_LOGIN 