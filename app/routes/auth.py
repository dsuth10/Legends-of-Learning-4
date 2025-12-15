from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_user, logout_user, login_required, current_user
from app.models import db
from app.models.user import User, UserRole
from app.forms.auth import LoginForm, SignupForm
from urllib.parse import urlparse

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

def is_safe_redirect_url(url, user_role):
    """
    Validate that a redirect URL is safe and appropriate for the user's role.
    
    Args:
        url: The URL to validate (can be None)
        user_role: The UserRole of the user (UserRole.TEACHER, UserRole.STUDENT, etc.)
    
    Returns:
        The sanitized URL path if valid, None otherwise
    """
    if not url:
        return None
    
    # Parse the URL to check if it's external
    parsed = urlparse(url)
    
    # Reject external URLs (must be relative path starting with /)
    if parsed.scheme or parsed.netloc:
        return None
    
    # Must start with / to be a valid internal path
    if not url.startswith('/'):
        return None
    
    # Reject URLs containing // (potential protocol-relative or path traversal)
    if '//' in url:
        return None
    
    # Validate role-appropriateness
    if user_role == UserRole.STUDENT:
        # Students should not be redirected to teacher routes
        if url.startswith('/teacher'):
            return None
    elif user_role == UserRole.TEACHER:
        # Teachers should not be redirected to student routes
        if url.startswith('/student'):
            return None
    
    # URL is safe and role-appropriate
    return url

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        if current_user.role == UserRole.TEACHER:
            return redirect(url_for('teacher.dashboard'))
        elif current_user.role == UserRole.STUDENT:
            return redirect(url_for('student.character'))
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
                # Validate and sanitize the next parameter
                safe_next = is_safe_redirect_url(next_page, user.role)
                
                if user.role == UserRole.TEACHER:
                    return redirect(safe_next or url_for('teacher.dashboard'))
                elif user.role == UserRole.STUDENT:
                    return redirect(safe_next or url_for('student.character'))
                else:
                    return redirect(safe_next or url_for('main.index'))
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