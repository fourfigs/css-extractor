"""Configuration utility for CSS Extractor."""

import os

# Project version
VERSION = "1.0.0"

# Default directories
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE_DIR = os.path.join(BASE_DIR, 'cache')
TEMP_DIR = os.path.join(BASE_DIR, 'tmp')

# File size limits (in bytes)
MAX_CSS_SIZE = 5 * 1024 * 1024      # 5 MB
MAX_HTML_SIZE = 10 * 1024 * 1024    # 10 MB
MAX_DIRECTORY_SIZE = 1 * 1024 * 1024 * 1024  # 1 GB
MAX_FILES_TO_PROCESS = 1000

# Import depth
MAX_IMPORT_DEPTH = 10

# Resource limits
MAX_CPU_PERCENT = 90
MAX_MEMORY_MB = 1024
MAX_DISK_MB = 1024
MAX_NETWORK_MB = 100

# Timeouts (in seconds)
REQUEST_TIMEOUT = 30
FILE_OPERATION_TIMEOUT = 10

# Supported file extensions
HTML_EXTENSIONS = ['.html', '.htm', '.xhtml', '.php', '.asp', '.aspx', '.jsp']
CSS_EXTENSIONS = ['.css']

# User-Agent for requests
USER_AGENT = (
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
    'AppleWebKit/537.36 (KHTML, like Gecko) '
    'Chrome/91.0.4472.124 Safari/537.36'
)

# Logging
LOG_FILE = os.path.join(BASE_DIR, 'css_extractor.log')
LOG_LEVEL = 'INFO'

# Other settings
ENABLE_COLOR = True
ENABLE_PROGRESS = True

# Exported config
__all__ = [
    'VERSION', 'BASE_DIR', 'CACHE_DIR', 'TEMP_DIR',
    'MAX_CSS_SIZE', 'MAX_HTML_SIZE', 'MAX_DIRECTORY_SIZE', 'MAX_FILES_TO_PROCESS',
    'MAX_IMPORT_DEPTH',
    'MAX_CPU_PERCENT', 'MAX_MEMORY_MB', 'MAX_DISK_MB', 'MAX_NETWORK_MB',
    'REQUEST_TIMEOUT', 'FILE_OPERATION_TIMEOUT',
    'HTML_EXTENSIONS', 'CSS_EXTENSIONS',
    'USER_AGENT', 'LOG_FILE', 'LOG_LEVEL',
    'ENABLE_COLOR', 'ENABLE_PROGRESS',
] 