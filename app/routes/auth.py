from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_user, logout_user, login_required, current_user
from app.models import db
from app.models.user import User, UserRole
from app.forms.auth import LoginForm, SignupForm

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        if current_user.role == UserRole.TEACHER:
            return redirect(url_for('teacher.dashboard'))
        elif current_user.role == UserRole.STUDENT:
            return redirect(url_for('student.dashboard'))
        else:
            return redirect(url_for('main.index'))
    
    form = LoginForm()
    if form.validate_on_submit():
        username_or_email = form.username.data
        password = form.password.data
        user = User.query.filter((User.username == username_or_email) | (User.email == username_or_email)).first()
        if user and user.check_password(password):
            if not user.is_active:
                flash('Account is inactive. Please contact your administrator.', 'danger')
            else:
                login_user(user)
                flash('Logged in successfully.', 'success')
                next_page = request.args.get('next')
                if user.role == UserRole.TEACHER:
                    return redirect(next_page or url_for('teacher.dashboard'))
                elif user.role == UserRole.STUDENT:
                    return redirect(next_page or url_for('student.dashboard'))
                else:
                    return redirect(next_page or url_for('main.index'))
        else:
            flash('Invalid username/email or password.', 'danger')
            
    return render_template('login.html', title='Login', form=form)

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))

@auth_bp.route('/signup', methods=['GET', 'POST'])
def signup():
    form = SignupForm()
    if form.validate_on_submit():
        access_code = form.access_code.data
        valid_access_code = current_app.config.get('TEACHER_ACCESS_CODE')
        
        if access_code != valid_access_code:
            flash('Invalid access code', 'danger')
            return render_template('signup.html', form=form)

        new_user = User(
            username=form.username.data,
            email=form.email.data,
            role=UserRole.TEACHER
        )
        new_user.set_password(form.password.data)
        db.session.add(new_user)
        db.session.commit()

        login_user(new_user)
        flash('Account created successfully!', 'success')
        return redirect(url_for('teacher.dashboard'))

    return render_template('signup.html', form=form)