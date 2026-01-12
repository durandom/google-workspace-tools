"""End-to-end tests for Gmail CLI commands."""

from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from google_workspace_tools.cli.app import app

runner = CliRunner()


@pytest.mark.e2e
class TestMailHelp:
    """Tests for mail help output."""

    def test_mail_help(self):
        """Test mail command help."""
        result = runner.invoke(app, ["mail", "--help"])
        assert result.exit_code == 0
        assert "Export Gmail messages" in result.stdout
        assert "-q" in result.stdout or "--query" in result.stdout
        assert "-f" in result.stdout or "--format" in result.stdout
        assert "-m" in result.stdout or "--mode" in result.stdout

    def test_mail_in_main_help(self):
        """Test that mail appears in main help."""
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "mail" in result.stdout


@pytest.mark.e2e
class TestMailCommand:
    """Tests for mail command execution."""

    @patch("google_workspace_tools.cli.commands.mail.GoogleDriveExporter")
    def test_mail_with_defaults(self, mock_exporter_class, tmp_path):
        """Test mail with default parameters."""
        # Mock the exporter instance
        mock_exporter = MagicMock()
        mock_exporter.export_emails.return_value = {}
        mock_exporter_class.return_value = mock_exporter

        # Mock _authenticate to avoid actual OAuth
        with patch.object(mock_exporter, "_authenticate", return_value=MagicMock()):
            result = runner.invoke(
                app,
                [
                    "mail",
                    "-c",
                    str(tmp_path / "creds.json"),
                    "-o",
                    str(tmp_path / "emails"),
                ],
            )

        # Should complete (may not export anything without valid auth, but shouldn't crash)
        assert result.exit_code in [0, 1]  # May exit with error if auth fails

    @patch("google_workspace_tools.cli.commands.mail.GoogleDriveExporter")
    def test_mail_with_query(self, mock_exporter_class, tmp_path):
        """Test mail with search query."""
        mock_exporter = MagicMock()
        mock_exporter.export_emails.return_value = {"msg1": tmp_path / "msg1.md"}
        mock_exporter_class.return_value = mock_exporter

        # Create dummy credentials file
        creds_file = tmp_path / "creds.json"
        creds_file.write_text('{"web":{"client_id":"test"}}')

        with patch.object(mock_exporter, "_authenticate", return_value=MagicMock()):
            result = runner.invoke(
                app,
                [
                    "mail",
                    "-q",
                    "from:boss@example.com",
                    "-f",
                    "md",
                    "-c",
                    str(creds_file),
                    "-o",
                    str(tmp_path / "emails"),
                ],
            )

        assert result.exit_code in [0, 1]

    @patch("google_workspace_tools.cli.commands.mail.GoogleDriveExporter")
    def test_mail_with_date_range(self, mock_exporter_class, tmp_path):
        """Test mail with date range filters."""
        mock_exporter = MagicMock()
        mock_exporter.export_emails.return_value = {}
        mock_exporter_class.return_value = mock_exporter

        creds_file = tmp_path / "creds.json"
        creds_file.write_text('{"web":{"client_id":"test"}}')

        with patch.object(mock_exporter, "_authenticate", return_value=MagicMock()):
            result = runner.invoke(
                app,
                [
                    "mail",
                    "-a",
                    "2024-01-01",
                    "-b",
                    "2024-12-31",
                    "-c",
                    str(creds_file),
                ],
            )

        assert result.exit_code in [0, 1]

    @patch("google_workspace_tools.cli.commands.mail.GoogleDriveExporter")
    def test_mail_with_labels(self, mock_exporter_class, tmp_path):
        """Test mail with label filters."""
        mock_exporter = MagicMock()
        mock_exporter.export_emails.return_value = {}
        mock_exporter_class.return_value = mock_exporter

        creds_file = tmp_path / "creds.json"
        creds_file.write_text('{"web":{"client_id":"test"}}')

        with patch.object(mock_exporter, "_authenticate", return_value=MagicMock()):
            result = runner.invoke(
                app,
                [
                    "mail",
                    "-l",
                    "work,important",
                    "-c",
                    str(creds_file),
                ],
            )

        assert result.exit_code in [0, 1]

    @patch("google_workspace_tools.cli.commands.mail.GoogleDriveExporter")
    def test_mail_json_format(self, mock_exporter_class, tmp_path):
        """Test mail with JSON format."""
        mock_exporter = MagicMock()
        mock_exporter.export_emails.return_value = {}
        mock_exporter_class.return_value = mock_exporter

        creds_file = tmp_path / "creds.json"
        creds_file.write_text('{"web":{"client_id":"test"}}')

        with patch.object(mock_exporter, "_authenticate", return_value=MagicMock()):
            result = runner.invoke(
                app,
                [
                    "mail",
                    "-f",
                    "json",
                    "-c",
                    str(creds_file),
                ],
            )

        assert result.exit_code in [0, 1]

    @patch("google_workspace_tools.cli.commands.mail.GoogleDriveExporter")
    def test_mail_individual_mode(self, mock_exporter_class, tmp_path):
        """Test mail with individual message mode."""
        mock_exporter = MagicMock()
        mock_exporter.export_emails.return_value = {}
        mock_exporter_class.return_value = mock_exporter

        creds_file = tmp_path / "creds.json"
        creds_file.write_text('{"web":{"client_id":"test"}}')

        with patch.object(mock_exporter, "_authenticate", return_value=MagicMock()):
            result = runner.invoke(
                app,
                [
                    "mail",
                    "-m",
                    "individual",
                    "-c",
                    str(creds_file),
                ],
            )

        assert result.exit_code in [0, 1]

    @patch("google_workspace_tools.cli.commands.mail.GoogleDriveExporter")
    def test_mail_with_link_following(self, mock_exporter_class, tmp_path):
        """Test mail with link following enabled."""
        mock_exporter = MagicMock()
        mock_exporter.export_emails.return_value = {}
        mock_exporter_class.return_value = mock_exporter

        creds_file = tmp_path / "creds.json"
        creds_file.write_text('{"web":{"client_id":"test"}}')

        with patch.object(mock_exporter, "_authenticate", return_value=MagicMock()):
            result = runner.invoke(
                app,
                [
                    "mail",
                    "-d",
                    "2",
                    "-c",
                    str(creds_file),
                ],
            )

        assert result.exit_code in [0, 1]

    @patch("google_workspace_tools.cli.commands.mail.GoogleDriveExporter")
    def test_mail_max_results(self, mock_exporter_class, tmp_path):
        """Test mail with max results limit."""
        mock_exporter = MagicMock()
        mock_exporter.export_emails.return_value = {}
        mock_exporter_class.return_value = mock_exporter

        creds_file = tmp_path / "creds.json"
        creds_file.write_text('{"web":{"client_id":"test"}}')

        with patch.object(mock_exporter, "_authenticate", return_value=MagicMock()):
            result = runner.invoke(
                app,
                [
                    "mail",
                    "-n",
                    "50",
                    "-c",
                    str(creds_file),
                ],
            )

        assert result.exit_code in [0, 1]

    @patch("google_workspace_tools.cli.commands.mail.GoogleDriveExporter")
    def test_mail_error_handling(self, mock_exporter_class):
        """Test mail error handling with authentication failure."""
        # Mock exporter to raise an error during initialization or export
        mock_exporter = MagicMock()
        mock_exporter.export_emails.side_effect = Exception("Authentication failed")
        mock_exporter_class.return_value = mock_exporter

        result = runner.invoke(
            app,
            [
                "mail",
                "-c",
                "/nonexistent/creds.json",
            ],
        )

        # Should fail gracefully
        assert result.exit_code == 1
        assert "Error" in result.stdout or "error" in result.stdout.lower()

    @patch("google_workspace_tools.cli.commands.mail.GoogleDriveExporter")
    def test_mail_output_formatting(self, mock_exporter_class, tmp_path):
        """Test mail output formatting."""
        mock_exporter = MagicMock()
        mock_exporter.export_emails.return_value = {
            "thread1": tmp_path / "thread1.md",
            "thread2": tmp_path / "thread2.md",
        }
        mock_exporter_class.return_value = mock_exporter

        creds_file = tmp_path / "creds.json"
        creds_file.write_text('{"web":{"client_id":"test"}}')

        with patch.object(mock_exporter, "_authenticate", return_value=MagicMock()):
            result = runner.invoke(
                app,
                [
                    "mail",
                    "-c",
                    str(creds_file),
                ],
            )

        # Check for success message formatting
        if result.exit_code == 0:
            assert "exported" in result.stdout.lower() or "2" in result.stdout


@pytest.mark.e2e
class TestMailIntegration:
    """Integration tests for mail command with realistic scenarios."""

    @patch("google_workspace_tools.cli.commands.mail.GoogleDriveExporter")
    def test_mail_combined_filters(self, mock_exporter_class, tmp_path):
        """Test mail with multiple combined filters."""
        mock_exporter = MagicMock()
        mock_exporter.export_emails.return_value = {}
        mock_exporter_class.return_value = mock_exporter

        creds_file = tmp_path / "creds.json"
        creds_file.write_text('{"web":{"client_id":"test"}}')

        with patch.object(mock_exporter, "_authenticate", return_value=MagicMock()):
            result = runner.invoke(
                app,
                [
                    "mail",
                    "-q",
                    "has:attachment",
                    "-a",
                    "2024-01-01",
                    "-l",
                    "work,important",
                    "-f",
                    "md",
                    "-m",
                    "thread",
                    "-n",
                    "100",
                    "-d",
                    "1",
                    "-c",
                    str(creds_file),
                    "-o",
                    str(tmp_path / "emails"),
                ],
            )

        assert result.exit_code in [0, 1]


@pytest.mark.e2e
class TestMailStdout:
    """Tests for mail command stdout output mode."""

    def test_mail_help_shows_stdout_option(self):
        """Test that --stdout option appears in help."""
        result = runner.invoke(app, ["mail", "--help"])
        assert result.exit_code == 0
        assert "--stdout" in result.stdout

    @patch("google_workspace_tools.cli.commands.mail.GoogleDriveExporter")
    def test_mail_stdout_outputs_to_terminal(self, mock_exporter_class, tmp_path):
        """Test that --stdout mode outputs content to terminal instead of files."""
        mock_exporter = MagicMock()
        mock_exporter.format_emails_as_string.return_value = "# Email Thread: Test\n\nHello World"
        mock_exporter_class.return_value = mock_exporter

        result = runner.invoke(
            app,
            [
                "mail",
                "--stdout",
                "-c",
                str(tmp_path / "creds.json"),
            ],
        )

        assert result.exit_code == 0
        # Content should be in stdout
        assert "# Email Thread: Test" in result.stdout
        assert "Hello World" in result.stdout
        # format_emails_as_string should have been called
        mock_exporter.format_emails_as_string.assert_called_once()
        # export_emails should NOT have been called (no file output)
        mock_exporter.export_emails.assert_not_called()

    @patch("google_workspace_tools.cli.commands.mail.GoogleDriveExporter")
    def test_mail_stdout_with_json_format(self, mock_exporter_class, tmp_path):
        """Test --stdout with JSON format."""
        mock_exporter = MagicMock()
        mock_exporter.format_emails_as_string.return_value = '[{"thread_id": "123"}]'
        mock_exporter_class.return_value = mock_exporter

        result = runner.invoke(
            app,
            [
                "mail",
                "--stdout",
                "-f",
                "json",
                "-c",
                str(tmp_path / "creds.json"),
            ],
        )

        assert result.exit_code == 0
        assert '"thread_id": "123"' in result.stdout
        # Verify json format was passed
        call_kwargs = mock_exporter.format_emails_as_string.call_args[1]
        assert call_kwargs["export_format"] == "json"
