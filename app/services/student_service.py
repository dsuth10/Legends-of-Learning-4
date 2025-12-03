from app.models import db
from app.models.user import User, UserRole
from app.models.student import Student
from sqlalchemy.exc import IntegrityError

class StudentService:
    @staticmethod
    def create_student(username, email, password, classroom, first_name='', last_name=''):
        """
        Create a new student user and assign them to a classroom.
        
        Args:
            username (str): The student's username.
            email (str): The student's email.
            password (str): The student's password.
            classroom (Classroom): The classroom to assign the student to.
            first_name (str, optional): The student's first name.
            last_name (str, optional): The student's last name.
            
        Returns:
            User: The created user object.
            
        Raises:
            ValueError: If the username or email already exists.
        """
        # Check for existing user
        existing_user = User.query.filter((User.username == username) | (User.email == email)).first()
        if existing_user:
            raise ValueError("Username or email already exists.")
            
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
            
            return new_user
        except IntegrityError:
            db.session.rollback()
            raise ValueError("Username or email already exists.")
        except Exception as e:
            db.session.rollback()
            raise e
