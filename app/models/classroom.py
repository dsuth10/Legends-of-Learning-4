from app.models.base import Base
from app.models import db
from datetime import datetime

# Association table for student-class relationship
class_students = db.Table(
    'class_students',
    db.Column('class_id', db.Integer, db.ForeignKey('classes.id', ondelete='CASCADE'), primary_key=True),
    db.Column('user_id', db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), primary_key=True),
    db.Column('joined_at', db.DateTime, nullable=False, default=datetime.utcnow)
)

class Class(Base):
    """Class model for managing teacher-student relationships."""
    
    __tablename__ = 'classes'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), nullable=False)
    description = db.Column(db.Text)
    join_code = db.Column(db.String(8), unique=True, nullable=False, index=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    
    # Class settings
    max_students = db.Column(db.Integer, default=30)
    max_clans = db.Column(db.Integer, default=6)
    min_clan_size = db.Column(db.Integer, default=3)
    max_clan_size = db.Column(db.Integer, default=6)
    
    # Relationships
    teacher_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    teacher = db.relationship('User', backref=db.backref('teaching_classes', lazy='dynamic'))
    
    students = db.relationship(
        'User',
        secondary=class_students,
        lazy='dynamic',
        backref=db.backref('enrolled_classes', lazy='dynamic')
    )
    
    __table_args__ = (
        db.Index('idx_class_teacher_active', 'teacher_id', 'is_active'),  # For teacher's active classes
    )
    
    def __init__(self, name, teacher_id, join_code, **kwargs):
        super().__init__(**kwargs)
        self.name = name
        self.teacher_id = teacher_id
        self.join_code = join_code
    
    def add_student(self, student):
        """Add a student to the class."""
        if not self.is_active:
            raise ValueError("Cannot add student to inactive class")
        if self.students.count() >= self.max_students:
            raise ValueError("Class is at maximum capacity")
        if not self.students.filter_by(id=student.id).first():
            self.students.append(student)
            self.save()
    
    def remove_student(self, student):
        """Remove a student from the class."""
        if self.students.filter_by(id=student.id).first():
            self.students.remove(student)
            self.save()
    
    @classmethod
    def get_by_join_code(cls, join_code):
        """Get a class by its join code."""
        return cls.query.filter_by(join_code=join_code, is_active=True).first()
    
    @classmethod
    def get_active_by_teacher(cls, teacher_id):
        """Get all active classes for a teacher."""
        return cls.query.filter_by(teacher_id=teacher_id, is_active=True).all()
    
    def get_student_count(self):
        """Get the current number of students in the class."""
        return self.students.count()
    
    def __repr__(self):
        return f'<Class {self.name}>' 