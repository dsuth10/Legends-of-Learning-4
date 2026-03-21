"""
One-time data repair: sync the class_students association table with Student.class_id.

Run from project root, e.g.:
    python scripts/backfill_class_students.py

Students assigned only via Student.class_id (e.g. CSV reassign or unassigned flow
before the fix) may be missing a row in class_students; this script adds them.
"""
from app import create_app
from app.models.student import Student


def main():
    app = create_app()
    with app.app_context():
        inserted = 0
        skipped = 0
        errors = []
        for student in Student.query.filter(Student.class_id.isnot(None)).all():
            user = student.user
            classroom = student.classroom
            if not user or not classroom:
                continue
            if classroom.students.filter_by(id=user.id).first():
                skipped += 1
                continue
            try:
                classroom.add_student(user)
                inserted += 1
            except Exception as e:
                errors.append((student.id, str(e)))
        print(f"backfill_class_students: inserted={inserted}, already_linked={skipped}, errors={len(errors)}")
        for sid, msg in errors:
            print(f"  student_id={sid}: {msg}")


if __name__ == "__main__":
    main()
