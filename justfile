# justfile for google-workspace-tools

# List available recipes
default:
    @just --list

# Install dependencies
install:
    uv sync --group dev

# Run tests
test:
    uv run pytest

# Run tests with coverage
test-cov:
    uv run pytest --cov=src --cov-report=term-missing

# Run linting
lint:
    uv run ruff check
    uv run ruff format --check

# Fix linting issues
lint-fix:
    uv run ruff check --fix
    uv run ruff format

# Run type checking
typecheck:
    uv run mypy src/

# Run all checks (lint, typecheck, test)
check: lint typecheck test

# Dump CLI schema as JSON
dump-schema:
    uv run gwt dump-schema

# Dump CLI schema as YAML
dump-schema-yaml:
    uv run gwt dump-schema -f yaml

# Dump CLI schema to file
dump-schema-file OUTPUT="docs/cli-schema.json":
    uv run gwt dump-schema > {{OUTPUT}}

# Show all CLI commands with descriptions
show-commands:
    @uv run gwt --help

# Show help for a specific command
show-command CMD:
    @uv run gwt {{CMD}} --help

# Run the CLI
run *ARGS:
    uv run gwt {{ARGS}}

# Build the package
build:
    uv build

# Clean build artifacts
clean:
    rm -rf dist/ build/ *.egg-info .pytest_cache .coverage htmlcov/
    find . -type d -name __pycache__ -exec rm -rf {} +
    find . -type f -name "*.pyc" -delete

# Show version
version:
    uv run gwt version
