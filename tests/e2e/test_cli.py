"""End-to-end tests for CLI commands."""

from typer.testing import CliRunner

from google_workspace_tools.cli.app import app

runner = CliRunner()


class TestCLIHelp:
    """Tests for CLI help output."""

    def test_main_help(self):
        """Test main help output."""
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "Google Workspace Tools" in result.stdout
        assert "download" in result.stdout
        assert "mirror" in result.stdout
        assert "auth" in result.stdout

    def test_download_help(self):
        """Test download command help."""
        result = runner.invoke(app, ["download", "--help"])
        assert result.exit_code == 0
        assert "Download one or more Google Drive documents" in result.stdout
        assert "--format" in result.stdout
        assert "--output" in result.stdout

    def test_mirror_help(self):
        """Test mirror command help."""
        result = runner.invoke(app, ["mirror", "--help"])
        assert result.exit_code == 0
        assert "Mirror documents from a configuration file" in result.stdout

    def test_auth_help(self):
        """Test auth command help."""
        result = runner.invoke(app, ["auth", "--help"])
        assert result.exit_code == 0
        assert "Authenticate with Google Drive API" in result.stdout

    def test_formats_help(self):
        """Test formats command help."""
        result = runner.invoke(app, ["formats", "--help"])
        assert result.exit_code == 0
        assert "List supported export formats" in result.stdout


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


class TestDownloadCommand:
    """Tests for download command (without actual API calls)."""

    def test_download_reports_errors(self, tmp_path):
        """Test that download reports errors gracefully."""
        result = runner.invoke(
            app,
            [
                "download",
                "abc123",
                "-c",
                str(tmp_path / "nonexistent.json"),
                "-o",
                str(tmp_path / "output"),
            ],
        )
        # The command completes but reports no documents exported
        assert result.exit_code == 0
        assert "No documents were exported" in result.stdout or "0 document" in result.stdout


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
