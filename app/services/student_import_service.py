import csv
import io
from app.models import db
from app.models.user import User, UserRole
from app.models.student import Student
from sqlalchemy.exc import IntegrityError

class StudentImportService:
    REQUIRED_FIELDS = {'username', 'email', 'password'}

    @staticmethod
    def parse_csv(file_content):
        """Parse CSV content and return rows as a list of dictionaries."""
        try:
            stream = io.StringIO(file_content)
            reader = csv.DictReader(stream)
            return list(reader), reader.fieldnames
        except Exception as e:
            raise ValueError(f"Error parsing CSV: {e}")

    @staticmethod
    def validate_row(row, mapping=None):
        """Validate a single row of student data."""
        if mapping:
            username = row.get(mapping['username'], '').strip()
            email = row.get(mapping['email'], '').strip()
            password = row.get(mapping['password'], '').strip()
        else:
            username = row.get('username', '').strip()
            email = row.get('email', '').strip()
            password = row.get('password', '').strip()

        first_name = row.get('first_name', '').strip()
        last_name = row.get('last_name', '').strip()

        if not username or not email or not password:
            return None, "Missing required fields."

        existing_user = User.query.filter((User.username == username) | (User.email == email), User.role == UserRole.STUDENT).first()
        reassignable = False
        error = None
        user_id = None

        if existing_user:
            student_profile = Student.query.filter_by(user_id=existing_user.id).first()
            if student_profile and student_profile.class_id is None and student_profile.status == 'unassigned':
                reassignable = True
                user_id = existing_user.id
            else:
                error = "Username or email already exists."

        return {
            'username': username,
            'email': email,
            'password': password,
            'first_name': first_name,
            'last_name': last_name,
            'reassignable': reassignable,
            'user_id': user_id
        }, error

    @staticmethod
    def process_import(preview_data, classroom):
        """Process the import of validated student data."""
        created = 0
        reassigned = 0
        failed = 0
        errors = []

        for i, row in enumerate(preview_data, start=2):
            if row.get('error'):
                failed += 1
                errors.append(f'Row {i}: {row["error"]}')
                continue

            if row.get('reassignable') and row.get('user_id'):
                # Reassign unassigned student
                user_id = row['user_id']
                student_profile = Student.query.filter_by(user_id=user_id, class_id=None, status='unassigned').first()
                user = User.query.filter_by(id=user_id, role=UserRole.STUDENT).first()
                
                if student_profile and user:
                    student_profile.class_id = classroom.id
                    student_profile.status = 'active'
                    if row.get('first_name'):
                        user.first_name = row['first_name']
                    if row.get('last_name'):
                        user.last_name = row['last_name']
                    db.session.commit()
                    reassigned += 1
                else:
                    failed += 1
                    errors.append(f'Row {i}: Could not reassign student.')
                continue

            # Normal creation
            username = row['username']
            email = row['email']
            password = row['password']
            first_name = row.get('first_name', '')
            last_name = row.get('last_name', '')

            existing_user = User.query.filter((User.username == username) | (User.email == email), User.role == UserRole.STUDENT).first()
            if existing_user:
                failed += 1
                errors.append(f'Row {i}: Username or email already exists.')
                continue

            try:
                new_user = User(
                    username=username,
                    email=email,
                    role=UserRole.STUDENT,
                    first_name=first_name,
                    last_name=last_name
                )
                new_user.set_password(password)
                db.session.add(new_user)
                db.session.commit()

                classroom.add_student(new_user)
                student_profile = Student(user_id=new_user.id, class_id=classroom.id)
                db.session.add(student_profile)
                db.session.commit()
                created += 1
            except IntegrityError:
                db.session.rollback()
                failed += 1
                errors.append(f'Row {i}: Username or email already exists (detected at DB level).')

        return {
            'created': created,
            'reassigned': reassigned,
            'failed': failed,
            'errors': errors
        }
