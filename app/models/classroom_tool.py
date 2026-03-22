"""Per-classroom configuration for teacher classroom tools (e.g. volume meter)."""

from sqlalchemy import UniqueConstraint

from app.models import db
from app.models.base import Base


class ClassroomToolConfig(Base):
    """Stores saved settings for a tool type within a classroom."""

    __tablename__ = 'classroom_tool_configs'
    __table_args__ = (
        UniqueConstraint('classroom_id', 'tool_type', name='uq_classroom_tool_type'),
    )

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    classroom_id = db.Column(
        db.Integer, db.ForeignKey('classrooms.id', ondelete='CASCADE'), nullable=False, index=True
    )
    tool_type = db.Column(db.String(32), nullable=False)
    config_data = db.Column(db.JSON, nullable=False, default=dict)
    is_active = db.Column(db.Boolean, nullable=False, default=False)

    classroom = db.relationship('Classroom', backref=db.backref('tool_configs', lazy='dynamic'))

    def __repr__(self):
        return f'<ClassroomToolConfig class={self.classroom_id} tool={self.tool_type!r}>'
