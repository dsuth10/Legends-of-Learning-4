import pytest
from datetime import datetime, timedelta
from sqlalchemy.exc import IntegrityError
import uuid

@pytest.fixture
def test_user(db_session):
    from app.models.user import User, UserRole
    unique = uuid.uuid4().hex[:8]
    user = User(
        username=f'testuser_{unique}',
        email=f'test_{unique}@example.com',
        role=UserRole.STUDENT,
        password='password123'
    )
    db_session.add(user)
    db_session.commit()
    return user

@pytest.fixture
def test_character(db_session, test_user):
    from app.models.character import Character
    character = Character(
        name='TestChar',
        student_id=test_user.id,
        character_class='Warrior',
        level=1,
        gold=100
    )
    db_session.add(character)
    db_session.commit()
    return character

@pytest.fixture
def test_equipment(db_session):
    from app.models.equipment import Equipment, EquipmentType, EquipmentSlot
    equipment = Equipment(
        name='Test Sword',
        type=EquipmentType.WEAPON,
        slot=EquipmentSlot.MAIN_HAND,
        cost=100
    )
    db_session.add(equipment)
    db_session.commit()
    return equipment

@pytest.fixture
def test_ability(db_session):
    from app.models.ability import Ability, AbilityType
    ability = Ability(
        name='Test Ability',
        type=AbilityType.ATTACK,
        cost=50
    )
    db_session.add(ability)
    db_session.commit()
    return ability

class TestShopPurchase:
    def test_equipment_purchase_creation(self, db_session, test_character, test_equipment):
        from app.models.shop import ShopPurchase, PurchaseType
        purchase = ShopPurchase(
            character=test_character,
            purchase_type=PurchaseType.EQUIPMENT.value,
            item_id=test_equipment.id,
            gold_spent=test_equipment.cost
        )
        db_session.add(purchase)
        db_session.commit()
        saved_purchase = ShopPurchase.query.filter_by(
            character_id=test_character.id,
            item_id=test_equipment.id,
            purchase_type=PurchaseType.EQUIPMENT.value
        ).first()
        assert saved_purchase is not None
        assert saved_purchase.gold_spent == test_equipment.cost

    def test_ability_purchase_creation(self, db_session, test_character, test_ability):
        from app.models.shop import ShopPurchase, PurchaseType
        purchase = ShopPurchase(
            character=test_character,
            purchase_type=PurchaseType.ABILITY.value,
            item_id=test_ability.id,
            gold_spent=test_ability.cost
        )
        db_session.add(purchase)
        db_session.commit()
        saved_purchase = ShopPurchase.query.filter_by(
            character_id=test_character.id,
            item_id=test_ability.id,
            purchase_type=PurchaseType.ABILITY.value
        ).first()
        assert saved_purchase is not None
        assert saved_purchase.gold_spent == test_ability.cost

    def test_invalid_purchase_type(self, db_session, test_character):
        from app.models.shop import ShopPurchase
        with pytest.raises(ValueError):
            ShopPurchase(
                character=test_character,
                purchase_type='invalid',
                item_id=1,
                gold_spent=10
            )

    def test_negative_gold_spent(self, db_session, test_character, test_equipment):
        from app.models.shop import ShopPurchase, PurchaseType
        with pytest.raises(ValueError):
            ShopPurchase(
                character=test_character,
                purchase_type=PurchaseType.EQUIPMENT.value,
                item_id=test_equipment.id,
                gold_spent=-5
            )

    def test_get_character_purchases(self, db_session, test_character, test_equipment, test_ability):
        from app.models.shop import ShopPurchase, PurchaseType
        # Add purchases
        purchase1 = ShopPurchase(
            character=test_character,
            purchase_type=PurchaseType.EQUIPMENT.value,
            item_id=test_equipment.id,
            gold_spent=test_equipment.cost
        )
        purchase2 = ShopPurchase(
            character=test_character,
            purchase_type=PurchaseType.ABILITY.value,
            item_id=test_ability.id,
            gold_spent=test_ability.cost
        )
        db_session.add_all([purchase1, purchase2])
        db_session.commit()
        # Query
        purchases = ShopPurchase.get_character_purchases(test_character.id)
        assert len(purchases) >= 2

class TestAuditLog:
    def test_audit_log_creation(self, db_session, test_user, test_character):
        from app.models.audit import AuditLog, EventType
        print(f"[DEBUG] AuditLog count before: {AuditLog.query.count()}")
        log = AuditLog(
            event_type=EventType.CHARACTER_CREATE.value,
            user=test_user,
            character=test_character,
            event_data={'name': 'TestChar', 'class': 'Warrior'},
            ip_address='127.0.0.1'
        )
        db_session.add(log)
        db_session.commit()
        print(f"[DEBUG] AuditLog count after: {AuditLog.query.count()}")
        saved_log = AuditLog.query.first()
        assert saved_log is not None
        assert saved_log.event_type == EventType.CHARACTER_CREATE.value
        assert saved_log.user_id == test_user.id

    def test_audit_log_event_types(self, db_session, test_user, test_character):
        from app.models.audit import AuditLog, EventType
        print(f"[DEBUG] AuditLog count before: {AuditLog.query.count()}")
        for event_type in EventType:
            log = AuditLog(
                event_type=event_type.value,
                user=test_user,
                character=test_character,
                event_data={'test': 'data'},
                ip_address='127.0.0.1'
            )
            db_session.add(log)
        db_session.commit()
        print(f"[DEBUG] AuditLog count after: {AuditLog.query.count()}")
        logs = AuditLog.query.all()
        assert len(logs) == len(EventType)

    def test_audit_log_repr(self, db_session, test_user, test_character):
        from app.models.audit import AuditLog, EventType
        print(f"[DEBUG] AuditLog count before: {AuditLog.query.count()}")
        log = AuditLog(
            event_type=EventType.CHARACTER_CREATE.value,
            user=test_user,
            character=test_character,
            event_data={'name': 'TestChar'},
            ip_address='127.0.0.1'
        )
        db_session.add(log)
        db_session.commit()
        print(f"[DEBUG] AuditLog count after: {AuditLog.query.count()}")
        assert repr(log).startswith('<AuditLog')

    def test_audit_log_event_data(self, db_session, test_user, test_character):
        from app.models.audit import AuditLog, EventType
        print(f"[DEBUG] AuditLog count before: {AuditLog.query.count()}")
        log = AuditLog(
            event_type=EventType.CHARACTER_CREATE.value,
            user=test_user,
            character=test_character,
            event_data={'foo': 'bar'},
            ip_address='127.0.0.1'
        )
        db_session.add(log)
        db_session.commit()
        print(f"[DEBUG] AuditLog count after: {AuditLog.query.count()}")
        saved_log = AuditLog.query.first()
        assert saved_log.event_data['foo'] == 'bar'

    def test_audit_log_ip_address(self, db_session, test_user, test_character):
        from app.models.audit import AuditLog, EventType
        print(f"[DEBUG] AuditLog count before: {AuditLog.query.count()}")
        log = AuditLog(
            event_type=EventType.CHARACTER_CREATE.value,
            user=test_user,
            character=test_character,
            event_data={'foo': 'bar'},
            ip_address='192.168.1.1'
        )
        db_session.add(log)
        db_session.commit()
        print(f"[DEBUG] AuditLog count after: {AuditLog.query.count()}")
        saved_log = AuditLog.query.first()
        assert saved_log.ip_address == '192.168.1.1'

    def test_invalid_event_type(self, db_session, test_user):
        from app.models.audit import AuditLog, EventType
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
        from app.models.audit import AuditLog, EventType
        # Create multiple events
        events = [
            AuditLog(
                event_type=EventType.USER_LOGIN.value,
                user=test_user,
                event_data={},
                ip_address='127.0.0.1'
            ),
            AuditLog(
                event_type=EventType.USER_LOGOUT.value,
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
            test_user.id, event_type=EventType.USER_LOGIN.value
        )
        assert len(login_events) == 1
        assert login_events[0].event_type == EventType.USER_LOGIN.value

    def test_get_character_events(self, db_session, test_character):
        from app.models.audit import AuditLog, EventType
        # Create multiple character events
        events = [
            AuditLog(
                event_type=EventType.XP_GAIN.value,
                user=test_character.student,
                character=test_character,
                event_data={'xp': 100},
                ip_address='127.0.0.1'
            ),
            AuditLog(
                event_type=EventType.GOLD_TRANSACTION.value,
                user=test_character.student,
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
            test_character.id, event_type=EventType.XP_GAIN.value
        )
        assert len(xp_events) == 1
        assert xp_events[0].event_type == EventType.XP_GAIN.value

    def test_get_recent_events(self, db_session, test_user):
        from app.models.audit import AuditLog, EventType
        # Create events with different timestamps
        now = datetime.utcnow()
        events = [
            AuditLog(
                event_type=EventType.USER_LOGIN.value,
                user=test_user,
                event_data={},
                ip_address='127.0.0.1',
                event_timestamp=now - timedelta(hours=2)
            ),
            AuditLog(
                event_type=EventType.USER_LOGOUT.value,
                user=test_user,
                event_data={},
                ip_address='127.0.0.1',
                event_timestamp=now - timedelta(hours=1)
            )
        ]
        db_session.add_all(events)
        db_session.commit()

        # Test retrieving recent events (limit=1)
        recent_events = AuditLog.get_recent_events(limit=1)
        assert len(recent_events) == 1
        assert recent_events[0].event_type == EventType.USER_LOGOUT.value

        # Test retrieving all events (limit=10)
        all_events = AuditLog.get_recent_events(limit=10)
        assert len(all_events) == 2

        # Test with event type filter
        login_events = AuditLog.get_recent_events(limit=10, event_type=EventType.USER_LOGIN.value)
        assert len(login_events) == 1
        assert login_events[0].event_type == EventType.USER_LOGIN.value 