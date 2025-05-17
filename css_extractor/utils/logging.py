"""Logging utility for CSS Extractor."""

import logging
import os
from .config import LOG_FILE, LOG_LEVEL

def setup_logging(log_level: int = logging.DEBUG) -> None:
    """Set up logging configuration."""
    log_dir = os.path.dirname(LOG_FILE)
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        handlers=[
            logging.FileHandler(LOG_FILE),
            logging.StreamHandler()
        ]
    )

def get_logger(name):
    """Get a logger instance for the specified module.
    
    Args:
        name: Name of the module
        
    Returns:
        Logger instance
    """
    return logging.getLogger(name)

# Exported functions
__all__ = ['setup_logging', 'get_logger'] 