import sys
import os
import tempfile
import pytest
from alembic.config import Config
from alembic import command
import sqlite3
from sqlalchemy import text

# Do NOT import app/db until after Alembic runs!

def drop_all_tables(db_path):
    print(f"[DEBUG] Dropping all tables in {db_path} before Alembic migration...")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    for (table_name,) in tables:
        if table_name != 'sqlite_sequence':
            cursor.execute(f'DROP TABLE IF EXISTS {table_name};')
            print(f"[DEBUG] Dropped table: {table_name}")
    conn.commit()
    conn.close()

def run_alembic_upgrade(database_uri):
    alembic_cfg_path = os.path.join(os.path.dirname(__file__), '..', 'migrations', 'alembic.ini')
    print(f"[DEBUG] Alembic config: {alembic_cfg_path}")
    alembic_cfg = Config(alembic_cfg_path)
    alembic_cfg.set_main_option('sqlalchemy.url', database_uri)
    script_location = alembic_cfg.get_main_option('script_location')
    print(f"[DEBUG] Alembic script_location: {script_location}")
    print(f"[DEBUG] Alembic DB URI: {database_uri}")
    import glob
    migration_files = glob.glob(os.path.join(os.path.dirname(__file__), '..', 'migrations', 'versions', '*.py'))
    print(f"[DEBUG] Migration files: {migration_files}")
    if migration_files:
        with open(migration_files[-1], 'r') as f:
            print(f"[DEBUG] Last migration file contents:\n{f.read(1000)}")
    # Drop all tables before running Alembic
    if database_uri.startswith('sqlite:///'):
        db_path = database_uri.replace('sqlite:///', '')
        drop_all_tables(db_path)
    try:
        from alembic.script import ScriptDirectory
        script = ScriptDirectory.from_config(alembic_cfg)
        print(f"[DEBUG] Alembic heads before upgrade: {script.get_heads()}")
        command.upgrade(alembic_cfg, 'head')
        print(f"[DEBUG] Alembic heads after upgrade: {script.get_heads()}")
    except Exception as e:
        print(f"[DEBUG] Alembic upgrade exception: {e}")
        raise

def check_equipment_cost_column(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(equipment);")
    columns = cursor.fetchall()
    print(f"[DEBUG] equipment table columns: {columns}")
    has_cost = any(col[1] == 'cost' for col in columns)
    if not has_cost:
        raise RuntimeError("[SCHEMA ERROR] 'cost' column missing from equipment table after Alembic migration!")
    conn.close()

@pytest.fixture(scope='function')
def test_db_file():
    db_fd, db_path = tempfile.mkstemp(suffix='.db')
    os.close(db_fd)
    db_uri = f'sqlite:///{db_path}'
    print(f"[DEBUG] Creating new test DB at {db_path}")
    run_alembic_upgrade(db_uri)
    # Print tables after Alembic
    conn = sqlite3.connect(db_path)
    tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table';").fetchall()
    print(f"[DEBUG] Tables after Alembic: {tables}")
    if not tables:
        raise RuntimeError("Alembic migration did not create any tables! Check env.py and model imports.")
    # Print alembic_version table contents if it exists
    if any(t[0] == 'alembic_version' for t in tables):
        version = conn.execute("SELECT version_num FROM alembic_version;").fetchall()
        print(f"[DEBUG] alembic_version table: {version}")
    else:
        print("[DEBUG] alembic_version table does not exist.")
    conn.close()
    # Check for cost column in equipment
    check_equipment_cost_column(db_path)
    yield db_path
    try:
        os.remove(db_path)
    except FileNotFoundError:
        pass

@pytest.fixture(scope='function')
def app(test_db_file):
    from app import create_app, db
    app = create_app()
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False  # Disable CSRF for tests
    app.config['SQLALCHEMY_DATABASE_URI'] = test_db_file
    print(f"[DEBUG] Flask app SQLALCHEMY_DATABASE_URI: {app.config['SQLALCHEMY_DATABASE_URI']}")
    # Confirm Alembic and SQLAlchemy URIs match
    if test_db_file != app.config['SQLALCHEMY_DATABASE_URI']:
        print(f"[ERROR] Alembic DB URI and SQLAlchemy DB URI do not match! {test_db_file} != {app.config['SQLALCHEMY_DATABASE_URI']}")
    with app.app_context():
        db.metadata.clear()  # Drop all old SQLAlchemy metadata
        db.reflect()  # Ensure SQLAlchemy metadata is in sync with DB schema
        yield app
        db.session.remove()
        db.engine.dispose()

@pytest.fixture(scope='function')
def db_session(app):
    from app import db
    yield db.session
    db.session.rollback()

@pytest.fixture
def client(app):
    return app.test_client()

# Add a fixture to truncate all tables before each test for full isolation
@pytest.fixture(autouse=True, scope='function')
def truncate_tables(app):
    from app import db
    meta = db.metadata
    engine = db.engine
    # Disable foreign key checks for SQLite
    if engine.dialect.name == 'sqlite':
        db.session.execute(text('PRAGMA foreign_keys=OFF'))
    try:
        for table in reversed(meta.sorted_tables):
            db.session.execute(table.delete())
        db.session.commit()
    finally:
        # Re-enable foreign key checks for SQLite
        if engine.dialect.name == 'sqlite':
            db.session.execute(text('PRAGMA foreign_keys=ON')) 