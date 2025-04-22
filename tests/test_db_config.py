"""
Tests for database configuration and initialization.
"""

import pytest
import sqlite3
from pathlib import Path

from app import create_app, db
from app.models.db_init import (
    init_db,
    verify_db_config,
    verify_db_file_exists,
    test_db_configuration,
    DatabaseConfigError
)
from app.models.db_config import SQLITE_CONFIG, DB_PATH

@pytest.fixture
def app():
    """Create and configure a test Flask application."""
    # Use a test database file
    test_db_path = Path('instance/test.db')
    
    # Create test config
    test_config = {
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': f'sqlite:///{test_db_path}'
    }
    
    # Create the application
    app = create_app(test_config)
    
    # Create test database and context
    with app.app_context():
        init_db(app)
        yield app
        
        # Cleanup after tests
        db.drop_all()
        if test_db_path.exists():
            test_db_path.unlink()

@pytest.fixture
def client(app):
    """Create a test client."""
    return app.test_client()

def test_database_initialization(app):
    """Test that database is properly initialized."""
    with app.app_context():
        # Verify database file exists
        assert verify_db_file_exists()
        
        # Verify configuration
        assert verify_db_config()
        
        # Test direct SQLite connection
        test_db_configuration()

def test_wal_mode_configuration(app):
    """Test that WAL mode is properly configured."""
    with app.app_context():
        with db.engine.connect() as conn:
            result = conn.execute("PRAGMA journal_mode;")
            assert result.scalar().upper() == "WAL"

def test_foreign_keys_enabled(app):
    """Test that foreign keys are enabled."""
    with app.app_context():
        with db.engine.connect() as conn:
            result = conn.execute("PRAGMA foreign_keys;")
            assert result.scalar() == 1

def test_busy_timeout_configuration(app):
    """Test that busy timeout is properly configured."""
    with app.app_context():
        with db.engine.connect() as conn:
            result = conn.execute("PRAGMA busy_timeout;")
            timeout = result.scalar()
            assert timeout >= (SQLITE_CONFIG.get('timeout', 30) * 1000)

def test_invalid_database_path():
    """Test error handling for invalid database path."""
    invalid_config = {
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///nonexistent/path/db.sqlite'
    }
    app = create_app(invalid_config)
    
    with app.app_context():
        with pytest.raises(DatabaseConfigError):
            verify_db_file_exists()

def test_database_accessibility(app):
    """Test database file accessibility check."""
    with app.app_context():
        # Test with valid database
        assert verify_db_file_exists()
        
        # Test with inaccessible database (make read-only)
        test_db_path = Path(app.config['SQLALCHEMY_DATABASE_URI'].replace('sqlite:///', ''))
        test_db_path.chmod(0o444)  # Read-only
        
        # Should still be readable
        assert verify_db_file_exists()
        
        # Restore permissions
        test_db_path.chmod(0o666)

def test_concurrent_access(app):
    """Test concurrent database access with WAL mode."""
    with app.app_context():
        # Create multiple connections
        conn1 = sqlite3.connect(str(DB_PATH))
        conn2 = sqlite3.connect(str(DB_PATH))
        
        try:
            # Should be able to read while writing with WAL mode
            cursor1 = conn1.cursor()
            cursor2 = conn2.cursor()
            
            # Start a write transaction in first connection
            cursor1.execute("CREATE TABLE IF NOT EXISTS test_table (id INTEGER PRIMARY KEY)")
            
            # Should be able to read from second connection
            cursor2.execute("SELECT 1")
            assert cursor2.fetchone() is not None
            
        finally:
            conn1.close()
            conn2.close() 