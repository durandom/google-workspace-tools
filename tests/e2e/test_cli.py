"""End-to-end tests for CLI commands."""

from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from google_workspace_tools.cli.app import app

runner = CliRunner()


@pytest.mark.e2e
class TestCLIHelp:
    """Tests for CLI help output."""

    def test_main_help(self):
        """Test main help output."""
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "Google Workspace Tools" in result.stdout
        assert "download" in result.stdout
        assert "mirror" in result.stdout
        assert "credentials" in result.stdout

    def test_download_help(self):
        """Test download command help."""
        result = runner.invoke(app, ["download", "--help"])
        assert result.exit_code == 0
        assert "Download one or more Google Drive documents" in result.stdout
        # Check for short options since Rich formatting may wrap long option names
        assert "-f" in result.stdout  # --format
        assert "-o" in result.stdout  # --output

    def test_mirror_help(self):
        """Test mirror command help."""
        result = runner.invoke(app, ["mirror", "--help"])
        assert result.exit_code == 0
        assert "Mirror documents from a configuration file" in result.stdout

    def test_credentials_help(self):
        """Test credentials command help."""
        result = runner.invoke(app, ["credentials", "--help"])
        assert result.exit_code == 0
        assert "Manage Google OAuth credentials" in result.stdout
        assert "login" in result.stdout
        assert "logout" in result.stdout
        assert "status" in result.stdout

    def test_formats_help(self):
        """Test formats command help."""
        result = runner.invoke(app, ["formats", "--help"])
        assert result.exit_code == 0
        assert "List supported export formats" in result.stdout


@pytest.mark.e2e
class TestVersionCommand:
    """Tests for version command."""

    def test_version_command(self):
        """Test version command output."""
        result = runner.invoke(app, ["version"])
        assert result.exit_code == 0
        assert "google-workspace-tools" in result.stdout
        assert "0.1.0" in result.stdout

    def test_version_flag(self):
        """Test --version flag."""
        result = runner.invoke(app, ["--version"])
        assert result.exit_code == 0
        assert "google-workspace-tools" in result.stdout


@pytest.mark.e2e
class TestFormatsCommand:
    """Tests for formats command."""

    def test_formats_document(self):
        """Test formats for documents."""
        result = runner.invoke(app, ["formats"])
        assert result.exit_code == 0
        assert "pdf" in result.stdout
        assert "md" in result.stdout
        assert "docx" in result.stdout

    def test_formats_spreadsheet(self):
        """Test formats for spreadsheets."""
        result = runner.invoke(app, ["formats", "-t", "spreadsheet"])
        assert result.exit_code == 0
        assert "xlsx" in result.stdout
        assert "csv" in result.stdout

    def test_formats_presentation(self):
        """Test formats for presentations."""
        result = runner.invoke(app, ["formats", "-t", "presentation"])
        assert result.exit_code == 0
        assert "pptx" in result.stdout
        assert "odp" in result.stdout

    def test_formats_json_output(self):
        """Test JSON output format."""
        result = runner.invoke(app, ["formats", "--json"])
        assert result.exit_code == 0
        assert '"document_type"' in result.stdout
        assert '"formats"' in result.stdout


@pytest.mark.e2e
class TestExtractIdCommand:
    """Tests for extract-id command."""

    def test_extract_id_from_docs_url(self):
        """Test extracting ID from a Google Docs URL."""
        result = runner.invoke(
            app,
            ["extract-id", "https://docs.google.com/document/d/abc123xyz/edit"],
        )
        assert result.exit_code == 0
        assert "abc123xyz" in result.stdout
        assert "document" in result.stdout.lower()

    def test_extract_id_from_sheets_url(self):
        """Test extracting ID from a Google Sheets URL."""
        result = runner.invoke(
            app,
            ["extract-id", "https://docs.google.com/spreadsheets/d/sheet456/edit"],
        )
        assert result.exit_code == 0
        assert "sheet456" in result.stdout
        assert "spreadsheet" in result.stdout.lower()

    def test_extract_id_invalid_url(self):
        """Test error handling for invalid URLs."""
        result = runner.invoke(
            app,
            ["extract-id", "https://example.com/not-a-drive-url"],
        )
        assert result.exit_code == 1
        assert "Error" in result.stdout


@pytest.mark.e2e
class TestDownloadCommand:
    """Tests for download command (without actual API calls)."""

    @patch("google_workspace_tools.cli.commands.download.GoogleDriveExporter")
    def test_download_reports_errors(self, mock_exporter_class, tmp_path):
        """Test that download reports errors gracefully when export fails."""
        # Setup mock exporter to return empty results (simulating export failure)
        mock_exporter = MagicMock()
        mock_exporter.export_document.return_value = {}  # Empty = no files exported
        mock_exporter.export_multiple.return_value = {}
        mock_exporter.extract_document_id.return_value = "abc123"
        mock_exporter.detect_document_type.return_value = "document"
        mock_exporter.get_document_metadata.return_value = {
            "name": "Test Doc",
            "mimeType": "application/vnd.google-apps.document",
        }
        mock_exporter_class.return_value = mock_exporter

        result = runner.invoke(
            app,
            [
                "download",
                "abc123",
                "-c",
                str(tmp_path / "creds.json"),
                "-o",
                str(tmp_path / "output"),
            ],
        )
        # The command exits with error code when no documents are exported
        assert result.exit_code == 1
        assert "not exported" in result.stdout or "error" in result.stdout.lower()


@pytest.mark.e2e
class TestMirrorCommand:
    """Tests for mirror command."""

    def test_mirror_missing_config(self, tmp_path):
        """Test error when config file is missing."""
        result = runner.invoke(
            app,
            ["mirror", str(tmp_path / "nonexistent.yaml")],
        )
        assert result.exit_code == 1
        assert "not found" in result.stdout.lower()
