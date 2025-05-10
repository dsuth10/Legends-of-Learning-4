from app import db
from app.models.character import Character
from app.models.student import Student

updated = 0
missing = 0

for character in Character.query.all():
    # The old character.student_id is actually a user_id
    student = Student.query.filter_by(user_id=character.student_id).first()
    if student:
        character.student_id = student.id
        updated += 1
    else:
        print(f"No student found for character {character.id} (user_id={character.student_id})")
        missing += 1

db.session.commit()
print(f"Updated {updated} characters. {missing} had no matching student.") 