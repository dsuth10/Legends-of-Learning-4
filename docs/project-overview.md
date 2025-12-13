# Legends of Learning - Project Overview

**Generated:** 2025-01-27  
**Project Type:** Monolith Backend (Flask/Python)  
**Architecture:** Layered MVC with Blueprint-based routing

## Executive Summary

Legends of Learning is a gamified learning platform built with Flask. The application provides separate dashboards for teachers and students, enabling educational quest management, character progression, clan collaboration, and an in-game economy.

## Technology Stack

| Category | Technology | Version | Justification |
|----------|-----------|---------|---------------|
| **Language** | Python | 3.8+ | Core application language |
| **Framework** | Flask | >=3.0 | Web framework for API and templating |
| **ORM** | SQLAlchemy | >=2.0 | Database abstraction and migrations |
| **Database** | SQLite (Dev) | - | Development database |
| **Migrations** | Alembic | >=1.12 | Database schema versioning |
| **Authentication** | Flask-Login | >=0.6.2 | Session-based authentication |
| **JWT** | Flask-JWT-Extended | Latest | API token authentication |
| **Forms** | Flask-WTF | >=1.2 | Form handling and CSRF protection |
| **Testing** | Pytest | >=7.4 | Test framework |

## Architecture Pattern

**Layered MVC Architecture:**
- **Models** (`app/models/`): SQLAlchemy ORM models representing database entities
- **Views** (`app/templates/`): Jinja2 HTML templates for server-side rendering
- **Controllers** (`app/routes/`): Flask Blueprints handling HTTP requests and business logic
- **Services** (`app/services/`): Business logic and utility functions

## Repository Structure

**Type:** Monolith - Single cohesive codebase

```
Legends-of-Learning-4/
├── app/                    # Main application package
│   ├── models/            # SQLAlchemy database models
│   ├── routes/            # Flask Blueprint route handlers
│   │   ├── student/       # Student-specific routes
│   │   └── teacher/       # Teacher-specific routes
│   ├── services/          # Business logic services
│   ├── templates/         # Jinja2 HTML templates
│   ├── static/            # Static assets (CSS, JS, images)
│   └── utils/             # Utility functions
├── migrations/            # Alembic database migrations
├── tests/                 # Pytest test suite
├── docs/                  # Project documentation
├── static/                # Global static assets
└── instance/              # Instance-specific files (database)
```

## Key Features

### Teacher Dashboard
- Class and student management
- Quest creation and assignment
- Clan oversight and analytics
- Student progress tracking
- Shop configuration (planned)

### Student Dashboard
- Quest board and completion
- Character progression (XP, levels, stats)
- Equipment shop and inventory
- Clan membership and collaboration
- Battle system
- Ability system

## Entry Points

- **Application Factory:** `app/__init__.py::create_app()`
- **Main Entry:** `run.py`
- **Database Initialization:** `app/models/__init__.py::init_db()`

## Getting Started

See [Development Guide](./development-guide.md) for setup instructions.

## Documentation Index

- [Architecture](./architecture.md) - System architecture and design patterns
- [API Contracts](./api-contracts.md) - REST API endpoints and contracts
- [Data Models](./data-models.md) - Database schema and relationships
- [Source Tree Analysis](./source-tree-analysis.md) - Directory structure details
- [Development Guide](./development-guide.md) - Setup and development workflow

