from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from app.models import db
from app.models.user import User, UserRole

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        # Redirect based on role if already logged in
        if current_user.role == UserRole.TEACHER:
            return redirect(url_for('teacher.dashboard'))
        elif current_user.role == UserRole.STUDENT:
            return redirect(url_for('student.dashboard'))
        else:
            return redirect(url_for('main.index'))
    error = None
    if request.method == 'POST':
        username_or_email = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter((User.username == username_or_email) | (User.email == username_or_email)).first()
        if user and user.check_password(password):
            if not user.is_active:
                error = 'Account is inactive. Please contact your administrator.'
            else:
                login_user(user)
                flash('Logged in successfully.', 'success')
                next_page = request.args.get('next')
                # Role-based redirect after login
                if user.role == UserRole.TEACHER:
                    return redirect(next_page or url_for('teacher.dashboard'))
                elif user.role == UserRole.STUDENT:
                    return redirect(next_page or url_for('student.dashboard'))
                else:
                    return redirect(next_page or url_for('main.index'))
        else:
            error = 'Invalid username/email or password.'
    if error:
        flash(error, 'danger')
    return render_template('login.html', title='Login')

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))

@auth_bp.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        access_code = request.form.get('access_code')

        # Validation
        if not all([username, email, password, confirm_password, access_code]):
            flash('All fields are required', 'danger')
            return render_template('signup.html')

        if password != confirm_password:
            flash('Passwords do not match', 'danger')
            return render_template('signup.html')

        # Check if user already exists
        existing_user = User.query.filter(
            (User.username == username) | (User.email == email)
        ).first()
        if existing_user:
            flash('Username or email already exists', 'danger')
            return render_template('signup.html')

        # Validate access code
        from flask import current_app
        valid_access_code = current_app.config.get('TEACHER_ACCESS_CODE')
        if access_code != valid_access_code:
            flash('Invalid access code', 'danger')
            return render_template('signup.html')

        # Create new teacher user
        new_user = User(
            username=username,
            email=email,
            role=UserRole.TEACHER
        )
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()

        # Log the user in
        login_user(new_user)
        flash('Account created successfully!', 'success')
        # Redirect to teacher dashboard after signup
        return redirect(url_for('teacher.dashboard'))

    return render_template('signup.html') 