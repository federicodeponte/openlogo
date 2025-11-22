# Contributing to crawl4logo

Thank you for your interest in contributing to crawl4logo! This document provides guidelines for contributing to the project.

## Code of Conduct

This project adheres to a code of conduct. By participating, you are expected to uphold this code.

## How Can I Contribute?

### Reporting Bugs

Before creating bug reports, please check the issue list as you might find that you don't need to create one. When you are creating a bug report, please include as many details as possible:

* Use a clear and descriptive title
* Describe the exact steps to reproduce the problem
* Provide specific examples to demonstrate the steps
* Describe the behavior you observed and what behavior you expected
* Include Python version, OS, and package version

### Suggesting Enhancements

Enhancement suggestions are tracked as GitHub issues. When creating an enhancement suggestion, please include:

* Use a clear and descriptive title
* Provide a step-by-step description of the suggested enhancement
* Explain why this enhancement would be useful
* List some examples of how it would be used

### Pull Requests

1. Fork the repo and create your branch from `main`
2. If you've added code that should be tested, add tests
3. If you've changed APIs, update the documentation
4. Ensure the test suite passes
5. Make sure your code follows the existing style (use `black` and `isort`)
6. Issue that pull request!

## Development Setup

### 1. Clone the repository

```bash
git clone https://github.com/federicodeponte/crawl4logo.git
cd crawl4logo
```

### 2. Install system dependencies

**macOS:**
```bash
brew install cairo
```

**Ubuntu/Debian:**
```bash
sudo apt-get install libcairo2-dev
```

### 3. Create a virtual environment

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 4. Install development dependencies

```bash
pip install -e ".[dev]"
```

### 5. Set up environment variables

```bash
cp .env.example .env
# Edit .env and add your OpenAI API key
```

## Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=fede_crawl4ai

# Run specific test file
pytest tests/unit/test_logo_crawler.py

# Run with verbose output
pytest -v
```

## Code Style

This project uses:
- **black** for code formatting (line length: 100)
- **isort** for import sorting
- **flake8** for linting
- **mypy** for type checking (optional)

```bash
# Format code
black fede_crawl4ai tests

# Sort imports
isort fede_crawl4ai tests

# Lint
flake8 fede_crawl4ai

# Type check
mypy fede_crawl4ai
```

## Git Commit Messages

* Use the present tense ("Add feature" not "Added feature")
* Use the imperative mood ("Move cursor to..." not "Moves cursor to...")
* Limit the first line to 72 characters or less
* Reference issues and pull requests liberally after the first line

### Commit Message Format

```
<type>: <subject>

<body>

<footer>
```

**Types:**
- **feat**: New feature
- **fix**: Bug fix
- **docs**: Documentation changes
- **style**: Code style changes (formatting, etc.)
- **refactor**: Code refactoring
- **test**: Adding or updating tests
- **chore**: Maintenance tasks

## Project Structure

```
crawl4logo/
├── fede_crawl4ai/          # Main package
│   ├── __init__.py
│   └── logo_crawler.py     # Core crawler logic
├── tests/                  # Test suite
│   ├── unit/              # Unit tests
│   ├── integration/       # Integration tests
│   └── e2e/               # End-to-end tests
├── .github/workflows/     # CI/CD workflows
├── pyproject.toml         # Package configuration
└── README.md
```

## Release Process

1. Update version in `pyproject.toml`
2. Update `CHANGELOG.md`
3. Create a git tag: `git tag v0.x.0`
4. Push tag: `git push origin v0.x.0`
5. Create GitHub release
6. GitHub Actions will automatically publish to PyPI

## Questions?

Feel free to open an issue with your question or reach out to the maintainers.

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
