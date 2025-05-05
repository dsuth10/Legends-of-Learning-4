from datetime import datetime
from app.models.db_config import db

class Base(db.Model):
    """Base model class that includes common functionality."""
    
    __abstract__ = True
    
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    def save(self):
        db.session.add(self)
        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            raise e
    
    def delete(self):
        db.session.delete(self)
        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            raise e
    
    @classmethod
    def get_by_id(cls, id):
        return db.session.get(cls, id)
    
    def update(self, **kwargs):
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
        self.save() 