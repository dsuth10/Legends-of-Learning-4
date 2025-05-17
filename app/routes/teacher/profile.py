from .blueprint import teacher_bp, teacher_required
from flask_login import login_required, current_user
from flask import render_template, request, flash
from app.models import db
from app.models.user import User
import os

@teacher_bp.route('/profile', methods=['GET', 'POST'])
@login_required
@teacher_required
def profile():
    teacher = current_user
    avatar_url = teacher.avatar_url
    if request.method == 'POST':
        username = request.form.get('username', teacher.username).strip()
        email = request.form.get('email', teacher.email).strip()
        first_name = request.form.get('first_name', teacher.first_name).strip()
        last_name = request.form.get('last_name', teacher.last_name).strip()
        display_name = request.form.get('display_name', teacher.display_name).strip()
        # Password change fields
        current_password = request.form.get('current_password', '').strip()
        new_password = request.form.get('new_password', '').strip()
        confirm_password = request.form.get('confirm_password', '').strip()
        # Avatar upload
        avatar_file = request.files.get('avatar')
        if avatar_file and avatar_file.filename:
            allowed = {'png', 'jpg', 'jpeg', 'gif'}
            ext = avatar_file.filename.rsplit('.', 1)[-1].lower()
            # Check file size (max 2MB)
            avatar_file.stream.seek(0, os.SEEK_END)
            file_size = avatar_file.stream.tell()
            avatar_file.stream.seek(0)
            max_size = 2 * 1024 * 1024  # 2MB
            if file_size > max_size:
                flash('Avatar image must be 2MB or less.', 'danger')
                return render_template('teacher/profile.html', teacher=teacher, avatar_url=avatar_url)
            if ext not in allowed:
                flash('Only image files (png, jpg, jpeg, gif) are allowed for avatar.', 'danger')
                return render_template('teacher/profile.html', teacher=teacher, avatar_url=avatar_url)
            # Save file
            avatar_dir = os.path.join('static', 'avatars')
            os.makedirs(avatar_dir, exist_ok=True)
            filename = f"teacher_{teacher.id}_avatar.{ext}"
            filepath = os.path.join(avatar_dir, filename)
            avatar_file.save(filepath)
            teacher.avatar_url = f"/static/avatars/{filename}"
            avatar_url = teacher.avatar_url
            flash('Avatar updated!', 'success')
        # Basic validation
        if not username or not email:
            flash('Username and email are required.', 'danger')
            return render_template('teacher/profile.html', teacher=teacher, avatar_url=avatar_url)
        # Check for username/email conflicts (other users)
        existing_user = User.query.filter(
            ((User.username == username) | (User.email == email)) & (User.id != teacher.id)
        ).first()
        if existing_user:
            flash('Username or email already in use.', 'danger')
            return render_template('teacher/profile.html', teacher=teacher, avatar_url=avatar_url)
        # Password change logic
        if new_password:
            if not current_password:
                flash('Current password is required to change your password.', 'danger')
                return render_template('teacher/profile.html', teacher=teacher, avatar_url=avatar_url)
            if not teacher.check_password(current_password):
                flash('Current password is incorrect.', 'danger')
                return render_template('teacher/profile.html', teacher=teacher, avatar_url=avatar_url)
            if new_password != confirm_password:
                flash('New password and confirmation do not match.', 'danger')
                return render_template('teacher/profile.html', teacher=teacher, avatar_url=avatar_url)
            teacher.set_password(new_password)
            flash('Password updated successfully!', 'success')
        teacher.username = username
        teacher.email = email
        teacher.first_name = first_name
        teacher.last_name = last_name
        teacher.display_name = display_name
        try:
            db.session.commit()
            if not new_password and not (avatar_file and avatar_file.filename):
                flash('Profile updated successfully!', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating profile: {e}', 'danger')
    return render_template('teacher/profile.html', teacher=teacher, avatar_url=teacher.avatar_url) 