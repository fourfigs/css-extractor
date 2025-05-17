# CSS Extractor v3.0.0

A powerful and efficient CSS extraction and processing tool with advanced features for handling large-scale CSS operations.

## Features

### Core Functionality
- CSS extraction from HTML files and directories
- CSS processing and optimization
- CSS validation and sanitization
- HTML parsing and validation
- URL normalization and validation

### Resource Management
- Cache management with size limits and expiration
- Memory management with leak detection
- Network request management with connection pooling
- File system operations with proper locking
- Resource usage monitoring and optimization

### Security Features
- Input validation and sanitization
- URL and path validation
- CSS and HTML content validation
- File integrity checks
- Security event logging

### Performance Optimization
- Thread-safe operations
- Concurrent processing
- Rate limiting
- Resource pooling
- Performance monitoring

### Error Handling
- Comprehensive error recovery
- Detailed error logging
- Graceful degradation
- Resource cleanup
- Exception tracking

## Installation

### From Source
```bash
# Clone the repository
git clone https://github.com/fourfigs/css-extractor.git
cd css-extractor

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### From PyPI
```bash
pip install css-extractor
```

## Quick Start

### Command Line Usage
```bash
# Extract CSS from a directory
python css_extractor.py --input /path/to/html/files --output /path/to/output

# Extract CSS from a single HTML file
python css_extractor.py --input file.html --output style.css

# Extract with additional options
python css_extractor.py --input /path/to/html/files --output /path/to/output --minify --verbose

# Available options:
# --input: Input file or directory (required)
# --output: Output file or directory (required)
# --minify: Minify the output CSS
# --verbose: Show detailed progress
# --quiet: Suppress non-error output
# --format: Output format (text/json)
# --verify-ssl: Verify SSL certificates (default: true)
```

### Python API Usage
```python
from css_extractor import CSSExtractor

# Initialize extractor
extractor = CSSExtractor()

# Extract CSS from HTML
css = extractor.extract_from_html(html_content)

# Extract CSS from directory
css_files = extractor.extract_from_directory(directory_path)

# Process and optimize CSS
processed_css = extractor.process_css(css_content)

# Validate CSS
is_valid = extractor.validate_css(css_content)
```

## Advanced Usage

### Resource Management

```python
from css_extractor.managers import ManagerFactory

# Create resource managers
factory = ManagerFactory()
cache_manager = factory.create_cache_manager()
memory_manager = factory.create_memory_manager()
network_manager = factory.create_network_manager()

# Monitor resources
stats = factory.get_all_stats()
```

### Security Features

```python
from css_extractor.utils.security import SecurityManager

# Initialize security manager
security = SecurityManager()

# Configure security settings
security.add_allowed_domain('example.com')
security.add_blocked_domain('malicious.com')

# Validate content
is_valid = security.validate_css(css_content)
```

### Performance Optimization

```python
from css_extractor.utils.concurrency import ThreadPool, RateLimiter

# Create thread pool
with ThreadPool(max_workers=4) as pool:
    # Submit tasks
    future = pool.submit(process_css, css_content)

# Use rate limiter
with RateLimiter(rate=10) as limiter:
    # Make requests
    response = make_request(url)
```

## Configuration

The CSS Extractor can be configured through environment variables or a configuration file:

```python
# Environment variables
CSS_EXTRACTOR_CACHE_DIR=/path/to/cache
CSS_EXTRACTOR_MEMORY_LIMIT=1024
CSS_EXTRACTOR_NETWORK_TIMEOUT=30

# Configuration file
{
    "cache": {
        "dir": "/path/to/cache",
        "size_limit": 1024,
        "expiration": 3600
    },
    "memory": {
        "limit": 1024,
        "cleanup_interval": 300
    },
    "network": {
        "timeout": 30,
        "max_retries": 3,
        "rate_limit": 10
    }
}
```

## Development Setup

1. Clone the repository:
```bash
git clone https://github.com/fourfigs/css-extractor.git
cd css-extractor
```

2. Create a virtual environment:
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

3. Install development dependencies:
```bash
pip install -r requirements.txt
pip install -r css_extractor/tests/requirements-test.txt
```

4. Set up pre-commit hooks:
```bash
pip install pre-commit
pre-commit install
```

5. Run tests:
```bash
python -m pytest css_extractor/tests/
```

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Run tests (`python -m pytest css_extractor/tests/`)
5. Commit your changes (`git commit -m 'Add amazing feature'`)
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

## License

MIT License

## Changelog

### v3.0.0 (Major Release)
- Complete rewrite of core functionality
- Added comprehensive resource management
- Enhanced security features
- Improved performance optimization
- Added thread safety and concurrency
- Implemented proper error handling
- Added extensive test coverage
- Improved documentation
- Added command-line interface
- Added directory processing support

### v2.0.0
- Added CSS processing features
- Improved HTML parsing
- Enhanced URL handling

### v1.0.0
- Initial release
- Basic CSS extraction
- Simple HTML parsing 