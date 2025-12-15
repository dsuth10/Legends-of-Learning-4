# Source Tree Analysis - Legends of Learning

**Generated:** 2025-01-27

## Complete Directory Structure

```
Legends-of-Learning-4/
├── app/                              # Main application package
│   ├── __init__.py                   # Application factory (create_app)
│   ├── commands.py                   # Flask CLI commands
│   │
│   ├── models/                       # SQLAlchemy ORM models
│   │   ├── __init__.py               # Model initialization (init_db)
│   │   ├── base.py                   # Base model class with timestamps
│   │   ├── user.py                   # User authentication model
│   │   ├── student.py                 # Student profile model
│   │   ├── teacher.py                 # Teacher model
│   │   ├── character.py              # Character/game avatar model
│   │   ├── classroom.py              # Classroom model
│   │   ├── quest.py                  # Quest and QuestLog models
│   │   ├── equipment.py              # Equipment and Inventory models
│   │   ├── ability.py                # Ability and CharacterAbility models
│   │   ├── clan.py                   # Clan model
│   │   ├── achievement_badge.py      # Achievement badge model
│   │   ├── shop.py                   # ShopPurchase model
│   │   ├── shop_config.py            # ShopItemOverride model
│   │   ├── audit.py                  # AuditLog model
│   │   ├── assist_log.py             # AssistLog model
│   │   ├── clan_progress.py          # ClanProgressHistory model
│   │   ├── battle.py                  # Battle and Monster models
│   │   ├── education.py              # QuestionSet and Question models
│   │   ├── equipment_data.py         # Hardcoded equipment data
│   │   ├── db_config.py              # Database configuration
│   │   └── db_maintenance.py         # Database maintenance utilities
│   │
│   ├── routes/                        # Flask Blueprint route handlers
│   │   ├── __init__.py               # Blueprint registration
│   │   ├── main.py                   # Public routes (home, test)
│   │   ├── auth.py                   # Authentication (login, logout, signup)
│   │   ├── student_main.py           # Student dashboard routes
│   │   ├── clan.py                   # Clan API (JWT-protected)
│   │   │
│   │   ├── student/                   # Student sub-routes
│   │   │   ├── __init__.py
│   │   │   ├── abilities.py           # Ability usage routes
│   │   │   └── battle.py             # Battle system routes
│   │   │
│   │   └── teacher/                   # Teacher routes
│   │       ├── __init__.py           # Teacher blueprint setup
│   │       ├── blueprint.py          # Teacher decorators (@teacher_required)
│   │       ├── classes.py            # Class management
│   │       ├── quests.py             # Quest creation and management
│   │       ├── profile.py           # Teacher profile
│   │       ├── clan.py               # Clan management
│   │       ├── misc.py               # Analytics, backup, shop config
│   │       ├── education.py         # Question sets management
│   │       ├── students_list.py     # Student listing
│   │       ├── students_crud.py      # Student CRUD operations
│   │       ├── students_import.py    # CSV student import
│   │       ├── students_unassigned.py # Unassigned students
│   │       ├── students_characters.py # Character management
│   │       └── students_api.py      # Student API endpoints
│   │
│   ├── services/                      # Business logic services
│   │   ├── __init__.py
│   │   ├── student_service.py        # Student operations
│   │   ├── student_import_service.py # CSV import logic
│   │   ├── clan_metrics.py          # Clan calculations
│   │   ├── analytics_service.py     # Analytics aggregation
│   │   ├── quest_map_utils.py       # Quest map utilities
│   │   ├── backup_service.py        # Database backup
│   │   └── scheduled_tasks.py       # Scheduled background tasks
│   │
│   ├── templates/                     # Jinja2 HTML templates
│   │   ├── base.html                 # Base template
│   │   ├── home.html                 # Home page
│   │   ├── login.html                # Login page
│   │   ├── signup.html               # Signup page
│   │   ├── index.html                # Index page
│   │   │
│   │   ├── student/                  # Student templates
│   │   │   ├── dashboard.html
│   │   │   ├── quests.html
│   │   │   ├── character.html
│   │   │   ├── shop.html
│   │   │   ├── clan.html
│   │   │   ├── progress.html
│   │   │   └── ...
│   │   │
│   │   └── teacher/                   # Teacher templates
│   │       ├── dashboard.html
│   │       ├── classes.html
│   │       ├── students.html
│   │       ├── quests.html
│   │       ├── clans.html
│   │       ├── analytics.html
│   │       └── ...
│   │
│   ├── static/                        # App-specific static files
│   │   └── csv/                      # CSV templates
│   │       └── student_import_template.csv
│   │
│   └── utils/                         # Utility functions
│       ├── __init__.py
│       ├── backup_utils.py           # Backup utilities
│       ├── date_utils.py             # Date/time utilities
│       └── error_handling.py         # Error handling utilities
│
├── static/                            # Global static assets
│   ├── css/
│   │   └── style.css                 # Main stylesheet
│   ├── js/                           # JavaScript files
│   │   ├── main.js
│   │   ├── abilities.js
│   │   ├── clans.js
│   │   └── teacher_quest_progress.js
│   ├── images/                       # Game images
│   │   ├── badges/                   # Achievement badges
│   │   ├── clan_icons/               # Clan icons
│   │   ├── equipment/                 # Equipment images
│   │   │   ├── druid/
│   │   │   ├── sorcerer/
│   │   │   └── warrior/
│   │   └── quest_maps/                # Quest map images
│   └── avatars/                      # Character/teacher avatars
│
├── migrations/                        # Alembic database migrations
│   ├── versions/                     # Migration files
│   │   ├── 2f80bb7d33f7_add_shop_item_overrides_table.py
│   │   ├── 61cdd5cdfb65_add_audit_log_table.py
│   │   ├── b0e9124e43e3_add_quest_columns.py
│   │   └── c8d9e2f4a5b6_add_shop_purchases_table.py
│   ├── env.py                        # Alembic environment
│   └── script.py.mako                # Migration template
│
├── tests/                            # Pytest test suite
│   ├── conftest.py                   # Test fixtures
│   ├── test_models.py                # Model tests
│   ├── test_auth.py                  # Authentication tests
│   ├── test_character_management.py  # Character tests
│   ├── test_clan_api.py              # Clan API tests
│   ├── test_shop_api.py              # Shop API tests
│   └── ...
│
├── docs/                             # Project documentation
│   ├── equipment_data_system.md
│   └── sprint-artifacts/             # BMAD sprint artifacts
│
├── scripts/                          # Utility scripts
│   ├── add_dummy_class.py
│   ├── seed_badges.py
│   └── ...
│
├── instance/                         # Instance-specific files
│   └── legends.db                    # SQLite database (development)
│
├── run.py                            # Application entry point
├── requirements.txt                  # Python dependencies
├── requirements-dev.txt              # Development dependencies
├── alembic.ini                       # Alembic configuration
├── pytest.ini                        # Pytest configuration
└── README.md                         # Project README
```

## Critical Directories

### `app/models/`
**Purpose:** Data layer - SQLAlchemy ORM models
**Key Files:**
- `base.py` - Base model with timestamps
- `user.py` - Authentication model
- `character.py` - Game character model
- `quest.py` - Quest system models

### `app/routes/`
**Purpose:** Controller layer - HTTP request handlers
**Key Files:**
- `auth.py` - Authentication routes
- `student_main.py` - Student dashboard
- `teacher/` - Teacher management routes

### `app/services/`
**Purpose:** Business logic layer
**Key Files:**
- `student_service.py` - Student operations
- `clan_metrics.py` - Clan calculations

### `app/templates/`
**Purpose:** View layer - HTML templates
**Structure:** Mirrors route structure (student/, teacher/)

### `migrations/`
**Purpose:** Database schema versioning
**Usage:** Run `alembic upgrade head` to apply migrations

## Entry Points

1. **Application Entry:** `run.py` → `app.create_app()`
2. **Database Init:** `app/models/__init__.py::init_db()`
3. **Route Registration:** `app/routes/__init__.py::init_app()`

## Integration Points

- **Models ↔ Routes:** Direct imports in route handlers
- **Routes ↔ Services:** Service layer called from routes
- **Templates ↔ Routes:** Template rendering in route handlers
- **Static Assets:** Served from `static/` directory

## Key Patterns

- **Blueprint Pattern:** Routes organized by feature/role
- **Application Factory:** `create_app()` pattern
- **Service Layer:** Business logic separated from routes
- **Model Relationships:** Foreign keys with cascade options





