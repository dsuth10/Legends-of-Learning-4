"""
Database initialization and verification module.

This module handles the initialization and verification of the SQLite database,
ensuring it is properly configured with WAL mode and other required settings.
"""

import logging
import sqlite3
from pathlib import Path
from typing import Optional

from sqlalchemy import event
from flask_sqlalchemy import SQLAlchemy
from flask import current_app

from .db_config import DB_PATH, SQLITE_PRAGMAS
from ..exceptions import DatabaseConfigError

logger = logging.getLogger(__name__)

def set_sqlite_pragma(dbapi_connection, connection_record):
    """
    SQLAlchemy event listener to set PRAGMAs after connection.
    
    Args:
        dbapi_connection: The raw SQLite connection
        connection_record: SQLAlchemy connection record
    """
    cursor = dbapi_connection.cursor()
    for pragma, value in SQLITE_PRAGMAS.items():
        cursor.execute(f"PRAGMA {pragma}={value}")
    cursor.close()

def verify_db_config(connection: sqlite3.Connection) -> None:
    """
    Verify that the database is configured correctly.
    
    Args:
        connection: SQLite connection to verify
        
    Raises:
        DatabaseConfigError: If any configuration check fails
    """
    cursor = connection.cursor()
    
    # Check journal mode
    cursor.execute("PRAGMA journal_mode")
    journal_mode = cursor.fetchone()[0].upper()
    if journal_mode != 'WAL':
        raise DatabaseConfigError(f"Incorrect journal mode: {journal_mode}")
    
    # Check foreign keys
    cursor.execute("PRAGMA foreign_keys")
    foreign_keys = cursor.fetchone()[0]
    if not foreign_keys:
        raise DatabaseConfigError("Foreign keys are not enabled")
    
    cursor.close()

def verify_db_file_exists() -> None:
    """
    Verify that the database file exists and is accessible.
    Creates the database file if it doesn't exist.
    """
    if not DB_PATH.exists():
        # Create parent directory if it doesn't exist
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        
        # Create database file and set initial PRAGMAs
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        for pragma, value in SQLITE_PRAGMAS.items():
            cursor.execute(f"PRAGMA {pragma}={value}")
        conn.commit()
        conn.close()
        logger.info(f"Created new database file at {DB_PATH}")

def init_db(db: SQLAlchemy) -> None:
    """
    Initialize the database, create tables, and verify configuration.
    
    Args:
        db: SQLAlchemy database instance
    """
    try:
        # Register PRAGMA setter
        event.listen(db.engine, 'connect', set_sqlite_pragma)
        
        # Ensure database file exists
        verify_db_file_exists()
        
        # Create all tables
        db.create_all()
        
        # Verify configuration
        with sqlite3.connect(DB_PATH) as conn:
            verify_db_config(conn)
        
        logger.info("Database initialized successfully")
        
    except Exception as e:
        logger.error(f"Failed to initialize database: {str(e)}")
        raise

def test_db_configuration(db_path: Optional[Path] = None) -> None:
    """
    Test function to verify database configuration.
    
    Args:
        db_path: Optional path to database file. Uses DB_PATH if not provided.
    """
    path = db_path or DB_PATH
    try:
        with sqlite3.connect(path) as conn:
            verify_db_config(conn)
        print("Database configuration verified successfully")
    except Exception as e:
        print(f"Database configuration verification failed: {str(e)}")