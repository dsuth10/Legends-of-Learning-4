from werkzeug.security import generate_password_hash, check_password_hash
from app.models.base import Base
from app.models import db
from enum import Enum

class UserRole(Enum):
    TEACHER = 'teacher'
    STUDENT = 'student'
    ADMIN = 'admin'

class User(Base):
    """User model for authentication and role management."""
    
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.Enum(UserRole), nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    
    # Profile fields
    first_name = db.Column(db.String(64))
    last_name = db.Column(db.String(64))
    display_name = db.Column(db.String(64))  # For in-game display
    
    # Relationships will be added by other models (class membership, characters, etc.)
    
    __table_args__ = (
        db.Index('idx_user_role_active', 'role', 'is_active'),  # For filtering active users by role
    )
    
    def __init__(self, username, email, role, password=None, **kwargs):
        super().__init__(**kwargs)
        self.username = username
        self.email = email
        self.role = role
        if password:
            self.set_password(password)
    
    def set_password(self, password):
        """Set the user's password hash."""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Check if the provided password matches the hash."""
        return check_password_hash(self.password_hash, password)
    
    @property
    def full_name(self):
        """Get the user's full name."""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.username
    
    def get_display_name(self):
        """Get the user's display name for the game."""
        return self.display_name or self.username
    
    @classmethod
    def get_by_username(cls, username):
        """Get a user by their username."""
        return cls.query.filter_by(username=username).first()
    
    @classmethod
    def get_by_email(cls, email):
        """Get a user by their email."""
        return cls.query.filter_by(email=email).first()
    
    @classmethod
    def get_active_by_role(cls, role):
        """Get all active users with a specific role."""
        return cls.query.filter_by(role=role, is_active=True).all()
    
    def __repr__(self):
        return f'<User {self.username}>' 