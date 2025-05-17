"""Pytest configuration for CSS Extractor tests."""

import os
import pytest
import logging
import tempfile
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

@pytest.fixture(scope='session')
def test_dir():
    """Create and return test directory."""
    test_dir = Path('test_output')
    test_dir.mkdir(exist_ok=True)
    yield test_dir
    # Cleanup after tests
    for item in test_dir.iterdir():
        if item.is_file():
            item.unlink()
        elif item.is_dir():
            for subitem in item.iterdir():
                subitem.unlink()
            item.rmdir()
    test_dir.rmdir()

@pytest.fixture(scope='session')
def temp_cache_dir():
    """Create temporary cache directory."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)

@pytest.fixture(scope='session')
def sample_css():
    """Return sample CSS content for testing."""
    return """
    body {
        color: #333;
        font-family: Arial, sans-serif;
        margin: 0;
        padding: 20px;
    }
    
    .container {
        max-width: 1200px;
        margin: 0 auto;
    }
    
    .header {
        background-color: #f5f5f5;
        padding: 10px;
        border-bottom: 1px solid #ddd;
    }
    
    .content {
        display: flex;
        flex-wrap: wrap;
        gap: 20px;
    }
    
    .sidebar {
        flex: 0 0 300px;
        background-color: #f9f9f9;
        padding: 15px;
    }
    
    .main {
        flex: 1;
        min-width: 0;
    }
    
    @media (max-width: 768px) {
        .content {
            flex-direction: column;
        }
        
        .sidebar {
            flex: none;
            width: 100%;
        }
    }
    """

@pytest.fixture(scope='session')
def sample_html():
    """Return sample HTML content for testing."""
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Test Page</title>
        <link rel="stylesheet" href="styles.css">
        <style>
            .inline-style {
                color: blue;
                font-weight: bold;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <header class="header">
                <h1>Test Page</h1>
            </header>
            <div class="content">
                <aside class="sidebar">
                    <nav>
                        <ul>
                            <li><a href="#">Home</a></li>
                            <li><a href="#">About</a></li>
                            <li><a href="#">Contact</a></li>
                        </ul>
                    </nav>
                </aside>
                <main class="main">
                    <article>
                        <h2>Test Content</h2>
                        <p class="inline-style">This is a test paragraph with inline styles.</p>
                        <p>This is a regular paragraph.</p>
                    </article>
                </main>
            </div>
        </div>
    </body>
    </html>
    """

@pytest.fixture(scope='session')
def mock_urls():
    """Return mock URLs for testing."""
    return {
        'valid': [
            'http://example.com',
            'https://example.com/path',
            'https://sub.example.com/page?param=value',
            'http://localhost:8080',
            'https://user:pass@example.com'
        ],
        'invalid': [
            'not-a-url',
            'http://',
            'https://',
            'ftp://',
            '://example.com',
            'http:///example.com',
            'http://example',
            'http://.com',
            'http://example..com'
        ]
    }

@pytest.fixture(scope='session')
def large_css():
    """Return large CSS content for testing."""
    return "body { color: red; }" * 10000  # ~200KB

@pytest.fixture(scope='session')
def special_chars_css():
    """Return CSS with special characters for testing."""
    return """
    body {
        content: '\\u00A9';
        font-family: "Helvetica Neue", sans-serif;
        background: url('image.jpg?param=value#fragment');
    }
    """

@pytest.fixture(scope='session')
def corrupted_metadata():
    """Return corrupted metadata for testing."""
    return "invalid json content"

@pytest.fixture(scope='session')
def mock_process():
    """Return mock process for testing."""
    class MockProcess:
        def memory_info(self):
            return type('MemoryInfo', (), {'rss': 1024 * 1024})()
            
    return MockProcess()

@pytest.fixture(scope='session')
def mock_network_stats():
    """Return mock network statistics for testing."""
    return {
        'request_count': 5,
        'max_requests': 10,
        'elapsed_time': 1.5
    } 