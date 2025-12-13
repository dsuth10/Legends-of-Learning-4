"""
Utility functions for backup operations.
"""

from pathlib import Path
from typing import Optional


def format_file_size(size_bytes: int) -> str:
    """
    Format file size in human-readable format.
    
    Args:
        size_bytes: Size in bytes
        
    Returns:
        str: Formatted size string (e.g., "1.5 MB")
    """
    if size_bytes == 0:
        return "0 B"
    
    units = ['B', 'KB', 'MB', 'GB', 'TB']
    unit_index = 0
    size = float(size_bytes)
    
    while size >= 1024 and unit_index < len(units) - 1:
        size /= 1024
        unit_index += 1
    
    return f"{size:.2f} {units[unit_index]}"


def generate_safe_filename(base_name: str, extension: str = '') -> str:
    """
    Generate a safe filename by removing invalid characters.
    
    Args:
        base_name: Base name for the file
        extension: File extension (with or without dot)
        
    Returns:
        str: Safe filename
    """
    # Remove invalid characters for filenames
    invalid_chars = '<>:"/\\|?*'
    safe_name = ''.join(c if c not in invalid_chars else '_' for c in base_name)
    
    # Ensure extension starts with dot
    if extension and not extension.startswith('.'):
        extension = '.' + extension
    
    return safe_name + extension








