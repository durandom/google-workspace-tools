"""Tests for Google Calendar export functionality."""

import json
from datetime import datetime

import pytest
from pydantic import ValidationError

from google_workspace_tools.core.config import GoogleDriveExporterConfig
from google_workspace_tools.core.exporter import GoogleDriveExporter
from google_workspace_tools.core.filters import CalendarEventFilter


class TestCalendarEventFilter:
    """Tests for Calendar event filter configuration."""

    def test_default_values(self):
        """Test filter default values."""
        filter_obj = CalendarEventFilter()
        assert filter_obj.time_min is None
        assert filter_obj.time_max is None
        assert filter_obj.calendar_ids == ["primary"]
        assert filter_obj.query == ""
        assert filter_obj.single_events is True
        assert filter_obj.max_results == 250
        assert filter_obj.order_by == "startTime"

    def test_get_calendar_ids_default(self):
        """Test getting calendar IDs with default."""
        filter_obj = CalendarEventFilter()
        assert filter_obj.get_calendar_ids() == ["primary"]

    def test_get_calendar_ids_custom(self):
        """Test getting custom calendar IDs."""
        filter_obj = CalendarEventFilter(calendar_ids=["work@example.com", "personal@example.com"])
        assert filter_obj.get_calendar_ids() == ["work@example.com", "personal@example.com"]

    def test_get_calendar_ids_empty_list(self):
        """Test that empty list defaults to primary."""
        filter_obj = CalendarEventFilter(calendar_ids=[])
        assert filter_obj.get_calendar_ids() == ["primary"]

    def test_time_range_filters(self):
        """Test time range filter configuration."""
        start = datetime(2024, 1, 1)
        end = datetime(2024, 12, 31)

        filter_obj = CalendarEventFilter(time_min=start, time_max=end)
        assert filter_obj.time_min == start
        assert filter_obj.time_max == end

    def test_query_filter(self):
        """Test text query filter."""
        filter_obj = CalendarEventFilter(query="sprint planning")
        assert filter_obj.query == "sprint planning"

    def test_max_results_validation(self):
        """Test that max_results is validated."""
        # Valid range
        filter_obj = CalendarEventFilter(max_results=100)
        assert filter_obj.max_results == 100

        # Test boundaries
        with pytest.raises(ValidationError):
            CalendarEventFilter(max_results=0)

        with pytest.raises(ValidationError):
            CalendarEventFilter(max_results=2501)

    def test_order_by_options(self):
        """Test order_by field options."""
        # Valid options
        filter_obj = CalendarEventFilter(order_by="startTime")
        assert filter_obj.order_by == "startTime"

        filter_obj = CalendarEventFilter(order_by="updated")
        assert filter_obj.order_by == "updated"

        # Invalid option should fail
        with pytest.raises(ValidationError):
            CalendarEventFilter(order_by="invalid")

    def test_single_events_flag(self):
        """Test single_events flag configuration."""
        filter_obj = CalendarEventFilter(single_events=False)
        assert filter_obj.single_events is False

        filter_obj = CalendarEventFilter(single_events=True)
        assert filter_obj.single_events is True


class TestCalendarExportFormats:
    """Tests for calendar export format definitions."""

    def test_calendar_formats_exist(self):
        """Test that calendar export formats are defined."""
        formats = GoogleDriveExporter.CALENDAR_EXPORT_FORMATS

        assert "json" in formats
        assert "md" in formats

    def test_calendar_format_extensions(self):
        """Test calendar format extensions."""
        formats = GoogleDriveExporter.CALENDAR_EXPORT_FORMATS

        assert formats["json"].extension == "json"
        assert formats["md"].extension == "md"

    def test_calendar_format_mime_types(self):
        """Test calendar format MIME types."""
        formats = GoogleDriveExporter.CALENDAR_EXPORT_FORMATS

        assert formats["json"].mime_type == "application/json"
        assert formats["md"].mime_type == "text/markdown"


class TestExportCalendarEventAsJSON:
    """Tests for JSON calendar event export."""

    @pytest.fixture
    def exporter(self):
        """Create an exporter instance."""
        return GoogleDriveExporter()

    def test_export_simple_event_json(self, exporter, tmp_path):
        """Test exporting simple calendar event as JSON."""
        event = {
            "id": "event123",
            "summary": "Team Meeting",
            "description": "Weekly sync",
            "start": {"dateTime": "2024-01-15T10:00:00Z"},
            "end": {"dateTime": "2024-01-15T11:00:00Z"},
            "attendees": [],
        }

        output_path = tmp_path / "event.json"
        success = exporter._export_calendar_event_as_json(event, output_path)

        assert success
        assert output_path.exists()

        # Verify JSON structure
        with open(output_path) as f:
            data = json.load(f)
            assert data["id"] == "event123"
            assert data["summary"] == "Team Meeting"
            assert "exported_at" in data
            assert "drive_links" in data

    def test_export_all_day_event_json(self, exporter, tmp_path):
        """Test exporting all-day event."""
        event = {"id": "event456", "summary": "Holiday", "start": {"date": "2024-12-25"}, "end": {"date": "2024-12-26"}}

        output_path = tmp_path / "event.json"
        success = exporter._export_calendar_event_as_json(event, output_path)

        assert success
        with open(output_path) as f:
            data = json.load(f)
            assert data["summary"] == "Holiday"
            # All-day events use date instead of dateTime
            assert "date" in str(data["start"])

    def test_export_event_with_attachments_json(self, exporter, tmp_path):
        """Test exporting event with Drive attachments."""
        event = {
            "id": "event789",
            "summary": "Project Review",
            "description": "Review slides",
            "start": {"dateTime": "2024-01-20T14:00:00Z"},
            "end": {"dateTime": "2024-01-20T15:00:00Z"},
            "attachments": [{"fileUrl": "https://drive.google.com/file/d/abc123/view", "title": "Slides.pptx"}],
        }

        output_path = tmp_path / "event.json"
        success = exporter._export_calendar_event_as_json(event, output_path)

        assert success
        with open(output_path) as f:
            data = json.load(f)
            # Drive links should be extracted from attachments
            assert isinstance(data["drive_links"], list)


class TestExportCalendarEventAsMarkdown:
    """Tests for Markdown calendar event export."""

    @pytest.fixture
    def exporter(self):
        """Create an exporter instance with frontmatter enabled."""
        config = GoogleDriveExporterConfig(enable_frontmatter=True)
        return GoogleDriveExporter(config)

    def test_export_simple_event_markdown(self, exporter, tmp_path):
        """Test exporting simple event as Markdown."""
        event = {
            "id": "event123",
            "_calendar_id": "primary",
            "summary": "Weekly Standup",
            "description": "Team sync meeting",
            "location": "Conference Room A",
            "start": {"dateTime": "2024-01-15T09:00:00Z"},
            "end": {"dateTime": "2024-01-15T09:30:00Z"},
            "organizer": {"email": "organizer@example.com", "displayName": "Team Lead"},
            "attendees": [],
        }

        output_path = tmp_path / "event.md"
        success = exporter._export_calendar_event_as_markdown(event, output_path)

        assert success
        assert output_path.exists()

        content = output_path.read_text()
        # Check frontmatter
        assert content.startswith("---\n")
        assert "event_id: event123" in content
        assert "summary: Weekly Standup" in content
        assert "calendar_id: primary" in content

        # Check event content
        assert "# Weekly Standup" in content
        assert "**When:**" in content
        assert "**Where:** Conference Room A" in content
        assert "**Organizer:** Team Lead" in content

    def test_export_event_with_attendees_markdown(self, exporter, tmp_path):
        """Test exporting event with attendees."""
        event = {
            "id": "event456",
            "_calendar_id": "work@example.com",
            "summary": "Planning Session",
            "start": {"dateTime": "2024-01-20T14:00:00Z"},
            "end": {"dateTime": "2024-01-20T16:00:00Z"},
            "organizer": {"email": "boss@example.com"},
            "attendees": [
                {"email": "alice@example.com", "displayName": "Alice", "responseStatus": "accepted", "organizer": True},
                {"email": "bob@example.com", "displayName": "Bob", "responseStatus": "tentative", "optional": True},
            ],
        }

        output_path = tmp_path / "event.md"
        success = exporter._export_calendar_event_as_markdown(event, output_path)

        assert success
        content = output_path.read_text()

        assert "**Attendees:**" in content
        assert "Alice" in content
        assert "accepted" in content
        assert "Bob" in content
        assert "tentative" in content
        assert "(optional)" in content
        assert "(organizer)" in content

    def test_export_all_day_event_markdown(self, exporter, tmp_path):
        """Test exporting all-day event."""
        event = {
            "id": "event789",
            "_calendar_id": "primary",
            "summary": "Conference",
            "start": {"date": "2024-03-15"},
            "end": {"date": "2024-03-16"},
            "organizer": {},
        }

        output_path = tmp_path / "event.md"
        success = exporter._export_calendar_event_as_markdown(event, output_path)

        assert success
        content = output_path.read_text()

        assert "# Conference" in content
        assert "2024-03-15" in content
        # All-day events use date format

    def test_export_event_with_html_description_markdown(self, exporter, tmp_path):
        """Test HTML description conversion to Markdown."""
        event = {
            "id": "event999",
            "_calendar_id": "primary",
            "summary": "Training",
            "description": "<p>Topics to cover:</p><ul><li>Item 1</li><li>Item 2</li></ul>",
            "start": {"dateTime": "2024-02-01T10:00:00Z"},
            "end": {"dateTime": "2024-02-01T12:00:00Z"},
            "organizer": {},
        }

        output_path = tmp_path / "event.md"
        success = exporter._export_calendar_event_as_markdown(event, output_path)

        assert success
        content = output_path.read_text()

        # html_to_markdown should convert HTML
        assert "## Description" in content
        assert "Topics to cover" in content

    def test_export_event_with_attachments_markdown(self, exporter, tmp_path):
        """Test exporting event with attachments."""
        event = {
            "id": "event101",
            "_calendar_id": "primary",
            "summary": "Review Meeting",
            "start": {"dateTime": "2024-01-25T15:00:00Z"},
            "end": {"dateTime": "2024-01-25T16:00:00Z"},
            "organizer": {},
            "attachments": [
                {"fileUrl": "https://docs.google.com/document/d/abc123", "title": "Meeting Agenda"},
                {"fileUrl": "https://docs.google.com/spreadsheets/d/xyz789", "title": "Budget Sheet"},
            ],
        }

        output_path = tmp_path / "event.md"
        success = exporter._export_calendar_event_as_markdown(event, output_path)

        assert success
        content = output_path.read_text()

        assert "**Attachments:**" in content
        assert "[Meeting Agenda]" in content
        assert "[Budget Sheet]" in content
        assert "docs.google.com" in content

    def test_export_event_no_title_markdown(self, exporter, tmp_path):
        """Test exporting event without summary (no title)."""
        event = {
            "id": "event000",
            "_calendar_id": "primary",
            "start": {"dateTime": "2024-01-10T08:00:00Z"},
            "end": {"dateTime": "2024-01-10T09:00:00Z"},
            "organizer": {},
        }

        output_path = tmp_path / "event.md"
        success = exporter._export_calendar_event_as_markdown(event, output_path)

        assert success
        content = output_path.read_text()

        # Should handle missing summary gracefully
        assert "# (No title)" in content

    def test_export_event_no_location_markdown(self, exporter, tmp_path):
        """Test exporting event without location."""
        event = {
            "id": "event202",
            "_calendar_id": "primary",
            "summary": "Virtual Meeting",
            "start": {"dateTime": "2024-01-30T11:00:00Z"},
            "end": {"dateTime": "2024-01-30T12:00:00Z"},
            "organizer": {},
        }

        output_path = tmp_path / "event.md"
        success = exporter._export_calendar_event_as_markdown(event, output_path)

        assert success
        content = output_path.read_text()

        # Location field should not appear
        assert "**Where:**" not in content or "Where: None" not in content


class TestCalendarTimezoneHandling:
    """Tests for calendar timezone and date format handling."""

    @pytest.fixture
    def exporter(self):
        """Create an exporter instance."""
        return GoogleDriveExporter()

    def test_datetime_with_timezone(self, exporter, tmp_path):
        """Test handling dateTime with timezone."""
        event = {
            "id": "evt1",
            "summary": "Test Event",
            "start": {"dateTime": "2024-01-15T10:00:00-05:00"},
            "end": {"dateTime": "2024-01-15T11:00:00-05:00"},
            "organizer": {},
        }

        output_path = tmp_path / "event.json"
        success = exporter._export_calendar_event_as_json(event, output_path)

        assert success
        with open(output_path) as f:
            data = json.load(f)
            # Timezone should be preserved
            assert "-05:00" in str(data)

    def test_datetime_utc(self, exporter, tmp_path):
        """Test handling dateTime in UTC."""
        event = {
            "id": "evt2",
            "summary": "UTC Event",
            "start": {"dateTime": "2024-01-15T15:00:00Z"},
            "end": {"dateTime": "2024-01-15T16:00:00Z"},
            "organizer": {},
        }

        output_path = tmp_path / "event.json"
        success = exporter._export_calendar_event_as_json(event, output_path)

        assert success
        with open(output_path) as f:
            data = json.load(f)
            assert "Z" in str(data) or "UTC" in str(data).upper()

    def test_date_only_format(self, exporter, tmp_path):
        """Test handling date-only format (all-day events)."""
        event = {
            "id": "evt3",
            "summary": "All Day Event",
            "start": {"date": "2024-01-15"},
            "end": {"date": "2024-01-16"},
            "organizer": {},
        }

        output_path = tmp_path / "event.json"
        success = exporter._export_calendar_event_as_json(event, output_path)

        assert success
        with open(output_path) as f:
            data = json.load(f)
            # Should preserve date format
            assert "2024-01-15" in str(data)
