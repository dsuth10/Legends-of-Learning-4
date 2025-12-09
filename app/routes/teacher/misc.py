from .blueprint import teacher_bp, teacher_required
from flask_login import login_required, current_user
from flask import render_template, request, jsonify, flash, send_file, abort
from app.models import db
from app.models.classroom import Classroom
from app.models.clan import Clan
from app.models.quest import Quest
from app.models.audit import AuditLog
from app.models.user import User
from app.models.character import Character
from app.models.shop import ShopPurchase
from app.models.student import Student
from app.models.equipment import Equipment
from app.models.ability import Ability
from app.services.backup_service import (
    create_database_backup,
    get_available_tables,
    get_database_info,
    export_table_to_csv,
    export_table_to_json,
    validate_table_name
)
from app.utils.backup_utils import format_file_size, generate_safe_filename
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

@teacher_bp.route('/dashboard')
@login_required
@teacher_required
def dashboard():
    # Get stats for the current teacher
    stats = {
        'active_classes': Classroom.query.filter_by(
            teacher_id=current_user.id, 
            is_active=True
        ).count(),
        'total_students': db.session.query(User).\
            join(Classroom.students).\
            filter(Classroom.teacher_id == current_user.id).\
            distinct().\
            count(),
        'active_clans': Clan.query.\
            join(Classroom, Clan.class_id == Classroom.id).\
            filter(Classroom.teacher_id == current_user.id,
                  Clan.is_active == True).\
            count(),
        'active_quests': Quest.query.\
            join(Classroom, Quest.id == Classroom.id).\
            filter(Classroom.teacher_id == current_user.id,
                  Quest.end_date >= datetime.now(timezone.utc).replace(tzinfo=None)).\
            count()
    }
    total_classes = Classroom.query.filter_by(teacher_id=current_user.id, is_active=True).count()
    total_students = db.session.query(User).\
        join(Classroom.students).\
        filter(Classroom.teacher_id == current_user.id).\
        distinct().\
        count()
    active_students = db.session.query(User).\
        join(Classroom.students).\
        filter(Classroom.teacher_id == current_user.id, User.is_active == True).\
        distinct().\
        count()
    inactive_students = total_students - active_students
    seven_days_ago = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=7)
    recent_activities = []
    audit_logs = AuditLog.query.\
        join(Character, AuditLog.character_id == Character.id).\
        join(Classroom, Classroom.id == Character.student_id).\
        filter(
            Classroom.teacher_id == current_user.id,
            AuditLog.event_timestamp >= seven_days_ago,
            AuditLog.event_type.in_([
                'QUEST_START', 'QUEST_COMPLETE', 'QUEST_FAIL',
                'CLAN_JOIN', 'CLAN_LEAVE', 'LEVEL_UP',
                'ABILITY_LEARN', 'EQUIPMENT_CHANGE'
            ])
        ).\
        order_by(AuditLog.event_timestamp.desc()).\
        limit(10).all()
    for log in audit_logs:
        activity = {
            'title': AuditLog.EVENT_TYPES.get(log.event_type, log.event_type),
            'timestamp': log.event_timestamp,
            'description': f"{log.character.name} - {log.event_data.get('description', '')}",
            'details': log.event_data.get('details', '')
        }
        recent_activities.append(activity)
    classes = Classroom.query.filter_by(teacher_id=current_user.id, is_active=True).all()
    class_labels = []
    class_counts = []
    active_counts = []
    inactive_counts = []
    for c in classes:
        class_labels.append(c.name)
        total = c.students.count()
        class_counts.append(total)
        active = sum(1 for s in c.students if s.is_active)
        inactive = total - active
        active_counts.append(active)
        inactive_counts.append(inactive)
    return render_template(
        'teacher/dashboard.html',
        title='Teacher Dashboard',
        teacher=current_user,
        stats=stats,
        recent_activities=recent_activities,
        active_page='dashboard',
        classes=classes,
        total_classes=total_classes,
        total_students=total_students,
        active_students=active_students,
        inactive_students=inactive_students,
        class_labels=json.dumps(class_labels),
        class_counts=json.dumps(class_counts),
        active_counts=json.dumps(active_counts),
        inactive_counts=json.dumps(inactive_counts)
    )

@teacher_bp.route('/shop')
@login_required
@teacher_required
def shop():
    return render_template('teacher/shop.html', active_page='shop')

@teacher_bp.route('/analytics')
@login_required
@teacher_required
def analytics():
    classes = Classroom.query.filter_by(teacher_id=current_user.id, is_active=True).all()
    class_id = request.args.get('class_id', type=int)
    selected_class = None
    class_labels = []
    class_counts = []
    active_counts = []
    inactive_counts = []
    if class_id:
        selected_class = Classroom.query.filter_by(id=class_id, teacher_id=current_user.id).first()
        if selected_class:
            class_labels = [selected_class.name]
            total = selected_class.students.count()
            class_counts = [total]
            active = sum(1 for s in selected_class.students if s.is_active)
            inactive = total - active
            active_counts = [active]
            inactive_counts = [inactive]
    return render_template(
        'teacher/analytics.html',
        active_page='analytics',
        classes=classes,
        selected_class=selected_class,
        class_labels=json.dumps(class_labels),
        class_counts=json.dumps(class_counts),
        active_counts=json.dumps(active_counts),
        inactive_counts=json.dumps(inactive_counts)
    )

@teacher_bp.route('/analytics/data')
@login_required
@teacher_required
def analytics_data():
    class_id = request.args.get('class_id', type=int)
    if not class_id:
        return {'error': 'Missing class_id'}, 400
    selected_class = Classroom.query.filter_by(id=class_id, teacher_id=current_user.id).first()
    if not selected_class:
        return {'error': 'Class not found or not authorized'}, 404
    class_labels = [selected_class.name]
    total = selected_class.students.count()
    class_counts = [total]
    active = sum(1 for s in selected_class.students if s.is_active)
    inactive = total - active
    active_counts = [active]
    inactive_counts = [inactive]
    return {
        'class_labels': class_labels,
        'class_counts': class_counts,
        'active_counts': active_counts,
        'inactive_counts': inactive_counts
    }

@teacher_bp.route('/backup')
@login_required
@teacher_required
def backup():
    """Display backup page with database info and export options."""
    try:
        db_info = get_database_info()
        tables = get_available_tables()
        
        # Format file size for display
        db_info['formatted_size'] = format_file_size(db_info['size']) if db_info['size'] > 0 else 'N/A'
        
        return render_template(
            'teacher/backup.html',
            active_page='backup',
            db_info=db_info,
            tables=tables
        )
    except Exception as e:
        flash(f'Error loading backup page: {str(e)}', 'danger')
        return render_template('teacher/backup.html', active_page='backup', db_info=None, tables=[])


@teacher_bp.route('/backup/download')
@login_required
@teacher_required
def backup_download():
    """Download full database backup file."""
    backup_path = None
    try:
        backup_path = create_database_backup()
        
        # Generate safe filename for download
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        download_filename = generate_safe_filename(f"legends_backup_{timestamp}", ".db")
        
        # Schedule cleanup after response is sent
        try:
            @request.after_this_request
            def remove_file(response):
                try:
                    if backup_path and backup_path.exists():
                        os.remove(backup_path)
                except Exception:
                    pass  # Ignore cleanup errors
                return response
        except AttributeError:
            # Fallback for older Flask versions - temp files will be cleaned by OS
            pass
        
        return send_file(
            str(backup_path),
            as_attachment=True,
            download_name=download_filename,
            mimetype='application/x-sqlite3'
        )
    except FileNotFoundError as e:
        if backup_path and backup_path.exists():
            try:
                os.remove(backup_path)
            except Exception:
                pass
        flash(f'Database file not found: {str(e)}', 'danger')
        abort(404)
    except PermissionError as e:
        if backup_path and backup_path.exists():
            try:
                os.remove(backup_path)
            except Exception:
                pass
        flash(f'Permission denied: {str(e)}', 'danger')
        abort(403)
    except Exception as e:
        # Clean up on error
        if backup_path and backup_path.exists():
            try:
                os.remove(backup_path)
            except Exception:
                pass
        flash(f'Error creating backup: {str(e)}', 'danger')
        abort(500)


@teacher_bp.route('/backup/export')
@login_required
@teacher_required
def backup_export_table():
    """Export a specific table to CSV or JSON format."""
    table_name = request.args.get('table')
    format_type = request.args.get('format', 'csv').lower()
    
    if not table_name:
        flash('Table name is required', 'danger')
        abort(400)
    
    if format_type not in ['csv', 'json']:
        flash('Invalid format. Use "csv" or "json"', 'danger')
        abort(400)
    
    if not validate_table_name(table_name):
        flash(f'Invalid or non-existent table: {table_name}', 'danger')
        abort(400)
    
    export_path = None
    try:
        if format_type == 'csv':
            export_path = export_table_to_csv(table_name)
            mimetype = 'text/csv'
            extension = '.csv'
        else:  # json
            export_path = export_table_to_json(table_name)
            mimetype = 'application/json'
            extension = '.json'
        
        # Generate safe filename for download
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        download_filename = generate_safe_filename(f"{table_name}_export_{timestamp}", extension)
        
        # Schedule cleanup after response is sent
        try:
            @request.after_this_request
            def remove_file(response):
                try:
                    if export_path and export_path.exists():
                        os.remove(export_path)
                except Exception:
                    pass  # Ignore cleanup errors
                return response
        except AttributeError:
            # Fallback for older Flask versions - temp files will be cleaned by OS
            pass
        
        return send_file(
            str(export_path),
            as_attachment=True,
            download_name=download_filename,
            mimetype=mimetype
        )
    except ValueError as e:
        if export_path and export_path.exists():
            try:
                os.remove(export_path)
            except Exception:
                pass
        flash(str(e), 'danger')
        abort(400)
    except Exception as e:
        if export_path and export_path.exists():
            try:
                os.remove(export_path)
            except Exception:
                pass
        flash(f'Error exporting table: {str(e)}', 'danger')
        abort(500)

@teacher_bp.route('/purchases')
@login_required
@teacher_required
def purchase_log():
    purchases = ShopPurchase.query.order_by(ShopPurchase.purchase_date.desc()).limit(100).all()
    purchase_data = []
    for p in purchases:
        student = Student.query.get(p.student_id)
        user = User.query.get(student.user_id) if student else None
        item_name = None
        if p.purchase_type == 'equipment':
            item = Equipment.query.get(p.item_id)
            item_name = item.name if item else 'Unknown Equipment'
        elif p.purchase_type == 'ability':
            item = Ability.query.get(p.item_id)
            item_name = item.name if item else 'Unknown Ability'
        else:
            item_name = 'Unknown'
        purchase_data.append({
            'student': user.username if user else 'Unknown',
            'item_name': item_name,
            'item_type': p.purchase_type,
            'gold_spent': p.gold_spent,
            'date': p.purchase_date.strftime('%Y-%m-%d %H:%M'),
        })
    return render_template('teacher/purchase_log.html', purchases=purchase_data, active_page='purchase_log') 