from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, SelectField
from wtforms.validators import DataRequired, Email, Length, Optional, ValidationError
from app.models.user import User

class AddStudentForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=64)])
    email = StringField('Email', validators=[DataRequired(), Email(), Length(max=120)])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    first_name = StringField('First Name', validators=[Optional(), Length(max=64)])
    last_name = StringField('Last Name', validators=[Optional(), Length(max=64)])
    class_id = SelectField('Class', coerce=int, validators=[DataRequired()])
    submit = SubmitField('Add Student')

    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError('Username already exists.')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('Email already exists.')
