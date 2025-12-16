"""Tests for GoogleDriveExporter."""

import pytest

from google_workspace_tools.core.exporter import GoogleDriveExporter
from google_workspace_tools.core.config import GoogleDriveExporterConfig
from google_workspace_tools.core.types import DocumentType


class TestExtractDocumentId:
    """Tests for document ID extraction from URLs."""

    @pytest.fixture
    def exporter(self):
        """Create an exporter instance without authentication."""
        return GoogleDriveExporter()

    def test_extract_from_docs_url(self, exporter):
        """Test extracting ID from Google Docs URL."""
        url = "https://docs.google.com/document/d/1abc123xyz_-/edit"
        assert exporter.extract_document_id(url) == "1abc123xyz_-"

    def test_extract_from_docs_url_with_user(self, exporter):
        """Test extracting ID from Google Docs URL with user path."""
        url = "https://docs.google.com/document/u/0/d/1abc123xyz/edit"
        assert exporter.extract_document_id(url) == "1abc123xyz"

    def test_extract_from_sheets_url(self, exporter):
        """Test extracting ID from Google Sheets URL."""
        url = "https://docs.google.com/spreadsheets/d/spreadsheet123/edit#gid=0"
        assert exporter.extract_document_id(url) == "spreadsheet123"

    def test_extract_from_slides_url(self, exporter):
        """Test extracting ID from Google Slides URL."""
        url = "https://docs.google.com/presentation/d/presentation456/edit"
        assert exporter.extract_document_id(url) == "presentation456"

    def test_extract_from_drive_open_url(self, exporter):
        """Test extracting ID from drive.google.com/open URL."""
        url = "https://drive.google.com/open?id=driveFile789"
        assert exporter.extract_document_id(url) == "driveFile789"

    def test_extract_returns_id_if_not_url(self, exporter):
        """Test that non-URL strings are returned as-is (assumed to be IDs)."""
        doc_id = "1abc123xyz"
        assert exporter.extract_document_id(doc_id) == doc_id

    def test_extract_invalid_url_raises(self, exporter):
        """Test that invalid URLs raise ValueError."""
        with pytest.raises(ValueError, match="Could not extract document ID"):
            exporter.extract_document_id("https://example.com/not-a-drive-url")


class TestDetectDocumentType:
    """Tests for document type detection."""

    @pytest.fixture
    def exporter(self):
        """Create an exporter instance."""
        return GoogleDriveExporter()

    def test_detect_document(self, exporter):
        """Test detecting Google Docs document."""
        url = "https://docs.google.com/document/d/abc123/edit"
        assert exporter.detect_document_type(url) == DocumentType.DOCUMENT

    def test_detect_spreadsheet(self, exporter):
        """Test detecting Google Sheets spreadsheet."""
        url = "https://docs.google.com/spreadsheets/d/abc123/edit"
        assert exporter.detect_document_type(url) == DocumentType.SPREADSHEET

    def test_detect_presentation(self, exporter):
        """Test detecting Google Slides presentation."""
        url = "https://docs.google.com/presentation/d/abc123/edit"
        assert exporter.detect_document_type(url) == DocumentType.PRESENTATION

    def test_detect_unknown_for_id(self, exporter):
        """Test that plain IDs return UNKNOWN type."""
        doc_id = "abc123"
        assert exporter.detect_document_type(doc_id) == DocumentType.UNKNOWN

    def test_detect_unknown_for_other_urls(self, exporter):
        """Test that non-Google URLs return UNKNOWN type."""
        url = "https://example.com/files/abc123"
        assert exporter.detect_document_type(url) == DocumentType.UNKNOWN


class TestExportFormats:
    """Tests for export format dictionaries."""

    def test_document_formats_exist(self):
        """Test that document export formats are defined."""
        formats = GoogleDriveExporter.DOCUMENT_EXPORT_FORMATS

        assert "pdf" in formats
        assert "docx" in formats
        assert "md" in formats
        assert "html" in formats
        assert "txt" in formats

    def test_spreadsheet_formats_exist(self):
        """Test that spreadsheet export formats are defined."""
        formats = GoogleDriveExporter.SPREADSHEET_EXPORT_FORMATS

        assert "pdf" in formats
        assert "xlsx" in formats
        assert "csv" in formats
        assert "tsv" in formats

    def test_presentation_formats_exist(self):
        """Test that presentation export formats are defined."""
        formats = GoogleDriveExporter.PRESENTATION_EXPORT_FORMATS

        assert "pdf" in formats
        assert "pptx" in formats
        assert "odp" in formats

    def test_markdown_not_in_spreadsheet_formats(self):
        """Test that markdown is not available for spreadsheets."""
        formats = GoogleDriveExporter.SPREADSHEET_EXPORT_FORMATS
        assert "md" not in formats

    def test_markdown_not_in_presentation_formats(self):
        """Test that markdown is not available for presentations."""
        formats = GoogleDriveExporter.PRESENTATION_EXPORT_FORMATS
        assert "md" not in formats


class TestResetProcessedDocs:
    """Tests for reset_processed_docs method."""

    def test_reset_clears_processed_set(self):
        """Test that reset clears the processed documents set."""
        exporter = GoogleDriveExporter()

        # Simulate processing some docs
        exporter._processed_docs.add("doc1")
        exporter._processed_docs.add("doc2")
        assert len(exporter._processed_docs) == 2

        # Reset
        exporter.reset_processed_docs()
        assert len(exporter._processed_docs) == 0
