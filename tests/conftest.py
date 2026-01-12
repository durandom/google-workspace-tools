"""Pytest fixtures for Google Workspace Tools tests."""

import base64
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

from google_workspace_tools.core.config import GoogleDriveExporterConfig
from google_workspace_tools.core.exporter import GoogleDriveExporter

# =============================================================================
# Basic Fixtures (existing)
# =============================================================================


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


# =============================================================================
# Mock Google API Services
# =============================================================================


@pytest.fixture
def mock_credentials() -> MagicMock:
    """Mock Google OAuth credentials."""
    creds = MagicMock()
    creds.valid = True
    creds.expired = False
    creds.refresh_token = "mock_refresh_token"
    return creds


@pytest.fixture
def mock_drive_service() -> MagicMock:
    """Mock Google Drive API service.

    Provides default responses for common operations:
    - files().get() -> document metadata
    - files().export_media() -> file content
    """
    service = MagicMock()

    # Default metadata response
    service.files.return_value.get.return_value.execute.return_value = {
        "name": "Test Document",
        "mimeType": "application/vnd.google-apps.document",
        "id": "test_doc_id_123",
    }

    # Default export response (returns bytes)
    mock_request = MagicMock()
    mock_request.execute.return_value = b"<html><body>Test content</body></html>"
    service.files.return_value.export_media.return_value = mock_request

    # About response for user info
    service.about.return_value.get.return_value.execute.return_value = {
        "user": {"emailAddress": "test@example.com", "displayName": "Test User"}
    }

    return service


@pytest.fixture
def mock_gmail_service() -> MagicMock:
    """Mock Gmail API service.

    Provides default responses for common operations:
    - users().messages().list() -> message list
    - users().messages().get() -> single message
    """
    service = MagicMock()

    # Default list response (empty)
    service.users.return_value.messages.return_value.list.return_value.execute.return_value = {
        "messages": [],
        "resultSizeEstimate": 0,
    }

    # Default get response
    service.users.return_value.messages.return_value.get.return_value.execute.return_value = {
        "id": "msg_123",
        "threadId": "thread_123",
        "labelIds": ["INBOX"],
        "internalDate": "1704067200000",
        "payload": {
            "mimeType": "text/plain",
            "headers": [
                {"name": "Subject", "value": "Test Subject"},
                {"name": "From", "value": "sender@example.com"},
                {"name": "To", "value": "recipient@example.com"},
                {"name": "Date", "value": "Mon, 1 Jan 2024 10:00:00 +0000"},
            ],
            "body": {"data": base64.urlsafe_b64encode(b"Test body").decode()},
        },
    }

    return service


@pytest.fixture
def mock_calendar_service() -> MagicMock:
    """Mock Google Calendar API service.

    Provides default responses for common operations:
    - calendarList().list() -> calendar list
    - events().list() -> event list
    """
    service = MagicMock()

    # Default calendar list
    service.calendarList.return_value.list.return_value.execute.return_value = {
        "items": [
            {"id": "primary", "summary": "Primary Calendar", "primary": True},
        ]
    }

    # Default events list (empty)
    service.events.return_value.list.return_value.execute.return_value = {
        "items": [],
    }

    return service


# =============================================================================
# Isolated Exporter Fixtures
# =============================================================================


@pytest.fixture
def isolated_exporter(
    tmp_path: Path,
    mock_drive_service: MagicMock,
    mock_gmail_service: MagicMock,
    mock_calendar_service: MagicMock,
) -> GoogleDriveExporter:
    """Fully isolated GoogleDriveExporter with mock services injected.

    Use this for tests that need a real exporter instance but should
    never touch the network or credential files. All API services are
    pre-mocked with sensible defaults.

    Example:
        def test_something(isolated_exporter):
            result = isolated_exporter.some_method()
            assert result == expected
    """
    config = GoogleDriveExporterConfig(
        credentials_path=tmp_path / "creds.json",
        token_path=tmp_path / "token.json",
        target_directory=tmp_path / "exports",
    )
    (tmp_path / "exports").mkdir(exist_ok=True)

    exporter = GoogleDriveExporter(config)

    # Inject mock services to bypass authentication
    exporter._service = mock_drive_service
    exporter._gmail_service = mock_gmail_service
    exporter._calendar_service = mock_calendar_service

    return exporter


@pytest.fixture
def exporter_factory(tmp_path: Path):
    """Factory to create isolated exporters with custom config.

    Use this when you need to customize the exporter configuration
    for specific test scenarios (e.g., testing with frontmatter enabled).

    Example:
        def test_with_frontmatter(exporter_factory):
            exporter = exporter_factory(enable_frontmatter=True)
            result = exporter.export_something()

        def test_spreadsheet_mode(exporter_factory):
            exporter = exporter_factory(spreadsheet_export_mode="separate")
    """

    def _create(**config_overrides) -> GoogleDriveExporter:
        defaults = {
            "credentials_path": tmp_path / "creds.json",
            "token_path": tmp_path / "token.json",
            "target_directory": tmp_path / "exports",
        }
        defaults.update(config_overrides)
        config = GoogleDriveExporterConfig(**defaults)
        (tmp_path / "exports").mkdir(exist_ok=True)

        exporter = GoogleDriveExporter(config)

        # Initialize services to None to prevent accidental auth
        # Tests that need services should use isolated_exporter instead
        exporter._service = None
        exporter._gmail_service = None
        exporter._calendar_service = None

        return exporter

    return _create


# =============================================================================
# Mock Response Factory
# =============================================================================


class MockResponseFactory:
    """Factory for creating realistic Google API mock responses.

    This class provides static methods to create properly structured
    mock responses that match the Google API schemas. Use these to
    configure mock services with specific test data.

    Example:
        def test_with_specific_email(mock_factory, mock_gmail_service):
            msg = mock_factory.gmail_message(
                subject="Important Meeting",
                from_addr="boss@company.com",
                body_text="Please attend tomorrow's meeting."
            )
            mock_gmail_service.users.return_value.messages.return_value.get.return_value.execute.return_value = msg
    """

    @staticmethod
    def gmail_message(
        msg_id: str = "msg_123",
        thread_id: str = "thread_123",
        subject: str = "Test Subject",
        from_addr: str = "sender@example.com",
        to_addr: str = "recipient@example.com",
        body_text: str = "Test email body",
        body_html: str = "",
        date: str = "Mon, 1 Jan 2024 10:00:00 +0000",
        internal_date: str = "1704067200000",
        label_ids: list[str] | None = None,
        attachments: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Create a mock Gmail message response.

        Args:
            msg_id: Unique message ID
            thread_id: Thread ID for grouping
            subject: Email subject line
            from_addr: Sender email address
            to_addr: Recipient email address
            body_text: Plain text body content
            body_html: HTML body content (if provided, creates multipart)
            date: RFC 2822 formatted date string
            internal_date: Unix timestamp in milliseconds (as string)
            label_ids: Gmail label IDs (e.g., ["INBOX", "IMPORTANT"])
            attachments: List of attachment metadata dicts
        """
        encoded_text = base64.urlsafe_b64encode(body_text.encode()).decode()

        headers = [
            {"name": "Subject", "value": subject},
            {"name": "From", "value": from_addr},
            {"name": "To", "value": to_addr},
            {"name": "Date", "value": date},
        ]

        if body_html:
            # Multipart message with both text and HTML
            encoded_html = base64.urlsafe_b64encode(body_html.encode()).decode()
            payload = {
                "mimeType": "multipart/alternative",
                "headers": headers,
                "parts": [
                    {"mimeType": "text/plain", "body": {"data": encoded_text}},
                    {"mimeType": "text/html", "body": {"data": encoded_html}},
                ],
            }
        else:
            # Simple text message
            payload = {
                "mimeType": "text/plain",
                "headers": headers,
                "body": {"data": encoded_text},
            }

        if attachments:
            payload["parts"] = payload.get("parts", []) + attachments

        return {
            "id": msg_id,
            "threadId": thread_id,
            "labelIds": label_ids or ["INBOX"],
            "internalDate": internal_date,
            "payload": payload,
        }

    @staticmethod
    def gmail_attachment(
        filename: str = "document.pdf",
        mime_type: str = "application/pdf",
        attachment_id: str = "att_123",
        size: int = 12345,
    ) -> dict[str, Any]:
        """Create a mock Gmail attachment part.

        Args:
            filename: Attachment filename
            mime_type: MIME type of the attachment
            attachment_id: Unique attachment ID
            size: File size in bytes
        """
        return {
            "filename": filename,
            "mimeType": mime_type,
            "body": {"attachmentId": attachment_id, "size": size},
        }

    @staticmethod
    def calendar_event(
        event_id: str = "evt_123",
        summary: str = "Test Event",
        description: str = "",
        start_datetime: str = "2024-01-15T10:00:00Z",
        end_datetime: str = "2024-01-15T11:00:00Z",
        location: str | None = None,
        organizer_email: str = "organizer@example.com",
        organizer_name: str | None = None,
        attendees: list[dict[str, Any]] | None = None,
        attachments: list[dict[str, Any]] | None = None,
        all_day: bool = False,
        calendar_id: str = "primary",
    ) -> dict[str, Any]:
        """Create a mock Calendar event response.

        Args:
            event_id: Unique event ID
            summary: Event title
            description: Event description (can include HTML)
            start_datetime: ISO 8601 datetime string (or date for all-day)
            end_datetime: ISO 8601 datetime string (or date for all-day)
            location: Event location
            organizer_email: Organizer's email address
            organizer_name: Organizer's display name
            attendees: List of attendee dicts
            attachments: List of Drive attachment dicts
            all_day: If True, use date instead of dateTime
            calendar_id: ID of the calendar this event belongs to
        """
        organizer = {"email": organizer_email}
        if organizer_name:
            organizer["displayName"] = organizer_name

        event: dict[str, Any] = {
            "id": event_id,
            "summary": summary,
            "description": description,
            "organizer": organizer,
            "attendees": attendees or [],
            "_calendar_id": calendar_id,  # Added by our exporter
        }

        if all_day:
            event["start"] = {"date": start_datetime[:10]}
            event["end"] = {"date": end_datetime[:10]}
        else:
            event["start"] = {"dateTime": start_datetime}
            event["end"] = {"dateTime": end_datetime}

        if location:
            event["location"] = location

        if attachments:
            event["attachments"] = attachments

        return event

    @staticmethod
    def calendar_attendee(
        email: str = "attendee@example.com",
        display_name: str | None = None,
        response_status: str = "accepted",
        organizer: bool = False,
        optional: bool = False,
    ) -> dict[str, Any]:
        """Create a mock Calendar attendee.

        Args:
            email: Attendee's email address
            display_name: Attendee's display name
            response_status: One of: needsAction, declined, tentative, accepted
            organizer: True if this attendee is the organizer
            optional: True if attendance is optional
        """
        attendee: dict[str, Any] = {
            "email": email,
            "responseStatus": response_status,
        }
        if display_name:
            attendee["displayName"] = display_name
        if organizer:
            attendee["organizer"] = True
        if optional:
            attendee["optional"] = True
        return attendee

    @staticmethod
    def drive_document(
        doc_id: str = "doc_123",
        name: str = "Test Document",
        mime_type: str = "application/vnd.google-apps.document",
    ) -> dict[str, Any]:
        """Create a mock Drive file metadata response.

        Args:
            doc_id: Unique document ID
            name: Document title
            mime_type: MIME type (determines document type)
        """
        return {
            "id": doc_id,
            "name": name,
            "mimeType": mime_type,
        }

    @staticmethod
    def drive_attachment(
        file_url: str = "https://docs.google.com/document/d/abc123",
        title: str = "Attached Document",
    ) -> dict[str, Any]:
        """Create a mock Drive attachment (for Calendar events).

        Args:
            file_url: URL to the Drive file
            title: Display title for the attachment
        """
        return {
            "fileUrl": file_url,
            "title": title,
        }


@pytest.fixture
def mock_factory() -> type[MockResponseFactory]:
    """Provide access to MockResponseFactory in tests.

    Example:
        def test_email_processing(mock_factory, isolated_exporter):
            msg = mock_factory.gmail_message(subject="Test")
            # Use msg in your test...
    """
    return MockResponseFactory
