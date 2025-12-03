from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from app.models import db
from app.models.education import QuestionSet, Question
from app.models.teacher import Teacher
from app.routes.teacher.blueprint import teacher_required

teacher_education_bp = Blueprint('teacher_education', __name__, url_prefix='/teacher/education')

@teacher_education_bp.route('/sets', methods=['GET'])
@login_required
@teacher_required
def list_sets():
    """List all question sets for the current teacher."""
    # Get or create teacher profile
    teacher = Teacher.query.filter_by(user_id=current_user.id).first()
    if not teacher:
        teacher = Teacher(user_id=current_user.id)
        db.session.add(teacher)
        db.session.commit()
    
    question_sets = QuestionSet.query.filter_by(teacher_id=teacher.id).order_by(QuestionSet.created_at.desc()).all()
    return render_template('teacher/education/sets.html', question_sets=question_sets, active_page='education')

@teacher_education_bp.route('/sets/create', methods=['GET', 'POST'])
@login_required
@teacher_required
def create_set():
    """Create a new question set."""
    # Get or create teacher profile
    teacher = Teacher.query.filter_by(user_id=current_user.id).first()
    if not teacher:
        teacher = Teacher(user_id=current_user.id)
        db.session.add(teacher)
        db.session.commit()
    
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        is_active = request.form.get('is_active') == 'on'
        
        if not title:
            flash('Title is required.', 'danger')
            return render_template('teacher/education/set_form.html', question_set=None, active_page='education')
        
        new_set = QuestionSet(
            title=title,
            description=description,
            teacher_id=teacher.id,
            is_active=is_active
        )
        db.session.add(new_set)
        db.session.commit()
        flash(f'Question set "{title}" created successfully!', 'success')
        return redirect(url_for('teacher_education.manage_questions', set_id=new_set.id))
    
    return render_template('teacher/education/set_form.html', question_set=None, active_page='education')

@teacher_education_bp.route('/sets/<int:set_id>/edit', methods=['GET', 'POST'])
@login_required
@teacher_required
def edit_set(set_id):
    """Edit an existing question set."""
    teacher = Teacher.query.filter_by(user_id=current_user.id).first()
    if not teacher:
        flash('Teacher profile not found.', 'danger')
        return redirect(url_for('teacher_education.list_sets'))
    
    question_set = QuestionSet.query.filter_by(id=set_id, teacher_id=teacher.id).first_or_404()
    
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        is_active = request.form.get('is_active') == 'on'
        
        if not title:
            flash('Title is required.', 'danger')
            return render_template('teacher/education/set_form.html', question_set=question_set, active_page='education')
        
        question_set.title = title
        question_set.description = description
        question_set.is_active = is_active
        db.session.commit()
        flash(f'Question set "{title}" updated successfully!', 'success')
        return redirect(url_for('teacher_education.list_sets'))
    
    return render_template('teacher/education/set_form.html', question_set=question_set, active_page='education')

@teacher_education_bp.route('/sets/<int:set_id>/delete', methods=['POST'])
@login_required
@teacher_required
def delete_set(set_id):
    """Delete a question set."""
    teacher = Teacher.query.filter_by(user_id=current_user.id).first()
    if not teacher:
        flash('Teacher profile not found.', 'danger')
        return redirect(url_for('teacher_education.list_sets'))
    
    question_set = QuestionSet.query.filter_by(id=set_id, teacher_id=teacher.id).first_or_404()
    title = question_set.title
    db.session.delete(question_set)
    db.session.commit()
    flash(f'Question set "{title}" deleted successfully.', 'success')
    return redirect(url_for('teacher_education.list_sets'))

@teacher_education_bp.route('/sets/<int:set_id>/questions', methods=['GET', 'POST'])
@login_required
@teacher_required
def manage_questions(set_id):
    """Manage questions in a question set."""
    teacher = Teacher.query.filter_by(user_id=current_user.id).first()
    if not teacher:
        flash('Teacher profile not found.', 'danger')
        return redirect(url_for('teacher_education.list_sets'))
    
    question_set = QuestionSet.query.filter_by(id=set_id, teacher_id=teacher.id).first_or_404()
    
    if request.method == 'POST':
        text = request.form.get('text', '').strip()
        question_type = request.form.get('question_type', 'multiple_choice')
        correct_answer = request.form.get('correct_answer', '').strip()
        difficulty = request.form.get('difficulty', type=int, default=1)
        
        # Get options (for multiple choice)
        options = []
        for i in range(1, 5):  # Support up to 4 options
            option = request.form.get(f'option_{i}', '').strip()
            if option:
                options.append(option)
        
        if not text or not correct_answer:
            flash('Question text and correct answer are required.', 'danger')
        elif question_type == 'multiple_choice' and len(options) < 2:
            flash('Multiple choice questions must have at least 2 options.', 'danger')
        elif question_type == 'multiple_choice' and correct_answer not in options:
            flash('Correct answer must be one of the options.', 'danger')
        else:
            new_question = Question(
                set_id=question_set.id,
                text=text,
                question_type=question_type,
                options=options,
                correct_answer=correct_answer,
                difficulty=difficulty
            )
            db.session.add(new_question)
            db.session.commit()
            flash('Question added successfully!', 'success')
            return redirect(url_for('teacher_education.manage_questions', set_id=set_id))
    
    questions = Question.query.filter_by(set_id=set_id).order_by(Question.id).all()
    return render_template('teacher/education/questions.html', question_set=question_set, questions=questions, active_page='education')

@teacher_education_bp.route('/questions/<int:question_id>/delete', methods=['POST'])
@login_required
@teacher_required
def delete_question(question_id):
    """Delete a question."""
    teacher = Teacher.query.filter_by(user_id=current_user.id).first()
    if not teacher:
        flash('Teacher profile not found.', 'danger')
        return redirect(url_for('teacher_education.list_sets'))
    
    question = Question.query.get_or_404(question_id)
    question_set = QuestionSet.query.filter_by(id=question.set_id, teacher_id=teacher.id).first_or_404()
    
    db.session.delete(question)
    db.session.commit()
    flash('Question deleted successfully.', 'success')
    return redirect(url_for('teacher_education.manage_questions', set_id=question_set.id))
