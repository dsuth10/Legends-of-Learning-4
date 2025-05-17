from app import create_app
from app.models import db
from app.models.user import User
from app.models.student import Student
from app.models.character import Character

app = create_app()

with app.app_context():
    # Find all users whose username starts with 'student' or contains 'test'
    users = User.query.filter(
        (User.username.ilike('student%')) | (User.username.ilike('%test%'))
    ).all()
    print(f"Found {len(users)} users with username starting with 'student' or containing 'test'.")
    for user in users:
        print(f"Deleting User: {user.id} - {user.username}")
        # Print and delete all students for this user
        students = Student.query.filter_by(user_id=user.id).all()
        for student in students:
            print(f"  Deleting Student: {student.id}")
            # Print and delete all characters for this student
            characters = Character.query.filter_by(student_id=student.id).all()
            for character in characters:
                print(f"    Deleting Character: {character.id} - {character.name}")
                db.session.delete(character)
            db.session.delete(student)
        db.session.delete(user)
        db.session.commit()

    # Clean up orphaned students and characters
    orphaned_students = Student.query.filter(~Student.user_id.in_([u.id for u in User.query.all()])).all()
    for student in orphaned_students:
        print(f"Deleting orphaned Student: {student.id}")
        db.session.delete(student)
    db.session.commit()

    orphaned_characters = Character.query.filter(~Character.student_id.in_([s.id for s in Student.query.all()])).all()
    for character in orphaned_characters:
        print(f"Deleting orphaned Character: {character.id} - {character.name}")
        db.session.delete(character)
    db.session.commit()

print("Cleanup of test/student users complete.") 