# Architecture - Legends of Learning

**Generated:** 2025-01-27  
**Architecture Pattern:** Layered MVC with Blueprint-based routing  
**Framework:** Flask 3.0+

## Executive Summary

Legends of Learning follows a traditional layered MVC architecture adapted for Flask. The application is organized into distinct layers: Models (data), Views (templates), and Controllers (routes), with a Services layer for business logic.

## Technology Stack

- **Backend Framework:** Flask 3.0+
- **ORM:** SQLAlchemy 2.0+
- **Database:** SQLite (development), PostgreSQL-ready
- **Authentication:** Flask-Login (sessions) + Flask-JWT-Extended (tokens)
- **Templating:** Jinja2
- **Migrations:** Alembic
- **Testing:** Pytest

## Architecture Pattern

### Layered MVC Structure

```
┌─────────────────────────────────────┐
│         Presentation Layer          │
│  (Templates, Static Assets, JS)    │
└─────────────────────────────────────┘
                  ↓
┌─────────────────────────────────────┐
│         Controller Layer            │
│  (Flask Blueprints, Route Handlers) │
└─────────────────────────────────────┘
                  ↓
┌─────────────────────────────────────┐
│         Service Layer               │
│  (Business Logic, Utilities)        │
└─────────────────────────────────────┘
                  ↓
┌─────────────────────────────────────┐
│         Model Layer                 │
│  (SQLAlchemy ORM Models)            │
└─────────────────────────────────────┘
                  ↓
┌─────────────────────────────────────┐
│         Database Layer              │
│  (SQLite/PostgreSQL)                │
└─────────────────────────────────────┘
```

## Directory Structure

```
app/
├── __init__.py              # Application factory
├── models/                  # Data models (SQLAlchemy)
│   ├── base.py             # Base model class
│   ├── user.py             # User authentication
│   ├── student.py          # Student profiles
│   ├── character.py        # Game characters
│   ├── quest.py            # Quests and rewards
│   ├── equipment.py        # Equipment items
│   ├── clan.py             # Clans/groups
│   └── ...
├── routes/                  # Route handlers (Controllers)
│   ├── __init__.py         # Blueprint registration
│   ├── auth.py             # Authentication routes
│   ├── main.py             # Public routes
│   ├── student_main.py     # Student dashboard routes
│   ├── student/            # Student sub-routes
│   │   ├── abilities.py    # Ability system
│   │   └── battle.py       # Battle system
│   ├── teacher/            # Teacher routes
│   │   ├── classes.py      # Class management
│   │   ├── quests.py       # Quest management
│   │   ├── students_*.py   # Student management modules
│   │   └── ...
│   └── clan.py             # Clan API
├── services/                # Business logic
│   ├── student_service.py  # Student operations
│   ├── clan_metrics.py     # Clan calculations
│   └── ...
├── templates/               # Jinja2 templates
│   ├── base.html           # Base template
│   ├── student/            # Student templates
│   └── teacher/            # Teacher templates
├── static/                  # Static assets
│   ├── css/                # Stylesheets
│   ├── js/                 # JavaScript
│   └── images/             # Images
└── utils/                   # Utility functions
```

## Data Architecture

### Database Design

- **Primary Database:** SQLite (development)
- **ORM:** SQLAlchemy 2.0+ with declarative models
- **Migrations:** Alembic for schema versioning
- **Relationships:** Foreign keys with cascade options

### Key Design Patterns

1. **Application Factory Pattern:** `create_app()` in `app/__init__.py`
2. **Blueprint Pattern:** Route organization by feature/role
3. **Repository Pattern:** Models encapsulate data access
4. **Service Layer:** Business logic separated from routes

## API Design

### Authentication

- **Session-based:** Flask-Login for web UI
- **Token-based:** Flask-JWT-Extended for API endpoints
- **Role-based:** UserRole enum (TEACHER, STUDENT, ADMIN)

### Route Organization

- **Student Routes:** `/student/*` (student dashboard, quests, shop, etc.)
- **Teacher Routes:** `/teacher/*` (class management, quest creation, analytics)
- **API Routes:** `/api/*` or JWT-protected endpoints
- **Public Routes:** `/` (home, login, signup)

### Request Flow

```
HTTP Request
    ↓
Flask App (create_app)
    ↓
Blueprint Router
    ↓
Route Handler (with decorators: @login_required, @teacher_required)
    ↓
Service Layer (business logic)
    ↓
Model Layer (database operations)
    ↓
Response (JSON or HTML template)
```

## Security Architecture

### Authentication & Authorization

- **Password Hashing:** Werkzeug security (bcrypt)
- **Session Management:** Flask-Login with secure cookies
- **JWT Tokens:** Flask-JWT-Extended for API access
- **CSRF Protection:** Flask-WTF forms
- **Role-based Access:** Decorators (`@teacher_required`, `@student_required`)

### Security Features

- Secure session cookies (HTTPOnly, SameSite)
- Password hashing (never store plaintext)
- SQL injection prevention (SQLAlchemy parameterized queries)
- XSS protection (Jinja2 auto-escaping)

## Component Overview

### Models Layer

- **Base Model:** Timestamps, common fields
- **User Model:** Authentication and roles
- **Game Models:** Character, Quest, Equipment, Clan, Ability
- **Progress Models:** QuestLog, ShopPurchase, AuditLog

### Routes Layer

- **Modular Blueprints:** Separate blueprints per feature area
- **Decorator-based Auth:** Reusable authentication decorators
- **Error Handling:** Centralized error responses

### Services Layer

- **Student Service:** Student operations and validations
- **Clan Metrics:** Clan calculations and rankings
- **Analytics Service:** Data aggregation for dashboards

## Development Workflow

1. **Database Changes:** Create Alembic migration
2. **Model Updates:** Update SQLAlchemy models
3. **Route Implementation:** Add Blueprint routes
4. **Template Updates:** Update Jinja2 templates
5. **Testing:** Write Pytest tests

## Deployment Architecture

### Development

- **Server:** Flask development server
- **Database:** SQLite file-based
- **Static Files:** Served by Flask

### Production-Ready

- **WSGI Server:** Gunicorn or uWSGI
- **Database:** PostgreSQL (SQLAlchemy supports)
- **Reverse Proxy:** Nginx for static files
- **Process Manager:** systemd or supervisor

## Testing Strategy

- **Framework:** Pytest
- **Test Structure:** `tests/` directory
- **Coverage:** Models, routes, services
- **Fixtures:** Database fixtures for testing

## Integration Points

### External Dependencies

- **Flask Ecosystem:** Flask-Login, Flask-WTF, Flask-Migrate
- **Database:** SQLAlchemy ORM
- **Authentication:** Werkzeug security, JWT
- **Data Processing:** Pandas, NumPy (for analytics)

### Internal Integration

- **Models ↔ Routes:** Direct model imports in route handlers
- **Routes ↔ Services:** Service layer called from routes
- **Templates ↔ Routes:** Template rendering in route handlers

## Performance Considerations

- **Database Indexing:** Indexes on foreign keys and frequently queried fields
- **Query Optimization:** Eager loading for relationships where needed
- **Session Management:** Efficient session handling
- **Static Assets:** Separate static file serving in production

## Future Architecture Considerations

- **API Versioning:** For future API expansion
- **Caching Layer:** Redis for session/data caching
- **Message Queue:** For async tasks (quest processing, notifications)
- **Microservices:** Potential split of teacher/student services

