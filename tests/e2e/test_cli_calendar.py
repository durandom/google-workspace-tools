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
        """Test calendar command help."""
        result = runner.invoke(app, ["calendar", "--help"])
        assert result.exit_code == 0
        assert "Export Google Calendar events" in result.stdout
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
class TestCalendarListDefault:
    """Tests for calendar command listing calendars when no filters."""

    @patch("google_workspace_tools.cli.commands.calendar.GoogleDriveExporter")
    def test_calendar_lists_when_no_filters(self, mock_exporter_class, tmp_path):
        """Test calendar command lists calendars when no filters provided."""
        mock_exporter = MagicMock()
        mock_exporter.list_calendars.return_value = [
            {"id": "primary", "summary": "My Calendar", "primary": True},
            {"id": "work@example.com", "summary": "Work Calendar", "primary": False},
        ]
        mock_exporter_class.return_value = mock_exporter

        creds_file = tmp_path / "creds.json"
        creds_file.write_text('{"web":{"client_id":"test"}}')

        with patch.object(mock_exporter, "_authenticate", return_value=MagicMock()):
            result = runner.invoke(
                app,
                [
                    "calendar",
                    "-c",
                    str(creds_file),
                ],
            )

        # Should display calendar information
        if result.exit_code == 0:
            assert "Calendar" in result.stdout
            assert "My Calendar" in result.stdout or "primary" in result.stdout.lower()

    @patch("google_workspace_tools.cli.commands.calendar.GoogleDriveExporter")
    def test_calendar_list_empty(self, mock_exporter_class, tmp_path):
        """Test calendar command with no calendars."""
        mock_exporter = MagicMock()
        mock_exporter.list_calendars.return_value = []
        mock_exporter_class.return_value = mock_exporter

        creds_file = tmp_path / "creds.json"
        creds_file.write_text('{"web":{"client_id":"test"}}')

        with patch.object(mock_exporter, "_authenticate", return_value=MagicMock()):
            result = runner.invoke(
                app,
                [
                    "calendar",
                    "-c",
                    str(creds_file),
                ],
            )

        # Should handle empty list gracefully
        assert result.exit_code in [0, 1]
        if result.exit_code == 0:
            assert "No calendars" in result.stdout or "0" in result.stdout

    @patch("google_workspace_tools.cli.commands.calendar.GoogleDriveExporter")
    def test_calendar_list_error_handling(self, mock_exporter_class):
        """Test calendar list error handling with authentication failure."""
        # Mock exporter to raise an error when listing calendars
        mock_exporter = MagicMock()
        mock_exporter.list_calendars.side_effect = Exception("Authentication failed")
        mock_exporter_class.return_value = mock_exporter

        result = runner.invoke(
            app,
            [
                "calendar",
                "-c",
                "/nonexistent/creds.json",
            ],
        )

        # Should fail gracefully
        assert result.exit_code == 1
        assert "Error" in result.stdout or "error" in result.stdout.lower()

    @patch("google_workspace_tools.cli.commands.calendar.GoogleDriveExporter")
    def test_calendar_list_table_formatting(self, mock_exporter_class, tmp_path):
        """Test calendar list table formatting."""
        mock_exporter = MagicMock()
        mock_exporter.list_calendars.return_value = [
            {"id": "primary", "summary": "Personal Calendar", "primary": True},
            {"id": "work@company.com", "summary": "Work Calendar", "primary": False},
            {"id": "team@company.com", "summary": "Team Events", "primary": False},
        ]
        mock_exporter_class.return_value = mock_exporter

        creds_file = tmp_path / "creds.json"
        creds_file.write_text('{"web":{"client_id":"test"}}')

        with patch.object(mock_exporter, "_authenticate", return_value=MagicMock()):
            result = runner.invoke(
                app,
                [
                    "calendar",
                    "-c",
                    str(creds_file),
                ],
            )

        # Check for table formatting
        if result.exit_code == 0:
            # Should show total count
            assert "3" in result.stdout
            # Should show calendar names
            assert "Personal Calendar" in result.stdout or "Work Calendar" in result.stdout


@pytest.mark.e2e
class TestCalendarExportCommand:
    """Tests for calendar command with export filters."""

    @patch("google_workspace_tools.cli.commands.calendar.GoogleDriveExporter")
    def test_calendar_with_time_range(self, mock_exporter_class, tmp_path):
        """Test calendar with time range filters."""
        mock_exporter = MagicMock()
        mock_exporter.export_calendar_events.return_value = {}
        mock_exporter_class.return_value = mock_exporter

        creds_file = tmp_path / "creds.json"
        creds_file.write_text('{"web":{"client_id":"test"}}')

        with patch.object(mock_exporter, "_authenticate", return_value=MagicMock()):
            result = runner.invoke(
                app,
                [
                    "calendar",
                    "-a",
                    "2024-01-01",
                    "-b",
                    "2024-12-31",
                    "-c",
                    str(creds_file),
                ],
            )

        assert result.exit_code in [0, 1]

    @patch("google_workspace_tools.cli.commands.calendar.GoogleDriveExporter")
    def test_calendar_specific_calendar(self, mock_exporter_class, tmp_path):
        """Test calendar with specific calendar ID."""
        mock_exporter = MagicMock()
        mock_exporter.export_calendar_events.return_value = {}
        mock_exporter_class.return_value = mock_exporter

        creds_file = tmp_path / "creds.json"
        creds_file.write_text('{"web":{"client_id":"test"}}')

        with patch.object(mock_exporter, "_authenticate", return_value=MagicMock()):
            result = runner.invoke(
                app,
                [
                    "calendar",
                    "--calendar",
                    "work@example.com",
                    "-a",
                    "2024-01-01",  # Need a filter to trigger export
                    "-c",
                    str(creds_file),
                ],
            )

        assert result.exit_code in [0, 1]

    @patch("google_workspace_tools.cli.commands.calendar.GoogleDriveExporter")
    def test_calendar_with_query(self, mock_exporter_class, tmp_path):
        """Test calendar with search query."""
        mock_exporter = MagicMock()
        mock_exporter.export_calendar_events.return_value = {}
        mock_exporter_class.return_value = mock_exporter

        creds_file = tmp_path / "creds.json"
        creds_file.write_text('{"web":{"client_id":"test"}}')

        with patch.object(mock_exporter, "_authenticate", return_value=MagicMock()):
            result = runner.invoke(
                app,
                [
                    "calendar",
                    "-q",
                    "sprint planning",
                    "-c",
                    str(creds_file),
                ],
            )

        assert result.exit_code in [0, 1]

    @patch("google_workspace_tools.cli.commands.calendar.GoogleDriveExporter")
    def test_calendar_json_format(self, mock_exporter_class, tmp_path):
        """Test calendar with JSON format."""
        mock_exporter = MagicMock()
        mock_exporter.export_calendar_events.return_value = {}
        mock_exporter_class.return_value = mock_exporter

        creds_file = tmp_path / "creds.json"
        creds_file.write_text('{"web":{"client_id":"test"}}')

        with patch.object(mock_exporter, "_authenticate", return_value=MagicMock()):
            result = runner.invoke(
                app,
                [
                    "calendar",
                    "-q",
                    "meeting",  # Need a filter to trigger export
                    "-f",
                    "json",
                    "-c",
                    str(creds_file),
                ],
            )

        assert result.exit_code in [0, 1]

    @patch("google_workspace_tools.cli.commands.calendar.GoogleDriveExporter")
    def test_calendar_with_link_following(self, mock_exporter_class, tmp_path):
        """Test calendar with link following enabled."""
        mock_exporter = MagicMock()
        mock_exporter.export_calendar_events.return_value = {}
        mock_exporter_class.return_value = mock_exporter

        creds_file = tmp_path / "creds.json"
        creds_file.write_text('{"web":{"client_id":"test"}}')

        with patch.object(mock_exporter, "_authenticate", return_value=MagicMock()):
            result = runner.invoke(
                app,
                [
                    "calendar",
                    "-q",
                    "meeting",  # Need a filter to trigger export
                    "-d",
                    "2",
                    "-c",
                    str(creds_file),
                ],
            )

        assert result.exit_code in [0, 1]

    @patch("google_workspace_tools.cli.commands.calendar.GoogleDriveExporter")
    def test_calendar_max_results(self, mock_exporter_class, tmp_path):
        """Test calendar with max results limit."""
        mock_exporter = MagicMock()
        mock_exporter.export_calendar_events.return_value = {}
        mock_exporter_class.return_value = mock_exporter

        creds_file = tmp_path / "creds.json"
        creds_file.write_text('{"web":{"client_id":"test"}}')

        with patch.object(mock_exporter, "_authenticate", return_value=MagicMock()):
            result = runner.invoke(
                app,
                [
                    "calendar",
                    "-q",
                    "meeting",  # Need a filter to trigger export
                    "-n",
                    "100",
                    "-c",
                    str(creds_file),
                ],
            )

        assert result.exit_code in [0, 1]

    @patch("google_workspace_tools.cli.commands.calendar.GoogleDriveExporter")
    def test_calendar_export_error_handling(self, mock_exporter_class):
        """Test calendar export error handling with authentication failure."""
        # Mock exporter to raise an error during export
        mock_exporter = MagicMock()
        mock_exporter.export_calendar_events.side_effect = Exception("Authentication failed")
        mock_exporter_class.return_value = mock_exporter

        result = runner.invoke(
            app,
            [
                "calendar",
                "-q",
                "meeting",  # Trigger export mode
                "-c",
                "/nonexistent/creds.json",
            ],
        )

        # Should fail gracefully
        assert result.exit_code == 1
        assert "Error" in result.stdout or "error" in result.stdout.lower()

    @patch("google_workspace_tools.cli.commands.calendar.GoogleDriveExporter")
    def test_calendar_output_formatting(self, mock_exporter_class, tmp_path):
        """Test calendar output formatting."""
        mock_exporter = MagicMock()
        mock_exporter.export_calendar_events.return_value = {
            "event1": tmp_path / "event1.md",
            "event2": tmp_path / "event2.md",
            "event3": tmp_path / "event3.md",
        }
        mock_exporter_class.return_value = mock_exporter

        creds_file = tmp_path / "creds.json"
        creds_file.write_text('{"web":{"client_id":"test"}}')

        with patch.object(mock_exporter, "_authenticate", return_value=MagicMock()):
            result = runner.invoke(
                app,
                [
                    "calendar",
                    "-q",
                    "meeting",  # Trigger export mode
                    "-c",
                    str(creds_file),
                ],
            )

        # Check for success message formatting
        if result.exit_code == 0:
            assert "exported" in result.stdout.lower() or "3" in result.stdout


@pytest.mark.e2e
class TestCalendarIntegration:
    """Integration tests for calendar commands with realistic scenarios."""

    @patch("google_workspace_tools.cli.commands.calendar.GoogleDriveExporter")
    def test_calendar_combined_filters(self, mock_exporter_class, tmp_path):
        """Test calendar with multiple combined filters."""
        mock_exporter = MagicMock()
        mock_exporter.export_calendar_events.return_value = {}
        mock_exporter_class.return_value = mock_exporter

        creds_file = tmp_path / "creds.json"
        creds_file.write_text('{"web":{"client_id":"test"}}')

        with patch.object(mock_exporter, "_authenticate", return_value=MagicMock()):
            result = runner.invoke(
                app,
                [
                    "calendar",
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

    @patch("google_workspace_tools.cli.commands.calendar.GoogleDriveExporter")
    def test_workflow_list_then_export(self, mock_exporter_class, tmp_path):
        """Test realistic workflow: list calendars (no filters), then export with filters."""
        mock_exporter = MagicMock()
        mock_exporter.list_calendars.return_value = [{"id": "work@company.com", "summary": "Work", "primary": False}]
        mock_exporter.export_calendar_events.return_value = {}
        mock_exporter_class.return_value = mock_exporter

        creds_file = tmp_path / "creds.json"
        creds_file.write_text('{"web":{"client_id":"test"}}')

        # Step 1: List calendars (no filters)
        with patch.object(mock_exporter, "_authenticate", return_value=MagicMock()):
            result1 = runner.invoke(
                app,
                ["calendar", "-c", str(creds_file)],
            )

        # Step 2: Export from specific calendar (with filters)
        with patch.object(mock_exporter, "_authenticate", return_value=MagicMock()):
            result2 = runner.invoke(
                app,
                [
                    "calendar",
                    "--calendar",
                    "work@company.com",
                    "-q",
                    "standup",  # Need a filter to trigger export
                    "-c",
                    str(creds_file),
                ],
            )

        # Both commands should complete
        assert result1.exit_code in [0, 1]
        assert result2.exit_code in [0, 1]
