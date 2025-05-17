from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from .teacher import student_required
from flask_sqlalchemy import SQLAlchemy
from app.models.character import Character
from app.models.equipment import Inventory, Equipment, EquipmentType, EquipmentSlot, TEST_ARMOR_IMAGE, TEST_RING_IMAGE, TEST_SWORD_IMAGE
from app.models.student import Student

student_bp = Blueprint('student', __name__, url_prefix='/student')
db = SQLAlchemy()

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
    return render_template('student/quests.html', student=current_user)

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
    if student_profile:
        main_character = student_profile.characters.filter_by(is_active=True).first()
    return render_template('student/character.html', student=current_user, main_character=main_character)

@student_bp.route('/shop')
@login_required
@student_required
def shop():
    return render_template('student/shop.html', student=current_user)

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
        from app.models import db
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
    from app.models import db
    db.session.commit()
    flash('Gained 500 XP!','success')
    return redirect(url_for('student.character'))

@student_bp.route('/character/add_test_weapon', methods=['POST'])
@login_required
@student_required
def add_test_weapon():
    from flask import redirect, url_for, flash
    from app.models.character import Character
    from app.models.equipment import Equipment, EquipmentType, EquipmentSlot, Inventory
    student_profile = Student.query.filter_by(user_id=current_user.id).first()
    if not student_profile:
        flash('No student profile found.', 'danger')
        return redirect(url_for('student.dashboard'))
    main_character = student_profile.characters.filter_by(is_active=True).first()
    if not main_character:
        flash('No character found.', 'danger')
        return redirect(url_for('student.character'))
    weapon = Equipment.query.filter_by(name='Test Sword').first()
    if not weapon:
        weapon = Equipment(
            name='Test Sword',
            description='A sharp blade for testing.',
            type=EquipmentType.WEAPON,
            slot=EquipmentSlot.MAIN_HAND,
            level_requirement=1,
            health_bonus=0,
            strength_bonus=5,
            defense_bonus=0,
            cost=0,
            image_url=TEST_SWORD_IMAGE
        )
        from app.models import db
        db.session.add(weapon)
        db.session.commit()
    inv = Inventory.query.filter_by(character_id=main_character.id, equipment_id=weapon.id).first()
    if not inv:
        inv = Inventory(character_id=main_character.id, equipment_id=weapon.id, is_equipped=True)
        from app.models import db
        db.session.add(inv)
    else:
        inv.is_equipped = True
    from app.models import db
    db.session.commit()
    inv.equip()
    flash('Test weapon added and equipped!','success')
    return redirect(url_for('student.character'))

@student_bp.route('/character/add_test_armor', methods=['POST'])
@login_required
@student_required
def add_test_armor():
    from flask import redirect, url_for, flash
    from app.models.character import Character
    from app.models.equipment import Equipment, EquipmentType, EquipmentSlot, Inventory
    student_profile = Student.query.filter_by(user_id=current_user.id).first()
    if not student_profile:
        flash('No student profile found.', 'danger')
        return redirect(url_for('student.dashboard'))
    main_character = student_profile.characters.filter_by(is_active=True).first()
    if not main_character:
        flash('No character found.', 'danger')
        return redirect(url_for('student.character'))
    armor = Equipment.query.filter_by(name='Test Armor').first()
    if not armor:
        armor = Equipment(
            name='Test Armor',
            description='Sturdy armor for testing.',
            type=EquipmentType.ARMOR,
            slot=EquipmentSlot.CHEST,
            level_requirement=1,
            health_bonus=20,
            strength_bonus=0,
            defense_bonus=5,
            cost=0,
            image_url=TEST_ARMOR_IMAGE
        )
        from app.models import db
        db.session.add(armor)
        db.session.commit()
    inv = Inventory.query.filter_by(character_id=main_character.id, equipment_id=armor.id).first()
    if not inv:
        inv = Inventory(character_id=main_character.id, equipment_id=armor.id, is_equipped=True)
        from app.models import db
        db.session.add(inv)
    else:
        inv.is_equipped = True
    from app.models import db
    db.session.commit()
    inv.equip()
    flash('Test armor added and equipped!','success')
    return redirect(url_for('student.character'))

@student_bp.route('/character/add_test_accessory', methods=['POST'])
@login_required
@student_required
def add_test_accessory():
    from flask import redirect, url_for, flash
    from app.models.character import Character
    from app.models.equipment import Equipment, EquipmentType, EquipmentSlot, Inventory
    student_profile = Student.query.filter_by(user_id=current_user.id).first()
    if not student_profile:
        flash('No student profile found.', 'danger')
        return redirect(url_for('student.dashboard'))
    main_character = student_profile.characters.filter_by(is_active=True).first()
    if not main_character:
        flash('No character found.', 'danger')
        return redirect(url_for('student.character'))
    accessory = Equipment.query.filter_by(name='Test Ring').first()
    if not accessory:
        accessory = Equipment(
            name='Test Ring',
            description='A magical ring for testing.',
            type=EquipmentType.ACCESSORY,
            slot=EquipmentSlot.RING,
            level_requirement=1,
            health_bonus=5,
            strength_bonus=2,
            defense_bonus=2,
            cost=0,
            image_url=TEST_RING_IMAGE
        )
        from app.models import db
        db.session.add(accessory)
        db.session.commit()
    inv = Inventory.query.filter_by(character_id=main_character.id, equipment_id=accessory.id).first()
    if not inv:
        inv = Inventory(character_id=main_character.id, equipment_id=accessory.id, is_equipped=True)
        from app.models import db
        db.session.add(inv)
    else:
        inv.is_equipped = True
    from app.models import db
    db.session.commit()
    inv.equip()
    flash('Test accessory added and equipped!','success')
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
    from app.models import db
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
    from app.models import db
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
    from app.models import db
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
    # Validate slot type
    slot_map = {
        'weapon': [EquipmentSlot.MAIN_HAND, EquipmentSlot.OFF_HAND],
        'armor': [EquipmentSlot.HEAD, EquipmentSlot.CHEST, EquipmentSlot.LEGS, EquipmentSlot.FEET],
        'accessory': [EquipmentSlot.NECK, EquipmentSlot.RING],
    }
    # Map slot string to type
    slot_type = None
    for t, slots in slot_map.items():
        if item.equipment.slot in slots and slot == t:
            slot_type = t
            break
    if not slot_type or slot_type != item.equipment.type.value:
        return jsonify({'success': False, 'message': f'Cannot equip {item.equipment.type.value} in {slot} slot.'}), 400
    # Unequip any currently equipped item in the same slot
    for inv in main_character.inventory_items:
        if inv.is_equipped and inv.equipment.slot == item.equipment.slot:
            inv.is_equipped = False
    item.is_equipped = True
    from app.models import db
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
    from app.models import db
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
    return jsonify({
        "clan": clan.to_dict(include_members=True, include_metrics=True)
    }) 