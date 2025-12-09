"""
Backup service module for database backup and export operations.
"""

import shutil
import sqlite3
import csv
import json
import tempfile
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional
from sqlalchemy import inspect
from app.models import db
from app.models.db_config import DB_PATH


def create_database_backup() -> Path:
    """
    Create a backup copy of the SQLite database file.
    
    Returns:
        Path: Path to the temporary backup file
        
    Raises:
        FileNotFoundError: If the database file doesn't exist
        PermissionError: If unable to read the database file
        Exception: For other backup errors
    """
    if not DB_PATH.exists():
        raise FileNotFoundError(f"Database file not found at {DB_PATH}")
    
    # Checkpoint WAL file to ensure consistency
    try:
        conn = sqlite3.connect(str(DB_PATH))
        conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        conn.close()
    except Exception as e:
        # Log warning but continue - backup may still work
        print(f"[Backup] Warning: Could not checkpoint WAL: {e}")
    
    # Generate timestamped filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_filename = f"legends_backup_{timestamp}.db"
    
    # Create temporary file
    temp_dir = Path(tempfile.gettempdir())
    backup_path = temp_dir / backup_filename
    
    try:
        # Copy database file
        shutil.copy2(DB_PATH, backup_path)
        return backup_path
    except PermissionError:
        raise PermissionError(f"Permission denied: Unable to read database file at {DB_PATH}")
    except Exception as e:
        raise Exception(f"Error creating backup: {e}")


def get_available_tables() -> List[str]:
    """
    Get list of all user tables in the database (excluding system tables).
    
    Returns:
        List[str]: List of table names
    """
    inspector = inspect(db.engine)
    all_tables = inspector.get_table_names()
    
    # Filter out SQLite system tables
    user_tables = [table for table in all_tables if not table.startswith('sqlite_')]
    
    return sorted(user_tables)


def validate_table_name(table_name: str) -> bool:
    """
    Validate that a table name is safe and exists.
    
    Args:
        table_name: Name of the table to validate
        
    Returns:
        bool: True if table is valid and exists
    """
    if not table_name or not isinstance(table_name, str):
        return False
    
    # Prevent path traversal and injection
    if '..' in table_name or '/' in table_name or '\\' in table_name:
        return False
    
    # Check if table exists
    available_tables = get_available_tables()
    return table_name in available_tables


def export_table_to_csv(table_name: str, output_path: Optional[Path] = None) -> Path:
    """
    Export a database table to CSV format.
    
    Args:
        table_name: Name of the table to export
        output_path: Optional path for output file. If None, creates temp file.
        
    Returns:
        Path: Path to the exported CSV file
        
    Raises:
        ValueError: If table name is invalid
        Exception: For export errors
    """
    if not validate_table_name(table_name):
        raise ValueError(f"Invalid or non-existent table name: {table_name}")
    
    # Create output file if not provided
    if output_path is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        temp_dir = Path(tempfile.gettempdir())
        output_path = temp_dir / f"{table_name}_export_{timestamp}.csv"
    
    try:
        # Connect to database and export
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()
        
        # Get all rows
        cursor.execute(f"SELECT * FROM {table_name}")
        rows = cursor.fetchall()
        
        # Get column names
        column_names = [description[0] for description in cursor.description]
        
        # Write to CSV
        with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(column_names)
            writer.writerows(rows)
        
        conn.close()
        return output_path
    except sqlite3.Error as e:
        raise Exception(f"Database error during CSV export: {e}")
    except Exception as e:
        raise Exception(f"Error exporting table to CSV: {e}")


def export_table_to_json(table_name: str, output_path: Optional[Path] = None) -> Path:
    """
    Export a database table to JSON format.
    
    Args:
        table_name: Name of the table to export
        output_path: Optional path for output file. If None, creates temp file.
        
    Returns:
        Path: Path to the exported JSON file
        
    Raises:
        ValueError: If table name is invalid
        Exception: For export errors
    """
    if not validate_table_name(table_name):
        raise ValueError(f"Invalid or non-existent table name: {table_name}")
    
    # Create output file if not provided
    if output_path is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        temp_dir = Path(tempfile.gettempdir())
        output_path = temp_dir / f"{table_name}_export_{timestamp}.json"
    
    try:
        # Connect to database and export
        conn = sqlite3.connect(str(DB_PATH))
        conn.row_factory = sqlite3.Row  # Enable column access by name
        cursor = conn.cursor()
        
        # Get all rows
        cursor.execute(f"SELECT * FROM {table_name}")
        rows = cursor.fetchall()
        
        # Convert rows to list of dictionaries
        data = [dict(row) for row in rows]
        
        # Write to JSON
        with open(output_path, 'w', encoding='utf-8') as jsonfile:
            json.dump(data, jsonfile, indent=2, default=str)
        
        conn.close()
        return output_path
    except sqlite3.Error as e:
        raise Exception(f"Database error during JSON export: {e}")
    except Exception as e:
        raise Exception(f"Error exporting table to JSON: {e}")


def get_database_info() -> Dict[str, any]:
    """
    Get information about the database file.
    
    Returns:
        Dict with keys: size, last_modified, exists
    """
    info = {
        'exists': DB_PATH.exists(),
        'size': 0,
        'last_modified': None,
        'path': str(DB_PATH)
    }
    
    if DB_PATH.exists():
        stat = DB_PATH.stat()
        info['size'] = stat.st_size
        info['last_modified'] = datetime.fromtimestamp(stat.st_mtime)
    
    return info

