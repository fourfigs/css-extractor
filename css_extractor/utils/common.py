"""Common utilities for CSS Extractor."""

import os
import logging
from typing import Optional, Tuple
from .error import FileOperationError

def ensure_directory(path: str) -> bool:
    """Ensure directory exists.
    
    Args:
        path: Directory path
        
    Returns:
        True if directory exists or was created
        
    Raises:
        FileOperationError: If directory creation fails
    """
    try:
        if not os.path.exists(path):
            os.makedirs(path)
        return True
    except Exception as e:
        raise FileOperationError(f"Failed to create directory {path}: {e}")

def split_path(path: str) -> Tuple[str, str, str]:
    """Split path into directory, filename, and extension.
    
    Args:
        path: Path to split
        
    Returns:
        Tuple of (directory, filename, extension)
    """
    try:
        directory = os.path.dirname(path)
        filename = os.path.basename(path)
        name, ext = os.path.splitext(filename)
        return directory, name, ext
    except Exception as e:
        logging.error(f"Error splitting path: {e}")
        return '', '', ''

def get_file_extension(path: str) -> str:
    """Get file extension.
    
    Args:
        path: File path
        
    Returns:
        File extension (lowercase)
    """
    try:
        return os.path.splitext(path)[1].lower()
    except Exception as e:
        logging.error(f"Error getting file extension: {e}")
        return ''

def normalize_path(path: str) -> str:
    """Normalize file path.
    
    Args:
        path: Path to normalize
        
    Returns:
        Normalized path
    """
    try:
        # Convert to absolute path
        path = os.path.abspath(path)
        
        # Normalize separators
        path = os.path.normpath(path)
        
        # Convert to forward slashes
        path = path.replace('\\', '/')
        
        return path
    except Exception as e:
        logging.error(f"Error normalizing path: {e}")
        return path

# Exported functions
__all__ = [
    'ensure_directory',
    'split_path',
    'get_file_extension',
    'normalize_path',
] 