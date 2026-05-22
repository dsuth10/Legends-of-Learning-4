"""Adventures map system route blueprints (teacher + student)."""

from app.routes.adventures.teacher import adventures_teacher_bp
from app.routes.adventures.student import adventures_student_bp

__all__ = [
    "adventures_teacher_bp",
    "adventures_student_bp",
]
