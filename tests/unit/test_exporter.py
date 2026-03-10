"""Tests for GoogleDriveExporter."""

import pytest

from google_workspace_tools.core.config import GoogleDriveExporterConfig
from google_workspace_tools.core.exporter import GoogleDriveExporter
from google_workspace_tools.core.types import DocumentType


@pytest.mark.unit
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


@pytest.mark.unit
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


@pytest.mark.unit
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


@pytest.mark.unit
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


@pytest.mark.unit
class TestFrontmatter:
    """Tests for frontmatter generation."""

    def test_generate_frontmatter_basic(self):
        """Test basic frontmatter generation with auto fields only."""
        config = GoogleDriveExporterConfig(enable_frontmatter=True)
        exporter = GoogleDriveExporter(config)

        frontmatter = exporter._generate_frontmatter(
            document_id="abc123",
            title="Test Document",
            source_url="https://docs.google.com/document/d/abc123",
            doc_type=DocumentType.DOCUMENT,
        )

        assert frontmatter.startswith("---\n")
        assert frontmatter.endswith("---\n\n")
        assert "title: Test Document" in frontmatter
        assert "source: https://docs.google.com/document/d/abc123" in frontmatter
        assert "synced_at:" in frontmatter

    def test_generate_frontmatter_with_custom_fields(self):
        """Test frontmatter generation with custom fields."""
        config = GoogleDriveExporterConfig(
            enable_frontmatter=True, frontmatter_fields={"date": "2024-01-15", "meeting_type": "weekly-sync"}
        )
        exporter = GoogleDriveExporter(config)

        frontmatter = exporter._generate_frontmatter(
            document_id="abc123",
            title="Meeting Notes",
            source_url="https://docs.google.com/document/d/abc123",
            doc_type=DocumentType.DOCUMENT,
        )

        assert "title: Meeting Notes" in frontmatter
        assert "date: '2024-01-15'" in frontmatter or "date: 2024-01-15" in frontmatter
        assert "meeting_type: weekly-sync" in frontmatter

    def test_custom_fields_override_auto_fields(self):
        """Test that custom fields override auto-generated fields."""
        config = GoogleDriveExporterConfig(
            enable_frontmatter=True, frontmatter_fields={"title": "Custom Title", "custom_field": "value"}
        )
        exporter = GoogleDriveExporter(config)

        frontmatter = exporter._generate_frontmatter(
            document_id="abc123",
            title="Auto Title",
            source_url="https://docs.google.com/document/d/abc123",
            doc_type=DocumentType.DOCUMENT,
        )

        assert "title: Custom Title" in frontmatter
        assert "title: Auto Title" not in frontmatter
        assert "custom_field: value" in frontmatter

    def test_frontmatter_disabled_by_default(self):
        """Test that frontmatter is disabled by default in config."""
        config = GoogleDriveExporterConfig()
        assert config.enable_frontmatter is False
        assert config.frontmatter_fields == {}


@pytest.mark.unit
class TestUnwrapGoogleRedirectUrls:
    """Tests for _unwrap_google_redirect_urls static method."""

    def test_standard_redirect_url(self):
        """Standard Google redirect URL is replaced with the real target."""
        text = (
            "[GA - The Source]"
            "(https://www.google.com/url?q=https://source.redhat.com/groups/public/commonreleaseterms"
            "%2Fonprem%2Fgeneral_availability&sa=D&source=editors&ust=1773076718514988"
            "&usg=AOvVaw2n-EnUBtpTSQwuz4i9C_O_)"
        )
        result = GoogleDriveExporter._unwrap_google_redirect_urls(text)
        assert result == (
            "[GA - The Source]"
            "(https://source.redhat.com/groups/public/commonreleaseterms/onprem/general_availability)"
        )

    def test_url_encoded_characters_in_q(self):
        """Percent-encoded characters in the q value are decoded."""
        text = (
            "[Sheet link]"
            "(https://www.google.com/url?q=https://docs.google.com/spreadsheets/d/abc%3Ftab%3Dt.0"
            "&sa=D&source=editors&ust=123&usg=XYZ)"
        )
        result = GoogleDriveExporter._unwrap_google_redirect_urls(text)
        assert result == "[Sheet link](https://docs.google.com/spreadsheets/d/abc?tab=t.0)"

    def test_non_google_redirect_url_unchanged(self):
        """URLs that are not Google redirects are left untouched."""
        text = "[Example](https://example.com/some/path?foo=bar)"
        result = GoogleDriveExporter._unwrap_google_redirect_urls(text)
        assert result == text

    def test_multiple_redirect_urls_in_document(self):
        """All Google redirect URLs in a document are unwrapped."""
        text = (
            "See [link A](https://www.google.com/url?q=https://a.com&sa=D&usg=AA) "
            "and [link B](https://www.google.com/url?q=https://b.com%2Fpath&sa=D&usg=BB)."
        )
        result = GoogleDriveExporter._unwrap_google_redirect_urls(text)
        assert result == "See [link A](https://a.com) and [link B](https://b.com/path)."

    def test_redirect_url_missing_q_parameter(self):
        """Google redirect URL with no q param is left untouched."""
        text = "[Bad link](https://www.google.com/url?sa=D&source=editors&usg=XYZ)"
        result = GoogleDriveExporter._unwrap_google_redirect_urls(text)
        assert result == text

    def test_mixed_links(self):
        """Document with both redirect and normal links — only redirects are changed."""
        text = (
            "[Normal](https://example.com) "
            "[Wrapped](https://www.google.com/url?q=https://real.com&sa=D&usg=ZZ)"
        )
        result = GoogleDriveExporter._unwrap_google_redirect_urls(text)
        assert result == "[Normal](https://example.com) [Wrapped](https://real.com)"
