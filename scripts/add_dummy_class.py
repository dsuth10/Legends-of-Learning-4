from app import create_app
from app.models import db
from app.models.classroom import Classroom
from app.models.user import User
import random
import string

app = create_app()
with app.app_context():
    # Find the teacher user by username
    teacher = User.query.filter_by(username='jd').first()
    if not teacher:
        print("No teacher user with username 'jd' found. Please create this user first.")
        exit(1)
    # Generate a unique join code
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