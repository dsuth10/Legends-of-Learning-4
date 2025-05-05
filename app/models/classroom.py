from app.models.base import Base
from app.models import db
from datetime import datetime

# Association table for student-class relationship
class_students = db.Table(
    'class_students',
    db.Column('class_id', db.Integer, db.ForeignKey('classrooms.id', ondelete='CASCADE'), primary_key=True, nullable=False),
    db.Column('user_id', db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), primary_key=True, nullable=False),
    db.Column('joined_at', db.DateTime, nullable=False, default=datetime.utcnow),
    db.Column('created_at', db.DateTime, nullable=False, default=datetime.utcnow),
    db.Column('updated_at', db.DateTime, nullable=False, default=datetime.utcnow)
)

class Classroom(Base):
    """Classroom model for managing teacher-student relationships."""
    __tablename__ = 'classrooms'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), nullable=False)
    description = db.Column(db.Text, nullable=True)
    join_code = db.Column(db.String(8), nullable=False, unique=True)
    is_active = db.Column(db.Boolean, default=True)
    max_students = db.Column(db.Integer, default=30)
    max_clans = db.Column(db.Integer, default=6)
    min_clan_size = db.Column(db.Integer, default=None)
    max_clan_size = db.Column(db.Integer, default=None)
    teacher_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    students = db.relationship(
        'User',
        secondary=class_students,
        backref=db.backref('classes', lazy='dynamic'),
        lazy='dynamic'
    )
    clans = db.relationship('Clan', backref='classroom', lazy='dynamic', overlaps="classroom")
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    def add_student(self, student):
        """Add a student to the classroom."""
        if not self.is_active:
            raise ValueError("Cannot add student to inactive classroom")
        if self.students.count() >= self.max_students:
            raise ValueError("Classroom is at maximum capacity")
        if not self.students.filter_by(id=student.id).first():
            self.students.append(student)
            self.save()

    def remove_student(self, student):
        """Remove a student from the classroom."""
        if self.students.filter_by(id=student.id).first():
            self.students.remove(student)

    @classmethod
    def get_by_join_code(cls, join_code):
        """Get a classroom by its join code, only if active."""
        return cls.query.filter_by(join_code=join_code, is_active=True).first()

    def get_student_count(self):
        """Get the current number of students in the classroom."""
        return self.students.count()

    @classmethod
    def get_active_by_teacher(cls, teacher_id):
        """Return all active classes for a given teacher."""
        return cls.query.filter_by(teacher_id=teacher_id, is_active=True).all()

    def __repr__(self):
        return f'<Classroom {self.name}>' 