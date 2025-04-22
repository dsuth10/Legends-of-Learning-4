"""
Database configuration module for Legends of Learning.

This module defines all database-related configuration parameters and utilities
for the SQLite database used in the application.
"""

from typing import Dict, Any
import os
from pathlib import Path

# Base directory of the application
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Database file configuration
DB_NAME = 'legends.db'
DB_PATH = BASE_DIR / 'instance' / DB_NAME

# SQLite specific settings
SQLITE_CONFIG = {
    'journal_mode': 'WAL',  # Write-Ahead Logging for better concurrency
    'foreign_keys': 'ON',   # Enforce foreign key constraints
    'timeout': 30,         # Connection timeout in seconds
}

# SQLAlchemy connection pool settings
POOL_CONFIG = {
    'pool_size': 5,        # Maximum number of persistent connections
    'max_overflow': 10,    # Maximum number of connections that can be created beyond pool_size
    'pool_timeout': 30,    # Timeout for getting a connection from the pool
    'pool_recycle': 1800,  # Recycle connections after 30 minutes
}

# Retry configuration for database operations
RETRY_CONFIG = {
    'max_retries': 5,      # Maximum number of retry attempts
    'retry_delay': 0.1,    # Delay between retries in seconds
    'backoff_factor': 2,   # Multiply retry delay by this factor after each retry
}

def get_database_url() -> str:
    """
    Build and return the database URL for SQLAlchemy.
    
    The URL is constructed using the DB_PATH configuration, with query parameters
    for various SQLite settings.
    
    Returns:
        str: The complete database URL with configuration parameters
    """
    # Create instance directory if it doesn't exist
    os.makedirs(DB_PATH.parent, exist_ok=True)
    
    # Build query parameters from SQLITE_CONFIG
    params = '&'.join(f'{k}={v}' for k, v in SQLITE_CONFIG.items())
    
    return f'sqlite:///{DB_PATH}?{params}'

def get_sqlalchemy_config() -> Dict[str, Any]:
    """
    Get the complete SQLAlchemy configuration dictionary.
    
    Returns:
        Dict[str, Any]: Configuration dictionary for SQLAlchemy
    """
    return {
        'SQLALCHEMY_DATABASE_URI': get_database_url(),
        'SQLALCHEMY_TRACK_MODIFICATIONS': False,
        'SQLALCHEMY_ENGINE_OPTIONS': {
            **POOL_CONFIG,
            'connect_args': SQLITE_CONFIG
        }
    } 