# CSS Extractor (them3ripper)

A robust, scalable, and secure CSS extraction and management tool for modern web projects. Supports advanced caching, memory management, and concurrent operations on Windows, Linux, and macOS.

## Features
- Extracts CSS files from directories and outputs to a specified directory
- Thread-safe, cross-platform cache management
- Memory management with leak detection and critical usage alerts
- Network management with request limits and domain validation
- Comprehensive test suite (pytest)
- Custom license: Free for personal/commercial use with required user registration (see LICENSE)

## Installation
```sh
pip install .
```

## Usage
```sh
python -m css_extractor <input_dir> <output_dir>
```

## License & Registration
This software is free for personal and commercial use, but you must register your usage by emailing the author (see LICENSE for details). Unauthorized distribution is prohibited.

## Running Tests
```sh
pip install -r css_extractor/tests/requirements-test.txt
pytest css_extractor/tests/ -v
```

## Contributing
Pull requests are welcome! Please ensure all tests pass before submitting.

## Author
Kenneth Hanks

---
For questions or registration, contact: fourfigs@gmail.com 