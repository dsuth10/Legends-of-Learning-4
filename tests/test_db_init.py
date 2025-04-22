"""Tests for database initialization and configuration."""
import os
import sqlite3
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text

from app.models.db_config import DB_PATH, SQLITE_PRAGMAS
from app.models.db_init import init_db, verify_db_config, test_db_configuration


def test_db_initialization(tmp_path):
    """Test that database is initialized with correct settings."""
    # Use a temporary database file
    test_db_path = tmp_path / "test.db"
    
    # Initialize the database
    engine = create_engine(f"sqlite:///{test_db_path}")
    init_db(engine)
    
    # Verify the database exists
    assert test_db_path.exists()
    
    # Check database configuration
    with sqlite3.connect(test_db_path) as conn:
        # Check journal mode (WAL)
        cursor = conn.execute("PRAGMA journal_mode;")
        assert cursor.fetchone()[0].upper() == "WAL"
        
        # Check foreign keys
        cursor = conn.execute("PRAGMA foreign_keys;")
        assert cursor.fetchone()[0] == 1
        
        # Check synchronous setting
        cursor = conn.execute("PRAGMA synchronous;")
        assert cursor.fetchone()[0] == 1  # NORMAL


def test_verify_db_config():
    """Test the database configuration verification function."""
    # Create a test database with correct settings
    test_db_path = DB_PATH.parent / "test_verify.db"
    
    if test_db_path.exists():
        test_db_path.unlink()
    
    engine = create_engine(f"sqlite:///{test_db_path}")
    init_db(engine)
    
    try:
        # Should not raise any exceptions
        verify_db_config(engine)
        
        # Test with incorrect settings
        with sqlite3.connect(test_db_path) as conn:
            # Change journal mode to DELETE
            conn.execute("PRAGMA journal_mode=DELETE;")
            conn.commit()
        
        # Should raise an exception due to wrong journal mode
        with pytest.raises(RuntimeError) as exc_info:
            verify_db_config(engine)
        assert "journal_mode" in str(exc_info.value).lower()
        
    finally:
        # Cleanup
        if test_db_path.exists():
            test_db_path.unlink()


def test_db_connection_retry():
    """Test database connection with retry logic."""
    test_db_path = DB_PATH.parent / "test_retry.db"
    
    if test_db_path.exists():
        test_db_path.unlink()
    
    engine = create_engine(f"sqlite:///{test_db_path}")
    
    try:
        # Initialize database
        init_db(engine)
        
        # Test basic connection and query
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1;")).scalar()
            assert result == 1
            
    finally:
        # Cleanup
        if test_db_path.exists():
            test_db_path.unlink()


def test_pragmas_after_connect():
    """Test that PRAGMAs are set after each connection."""
    test_db_path = DB_PATH.parent / "test_pragmas.db"
    
    if test_db_path.exists():
        test_db_path.unlink()
    
    engine = create_engine(f"sqlite:///{test_db_path}")
    init_db(engine)
    
    try:
        # Create multiple connections and verify PRAGMAs
        for _ in range(3):
            with engine.connect() as conn:
                for pragma, value in SQLITE_PRAGMAS.items():
                    result = conn.execute(text(f"PRAGMA {pragma};")).scalar()
                    expected = value if isinstance(value, int) else value.upper()
                    actual = result if isinstance(result, int) else str(result).upper()
                    assert actual == expected, f"PRAGMA {pragma} mismatch"
                    
    finally:
        # Cleanup
        if test_db_path.exists():
            test_db_path.unlink()


def test_db_configuration_utility(capsys):
    """Test the database configuration test utility function."""
    test_db_path = DB_PATH.parent / "test_config_util.db"
    
    if test_db_path.exists():
        test_db_path.unlink()
    
    engine = create_engine(f"sqlite:///{test_db_path}")
    init_db(engine)
    
    try:
        # Test with correct configuration
        test_db_configuration(test_db_path)
        captured = capsys.readouterr()
        assert "successfully" in captured.out.lower()
        
        # Test with incorrect configuration
        with sqlite3.connect(test_db_path) as conn:
            conn.execute("PRAGMA journal_mode=DELETE;")
            conn.commit()
        
        test_db_configuration(test_db_path)
        captured = capsys.readouterr()
        assert "failed" in captured.out.lower()
        assert "journal_mode" in captured.out.lower()
        
    finally:
        # Cleanup
        if test_db_path.exists():
            test_db_path.unlink() 