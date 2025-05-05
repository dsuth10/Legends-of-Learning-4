import os
import sys
from app import create_app
from app.models import db
from app.models.classroom import Classroom, class_students
from app.models.student import Student
from app.models.user import User, UserRole

app = create_app()

with app.app_context():
    print('Deleting all class-student associations...')
    db.session.execute(class_students.delete())
    db.session.commit()
    print('Deleting all students...')
    Student.query.delete()
    db.session.commit()
    print('Deleting all classrooms...')
    Classroom.query.delete()
    db.session.commit()
    print('Deleting all teachers and students...')
    User.query.filter(User.role.in_([UserRole.TEACHER, UserRole.STUDENT])).delete(synchronize_session=False)
    db.session.commit()
    print('All class, teacher, and student data has been deleted.') 