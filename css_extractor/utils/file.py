"""File utility for CSS Extractor."""

import os
import shutil
import logging
from typing import Optional
from .config import CACHE_DIR, TEMP_DIR, FILE_OPERATION_TIMEOUT
from .common import ensure_directory
from .error import FileOperationError

def safe_write_file(file_path: str, content: str, encoding: str = 'utf-8') -> bool:
    """Safely write content to a file.
    
    Args:
        file_path: Path to the file
        content: Content to write
        encoding: File encoding
        
    Returns:
        True if successful
        
    Raises:
        FileOperationError: If file write fails
    """
    try:
        ensure_directory(os.path.dirname(file_path))
        with open(file_path, 'w', encoding=encoding) as f:
            f.write(content)
        return True
    except Exception as e:
        raise FileOperationError(f"Failed to write file {file_path}: {e}")

def safe_read_file(file_path: str, encoding: str = 'utf-8') -> str:
    """Safely read content from a file.
    
    Args:
        file_path: Path to the file
        encoding: File encoding
        
    Returns:
        File content
        
    Raises:
        FileOperationError: If file read fails
    """
    try:
        with open(file_path, 'r', encoding=encoding) as f:
            return f.read()
    except Exception as e:
        raise FileOperationError(f"Failed to read file {file_path}: {e}")

def clear_cache() -> None:
    """Clear the cache directory.
    
    Raises:
        FileOperationError: If cache clearing fails
    """
    try:
        if os.path.exists(CACHE_DIR):
            shutil.rmtree(CACHE_DIR)
        ensure_directory(CACHE_DIR)
    except Exception as e:
        raise FileOperationError(f"Failed to clear cache: {e}")

def clear_temp() -> None:
    """Clear the temporary directory.
    
    Raises:
        FileOperationError: If temp directory clearing fails
    """
    try:
        if os.path.exists(TEMP_DIR):
            shutil.rmtree(TEMP_DIR)
        ensure_directory(TEMP_DIR)
    except Exception as e:
        raise FileOperationError(f"Failed to clear temp directory: {e}")

# Exported functions
__all__ = ['safe_write_file', 'safe_read_file', 'clear_cache', 'clear_temp'] 