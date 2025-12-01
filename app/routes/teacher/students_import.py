"""
Handles importing and exporting students (CSV upload, preview, confirm).
"""

from .blueprint import teacher_bp, teacher_required
from flask_login import login_required, current_user
from flask import render_template, request, redirect, url_for, flash, session
from app.models.classroom import Classroom
from app.services.student_import_service import StudentImportService
from io import TextIOWrapper

@teacher_bp.route('/import-students', methods=['GET', 'POST'])
@login_required
@teacher_required
def import_students():
    classes = Classroom.query.filter_by(teacher_id=current_user.id, is_active=True).all()
    results = None
    errors = []
    preview_data = None
    
    if request.method == 'POST':
        # Step 1: Handle mapping form submit
        if request.form.get('mapping_submit') == '1':
            mapping = {f: request.form.get(f) for f in StudentImportService.REQUIRED_FIELDS}
            file_contents = request.form.get('file_contents')
            class_id = request.form.get('class_id')
            
            if not file_contents or not class_id:
                flash('Missing file or class selection.', 'danger')
                return render_template('teacher/import_students.html', classes=classes)
            
            try:
                rows, _ = StudentImportService.parse_csv(file_contents)
                preview_data = []
                for row in rows:
                    data, error = StudentImportService.validate_row(row, mapping)
                    data['error'] = error
                    preview_data.append(data)
                    
                session['import_preview_data'] = preview_data
                session['import_class_id'] = class_id
                return render_template('teacher/import_students.html', classes=classes, preview_data=preview_data, class_id=class_id)
            except Exception as e:
                flash(f'Error processing CSV: {e}', 'danger')
                return render_template('teacher/import_students.html', classes=classes)

        # Step 2: Confirmation step
        if request.form.get('confirm_import') == '1':
            preview_data = session.get('import_preview_data')
            class_id = session.get('import_class_id')
            
            if not preview_data or not class_id:
                flash('No preview data found. Please re-upload your CSV.', 'danger')
                return render_template('teacher/import_students.html', classes=classes)
            
            classroom = Classroom.query.get(class_id)
            if not classroom:
                flash('Class not found.', 'danger')
                return render_template('teacher/import_students.html', classes=classes)
            
            import_results = StudentImportService.process_import(preview_data, classroom)
            
            if import_results['created'] or import_results['reassigned']:
                flash(f'Successfully created {import_results["created"]} students, reassigned {import_results["reassigned"]} unassigned students.', 'success')
            
            if import_results['failed']:
                flash(f'Failed to create or reassign {import_results["failed"]} students. See errors below.', 'danger')
                errors = import_results['errors']
            
            session.pop('import_preview_data', None)
            session.pop('import_class_id', None)
            return render_template('teacher/import_students.html', classes=classes, results=import_results, errors=errors)

        # Step 3: Initial upload step
        file = request.files.get('csv_file')
        class_id = request.form.get('class_id')
        
        if not file or not class_id:
            flash('CSV file and class selection are required.', 'danger')
            return render_template('teacher/import_students.html', classes=classes)
        
        try:
            stream = TextIOWrapper(file.stream, encoding='utf-8')
            file_contents = stream.read()
            rows, csv_columns = StudentImportService.parse_csv(file_contents)
            
            if not csv_columns:
                flash('CSV file is empty or invalid.', 'danger')
                return render_template('teacher/import_students.html', classes=classes)
            
            if StudentImportService.REQUIRED_FIELDS.issubset(csv_columns):
                preview_data = []
                for row in rows:
                    data, error = StudentImportService.validate_row(row)
                    data['error'] = error
                    preview_data.append(data)
                
                session['import_preview_data'] = preview_data
                session['import_class_id'] = class_id
                return render_template('teacher/import_students.html', classes=classes, preview_data=preview_data, class_id=class_id)
            else:
                return render_template(
                    'teacher/import_students.html',
                    classes=classes,
                    mapping_needed=True,
                    csv_columns=csv_columns,
                    required_fields=StudentImportService.REQUIRED_FIELDS,
                    file_contents=file_contents,
                    class_id=class_id
                )
        except Exception as e:
            flash(f'Error processing CSV: {e}', 'danger')
            return render_template('teacher/import_students.html', classes=classes)

    # GET request
    return render_template('teacher/import_students.html', classes=classes)
