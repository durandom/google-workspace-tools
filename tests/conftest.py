"""Pytest fixtures for Google Workspace Tools tests."""

from pathlib import Path

import pytest


@pytest.fixture
def temp_output_dir(tmp_path: Path) -> Path:
    """Provide temporary output directory."""
    output = tmp_path / "exports"
    output.mkdir()
    return output


@pytest.fixture
def mock_credentials_file(tmp_path: Path) -> Path:
    """Create a mock credentials file."""
    creds = tmp_path / "credentials.json"
    creds.write_text('{"installed": {"client_id": "test", "client_secret": "test"}}')
    return creds


@pytest.fixture
def sample_config_file(tmp_path: Path) -> Path:
    """Create a sample mirror configuration file."""
    config = tmp_path / "sources.txt"
    config.write_text("""# Sample mirror configuration
https://docs.google.com/document/d/abc123/edit depth=0 # Test doc 1
https://docs.google.com/spreadsheets/d/xyz789/edit # Test spreadsheet
""")
    return config
