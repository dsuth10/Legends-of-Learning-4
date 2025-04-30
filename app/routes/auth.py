from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from app.models import db
from app.models.user import User

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
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