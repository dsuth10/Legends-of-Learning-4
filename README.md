# Legends of Learning 3.1

A Flask-based learning management system with robust database handling and migration support.

## Project Structure

```
legends-of-learning/
├── app/
│   ├── __init__.py          # Application factory and initialization
│   └── models/
│       ├── __init__.py
│       ├── db_config.py     # Database configuration settings
│       ├── db_init.py       # Database initialization module
│       └── migration_manager.py  # Migration management utilities
├── migrations/
│   ├── env.py              # Alembic environment configuration
│   ├── README             
│   ├── script.py.mako      # Migration script template
│   └── versions/           # Migration version files
├── tests/
│   └── test_migration_manager.py  # Migration manager test suite
├── instance/               # Instance-specific files (SQLite database)
├── alembic.ini            # Alembic configuration
├── requirements.txt       # Production dependencies
├── requirements-dev.txt   # Development dependencies
└── setup.py              # Package setup configuration
```

## Features

### Database Configuration
- SQLite database with Write-Ahead Logging (WAL) mode
- Optimized connection pooling and retry settings
- Foreign key enforcement
- Custom PRAGMA configurations for performance

### Migration Management
The project includes a robust migration management system built on Alembic, providing:

- Automated migration generation based on model changes
- Manual migration creation support
- Migration status tracking and verification
- Up/downgrade capabilities
- Migration history inspection

## Setup and Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd legends-of-learning
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt  # For development
```

4. Install the package in development mode:
```bash
pip install -e .
```

## Database Setup

The database is automatically initialized with the correct configuration when the application starts. Key features include:

- WAL journal mode for improved concurrency
- Foreign key constraints enabled
- Connection pooling configured
- Automatic retry on database locks

## Working with Migrations

### Creating a New Migration

```python
from app.models.migration_manager import MigrationManager

manager = MigrationManager()

# Create an auto-generated migration
revision = manager.create_migration("Add user table")

# Create a manual migration
revision = manager.create_migration("Custom migration", autogenerate=False)
```

### Applying Migrations

```python
# Upgrade to latest version
manager.upgrade()

# Upgrade to specific revision
manager.upgrade("abc123")

# Downgrade to previous version
manager.downgrade("previous_revision_id")
```

### Checking Migration Status

```python
# Get current revision
current = manager.get_current_revision()

# Check migration history
history = manager.check_history()

# Verify if any migrations are pending
is_current = manager.verify_pending_migrations()
```

## Development

### Running Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_migration_manager.py

# Run with coverage
pytest --cov=app tests/
```

### Development Dependencies

The project uses several development tools:
- pytest: Testing framework
- pytest-cov: Coverage reporting
- black: Code formatting
- flake8: Code linting
- mypy: Type checking

## Dependencies

### Production Dependencies
- Flask >= 3.0
- SQLAlchemy >= 2.0
- Flask-Login >= 0.6.2
- Alembic >= 1.12
- Flask-WTF >= 1.2
- Flask-Migrate >= 4.0
- Flask-CORS >= 4.0
- pandas >= 2.1
- numpy >= 1.24

### Development Dependencies
- pytest >= 7.4.0
- pytest-cov >= 4.1.0
- black >= 23.7.0
- flake8 >= 6.1.0
- mypy >= 1.5.1
- pre-commit >= 3.0

## Contributing

1. Create a new branch for your feature
2. Write tests for new functionality
3. Ensure all tests pass
4. Create a pull request

## License

[License information to be added]

## Contact

[Contact information to be added] 