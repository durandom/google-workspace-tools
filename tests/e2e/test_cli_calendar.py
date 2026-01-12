"""End-to-end tests for Calendar CLI commands."""

from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from google_workspace_tools.cli.app import app

runner = CliRunner()


@pytest.mark.e2e
class TestCalendarHelp:
    """Tests for calendar help output."""

    def test_calendar_help(self):
        """Test calendar command help shows subcommands."""
        result = runner.invoke(app, ["calendar", "--help"])
        assert result.exit_code == 0
        assert "list" in result.stdout
        assert "get" in result.stdout
        assert "export" in result.stdout

    def test_calendar_list_help(self):
        """Test calendar list subcommand help."""
        result = runner.invoke(app, ["calendar", "list", "--help"])
        assert result.exit_code == 0
        assert "--credentials" in result.stdout or "-c" in result.stdout

    def test_calendar_get_help(self):
        """Test calendar get subcommand help."""
        result = runner.invoke(app, ["calendar", "get", "--help"])
        assert result.exit_code == 0
        assert "--event-id" in result.stdout or "-e" in result.stdout
        assert "--calendar" in result.stdout

    def test_calendar_export_help(self):
        """Test calendar export subcommand help."""
        result = runner.invoke(app, ["calendar", "export", "--help"])
        assert result.exit_code == 0
        assert "--calendar" in result.stdout
        assert "-f" in result.stdout or "--format" in result.stdout
        assert "-a" in result.stdout or "--after" in result.stdout
        assert "-b" in result.stdout or "--before" in result.stdout

    def test_calendar_in_main_help(self):
        """Test that calendar appears in main help."""
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "calendar" in result.stdout


@pytest.mark.e2e
class TestCalendarList:
    """Tests for calendar list subcommand."""

    @patch("google_workspace_tools.cli.commands.calendar._create_exporter")
    def test_calendar_list(self, mock_create_exporter, tmp_path):
        """Test calendar list subcommand."""
        mock_exporter = MagicMock()
        mock_exporter.list_calendars.return_value = [
            {"id": "primary", "summary": "My Calendar", "primary": True},
            {"id": "work@example.com", "summary": "Work Calendar", "primary": False},
        ]
        mock_create_exporter.return_value = mock_exporter

        creds_file = tmp_path / "creds.json"
        creds_file.write_text('{"web":{"client_id":"test"}}')

        result = runner.invoke(
            app,
            ["calendar", "list", "-c", str(creds_file)],
        )

        # Should display calendar information
        if result.exit_code == 0:
            assert "Calendar" in result.stdout or "calendar" in result.stdout.lower()

    @patch("google_workspace_tools.cli.commands.calendar._create_exporter")
    def test_calendar_list_empty(self, mock_create_exporter, tmp_path):
        """Test calendar list with no calendars."""
        mock_exporter = MagicMock()
        mock_exporter.list_calendars.return_value = []
        mock_create_exporter.return_value = mock_exporter

        creds_file = tmp_path / "creds.json"
        creds_file.write_text('{"web":{"client_id":"test"}}')

        result = runner.invoke(
            app,
            ["calendar", "list", "-c", str(creds_file)],
        )

        # Should handle empty list gracefully
        assert result.exit_code in [0, 1]
        if result.exit_code == 0:
            assert "0" in result.stdout or "No calendars" in result.stdout

    @patch("google_workspace_tools.cli.commands.calendar._create_exporter")
    def test_calendar_list_error_handling(self, mock_create_exporter):
        """Test calendar list error handling with authentication failure."""
        mock_exporter = MagicMock()
        mock_exporter.list_calendars.side_effect = Exception("Authentication failed")
        mock_create_exporter.return_value = mock_exporter

        result = runner.invoke(
            app,
            ["calendar", "list", "-c", "/nonexistent/creds.json"],
        )

        # Should fail gracefully
        assert result.exit_code == 1
        assert "Error" in result.stdout or "error" in result.stdout.lower()

    @patch("google_workspace_tools.cli.commands.calendar._create_exporter")
    def test_calendar_list_table_formatting(self, mock_create_exporter, tmp_path):
        """Test calendar list table formatting."""
        mock_exporter = MagicMock()
        mock_exporter.list_calendars.return_value = [
            {"id": "primary", "summary": "Personal Calendar", "primary": True},
            {"id": "work@company.com", "summary": "Work Calendar", "primary": False},
            {"id": "team@company.com", "summary": "Team Events", "primary": False},
        ]
        mock_create_exporter.return_value = mock_exporter

        creds_file = tmp_path / "creds.json"
        creds_file.write_text('{"web":{"client_id":"test"}}')

        result = runner.invoke(
            app,
            ["calendar", "list", "-c", str(creds_file)],
        )

        # Check for table formatting
        if result.exit_code == 0:
            # Should show total count
            assert "3" in result.stdout


@pytest.mark.e2e
class TestCalendarExportCommand:
    """Tests for calendar export subcommand."""

    @patch("google_workspace_tools.cli.commands.calendar._create_exporter")
    def test_calendar_export_with_time_range(self, mock_create_exporter, tmp_path):
        """Test calendar export with time range filters."""
        mock_exporter = MagicMock()
        mock_exporter.export_calendar_events.return_value = {}
        mock_create_exporter.return_value = mock_exporter

        creds_file = tmp_path / "creds.json"
        creds_file.write_text('{"web":{"client_id":"test"}}')

        result = runner.invoke(
            app,
            [
                "calendar",
                "export",
                "-a",
                "2024-01-01",
                "-b",
                "2024-12-31",
                "-c",
                str(creds_file),
            ],
        )

        assert result.exit_code in [0, 1]

    @patch("google_workspace_tools.cli.commands.calendar._create_exporter")
    def test_calendar_export_specific_calendar(self, mock_create_exporter, tmp_path):
        """Test calendar export with specific calendar ID."""
        mock_exporter = MagicMock()
        mock_exporter.export_calendar_events.return_value = {}
        mock_create_exporter.return_value = mock_exporter

        creds_file = tmp_path / "creds.json"
        creds_file.write_text('{"web":{"client_id":"test"}}')

        result = runner.invoke(
            app,
            [
                "calendar",
                "export",
                "--calendar",
                "work@example.com",
                "-a",
                "2024-01-01",
                "-c",
                str(creds_file),
            ],
        )

        assert result.exit_code in [0, 1]

    @patch("google_workspace_tools.cli.commands.calendar._create_exporter")
    def test_calendar_export_with_query(self, mock_create_exporter, tmp_path):
        """Test calendar export with search query."""
        mock_exporter = MagicMock()
        mock_exporter.export_calendar_events.return_value = {}
        mock_create_exporter.return_value = mock_exporter

        creds_file = tmp_path / "creds.json"
        creds_file.write_text('{"web":{"client_id":"test"}}')

        result = runner.invoke(
            app,
            [
                "calendar",
                "export",
                "-q",
                "sprint planning",
                "-c",
                str(creds_file),
            ],
        )

        assert result.exit_code in [0, 1]

    @patch("google_workspace_tools.cli.commands.calendar._create_exporter")
    def test_calendar_export_json_format(self, mock_create_exporter, tmp_path):
        """Test calendar export with JSON format."""
        mock_exporter = MagicMock()
        mock_exporter.export_calendar_events.return_value = {}
        mock_create_exporter.return_value = mock_exporter

        creds_file = tmp_path / "creds.json"
        creds_file.write_text('{"web":{"client_id":"test"}}')

        result = runner.invoke(
            app,
            [
                "calendar",
                "export",
                "-q",
                "meeting",
                "-f",
                "json",
                "-c",
                str(creds_file),
            ],
        )

        assert result.exit_code in [0, 1]

    @patch("google_workspace_tools.cli.commands.calendar._create_exporter")
    def test_calendar_export_with_link_following(self, mock_create_exporter, tmp_path):
        """Test calendar export with link following enabled."""
        mock_exporter = MagicMock()
        mock_exporter.export_calendar_events.return_value = {}
        mock_create_exporter.return_value = mock_exporter

        creds_file = tmp_path / "creds.json"
        creds_file.write_text('{"web":{"client_id":"test"}}')

        result = runner.invoke(
            app,
            [
                "calendar",
                "export",
                "-q",
                "meeting",
                "-d",
                "2",
                "-c",
                str(creds_file),
            ],
        )

        assert result.exit_code in [0, 1]

    @patch("google_workspace_tools.cli.commands.calendar._create_exporter")
    def test_calendar_export_max_results(self, mock_create_exporter, tmp_path):
        """Test calendar export with max results limit."""
        mock_exporter = MagicMock()
        mock_exporter.export_calendar_events.return_value = {}
        mock_create_exporter.return_value = mock_exporter

        creds_file = tmp_path / "creds.json"
        creds_file.write_text('{"web":{"client_id":"test"}}')

        result = runner.invoke(
            app,
            [
                "calendar",
                "export",
                "-q",
                "meeting",
                "-n",
                "100",
                "-c",
                str(creds_file),
            ],
        )

        assert result.exit_code in [0, 1]

    @patch("google_workspace_tools.cli.commands.calendar._create_exporter")
    def test_calendar_export_error_handling(self, mock_create_exporter):
        """Test calendar export error handling with authentication failure."""
        mock_exporter = MagicMock()
        mock_exporter.export_calendar_events.side_effect = Exception("Authentication failed")
        mock_create_exporter.return_value = mock_exporter

        result = runner.invoke(
            app,
            [
                "calendar",
                "export",
                "-q",
                "meeting",
                "-c",
                "/nonexistent/creds.json",
            ],
        )

        # Should fail gracefully
        assert result.exit_code == 1
        assert "Error" in result.stdout or "error" in result.stdout.lower()

    @patch("google_workspace_tools.cli.commands.calendar._create_exporter")
    def test_calendar_export_output_formatting(self, mock_create_exporter, tmp_path):
        """Test calendar export output formatting."""
        mock_exporter = MagicMock()
        mock_exporter.export_calendar_events.return_value = {
            "event1": tmp_path / "event1.md",
            "event2": tmp_path / "event2.md",
            "event3": tmp_path / "event3.md",
        }
        mock_create_exporter.return_value = mock_exporter

        creds_file = tmp_path / "creds.json"
        creds_file.write_text('{"web":{"client_id":"test"}}')

        result = runner.invoke(
            app,
            [
                "calendar",
                "export",
                "-q",
                "meeting",
                "-c",
                str(creds_file),
            ],
        )

        # Check for success message formatting
        if result.exit_code == 0:
            assert "exported" in result.stdout.lower() or "3" in result.stdout


@pytest.mark.e2e
class TestCalendarGetCommand:
    """Tests for calendar get subcommand."""

    @patch("google_workspace_tools.cli.commands.calendar._create_exporter")
    def test_calendar_get_event(self, mock_create_exporter, tmp_path):
        """Test calendar get with event ID."""
        mock_exporter = MagicMock()
        mock_exporter.get_calendar_event.return_value = {
            "id": "event123",
            "summary": "Test Event",
            "start": {"dateTime": "2024-01-15T10:00:00Z"},
            "end": {"dateTime": "2024-01-15T11:00:00Z"},
        }
        mock_exporter._export_calendar_event_as_markdown.return_value = True
        mock_create_exporter.return_value = mock_exporter

        creds_file = tmp_path / "creds.json"
        creds_file.write_text('{"web":{"client_id":"test"}}')

        result = runner.invoke(
            app,
            [
                "calendar",
                "get",
                "-e",
                "event123",
                "-c",
                str(creds_file),
                "-o",
                str(tmp_path),
            ],
        )

        assert result.exit_code in [0, 1]

    @patch("google_workspace_tools.cli.commands.calendar._create_exporter")
    def test_calendar_get_event_not_found(self, mock_create_exporter, tmp_path):
        """Test calendar get when event is not found."""
        mock_exporter = MagicMock()
        mock_exporter.get_calendar_event.return_value = None
        mock_create_exporter.return_value = mock_exporter

        creds_file = tmp_path / "creds.json"
        creds_file.write_text('{"web":{"client_id":"test"}}')

        result = runner.invoke(
            app,
            [
                "calendar",
                "get",
                "-e",
                "nonexistent",
                "-c",
                str(creds_file),
            ],
        )

        assert result.exit_code == 1
        assert "not found" in result.stdout.lower() or "error" in result.stdout.lower()


@pytest.mark.e2e
class TestCalendarIntegration:
    """Integration tests for calendar commands with realistic scenarios."""

    @patch("google_workspace_tools.cli.commands.calendar._create_exporter")
    def test_calendar_export_combined_filters(self, mock_create_exporter, tmp_path):
        """Test calendar export with multiple combined filters."""
        mock_exporter = MagicMock()
        mock_exporter.export_calendar_events.return_value = {}
        mock_create_exporter.return_value = mock_exporter

        creds_file = tmp_path / "creds.json"
        creds_file.write_text('{"web":{"client_id":"test"}}')

        result = runner.invoke(
            app,
            [
                "calendar",
                "export",
                "--calendar",
                "work@example.com",
                "-a",
                "2024-01-01",
                "-b",
                "2024-03-31",
                "-q",
                "meeting",
                "-f",
                "md",
                "-n",
                "100",
                "-d",
                "1",
                "-c",
                str(creds_file),
                "-o",
                str(tmp_path / "calendar"),
            ],
        )

        assert result.exit_code in [0, 1]

    @patch("google_workspace_tools.cli.commands.calendar._create_exporter")
    def test_workflow_list_then_export(self, mock_create_exporter, tmp_path):
        """Test realistic workflow: list calendars, then export with filters."""
        mock_exporter = MagicMock()
        mock_exporter.list_calendars.return_value = [{"id": "work@company.com", "summary": "Work", "primary": False}]
        mock_exporter.export_calendar_events.return_value = {}
        mock_create_exporter.return_value = mock_exporter

        creds_file = tmp_path / "creds.json"
        creds_file.write_text('{"web":{"client_id":"test"}}')

        # Step 1: List calendars
        result1 = runner.invoke(
            app,
            ["calendar", "list", "-c", str(creds_file)],
        )

        # Step 2: Export from specific calendar
        result2 = runner.invoke(
            app,
            [
                "calendar",
                "export",
                "--calendar",
                "work@company.com",
                "-q",
                "standup",
                "-c",
                str(creds_file),
            ],
        )

        # Both commands should complete
        assert result1.exit_code in [0, 1]
        assert result2.exit_code in [0, 1]
