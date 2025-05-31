import pytest
from datetime import datetime, timedelta
from sqlalchemy.exc import IntegrityError
import uuid

@pytest.fixture
def test_user(db_session):
    from app.models.user import User, UserRole
    unique_id = uuid.uuid4().hex
    user = User(username=f'testuser_{unique_id}', email=f'test_{unique_id}@example.com', role=UserRole.TEACHER)
    user.set_password('password')
    db_session.add(user)
    db_session.commit()
    return user

@pytest.fixture
def test_classroom(db_session, test_user):
    from app.models.classroom import Classroom
    unique_id = uuid.uuid4().hex
    classroom = Classroom(name=f'Test Class {unique_id}', teacher_id=test_user.id, join_code=f'TEST1234_{unique_id}')
    db_session.add(classroom)
    db_session.commit()
    return classroom

@pytest.fixture
def test_clan(db_session, test_classroom):
    from app.models.clan import Clan
    unique_id = uuid.uuid4().hex
    clan = Clan(name=f'Test Clan {unique_id}', class_id=test_classroom.id)
    db_session.add(clan)
    db_session.commit()
    return clan

@pytest.fixture
def test_student(db_session, test_user, test_classroom):
    from app.models.student import Student
    student = Student(user_id=test_user.id, class_id=test_classroom.id, level=1, gold=200)
    db_session.add(student)
    db_session.commit()
    return student

@pytest.fixture
def test_character(db_session, test_student, test_clan):
    from app.models.character import Character
    character = Character(name='Test Character', student_id=test_student.id, clan_id=test_clan.id, character_class='Warrior')
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

@pytest.fixture
def equipment_with_item(db_session):
    from app.models.equipment import Equipment, EquipmentType, EquipmentSlot
    from app.models.item import Item
    equipment = Equipment(
        name='Test Sword',
        type=EquipmentType.WEAPON,
        slot=EquipmentSlot.MAIN_HAND,
        cost=100
    )
    db_session.add(equipment)
    db_session.commit()
    # Create a matching Item row with the same ID if it doesn't exist
    if not Item.query.get(equipment.id):
        item = Item(
            id=equipment.id,
            name=equipment.name,
            description="A test sword.",
            type="weapon",
            tier=1,
            slot="main_hand",
            class_restriction=None,
            level_requirement=1,
            price=equipment.cost,
            image_path=None
        )
        db_session.add(item)
        db_session.commit()
    return equipment

@pytest.fixture
def test_ability_with_item(db_session):
    from app.models.ability import Ability, AbilityType
    from app.models.item import Item
    ability = Ability(
        name='Test Ability',
        type=AbilityType.ATTACK,
        cost=50
    )
    db_session.add(ability)
    db_session.commit()
    # Create a matching Item row with the same ID if it doesn't exist
    if not Item.query.get(ability.id):
        item = Item(
            id=ability.id,
            name=ability.name,
            description="A test ability.",
            type="ability",
            tier=1,
            slot=None,
            class_restriction=None,
            level_requirement=1,
            price=ability.cost,
            image_path=None
        )
        db_session.add(item)
        db_session.commit()
    return ability

@pytest.fixture
def test_shop_purchase(db_session, test_character, test_student, equipment_with_item):
    from app.models.shop import ShopPurchase, PurchaseType
    purchase = ShopPurchase(
        character_id=test_character.id,
        student_id=test_student.id,
        purchase_type=PurchaseType.EQUIPMENT.value,
        item_id=equipment_with_item.id,
        gold_spent=equipment_with_item.cost
    )
    db_session.add(purchase)
    db_session.commit()
    return purchase

@pytest.fixture
def test_audit_log(db_session, test_user):
    from app.models.audit import AuditLog, EventType
    log = AuditLog(user_id=test_user.id, event_type=EventType.USER_LOGIN.value, event_data={'ip': '127.0.0.1'})
    db_session.add(log)
    db_session.commit()
    return log

class TestShopPurchase:
    def test_equipment_purchase_creation(self, db_session, test_character, equipment_with_item, test_student):
        from app.models.shop import ShopPurchase, PurchaseType
        purchase = ShopPurchase(
            character_id=test_character.id,
            student_id=test_student.id,
            purchase_type=PurchaseType.EQUIPMENT.value,
            item_id=equipment_with_item.id,
            gold_spent=equipment_with_item.cost
        )
        db_session.add(purchase)
        db_session.commit()
        assert purchase.id is not None

    def test_ability_purchase_creation(self, db_session, test_character, test_ability_with_item, test_student):
        from app.models.shop import ShopPurchase, PurchaseType
        purchase = ShopPurchase(
            character_id=test_character.id,
            student_id=test_student.id,
            purchase_type=PurchaseType.ABILITY.value,
            item_id=test_ability_with_item.id,
            gold_spent=test_ability_with_item.cost
        )
        db_session.add(purchase)
        db_session.commit()
        assert purchase.id is not None

    def test_invalid_purchase_type(self, db_session, test_character, test_student):
        from app.models.shop import ShopPurchase
        with pytest.raises(ValueError):
            ShopPurchase(
                character_id=test_character.id,
                student_id=test_student.id,
                purchase_type='invalid',
                item_id=1,
                gold_spent=10
            )

    def test_negative_gold_spent(self, db_session, test_character, equipment_with_item, test_student):
        from app.models.shop import ShopPurchase, PurchaseType
        with pytest.raises(ValueError):
            ShopPurchase(
                character_id=test_character.id,
                student_id=test_student.id,
                purchase_type=PurchaseType.EQUIPMENT.value,
                item_id=equipment_with_item.id,
                gold_spent=-5
            )

    def test_get_character_purchases(self, db_session, test_character, equipment_with_item, test_ability_with_item, test_student):
        from app.models.shop import ShopPurchase, PurchaseType
        # Add purchases
        purchase1 = ShopPurchase(
            character_id=test_character.id,
            student_id=test_student.id,
            purchase_type=PurchaseType.EQUIPMENT.value,
            item_id=equipment_with_item.id,
            gold_spent=equipment_with_item.cost
        )
        purchase2 = ShopPurchase(
            character_id=test_character.id,
            student_id=test_student.id,
            purchase_type=PurchaseType.ABILITY.value,
            item_id=test_ability_with_item.id,
            gold_spent=test_ability_with_item.cost
        )
        db_session.add_all([purchase1, purchase2])
        db_session.commit()
        purchases = db_session.query(ShopPurchase).filter_by(character_id=test_character.id).all()
        assert len(purchases) == 2

class TestAuditLog:
    def test_audit_log_creation(self, db_session, test_user, test_character):
        from app.models.audit import AuditLog, EventType
        user = test_user
        student_profile = user.student_profile
        print(f"[DEBUG] AuditLog count before: {AuditLog.query.count()}")
        log = AuditLog(
            event_type=EventType.CHARACTER_CREATE.value,
            user=user,
            character=test_character,
            event_data={'name': 'TestChar', 'class': 'Warrior'},
            ip_address='127.0.0.1'
        )
        db_session.add(log)
        db_session.commit()
        print(f"[DEBUG] AuditLog count after: {AuditLog.query.count()}")
        saved_log = AuditLog.query.filter_by(id=log.id).first()
        assert saved_log is not None
        assert saved_log.event_type == EventType.CHARACTER_CREATE.value
        assert saved_log.user_id == user.id

    def test_audit_log_event_types(self, db_session, test_user, test_character):
        from app.models.audit import AuditLog, EventType
        # Clear AuditLog table
        AuditLog.query.delete()
        db_session.commit()
        user = test_user
        student_profile = user.student_profile
        print(f"[DEBUG] AuditLog count before: {AuditLog.query.count()}")
        for event_type in EventType:
            log = AuditLog(
                event_type=event_type.value,
                user=user,
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
        user = test_user
        student_profile = user.student_profile
        print(f"[DEBUG] AuditLog count before: {AuditLog.query.count()}")
        log = AuditLog(
            event_type=EventType.CHARACTER_CREATE.value,
            user=user,
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
        user = test_user
        student_profile = user.student_profile
        print(f"[DEBUG] AuditLog count before: {AuditLog.query.count()}")
        log = AuditLog(
            event_type=EventType.CHARACTER_CREATE.value,
            user=user,
            character=test_character,
            event_data={'foo': 'bar'},
            ip_address='127.0.0.1'
        )
        db_session.add(log)
        db_session.commit()
        print(f"[DEBUG] AuditLog count after: {AuditLog.query.count()}")
        saved_log = AuditLog.query.filter_by(id=log.id).first()
        assert saved_log.event_data['foo'] == 'bar'

    def test_audit_log_ip_address(self, db_session, test_user, test_character):
        from app.models.audit import AuditLog, EventType
        user = test_user
        student_profile = user.student_profile
        print(f"[DEBUG] AuditLog count before: {AuditLog.query.count()}")
        log = AuditLog(
            event_type=EventType.CHARACTER_CREATE.value,
            user=user,
            character=test_character,
            event_data={'foo': 'bar'},
            ip_address='192.168.1.1'
        )
        db_session.add(log)
        db_session.commit()
        print(f"[DEBUG] AuditLog count after: {AuditLog.query.count()}")
        saved_log = AuditLog.query.filter_by(id=log.id).first()
        assert saved_log.ip_address == '192.168.1.1'

    def test_invalid_event_type(self, db_session, test_user):
        from app.models.audit import AuditLog, EventType
        user = test_user
        student_profile = user.student_profile
        with pytest.raises(ValueError):
            log = AuditLog(
                event_type='INVALID_EVENT',
                user=user,
                event_data={},
                ip_address='127.0.0.1'
            )
            db_session.add(log)
            db_session.commit()

    def test_get_user_events(self, db_session, test_user):
        from app.models.audit import AuditLog, EventType
        user = test_user
        student_profile = user.student_profile
        # Create multiple events
        events = [
            AuditLog(
                event_type=EventType.USER_LOGIN.value,
                user=user,
                event_data={},
                ip_address='127.0.0.1'
            ),
            AuditLog(
                event_type=EventType.USER_LOGOUT.value,
                user=user,
                event_data={},
                ip_address='127.0.0.1'
            )
        ]
        db_session.add_all(events)
        db_session.commit()

        # Test retrieving all user events
        user_events = AuditLog.get_user_events(user.id)
        assert len(user_events) == 2

        # Test filtering by event type
        login_events = AuditLog.get_user_events(
            user.id, event_type=EventType.USER_LOGIN.value
        )
        assert len(login_events) == 1
        assert login_events[0].event_type == EventType.USER_LOGIN.value

    def test_get_character_events(self, db_session, test_character, test_user):
        from app.models.audit import AuditLog, EventType
        user = test_user
        student_profile = user.student_profile
        # Create multiple character events
        events = [
            AuditLog(
                event_type=EventType.XP_GAIN.value,
                user=user,
                character=test_character,
                event_data={'xp': 100},
                ip_address='127.0.0.1'
            ),
            AuditLog(
                event_type=EventType.GOLD_TRANSACTION.value,
                user=user,
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
        user = test_user
        student_profile = user.student_profile
        # Clear AuditLog table
        AuditLog.query.delete()
        db_session.commit()
        # Create events with different timestamps
        now = datetime.utcnow()
        events = [
            AuditLog(
                event_type=EventType.USER_LOGIN.value,
                user=user,
                event_data={},
                ip_address='127.0.0.1',
                event_timestamp=now - timedelta(hours=2)
            ),
            AuditLog(
                event_type=EventType.USER_LOGOUT.value,
                user=user,
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

def test_shop_and_audit_logic(db_session, test_clan, test_character):
    from app.models.shop import ShopPurchase
    from app.models.audit import AuditLog, EventType
    # Create a login event for the test
    log = AuditLog(
        event_type=EventType.USER_LOGIN.value,
        user_id=1,
        event_data={},
        ip_address='127.0.0.1',
        event_timestamp=datetime.utcnow()
    )
    db_session.add(log)
    db_session.commit()
    login_events = AuditLog.get_recent_events(limit=10, event_type=EventType.USER_LOGIN.value)
    assert login_events[0].event_type == EventType.USER_LOGIN.value

def test_shop_purchase_creation(test_shop_purchase):
    assert test_shop_purchase.id is not None
    assert test_shop_purchase.purchase_type == 'equipment'
    assert test_shop_purchase.gold_spent == 100

def test_audit_log_creation(test_audit_log):
    assert test_audit_log.id is not None
    assert test_audit_log.event_type is not None
    # Debug print if assertion fails
    if test_audit_log.event_type is None:
        print('[DEBUG] AuditLog event_type:', test_audit_log.event_type) 