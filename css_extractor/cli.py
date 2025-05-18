#!/usr/bin/env python3
"""
Command-line interface for CSS Extractor.
"""

import argparse
import logging
import sys
import urllib.parse
import re
from pathlib import Path
from typing import Optional, Union
from concurrent.futures import ThreadPoolExecutor, TimeoutError
import requests
from requests.exceptions import RequestException
import validators

from css_extractor.extractor import CSSExtractor
from css_extractor.managers.cache import CacheManager
from css_extractor.managers.memory import MemoryManager

# Constants
MAX_RETRIES = 3
REQUEST_TIMEOUT = 30
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
VALID_CSS_PATTERNS = [
    r'^[^{]*{[^}]*}$',  # Basic CSS rule
    r'@import\s+url\([^)]+\);',  # @import rule
    r'@media\s+[^{]*{[^}]*}$',  # @media rule
]

def setup_logging(verbose: bool = False) -> None:
    """Set up logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

def validate_url(url: str) -> bool:
    """Validate URL format and accessibility."""
    if not validators.url(url):
        raise ValueError(f"Invalid URL format: {url}")
    
    try:
        response = requests.head(url, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        return True
    except RequestException as e:
        raise ValueError(f"URL not accessible: {str(e)}")

def validate_file_path(file_path: Path) -> bool:
    """Validate file path and accessibility."""
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    
    if not file_path.is_file():
        raise ValueError(f"Not a file: {file_path}")
    
    if file_path.stat().st_size > MAX_FILE_SIZE:
        raise ValueError(f"File too large (max {MAX_FILE_SIZE/1024/1024}MB): {file_path}")
    
    return True

def validate_css_content(content: str) -> bool:
    """Validate CSS content for basic structure and security."""
    if not content.strip():
        raise ValueError("Empty CSS content")
    
    # Check for basic CSS structure
    if not any(re.match(pattern, content, re.DOTALL) for pattern in VALID_CSS_PATTERNS):
        raise ValueError("Invalid CSS content structure")
    
    # Check for potentially malicious content
    dangerous_patterns = [
        r'expression\s*\(',
        r'eval\s*\(',
        r'javascript:',
        r'data:text/html',
    ]
    
    if any(re.search(pattern, content, re.IGNORECASE) for pattern in dangerous_patterns):
        raise ValueError("Potentially malicious CSS content detected")
    
    return True

def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description='Extract CSS from HTML files or URLs'
    )
    
    # Input source
    source_group = parser.add_mutually_exclusive_group(required=True)
    source_group.add_argument(
        '-f', '--file',
        help='Path to HTML file',
        type=Path
    )
    source_group.add_argument(
        '-u', '--url',
        help='URL to extract CSS from',
        type=str
    )
    
    # Output options
    parser.add_argument(
        '-o', '--output',
        help='Output directory for extracted CSS',
        type=Path,
        default=Path('extracted_css')
    )
    
    # Processing options
    parser.add_argument(
        '--minify',
        help='Minify extracted CSS',
        action='store_true'
    )
    parser.add_argument(
        '--remove-comments',
        help='Remove CSS comments',
        action='store_true'
    )
    parser.add_argument(
        '--remove-whitespace',
        help='Remove unnecessary whitespace',
        action='store_true'
    )
    
    # Cache options
    parser.add_argument(
        '--cache-dir',
        help='Directory for caching',
        type=Path,
        default=Path('.css_cache')
    )
    parser.add_argument(
        '--cache-size',
        help='Maximum cache size in MB',
        type=int,
        default=100
    )
    parser.add_argument(
        '--no-cache',
        help='Disable caching',
        action='store_true'
    )
    
    # Memory options
    parser.add_argument(
        '--memory-limit',
        help='Memory limit in MB',
        type=int,
        default=100
    )
    
    # Security options
    parser.add_argument(
        '--timeout',
        help='Request timeout in seconds',
        type=int,
        default=REQUEST_TIMEOUT
    )
    parser.add_argument(
        '--max-retries',
        help='Maximum number of retries for failed requests',
        type=int,
        default=MAX_RETRIES
    )
    
    # Other options
    parser.add_argument(
        '-v', '--verbose',
        help='Enable verbose output',
        action='store_true'
    )
    
    return parser.parse_args()

def main() -> int:
    """Main entry point for the CLI."""
    args = parse_args()
    setup_logging(args.verbose)
    
    try:
        # Validate input
        if args.url:
            validate_url(args.url)
        else:
            validate_file_path(args.file)
        
        # Create output directory if it doesn't exist
        try:
            args.output.mkdir(parents=True, exist_ok=True)
        except PermissionError:
            raise PermissionError(f"Cannot create output directory: {args.output}")
        
        # Initialize managers
        cache_manager = None if args.no_cache else CacheManager(
            cache_dir=args.cache_dir,
            max_size_mb=args.cache_size
        )
        
        memory_manager = MemoryManager(
            memory_limit_mb=args.memory_limit
        )
        
        # Initialize extractor
        extractor = CSSExtractor(
            cache_manager=cache_manager,
            memory_manager=memory_manager
        )
        
        # Process input with retries
        for attempt in range(args.max_retries):
            try:
                with ThreadPoolExecutor() as executor:
                    if args.file:
                        future = executor.submit(
                            extractor.extract_from_file,
                            args.file,
                            minify=args.minify,
                            remove_comments=args.remove_comments,
                            remove_whitespace=args.remove_whitespace
                        )
                    else:
                        future = executor.submit(
                            extractor.extract_from_url,
                            args.url,
                            minify=args.minify,
                            remove_comments=args.remove_comments,
                            remove_whitespace=args.remove_whitespace
                        )
                    
                    css_content = future.result(timeout=args.timeout)
                    break
            except TimeoutError:
                if attempt == args.max_retries - 1:
                    raise TimeoutError(f"Operation timed out after {args.timeout} seconds")
                logging.warning(f"Attempt {attempt + 1} timed out, retrying...")
            except Exception as e:
                if attempt == args.max_retries - 1:
                    raise
                logging.warning(f"Attempt {attempt + 1} failed: {str(e)}, retrying...")
        
        # Validate CSS content
        validate_css_content(css_content)
        
        # Save output
        output_file = args.output / 'extracted.css'
        try:
            output_file.write_text(css_content)
            logging.info(f"CSS saved to {output_file}")
        except PermissionError:
            raise PermissionError(f"Cannot write to output file: {output_file}")
        
        return 0
        
    except Exception as e:
        logging.error(f"Error: {str(e)}")
        return 1

if __name__ == '__main__':
    sys.exit(main()) 