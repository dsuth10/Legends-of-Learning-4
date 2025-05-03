from app import create_app
from app.models import db
from app.models.user import User, UserRole
from app.models.classroom import Classroom
import random
import string

app = create_app()
with app.app_context():
    # Create teacher user
    teacher = User.query.filter_by(username='jd').first()
    if not teacher:
        teacher = User(
            username='jd',
            email='jd@example.com',
            role=UserRole.TEACHER,
            is_active=True
        )
        teacher.set_password('123')
        db.session.add(teacher)
        db.session.commit()
        print(f"Teacher user 'jd' created with id={teacher.id}")
    else:
        print(f"Teacher user 'jd' already exists with id={teacher.id}")

    # Create dummy class
    join_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
    dummy_class = Classroom(
        name="Test Class",
        description="This is a dummy class for testing.",
        join_code=join_code,
        teacher_id=teacher.id
    )
    db.session.add(dummy_class)
    db.session.commit()
    print(f"Dummy class created with id={dummy_class.id}, join_code={join_code}, teacher_id={teacher.id}") 