from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user
from .teacher import student_required
from app.models import db
from app.models.character import Character
from app.models.equipment import Inventory, Equipment, EquipmentType, EquipmentSlot, TEST_ARMOR_IMAGE, TEST_RING_IMAGE, TEST_SWORD_IMAGE
from app.models.student import Student
from app.models.ability import Ability, CharacterAbility
from app.models.shop import ShopPurchase, PurchaseType
from app.models.quest import Quest, QuestLog, QuestStatus
import time

student_bp = Blueprint('student', __name__, url_prefix='/student')

@student_bp.route('/dashboard')
@login_required
@student_required
def dashboard():
    """Student dashboard main view."""
    student_profile = Student.query.filter_by(user_id=current_user.id).first()
    classes = list(getattr(current_user, 'classes', []))
    main_character = None
    if student_profile:
        main_character = student_profile.characters.filter_by(is_active=True).first()
    clan = main_character.clan if main_character and main_character.clan else None
    active_quests = main_character.quest_logs.filter_by(status='in_progress').all() if main_character else []
    recent_activities = list(current_user.audit_logs.order_by(db.desc('event_timestamp')).limit(10))
    return render_template(
        'student/dashboard.html',
        student=current_user,
        student_profile=student_profile,
        classes=classes,
        main_character=main_character,
        clan=clan,
        active_quests=active_quests,
        recent_activities=recent_activities
    )

@student_bp.route('/profile')
@login_required
@student_required
def profile():
    return render_template('student/profile.html', student=current_user)

@student_bp.route('/quests')
@login_required
@student_required
def quests():
    student_profile = Student.query.filter_by(user_id=current_user.id).first()
    main_char = student_profile.characters.filter_by(is_active=True).first() if student_profile else None
    assigned_quests = []
    if main_char:
        for log in main_char.quest_logs:
            print("DEBUG QUESTLOG:", log.quest_id, log.status, type(log.status), log.id)
            quest = log.quest
            assigned_quests.append({
                'quest': quest,
                'status': log.status,
                'x': log.x_coordinate,
                'y': log.y_coordinate,
                'log': log
            })
    return render_template('student/quests.html', student=current_user, assigned_quests=assigned_quests)

@student_bp.route('/quests/start/<int:quest_id>', methods=['POST'])
@login_required
@student_required
def start_quest(quest_id):
    student_profile = Student.query.filter_by(user_id=current_user.id).first()
    main_char = student_profile.characters.filter_by(is_active=True).first() if student_profile else None
    quest = Quest.query.get_or_404(quest_id)
    if not main_char:
        flash('No active character found.', 'danger')
        return redirect(url_for('student.quests'))
    existing_log = QuestLog.query.filter_by(character_id=main_char.id, quest_id=quest.id).first()
    if existing_log:
        if existing_log.status == QuestStatus.NOT_STARTED:
            existing_log.status = QuestStatus.IN_PROGRESS
            db.session.commit()
            db.session.refresh(existing_log)
            print("AFTER REFRESH:", existing_log.status)
            print("DEBUG: All quest logs for character after start_quest:")
            for log in QuestLog.query.filter_by(character_id=main_char.id).all():
                print(log.quest_id, log.status, type(log.status), log.id)
            flash('Quest started!', 'success')
        elif existing_log.status == QuestStatus.IN_PROGRESS:
            flash('You have already started this quest.', 'info')
        elif existing_log.status == QuestStatus.COMPLETED:
            flash('You have already completed this quest.', 'info')
        else:
            flash('Quest already in progress or completed.', 'info')
        return redirect(url_for('student.quests'))
    # If no log exists, create a new one (should not happen with current assign flow)
    new_log = QuestLog(character_id=main_char.id, quest_id=quest.id, status=QuestStatus.IN_PROGRESS)
    db.session.add(new_log)
    db.session.commit()
    flash('Quest accepted!', 'success')
    return redirect(url_for('student.quests'))

@student_bp.route('/quests/complete/<int:quest_id>', methods=['POST'])
@login_required
@student_required
def complete_quest(quest_id):
    student_profile = Student.query.filter_by(user_id=current_user.id).first()
    main_char = student_profile.characters.filter_by(is_active=True).first() if student_profile else None
    if not main_char:
        flash('No active character found.', 'danger')
        return redirect(url_for('student.quests'))
    quest_log = QuestLog.query.filter_by(character_id=main_char.id, quest_id=quest_id).first()
    if not quest_log or quest_log.status != QuestStatus.IN_PROGRESS:
        flash('Quest not in progress or already completed.', 'warning')
        return redirect(url_for('student.quests'))
    quest_log.complete_quest()
    db.session.commit()
    flash('Quest completed! Rewards granted.', 'success')
    return redirect(url_for('student.quests'))

@student_bp.route('/clan')
@login_required
@student_required
def clan():
    return render_template('student/clan.html', student=current_user)

@student_bp.route('/character')
@login_required
@student_required
def character():
    student_profile = Student.query.filter_by(user_id=current_user.id).first()
    main_character = None
    equipped_abilities = []
    if student_profile:
        main_character = student_profile.characters.filter_by(is_active=True).first()
        if main_character:
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
                    'is_equipped': ca.is_equipped
                }
                for ca in main_character.abilities.filter_by(is_equipped=True).all()
            ]
    now = int(time.time())
    ability_targets = []
    if main_character and main_character.clan:
        ability_targets = [
            {'id': member.id, 'name': member.name, 'character_class': member.character_class}
            for member in main_character.clan.members if member.id != main_character.id
        ]
    return render_template('student/character.html', student=current_user, main_character=main_character, equipped_abilities=equipped_abilities, now=now, ability_targets=ability_targets)

@student_bp.route('/shop')
@login_required
@student_required
def shop():
    student_profile = Student.query.filter_by(user_id=current_user.id).first()
    main_character = None
    owned_item_ids = set()
    owned_ability_ids = set()
    if student_profile:
        main_character = student_profile.characters.filter_by(is_active=True).first()
        if main_character:
            # Get owned item IDs
            owned_item_ids = set(inv.item_id for inv in main_character.inventory_items)
            # Get owned ability IDs
            if hasattr(main_character, 'abilities'):
                owned_ability_ids = set(a.ability_id for a in main_character.abilities)
    # Always define these, even if main_character is None
    char_gold = main_character.gold if main_character else 0
    char_level = main_character.level if main_character else 1
    char_class = main_character.character_class if main_character else ''
    # Query all items and abilities for the shop
    items = Equipment.query.all()
    print(f"[DEBUG] Shop route: Equipment.query.all() count = {len(items)}")
    items_list = []
    for eq in items:
        owned = eq.id in owned_item_ids
        can_afford = char_gold >= eq.cost
        unlocked = (char_level >= getattr(eq, 'level_requirement', 1)) and (not eq.class_restriction or eq.class_restriction.lower() == char_class.lower())
        can_buy = (not owned) and can_afford and unlocked
        print(f"[DEBUG] Shop filter: name={eq.name}, owned={owned}, can_afford={can_afford}, unlocked={unlocked}, can_buy={can_buy}, class_restriction={eq.class_restriction}, char_class={char_class}")
        items_list.append({
            'id': eq.id,
            'name': eq.name,
            'price': eq.cost,
            'image': eq.image_url or '/static/images/default_item.png',
            'category': 'equipment',
            'tier': getattr(eq, 'rarity', 1),
            'description': eq.description or '',
            'level_requirement': getattr(eq, 'level_requirement', 1),
            'class_restriction': getattr(eq, 'class_restriction', None),
            'owned': owned,
            'can_afford': can_afford,
            'unlocked': unlocked,
            'can_buy': can_buy,
        })
    ability_items = Ability.query.all()
    # Format items for the template
    items_list = []
    print(f"[DEBUG] /student/shop: char_class={char_class}, char_level={char_level}, gold={char_gold}")
    for eq in items:
        items_list.append({
            'id': eq.id,
            'name': eq.name,
            'price': eq.cost,
            'image': eq.image_url or '/static/images/default_item.png',
            'category': 'equipment',
            'tier': getattr(eq, 'rarity', 1),
            'description': eq.description or '',
            'level_requirement': getattr(eq, 'level_requirement', 1),
            'class_restriction': getattr(eq, 'class_restriction', None),
            'owned': eq.id in owned_item_ids,
            'can_afford': char_gold >= eq.cost,
            'unlocked': char_level >= getattr(eq, 'level_requirement', 1),
            'can_buy': (not eq.id in owned_item_ids) and (char_gold >= eq.cost) and (char_level >= getattr(eq, 'level_requirement', 1)) and (not eq.class_restriction or eq.class_restriction.lower() == char_class.lower()),
        })
    for ab in ability_items:
        owned = ab.id in owned_ability_ids
        can_afford = char_gold >= ab.cost
        unlocked = (char_level >= getattr(ab, 'level_requirement', 1))
        can_buy = (not owned) and can_afford and unlocked
        items_list.append({
            'id': ab.id,
            'name': ab.name,
            'price': ab.cost,
            'image': '/static/images/default_item.png',
            'category': 'ability',
            'tier': getattr(ab, 'tier', 1),
            'description': ab.description or '',
            'level_requirement': getattr(ab, 'level_requirement', 1),
            'class_restriction': None,
            'owned': owned,
            'can_afford': can_afford,
            'unlocked': unlocked,
            'can_buy': can_buy,
        })
    return render_template('student/shop.html', student=current_user, main_character=main_character, items=items_list)

@student_bp.route('/progress')
@login_required
@student_required
def progress():
    return render_template('student/progress.html', student=current_user)

@student_bp.route('/character/create', methods=['GET', 'POST'])
@login_required
@student_required
def character_create():
    from flask import request, redirect, url_for, flash
    from app.models.character import Character
    # Class base stats mapping
    CLASS_BASE_STATS = {
        "Warrior":   {"health": 120, "max_health": 120, "strength": 15, "defense": 15, "gold": 0},
        "Sorcerer":  {"health": 80,  "max_health": 80,  "strength": 20, "defense": 8,  "gold": 0},
        "Druid":     {"health": 100, "max_health": 100, "strength": 12, "defense": 12, "gold": 0},
    }
    # Get the correct student_id from the Student table
    student_profile = Student.query.filter_by(user_id=current_user.id).first()
    if student_profile and student_profile.characters.filter_by(is_active=True).first():
        flash('You already have a character.', 'info')
        return redirect(url_for('student.character'))

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        character_class = request.form.get('character_class', '').strip()
        gender = request.form.get('gender', '').strip()
        avatar_url = request.form.get('avatar_url', '').strip()
        # Basic validation
        if not name or not character_class or not gender:
            flash('Please fill out all required fields.', 'danger')
            return render_template('student/character_create.html', student=current_user, form=request.form)
        # Set base stats based on class
        base_stats = CLASS_BASE_STATS.get(character_class, CLASS_BASE_STATS["Warrior"])
        if not student_profile:
            flash('Student profile not found. Please contact your teacher or admin.', 'danger')
            return redirect(url_for('student.dashboard'))
        # Create character
        new_character = Character(
            name=name,
            character_class=character_class,
            gender=gender,
            avatar_url=avatar_url,
            student_id=student_profile.id,
            health=base_stats["health"],
            max_health=base_stats["max_health"],
            strength=base_stats["strength"],
            defense=base_stats["defense"],
            gold=base_stats["gold"]
        )
        db.session.add(new_character)
        db.session.commit()
        flash('Character created successfully!', 'success')
        return redirect(url_for('student.character'))
    # GET: Render form
    class_options = ['Warrior', 'Sorcerer', 'Druid']
    gender_options = ['Male', 'Female', 'Other']
    avatar_options = [
        '/static/avatars/warrior_m.png',
        '/static/avatars/warrior_f.png',
        '/static/avatars/sorcerer_m.png',
        '/static/avatars/sorcerer_f.png',
        '/static/avatars/druid_m.png',
        '/static/avatars/druid_f.png',
    ]
    return render_template('student/character_create.html', student=current_user, class_options=class_options, gender_options=gender_options, avatar_options=avatar_options, form={})

@student_bp.route('/character/gain_xp', methods=['POST'])
@login_required
@student_required
def gain_xp():
    from flask import redirect, url_for, flash
    from app.models.character import Character
    student_profile = Student.query.filter_by(user_id=current_user.id).first()
    if not student_profile:
        flash('No student profile found.', 'danger')
        return redirect(url_for('student.dashboard'))
    main_character = student_profile.characters.filter_by(is_active=True).first()
    if not main_character:
        flash('No character found.', 'danger')
        return redirect(url_for('student.character'))
    main_character.gain_experience(500)
    db.session.commit()
    flash('Gained 500 XP!','success')
    return redirect(url_for('student.character'))

@student_bp.route('/character/unequip_weapon', methods=['POST'])
@login_required
@student_required
def unequip_weapon():
    from flask import redirect, url_for, flash
    from app.models.character import Character
    from app.models.equipment import EquipmentType
    student_profile = Student.query.filter_by(user_id=current_user.id).first()
    if not student_profile or not student_profile.characters.filter_by(is_active=True).first().equipped_weapon:
        flash('No weapon equipped.', 'warning')
        return redirect(url_for('student.character'))
    main_character = student_profile.characters.filter_by(is_active=True).first()
    main_character.equipped_weapon.is_equipped = False
    db.session.commit()
    flash('Weapon unequipped and moved to inventory.', 'success')
    return redirect(url_for('student.character'))

@student_bp.route('/character/unequip_armor', methods=['POST'])
@login_required
@student_required
def unequip_armor():
    from flask import redirect, url_for, flash
    from app.models.character import Character
    from app.models.equipment import EquipmentType
    student_profile = Student.query.filter_by(user_id=current_user.id).first()
    if not student_profile or not student_profile.characters.filter_by(is_active=True).first().equipped_armor:
        flash('No armor equipped.', 'warning')
        return redirect(url_for('student.character'))
    main_character = student_profile.characters.filter_by(is_active=True).first()
    main_character.equipped_armor.is_equipped = False
    db.session.commit()
    flash('Armor unequipped and moved to inventory.', 'success')
    return redirect(url_for('student.character'))

@student_bp.route('/character/unequip_accessory', methods=['POST'])
@login_required
@student_required
def unequip_accessory():
    from flask import redirect, url_for, flash
    from app.models.character import Character
    from app.models.equipment import EquipmentType
    student_profile = Student.query.filter_by(user_id=current_user.id).first()
    if not student_profile or not student_profile.characters.filter_by(is_active=True).first().equipped_accessory:
        flash('No accessory equipped.', 'warning')
        return redirect(url_for('student.character'))
    main_character = student_profile.characters.filter_by(is_active=True).first()
    main_character.equipped_accessory.is_equipped = False
    db.session.commit()
    flash('Accessory unequipped and moved to inventory.', 'success')
    return redirect(url_for('student.character'))

@student_bp.route('/equipment/equip', methods=['PATCH'])
@login_required
@student_required
def api_equip_item():
    data = request.get_json()
    inventory_id = data.get('inventory_id')
    slot = data.get('slot')
    student_profile = Student.query.filter_by(user_id=current_user.id).first()
    if not student_profile:
        return jsonify({'success': False, 'message': 'No student profile found.'}), 404
    main_character = student_profile.characters.filter_by(is_active=True).first()
    if not main_character:
        return jsonify({'success': False, 'message': 'No character found.'}), 404
    item = Inventory.query.filter_by(id=inventory_id, character_id=main_character.id).first()
    if not item:
        return jsonify({'success': False, 'message': 'Item not found.'}), 404
    # Validate slot directly
    if item.item.slot != slot:
        return jsonify({'success': False, 'message': f'Cannot equip {item.item.type} in {slot} slot.'}), 400
    # Unequip any currently equipped item in the same slot
    for inv in main_character.inventory_items:
        if inv.is_equipped and inv.item.slot == item.item.slot:
            inv.is_equipped = False
    item.is_equipped = True
    db.session.commit()
    return jsonify({'success': True})

@student_bp.route('/equipment/unequip', methods=['PATCH'])
@login_required
@student_required
def api_unequip_item():
    data = request.get_json()
    inventory_id = data.get('inventory_id')
    student_profile = Student.query.filter_by(user_id=current_user.id).first()
    if not student_profile:
        return jsonify({'success': False, 'message': 'No student profile found.'}), 404
    main_character = student_profile.characters.filter_by(is_active=True).first()
    if not main_character:
        return jsonify({'success': False, 'message': 'No character found.'}), 404
    item = Inventory.query.filter_by(id=inventory_id, character_id=main_character.id).first()
    if not item or not item.is_equipped:
        return jsonify({'success': False, 'message': 'Item not equipped or not found.'}), 404
    item.is_equipped = False
    db.session.commit()
    return jsonify({'success': True})

@student_bp.route('/api/clan', methods=['GET'])
@login_required
@student_required
def api_get_student_clan():
    student_profile = Student.query.filter_by(user_id=current_user.id).first()
    if not student_profile:
        return jsonify({"clan": None}), 200
    main_character = student_profile.characters.filter_by(is_active=True).first()
    if not main_character or not main_character.clan:
        return jsonify({"clan": None}), 200
    clan = main_character.clan
    clan_data = clan.to_dict(include_members=True, include_metrics=True)
    clan_data["badges"] = [
        {"id": b.id, "name": b.name, "description": b.description, "icon": b.icon}
        for b in clan.badges
    ]
    return jsonify({"clan": clan_data})

@student_bp.route('/shop/buy', methods=['POST'])
@login_required
@student_required
def shop_buy():
    from flask import request
    from app.models.equipment import Equipment, Inventory
    from app.models.ability import Ability, CharacterAbility
    from app.models.shop import ShopPurchase, PurchaseType
    data = request.get_json()
    item_id = data.get('item_id')
    item_type = data.get('item_type')  # 'equipment' or 'ability', optional
    if not item_id:
        return jsonify({'success': False, 'message': 'Missing item_id.'}), 400
    # Get current student's active character
    student_profile = Student.query.filter_by(user_id=current_user.id).first()
    if not student_profile:
        return jsonify({'success': False, 'message': 'No student profile found.'}), 404
    character = student_profile.characters.filter_by(is_active=True).first()
    if not character:
        return jsonify({'success': False, 'message': 'No active character found.'}), 404
    # Determine item type and fetch item
    item = None
    purchase_type = None
    if item_type == 'equipment' or item_type is None:
        item = Equipment.query.filter_by(id=item_id).first()
        if item:
            purchase_type = PurchaseType.EQUIPMENT.value
    if not item and (item_type == 'ability' or item_type is None):
        item = Ability.query.filter_by(id=item_id).first()
        if item:
            purchase_type = PurchaseType.ABILITY.value
    if not item:
        return jsonify({'success': False, 'message': 'Item not found.'}), 404
    # Check ownership
    if purchase_type == PurchaseType.EQUIPMENT.value:
        already_owned = Inventory.query.filter_by(character_id=character.id, item_id=item.id).first()
    else:
        already_owned = CharacterAbility.query.filter_by(character_id=character.id, ability_id=item.id).first()
    if already_owned:
        return jsonify({'success': False, 'message': 'Item already owned.'}), 400
    # Validate gold
    cost = getattr(item, 'cost', 0)
    if character.gold < cost:
        return jsonify({'success': False, 'message': 'Not enough gold.'}), 400
    # Validate level
    level_req = getattr(item, 'level_requirement', 1)
    if character.level < level_req:
        return jsonify({'success': False, 'message': f'Level {level_req} required.'}), 400
    # Validate class restriction (equipment only)
    class_restr = getattr(item, 'class_restriction', None)
    if purchase_type == PurchaseType.EQUIPMENT.value and class_restr and class_restr.lower() != character.character_class.lower():
        return jsonify({'success': False, 'message': f'Class restriction: {class_restr}.'}), 400
    # Deduct gold
    character.gold -= cost
    # Set gold_spent to the item's price (or gold deducted)
    gold_spent = None
    if item_type == 'equipment':
        gold_spent = item.cost if item else None
    elif item_type == 'ability':
        gold_spent = item.cost if item else None
    else:
        gold_spent = item.cost if item else None
    if gold_spent is None:
        return jsonify({'success': False, 'message': 'Item has no cost set. Please contact your teacher/admin.'}), 400
    if gold_spent <= 0:
        return jsonify({'success': False, 'message': 'Invalid gold_spent value.'}), 400
    # Add to inventory or abilities
    if purchase_type == PurchaseType.EQUIPMENT.value:
        new_inv = Inventory(character_id=character.id, item_id=item.id, is_equipped=False)
        db.session.add(new_inv)
    else:
        new_ability = CharacterAbility(character_id=character.id, ability_id=item.id)
        db.session.add(new_ability)
    # Log purchase
    purchase = ShopPurchase(
        character_id=character.id,
        item_id=item.id,
        gold_spent=gold_spent,
        purchase_type=purchase_type,
        student_id=student_profile.id,
    )
    db.session.add(purchase)
    db.session.commit()
    # Prepare updated info
    inventory = [
        {'item_id': inv.item_id, 'is_equipped': inv.is_equipped}
        for inv in character.inventory_items
    ]
    abilities = [
        {'ability_id': ab.ability_id, 'level': ab.level}
        for ab in getattr(character, 'abilities', [])
    ]
    return jsonify({
        'success': True,
        'message': 'Item purchased successfully.',
        'character': {
            'id': character.id,
            'gold': character.gold,
            'level': character.level,
            'character_class': character.character_class
        },
        'inventory': inventory,
        'abilities': abilities
    }) 