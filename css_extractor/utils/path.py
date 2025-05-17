"""Path handling functionality."""

import os
import re
import logging
from pathlib import Path
from typing import Optional, List, Tuple
from urllib.parse import urlparse, urljoin
from .common import get_file_extension, normalize_path
from .error import FileOperationError, ValidationError

def is_directory(path: str) -> bool:
    """Check if path is a directory.
    
    Args:
        path: Path to check
        
    Returns:
        True if path is a directory
    """
    try:
        return os.path.isdir(path)
    except Exception as e:
        logging.error(f"Error checking directory: {e}")
        return False

def is_file(path: str) -> bool:
    """Check if path is a file.
    
    Args:
        path: Path to check
        
    Returns:
        True if path is a file
    """
    try:
        return os.path.isfile(path)
    except Exception as e:
        logging.error(f"Error checking file: {e}")
        return False

def is_valid_url(url: str) -> bool:
    """Check if string is a valid URL.
    
    Args:
        url: URL to check
        
    Returns:
        True if valid URL
    """
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except Exception:
        return False

def resolve_relative_path(base_path: str, relative_path: str) -> str:
    """Resolve relative path against base path.
    
    Args:
        base_path: Base path
        relative_path: Relative path to resolve
        
    Returns:
        Resolved path
        
    Raises:
        ValidationError: If path resolution fails
    """
    try:
        # Handle URLs
        if is_valid_url(base_path):
            return urljoin(base_path, relative_path)
            
        # Handle file paths
        base = Path(base_path)
        if base.is_file():
            base = base.parent
            
        resolved = base / relative_path
        return str(resolved.resolve())
    except Exception as e:
        raise ValidationError(f"Failed to resolve path {relative_path} against {base_path}: {e}")

def is_html_file(path: str) -> bool:
    """Check if file is HTML.
    
    Args:
        path: File path
        
    Returns:
        True if HTML file
    """
    try:
        ext = get_file_extension(path)
        return ext in ['.html', '.htm', '.xhtml']
    except Exception as e:
        logging.error(f"Error checking HTML file: {e}")
        return False

def is_css_file(path: str) -> bool:
    """Check if file is CSS.
    
    Args:
        path: File path
        
    Returns:
        True if CSS file
    """
    try:
        ext = get_file_extension(path)
        return ext == '.css'
    except Exception as e:
        logging.error(f"Error checking CSS file: {e}")
        return False

def find_files(directory: str, pattern: str = '*') -> List[str]:
    """Find files matching pattern in directory.
    
    Args:
        directory: Directory to search
        pattern: File pattern to match
        
    Returns:
        List of matching file paths
        
    Raises:
        ValidationError: If directory is invalid or search fails
    """
    try:
        if not is_directory(directory):
            raise ValidationError(f"Not a directory: {directory}")
            
        files = []
        for root, _, filenames in os.walk(directory):
            for filename in filenames:
                if re.match(pattern, filename):
                    files.append(os.path.join(root, filename))
                    
        return files
    except Exception as e:
        raise ValidationError(f"Failed to find files in {directory}: {e}")

def get_relative_path(path: str, base_path: str) -> str:
    """Get relative path from base path.
    
    Args:
        path: Path to convert
        base_path: Base path
        
    Returns:
        Relative path
        
    Raises:
        ValidationError: If path conversion fails
    """
    try:
        path = Path(path)
        base = Path(base_path)
        
        if base.is_file():
            base = base.parent
            
        return str(path.relative_to(base))
    except Exception as e:
        raise ValidationError(f"Failed to get relative path from {base_path} to {path}: {e}")

def is_same_file(path1: str, path2: str) -> bool:
    """Check if two paths refer to the same file.
    
    Args:
        path1: First path
        path2: Second path
        
    Returns:
        True if same file
    """
    try:
        return os.path.samefile(path1, path2)
    except Exception as e:
        logging.error(f"Error checking same file: {e}")
        return False

def is_path_in_directory(path: str, directory: str) -> bool:
    """Check if path is within directory.
    
    Args:
        path: Path to check
        directory: Directory to check against
        
    Returns:
        True if path is within directory
    """
    try:
        path = os.path.abspath(path)
        directory = os.path.abspath(directory)
        return path.startswith(directory)
    except Exception as e:
        logging.error(f"Error checking path in directory: {e}")
        return False

# Exported functions
__all__ = [
    'is_directory',
    'is_file',
    'is_valid_url',
    'resolve_relative_path',
    'is_html_file',
    'is_css_file',
    'find_files',
    'get_relative_path',
    'is_same_file',
    'is_path_in_directory',
] 