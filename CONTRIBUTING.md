# Contributing to google-workspace-tools

Thank you for your interest in contributing to google-workspace-tools! This document provides guidelines and instructions for contributing to this project.

## Code of Conduct

This project adheres to the [Contributor Covenant Code of Conduct](CODE_OF_CONDUCT.md). By participating, you are expected to uphold this code.

## Getting Started

### Development Setup

1. **Fork and clone the repository**

   ```bash
   git clone https://github.com/YOUR-USERNAME/google-workspace-tools.git
   cd google-workspace-tools
   ```

2. **Install dependencies with uv**

   This project uses [uv](https://github.com/astral-sh/uv) for dependency management:

   ```bash
   # Install uv if you don't have it
   curl -LsSf https://astral.sh/uv/install.sh | sh

   # Install project dependencies (including dev dependencies)
   uv sync --group dev
   ```

3. **Install pre-commit hooks**

   ```bash
   uv run pre-commit install
   ```

### Development Workflow

#### Running Tests

```bash
# Run all tests
uv run pytest

# Run tests with coverage
uv run pytest --cov=src --cov-report=term-missing

# Run specific test file
uv run pytest tests/unit/test_exporter.py

# Run with specific markers
uv run pytest -m unit
```

#### Linting and Formatting

```bash
# Run linter
uv run ruff check src/

# Auto-fix linting issues
uv run ruff check --fix src/

# Format code
uv run ruff format src/

# Check formatting without making changes
uv run ruff format --check src/
```

#### Type Checking

```bash
# Run type checker
uv run mypy src/
```

#### Running All Quality Checks

```bash
# Run all checks (what CI runs)
uv run ruff check src/
uv run ruff format --check src/
uv run mypy src/
uv run pytest --cov=src
```

### Making Changes

1. **Create a new branch**

   ```bash
   git checkout -b feature/your-feature-name
   # or
   git checkout -b fix/your-bug-fix
   ```

2. **Make your changes**
   - Follow the coding standards (see below)
   - Add tests for new functionality
   - Update documentation as needed

3. **Ensure all quality checks pass**

   ```bash
   uv run ruff check src/
   uv run mypy src/
   uv run pytest
   ```

4. **Commit your changes**

   We use [Conventional Commits](https://www.conventionalcommits.org/):

   ```bash
   # Format: <type>: <description>
   # Types: feat, fix, docs, style, refactor, test, chore

   git add .
   git commit -m "feat: add spreadsheet comment export support"
   # or
   git commit -m "fix: handle missing credentials gracefully"
   # or
   git commit -m "docs: update installation instructions"
   ```

5. **Push to your fork and create a pull request**

   ```bash
   git push origin feature/your-feature-name
   ```

   Then go to GitHub and create a pull request against the `main` branch.

## Coding Standards

### General Principles

- **Follow SOLID principles** - Keep classes focused, extensible, and maintainable
- **Don't over-engineer** - Simple, straightforward solutions are preferred
- **Write self-documenting code** - Clear variable names and function signatures

### Python Style

- **Line length**: Maximum 120 characters
- **Formatting**: Use `ruff format` (enforced by CI)
- **Linting**: Follow `ruff` rules (E, F, W, I, B, UP, PT, SIM)
- **Type hints**: Required for all function signatures
- **Docstrings**: Use for public APIs and complex functions

### Code Organization

```
src/google_workspace_tools/
├── __init__.py          # Public API exports
├── settings.py          # Pydantic settings (GWT_ env prefix)
├── core/                # Core business logic
│   ├── types.py         # Type definitions
│   ├── config.py        # Configuration classes
│   └── exporter.py      # Main export logic
├── cli/                 # CLI application
│   └── app.py           # Typer CLI
└── toolkit/             # Optional integrations
    └── gdrive.py        # Agno toolkit (optional)
```

### Testing

- **Unit tests**: Test individual components in isolation
- **E2E tests**: Test CLI commands and integration
- **Coverage**: Aim for 70%+ coverage on new code
- **Mocking**: Use mocks for external APIs (Google Drive)

Example test structure:

```python
import pytest
from google_workspace_tools import GoogleDriveExporter

def test_extract_document_id():
    """Test document ID extraction from URLs."""
    exporter = GoogleDriveExporter()
    url = "https://docs.google.com/document/d/abc123/edit"
    assert exporter.extract_document_id(url) == "abc123"

@pytest.mark.integration
def test_full_export_workflow():
    """Test complete export workflow (requires credentials)."""
    # Integration test here
    pass
```

## Pull Request Process

1. **Ensure your PR**:
   - Has a clear, descriptive title
   - References any related issues (`Fixes #123`)
   - Includes tests for new functionality
   - Passes all CI checks (linting, type checking, tests)
   - Updates documentation if needed

2. **PR Review**:
   - At least one maintainer approval required
   - All CI checks must pass
   - Address reviewer feedback
   - Keep commits clean and focused

3. **After Merge**:
   - Delete your feature branch
   - Pull the latest `main` branch

## Reporting Bugs

1. **Search existing issues** to avoid duplicates
2. **Use the bug report template** when creating a new issue
3. **Include**:
   - Clear description of the problem
   - Steps to reproduce
   - Expected vs actual behavior
   - Environment details (Python version, OS)
   - Relevant logs or error messages

## Requesting Features

1. **Search existing issues** for similar requests
2. **Use the feature request template**
3. **Explain**:
   - The problem you're trying to solve
   - Your proposed solution
   - Alternative approaches considered
   - Potential impact on existing functionality

## Development Tips

### Authentication Testing

For testing OAuth flows locally:

```bash
# Set up test credentials
cp .client_secret.googleusercontent.com.json.example .client_secret.googleusercontent.com.json
# Edit with your test credentials

# Run auth command
uv run gwt auth

# Test with a document
uv run gwt download https://docs.google.com/document/d/... -f md
```

### Debugging

Enable debug logging:

```bash
# CLI debugging
uv run gwt download URL -vv  # Very verbose

# Or set environment variable
export GWT_LOG_LEVEL=DEBUG
uv run gwt download URL
```

### Working with Dependencies

```bash
# Add a new dependency
# Edit pyproject.toml, then:
uv sync

# Update dependencies
uv sync --upgrade

# Add a dev dependency
# Add to [dependency-groups] dev in pyproject.toml, then:
uv sync --group dev
```

## Release Process

(For maintainers only)

1. Update version in `pyproject.toml`
2. Update `CHANGELOG.md`
3. Create and push a version tag:
   ```bash
   git tag -a v0.2.0 -m "Release v0.2.0"
   git push origin v0.2.0
   ```
4. GitHub Actions will automatically:
   - Build the package
   - Publish to PyPI
   - Create a GitHub release

## Questions?

- **GitHub Discussions**: For general questions and discussions
- **GitHub Issues**: For bugs and feature requests
- **Security Issues**: See [SECURITY.md](SECURITY.md) for reporting security vulnerabilities

## License

By contributing, you agree that your contributions will be licensed under the Apache License 2.0.
