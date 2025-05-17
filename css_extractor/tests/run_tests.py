#!/usr/bin/env python
"""Test runner for CSS Extractor."""

import os
import sys
import pytest
from pathlib import Path

def main():
    """Run tests with coverage reporting."""
    # Get the project root directory
    project_root = Path(__file__).parent.parent
    
    # Add project root to Python path
    sys.path.insert(0, str(project_root))
    
    # Configure pytest arguments
    args = [
        '--verbose',
        '--cov=css_extractor',
        '--cov-report=term-missing',
        '--cov-report=html',
        '--cov-report=xml',
        '--junitxml=test-results.xml',
        '--timeout=30',
        '-n', 'auto',  # Use all available CPU cores
        'test_managers.py'
    ]
    
    # Run tests
    return pytest.main(args)

if __name__ == '__main__':
    sys.exit(main()) 