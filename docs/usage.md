# CSS Extractor Usage Guide

## Installation

```bash
pip install css-extractor
```

## Basic Usage

### Extract CSS from a URL

```bash
css-extractor -u https://example.com
```

### Extract CSS from a local HTML file

```bash
css-extractor -f path/to/file.html
```

## Command Line Options

### Input Options

- `-f, --file`: Path to HTML file
- `-u, --url`: URL to extract CSS from

### Output Options

- `-o, --output`: Output directory for extracted CSS (default: `extracted_css`)

### Processing Options

- `--minify`: Minify extracted CSS
- `--remove-comments`: Remove CSS comments
- `--remove-whitespace`: Remove unnecessary whitespace

### Cache Options

- `--cache-dir`: Directory for caching (default: `.css_cache`)
- `--cache-size`: Maximum cache size in MB (default: 100)
- `--no-cache`: Disable caching

### Memory Options

- `--memory-limit`: Memory limit in MB (default: 100)

### Other Options

- `-v, --verbose`: Enable verbose output

## Examples

### Extract and Minify CSS

```bash
css-extractor -u https://example.com --minify
```

### Extract CSS with Custom Output Directory

```bash
css-extractor -f index.html -o my_css
```

### Extract CSS with Memory Management

```bash
css-extractor -u https://example.com --memory-limit 200
```

### Extract CSS with Caching Disabled

```bash
css-extractor -u https://example.com --no-cache
```

## Python API

You can also use CSS Extractor in your Python code:

```python
from css_extractor import CSSExtractor

# Initialize extractor
extractor = CSSExtractor()

# Extract from URL
css = extractor.extract_from_url(
    'https://example.com',
    minify=True,
    remove_comments=True
)

# Extract from file
css = extractor.extract_from_file(
    'path/to/file.html',
    minify=True,
    remove_comments=True
)
```

## Error Handling

The tool will exit with status code 1 if an error occurs. Common errors include:

- Invalid URL or file path
- Network errors when fetching URLs
- Permission errors when writing files
- Memory limit exceeded
- Cache errors

## Logging

Use the `-v` flag to enable verbose logging:

```bash
css-extractor -u https://example.com -v
```

This will show detailed information about the extraction process, including:
- Cache operations
- Memory usage
- Processing steps
- Any warnings or errors 