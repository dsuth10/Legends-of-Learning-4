# Project Constitution

## Code Style

- Use Python 3.8+ for all backend code
- Follow PEP 8 style guidelines
- Use type hints where appropriate (e.g., `from typing import List, Optional`)
- Keep functions focused and single-purpose
- Prefer functions over classes when possible for utility code
- Keep code simple and readable
- Use meaningful variable and function names
- Use docstrings for classes and complex functions
- Example:
```python
class Character(Base):
    """Character model representing a student's game avatar."""
    
    __tablename__ = 'characters'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), nullable=False)
```

## Testing

- Write tests for all new features and bug fixes
- Use pytest as the testing framework
- Aim for comprehensive test coverage
- Test both success and error cases
- Use fixtures from `tests/conftest.py` for common test setup
- Test models, routes, and services independently

## Architecture

- **Separation of Concerns**: Keep business logic in `/app/services/`, routes in `/app/routes/`, and models in `/app/models/`
- **Database**: Use SQLAlchemy ORM with Alembic for migrations
- **Migrations**: Always use Alembic migrations for schema changes; never use `db.create_all()` in production
- **Authentication**: Use Flask-Login for session management and Flask-JWT-Extended for API authentication
- **Forms**: Use Flask-WTF for form handling and validation
- **Templates**: Use Jinja2 templates organized by role (student/teacher)
- **Static Files**: Place static assets in `/static/` directory
- Avoid circular dependencies
- Keep files under 500 lines of code when possible
- Use blueprints to organize routes by feature/role

### Flask Blueprint Pattern
```python
from flask import Blueprint
from flask_login import current_user
from functools import wraps
from app.models.user import UserRole

teacher_bp = Blueprint('teacher', __name__, url_prefix='/teacher')

def teacher_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != UserRole.TEACHER:
            abort(403)
        return f(*args, **kwargs)
    return decorated_function
```

### Model Patterns
- All models inherit from `Base` (SQLAlchemy declarative base)
- Use `__tablename__` to explicitly name tables
- Include docstrings describing the model's purpose
- Use foreign keys with appropriate `ondelete` cascades
- Define relationships using `db.relationship()` with appropriate `backref` and `lazy` loading
- Use indexes for frequently queried columns

## Database Best Practices

- Always run `alembic upgrade head` after schema changes
- Use foreign keys with appropriate `ondelete` cascades (`CASCADE`, `SET NULL`, `RESTRICT`)
- Use association tables for many-to-many relationships (e.g., `character_abilities`, `inventories`)
- Never hardcode database paths; use environment variables
- Use transactions for multi-step operations
- Validate data at the model level with SQLAlchemy validators
- Use indexes for foreign keys and frequently queried columns
- Example foreign key pattern:
```python
student_id = db.Column(db.Integer, db.ForeignKey('students.id', ondelete='CASCADE'), nullable=False)
clan_id = db.Column(db.Integer, db.ForeignKey('clans.id', ondelete='SET NULL'), nullable=True)
```

### Naming Conventions
- **Character Classes**: Use "Sorcerer" (not "Mage"), "Warrior", "Druid"
- **Equipment Types**: Use enum values: `WEAPON`, `ARMOR`, `ACCESSORY`
- **Equipment Slots**: Use enum values: `MAIN_HAND`, `CHEST`, `RING`, etc.
- **Table Names**: Use plural, lowercase with underscores (e.g., `characters`, `achievement_badge`)

## Security

- Never commit secrets or API keys
- Use environment variables for sensitive configuration
- Validate and sanitize all user input
- Use Flask-WTF CSRF protection for forms
- Implement proper authentication and authorization checks
- Use secure session cookies (HTTPOnly, Secure, SameSite)

## Error Handling

- Use proper HTTP status codes
- Provide meaningful error messages to users
- Log errors appropriately for debugging
- Handle database errors gracefully
- Validate input before processing

## Documentation

- Document complex functions and classes with docstrings
- Keep README.md up to date
- Document API endpoints and their expected inputs/outputs
- Update migration notes when making schema changes

## Project Structure

- Models: `/app/models/`
- Routes: `/app/routes/` (organized by role: student/teacher)
- Services: `/app/services/` (business logic)
- Templates: `/app/templates/` (organized by role)
- Static Files: `/static/`
- Tests: `/tests/`
- Migrations: `/migrations/versions/`
- Scripts: `/scripts/` (utility and one-off scripts)

## Git Workflow

- Use meaningful commit messages
- Create branches for features
- Test before committing
- Keep commits focused and atomic

## API Patterns

- Use Pydantic `BaseModel` for request/response validation
- Return JSON responses with consistent structure: `{"success": True, "data": {...}}`
- Use appropriate HTTP status codes (200, 201, 400, 403, 404, 500)
- Example:
```python
from pydantic import BaseModel, Field

class CharacterBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=64)
    character_class: str
    is_active: bool = Field(default=True)
```

## Service Layer Patterns

- Business logic should be in `/app/services/` modules
- Services handle complex operations that involve multiple models
- Services return data structures, not Flask response objects
- Routes call services and format responses
- Example service pattern:
```python
# app/services/clan_metrics.py
def calculate_clan_metrics(clan_id):
    # Complex calculation logic
    return metrics_dict
```



