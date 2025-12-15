# Development Guide - Legends of Learning

**Generated:** 2025-01-27

## Prerequisites

- **Python:** 3.8 or higher
- **pip:** Python package manager
- **Git:** Version control (optional)

## Installation

### 1. Clone/Navigate to Project

```bash
cd Legends-of-Learning-4
```

### 2. Create Virtual Environment (Recommended)

```bash
# Windows (Git Bash/PowerShell)
python -m venv venv
source venv/Scripts/activate

# Windows (Command Prompt)
python -m venv venv
venv\Scripts\activate

# macOS/Linux
python -m venv venv
source venv/bin/activate
```

**Note:** You should see `(venv)` at the beginning of your command prompt when activated.

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

**Key Dependencies:**
- Flask >=3.0
- SQLAlchemy >=2.0
- Flask-Login >=0.6.2
- Flask-Migrate >=4.0
- Alembic >=1.12
- Flask-WTF >=1.2
- Flask-JWT-Extended
- pytest >=7.4 (for testing)

### 4. Environment Configuration

Create a `.env` file in the project root:

```env
SECRET_KEY=your-secret-key-here
TEACHER_ACCESS_CODE=your-secure-teacher-code
# Optional: Override database URI
# SQLALCHEMY_DATABASE_URI=sqlite:///instance/legends.db
```

### 5. Database Setup

```bash
# Apply database migrations (REQUIRED)
alembic upgrade head

# Seed initial data (optional, only needed once)
flask seed-db
```

**Important:** Always run `alembic upgrade head` after:
- Setting up the project for the first time
- Pulling new code with database changes
- Resetting or modifying the database schema

## Running the Application

### Development Server

```bash
python run.py
```

The server will start on `http://127.0.0.1:5000` or `http://localhost:5000`

### Access the Application

- **Home:** http://localhost:5000/
- **Login:** http://localhost:5000/login
- **Signup:** http://localhost:5000/signup

## Development Workflow

### Making Database Changes

1. **Modify Models:** Update SQLAlchemy models in `app/models/`
2. **Create Migration:**
   ```bash
   alembic revision --autogenerate -m "Description of changes"
   ```
3. **Review Migration:** Check generated migration file in `migrations/versions/`
4. **Apply Migration:**
   ```bash
   alembic upgrade head
   ```

### Adding New Routes

1. **Create Route Handler:** Add to appropriate Blueprint in `app/routes/`
2. **Register Blueprint:** Ensure Blueprint is registered in `app/routes/__init__.py`
3. **Add Template:** Create corresponding Jinja2 template in `app/templates/`
4. **Test:** Write tests in `tests/`

### Adding New Models

1. **Create Model:** Add SQLAlchemy model in `app/models/`
2. **Import in init_db:** Add import in `app/models/__init__.py::init_db()`
3. **Create Migration:** Generate Alembic migration
4. **Apply Migration:** Run `alembic upgrade head`

## Testing

### Run All Tests

```bash
pytest
```

### Run Specific Test File

```bash
pytest tests/test_models.py
```

### Run with Coverage

```bash
pytest --cov=app tests/
```

### Test Structure

- **Fixtures:** `tests/conftest.py` (database setup, test client)
- **Model Tests:** `tests/test_models.py`
- **Route Tests:** `tests/test_*.py` (auth, shop, clan, etc.)

## Common Development Tasks

### Create a New Student

```bash
python scripts/add_dummy_class.py  # Or use the web UI
```

### Reset Database

```bash
# Delete instance/legends.db
# Then run:
alembic upgrade head
flask seed-db
```

### View Database

Use SQLite browser or command line:
```bash
sqlite3 instance/legends.db
```

### Add Equipment Data

Equipment data is hardcoded in `app/models/equipment_data.py`. Modify `EQUIPMENT_DATA` dictionary.

## Code Organization

### Models (`app/models/`)
- One file per model or related models
- Inherit from `Base` (provides timestamps)
- Define relationships with `db.relationship()`

### Routes (`app/routes/`)
- Organized by Blueprint
- Use decorators: `@login_required`, `@teacher_required`, `@student_required`
- Return JSON for API endpoints, render templates for pages

### Services (`app/services/`)
- Business logic separated from routes
- Reusable across different routes
- Handle complex operations

### Templates (`app/templates/`)
- Jinja2 templates
- Extend `base.html` for consistent layout
- Use template inheritance

## Debugging

### Enable Debug Mode

Debug mode is enabled by default in `run.py`:
```python
app.run(debug=True, ...)
```

### View Logs

- **Development:** Console output
- **Production:** `logs/legends_of_learning.log` (if configured)

### Common Issues

**ModuleNotFoundError:**
- Solution: Run `pip install -r requirements.txt`

**Database errors:**
- Solution: Run `alembic upgrade head`

**Port 5000 already in use:**
- Solution: Change port in `run.py` or stop other process

## Building for Production

### 1. Update Configuration

- Set `SECRET_KEY` to secure value
- Set `SESSION_COOKIE_SECURE = True` (requires HTTPS)
- Configure production database (PostgreSQL)

### 2. Use Production WSGI Server

```bash
# Install Gunicorn
pip install gunicorn

# Run with Gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 "app:create_app()"
```

### 3. Set Up Reverse Proxy

Use Nginx or similar to:
- Serve static files
- Handle HTTPS
- Proxy requests to WSGI server

## Additional Resources

- **Flask Documentation:** https://flask.palletsprojects.com/
- **SQLAlchemy Documentation:** https://docs.sqlalchemy.org/
- **Alembic Documentation:** https://alembic.sqlalchemy.org/
- **Project README:** See `README.md` for more details





