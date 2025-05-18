# Contributing to CSS Extractor

Thank you for your interest in contributing to CSS Extractor! This document provides guidelines and instructions for contributing.

## Code of Conduct

Please be respectful and considerate of others when contributing to this project.

## How to Contribute

1. Fork the repository
2. Create a new branch for your feature/fix
3. Make your changes
4. Run the tests
5. Submit a pull request

## Development Setup

1. Clone your fork:
```bash
git clone https://github.com/YOUR-USERNAME/css-extractor.git
cd css-extractor
```

2. Create a virtual environment:
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

3. Install development dependencies:
```bash
pip install -r css_extractor/tests/requirements-test.txt
pip install -e .
```

4. Install pre-commit hooks:
```bash
pip install pre-commit
pre-commit install
```

## Running Tests

```bash
pytest css_extractor/tests/ -v
```

## Code Style

- Follow PEP 8 guidelines
- Use type hints
- Write docstrings for all functions and classes
- Keep functions small and focused
- Write tests for new features

## Pull Request Process

1. Update the README.md with details of changes if needed
2. Update the documentation if needed
3. Ensure all tests pass
4. The PR will be merged once you have the sign-off of at least one maintainer

## Reporting Bugs

Please use the GitHub issue tracker to report bugs. Include:
- A clear description of the bug
- Steps to reproduce
- Expected behavior
- Actual behavior
- Environment details

## Feature Requests

We welcome feature requests! Please:
- Describe the feature
- Explain why it would be useful
- Suggest implementation details if possible

## Questions?

Feel free to contact the maintainer at fourfigs@gmail.com 