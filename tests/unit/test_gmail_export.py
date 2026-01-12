"""Tests for Gmail export functionality."""

import base64
import json
from datetime import datetime

import pytest
from pydantic import ValidationError

from google_workspace_tools.core.config import GoogleDriveExporterConfig
from google_workspace_tools.core.exporter import GoogleDriveExporter
from google_workspace_tools.core.filters import GmailSearchFilter


class TestGmailSearchFilter:
    """Tests for Gmail search filter query building."""

    def test_build_query_empty(self):
        """Test query building with no filters."""
        filter_obj = GmailSearchFilter()
        assert filter_obj.build_query() == ""

    def test_build_query_with_text(self):
        """Test query building with text search."""
        filter_obj = GmailSearchFilter(query="from:boss@example.com")
        assert filter_obj.build_query() == "from:boss@example.com"

    def test_build_query_with_dates(self):
        """Test query building with date filters."""
        filter_obj = GmailSearchFilter(after_date=datetime(2024, 1, 1), before_date=datetime(2024, 12, 31))
        query = filter_obj.build_query()
        assert "after:2024/01/01" in query
        assert "before:2024/12/31" in query

    def test_build_query_with_labels(self):
        """Test query building with label filters."""
        filter_obj = GmailSearchFilter(labels=["INBOX", "IMPORTANT"])
        query = filter_obj.build_query()
        assert "label:INBOX" in query
        assert "label:IMPORTANT" in query

    def test_build_query_with_attachment_filter_true(self):
        """Test query building with attachment requirement."""
        filter_obj = GmailSearchFilter(has_attachment=True)
        assert filter_obj.build_query() == "has:attachment"

    def test_build_query_with_attachment_filter_false(self):
        """Test query building excluding attachments."""
        filter_obj = GmailSearchFilter(has_attachment=False)
        assert filter_obj.build_query() == "-has:attachment"

    def test_build_query_combined_filters(self):
        """Test query building with multiple filters combined."""
        filter_obj = GmailSearchFilter(
            query="subject:meeting", after_date=datetime(2024, 1, 1), labels=["work"], has_attachment=True
        )
        query = filter_obj.build_query()
        assert "subject:meeting" in query
        assert "after:2024/01/01" in query
        assert "label:work" in query
        assert "has:attachment" in query

    def test_max_results_validation(self):
        """Test that max_results is validated."""
        # Valid range
        filter_obj = GmailSearchFilter(max_results=100)
        assert filter_obj.max_results == 100

        # Test boundaries
        with pytest.raises(ValidationError):
            GmailSearchFilter(max_results=0)

        with pytest.raises(ValidationError):
            GmailSearchFilter(max_results=501)

    def test_default_values(self):
        """Test filter default values."""
        filter_obj = GmailSearchFilter()
        assert filter_obj.query == ""
        assert filter_obj.after_date is None
        assert filter_obj.before_date is None
        assert filter_obj.labels == []
        assert filter_obj.has_attachment is None
        assert filter_obj.max_results == 100
        assert filter_obj.include_spam_trash is False


class TestEmailExportFormats:
    """Tests for email export format definitions."""

    def test_email_formats_exist(self):
        """Test that email export formats are defined."""
        formats = GoogleDriveExporter.EMAIL_EXPORT_FORMATS

        assert "json" in formats
        assert "md" in formats

    def test_email_format_extensions(self):
        """Test email format extensions."""
        formats = GoogleDriveExporter.EMAIL_EXPORT_FORMATS

        assert formats["json"].extension == "json"
        assert formats["md"].extension == "md"

    def test_email_format_mime_types(self):
        """Test email format MIME types."""
        formats = GoogleDriveExporter.EMAIL_EXPORT_FORMATS

        assert formats["json"].mime_type == "application/json"
        assert formats["md"].mime_type == "text/markdown"


class TestExtractMessageBody:
    """Tests for email body extraction."""

    @pytest.fixture
    def exporter(self):
        """Create an exporter instance."""
        return GoogleDriveExporter()

    def test_extract_simple_text_body(self, exporter):
        """Test extracting simple text/plain body."""
        text_content = "This is a plain text email."
        encoded_text = base64.urlsafe_b64encode(text_content.encode()).decode()

        message = {"payload": {"mimeType": "text/plain", "body": {"data": encoded_text}}}

        text_body, html_body = exporter._extract_message_body(message)
        assert text_body == text_content
        assert html_body == ""

    def test_extract_simple_html_body(self, exporter):
        """Test extracting simple text/html body."""
        html_content = "<p>This is an HTML email.</p>"
        encoded_html = base64.urlsafe_b64encode(html_content.encode()).decode()

        message = {"payload": {"mimeType": "text/html", "body": {"data": encoded_html}}}

        text_body, html_body = exporter._extract_message_body(message)
        assert text_body == ""
        assert html_body == html_content

    def test_extract_multipart_body(self, exporter):
        """Test extracting multipart message with both text and HTML."""
        text_content = "Plain text version"
        html_content = "<p>HTML version</p>"
        encoded_text = base64.urlsafe_b64encode(text_content.encode()).decode()
        encoded_html = base64.urlsafe_b64encode(html_content.encode()).decode()

        message = {
            "payload": {
                "mimeType": "multipart/alternative",
                "parts": [
                    {"mimeType": "text/plain", "body": {"data": encoded_text}},
                    {"mimeType": "text/html", "body": {"data": encoded_html}},
                ],
            }
        }

        text_body, html_body = exporter._extract_message_body(message)
        assert text_body == text_content
        assert html_body == html_content

    def test_extract_nested_multipart(self, exporter):
        """Test extracting nested multipart message."""
        text_content = "Text content"
        encoded_text = base64.urlsafe_b64encode(text_content.encode()).decode()

        message = {
            "payload": {
                "mimeType": "multipart/mixed",
                "parts": [
                    {
                        "mimeType": "multipart/alternative",
                        "parts": [{"mimeType": "text/plain", "body": {"data": encoded_text}}],
                    }
                ],
            }
        }

        text_body, html_body = exporter._extract_message_body(message)
        assert text_body == text_content

    def test_extract_empty_message(self, exporter):
        """Test extracting from empty message."""
        message = {"payload": {}}

        text_body, html_body = exporter._extract_message_body(message)
        assert text_body == ""
        assert html_body == ""


class TestExtractEmailAttachments:
    """Tests for email attachment extraction."""

    @pytest.fixture
    def exporter(self):
        """Create an exporter instance."""
        return GoogleDriveExporter()

    def test_extract_single_attachment(self, exporter):
        """Test extracting single attachment metadata."""
        message = {
            "payload": {
                "parts": [
                    {
                        "filename": "document.pdf",
                        "mimeType": "application/pdf",
                        "body": {"attachmentId": "att123", "size": 12345},
                    }
                ]
            }
        }

        attachments = exporter._extract_email_attachments(message)
        assert len(attachments) == 1
        assert attachments[0]["filename"] == "document.pdf"
        assert attachments[0]["mime_type"] == "application/pdf"
        assert attachments[0]["size"] == 12345
        assert attachments[0]["attachment_id"] == "att123"

    def test_extract_multiple_attachments(self, exporter):
        """Test extracting multiple attachment metadata."""
        message = {
            "payload": {
                "parts": [
                    {
                        "filename": "doc1.pdf",
                        "mimeType": "application/pdf",
                        "body": {"attachmentId": "att1", "size": 1000},
                    },
                    {"filename": "image.png", "mimeType": "image/png", "body": {"attachmentId": "att2", "size": 2000}},
                ]
            }
        }

        attachments = exporter._extract_email_attachments(message)
        assert len(attachments) == 2
        assert attachments[0]["filename"] == "doc1.pdf"
        assert attachments[1]["filename"] == "image.png"

    def test_extract_no_attachments(self, exporter):
        """Test extraction with no attachments."""
        message = {"payload": {"parts": [{"mimeType": "text/plain", "body": {"data": "dGV4dA=="}}]}}

        attachments = exporter._extract_email_attachments(message)
        assert len(attachments) == 0

    def test_extract_nested_attachments(self, exporter):
        """Test extracting attachments from nested parts."""
        message = {
            "payload": {
                "parts": [
                    {
                        "mimeType": "multipart/mixed",
                        "parts": [
                            {
                                "filename": "nested.doc",
                                "mimeType": "application/msword",
                                "body": {"attachmentId": "att123", "size": 5000},
                            }
                        ],
                    }
                ]
            }
        }

        attachments = exporter._extract_email_attachments(message)
        assert len(attachments) == 1
        assert attachments[0]["filename"] == "nested.doc"


class TestGroupMessagesByThread:
    """Tests for thread grouping logic."""

    @pytest.fixture
    def exporter(self):
        """Create an exporter instance."""
        return GoogleDriveExporter()

    def test_group_single_thread(self, exporter):
        """Test grouping messages in a single thread."""
        messages = [
            {"id": "msg1", "thread_id": "thread1", "internal_date": "1000"},
            {"id": "msg2", "thread_id": "thread1", "internal_date": "2000"},
            {"id": "msg3", "thread_id": "thread1", "internal_date": "1500"},
        ]

        threads = exporter._group_messages_by_thread(messages)
        assert len(threads) == 1
        assert "thread1" in threads
        assert len(threads["thread1"]) == 3

        # Check chronological ordering
        assert threads["thread1"][0]["id"] == "msg1"
        assert threads["thread1"][1]["id"] == "msg3"
        assert threads["thread1"][2]["id"] == "msg2"

    def test_group_multiple_threads(self, exporter):
        """Test grouping messages into multiple threads."""
        messages = [
            {"id": "msg1", "thread_id": "thread1", "internal_date": "1000"},
            {"id": "msg2", "thread_id": "thread2", "internal_date": "2000"},
            {"id": "msg3", "thread_id": "thread1", "internal_date": "3000"},
        ]

        threads = exporter._group_messages_by_thread(messages)
        assert len(threads) == 2
        assert len(threads["thread1"]) == 2
        assert len(threads["thread2"]) == 1

    def test_group_empty_messages(self, exporter):
        """Test grouping with no messages."""
        messages = []
        threads = exporter._group_messages_by_thread(messages)
        assert len(threads) == 0

    def test_group_messages_without_thread_id(self, exporter):
        """Test grouping messages that lack thread_id (use message id)."""
        messages = [{"id": "msg1", "internal_date": "1000"}, {"id": "msg2", "internal_date": "2000"}]

        threads = exporter._group_messages_by_thread(messages)
        assert len(threads) == 2
        assert "msg1" in threads
        assert "msg2" in threads


class TestExportEmailThreadAsJSON:
    """Tests for JSON email export."""

    @pytest.fixture
    def exporter(self):
        """Create an exporter instance."""
        return GoogleDriveExporter()

    def test_export_thread_json(self, exporter, tmp_path):
        """Test exporting thread as JSON."""
        messages = [
            {
                "id": "msg1",
                "thread_id": "thread123",
                "headers": {"Subject": "Test Email"},
                "text_body": "Hello",
                "html_body": "",
                "attachments": [],
                "internal_date": "1000",
            }
        ]

        output_path = tmp_path / "thread.json"
        success = exporter._export_email_thread_as_json("thread123", messages, output_path)

        assert success
        assert output_path.exists()

        # Verify JSON structure
        with open(output_path) as f:
            data = json.load(f)
            assert data["thread_id"] == "thread123"
            assert data["subject"] == "Test Email"
            assert data["message_count"] == 1
            assert len(data["messages"]) == 1
            assert "exported_at" in data

    def test_export_multiple_messages_json(self, exporter, tmp_path):
        """Test exporting multiple messages in a thread."""
        messages = [
            {
                "id": "msg1",
                "headers": {"Subject": "Re: Meeting"},
                "text_body": "First message",
                "html_body": "",
                "attachments": [],
            },
            {
                "id": "msg2",
                "headers": {"Subject": "Re: Meeting"},
                "text_body": "Second message",
                "html_body": "",
                "attachments": [],
            },
        ]

        output_path = tmp_path / "thread.json"
        success = exporter._export_email_thread_as_json("thread456", messages, output_path)

        assert success
        with open(output_path) as f:
            data = json.load(f)
            assert data["message_count"] == 2


class TestExportEmailThreadAsMarkdown:
    """Tests for Markdown email export."""

    @pytest.fixture
    def exporter(self):
        """Create an exporter instance."""
        config = GoogleDriveExporterConfig(enable_frontmatter=True)
        return GoogleDriveExporter(config)

    def test_export_thread_markdown(self, exporter, tmp_path):
        """Test exporting thread as Markdown."""
        messages = [
            {
                "id": "msg1",
                "thread_id": "thread123",
                "headers": {
                    "Subject": "Meeting Notes",
                    "From": "sender@example.com",
                    "To": "recipient@example.com",
                    "Date": "Mon, 1 Jan 2024 10:00:00 +0000",
                },
                "text_body": "Let's meet tomorrow.",
                "html_body": "",
                "attachments": [],
                "label_ids": ["INBOX", "IMPORTANT"],
            }
        ]

        output_path = tmp_path / "thread.md"
        success = exporter._export_email_thread_as_markdown("thread123", messages, output_path)

        assert success
        assert output_path.exists()

        content = output_path.read_text()
        # Check frontmatter
        assert content.startswith("---\n")
        assert "thread_id: thread123" in content
        assert "subject: Meeting Notes" in content

        # Check message content
        assert "# Email Thread: Meeting Notes" in content
        assert "**From:** sender@example.com" in content
        assert "Let's meet tomorrow" in content

    def test_export_with_html_conversion(self, exporter, tmp_path):
        """Test HTML to Markdown conversion in export."""
        messages = [
            {
                "id": "msg1",
                "headers": {"Subject": "HTML Email"},
                "text_body": "",
                "html_body": "<p>This is <strong>bold</strong> text.</p>",
                "attachments": [],
                "label_ids": [],
            }
        ]

        output_path = tmp_path / "thread.md"
        success = exporter._export_email_thread_as_markdown("thread123", messages, output_path)

        assert success
        content = output_path.read_text()
        # html_to_markdown should convert HTML to markdown
        assert "bold" in content.lower() or "strong" in content.lower()

    def test_export_with_attachments(self, exporter, tmp_path):
        """Test exporting with attachment information."""
        messages = [
            {
                "id": "msg1",
                "headers": {"Subject": "Files Attached"},
                "text_body": "See attachments",
                "html_body": "",
                "attachments": [{"filename": "document.pdf", "size": 10240}, {"filename": "image.png", "size": 5120}],
                "label_ids": [],
            }
        ]

        output_path = tmp_path / "thread.md"
        success = exporter._export_email_thread_as_markdown("thread123", messages, output_path)

        assert success
        content = output_path.read_text()
        assert "**Attachments:**" in content
        assert "document.pdf" in content
        assert "image.png" in content
        assert "10.0 KB" in content  # Size formatting
        assert "5.0 KB" in content
