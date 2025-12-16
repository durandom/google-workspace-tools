"""Tests for configuration models."""

import pytest
from pathlib import Path

from google_workspace_tools.core.config import GoogleDriveExporterConfig
from google_workspace_tools.core.types import DocumentType, ExportFormat, DocumentConfig


class TestGoogleDriveExporterConfig:
    """Tests for GoogleDriveExporterConfig."""

    def test_default_config(self):
        """Test default configuration values."""
        config = GoogleDriveExporterConfig()

        assert config.credentials_path == Path(".client_secret.googleusercontent.com.json")
        assert config.token_path == Path("tmp/token_drive.json")
        assert config.target_directory == Path("exports")
        assert config.export_format == "html"
        assert config.link_depth == 0
        assert config.follow_links is False

    def test_custom_config(self, tmp_path: Path):
        """Test custom configuration values."""
        config = GoogleDriveExporterConfig(
            credentials_path=tmp_path / "creds.json",
            target_directory=tmp_path / "output",
            export_format="md",
            link_depth=2,
            follow_links=True,
        )

        assert config.credentials_path == tmp_path / "creds.json"
        assert config.target_directory == tmp_path / "output"
        assert config.export_format == "md"
        assert config.link_depth == 2
        assert config.follow_links is True

    def test_path_coercion(self):
        """Test that string paths are converted to Path objects."""
        config = GoogleDriveExporterConfig(
            target_directory="./my/output/dir"  # type: ignore
        )
        assert isinstance(config.target_directory, Path)
        assert config.target_directory == Path("./my/output/dir")

    def test_link_depth_validation(self):
        """Test link_depth validation bounds."""
        # Valid depths
        for depth in [0, 1, 2, 3, 4, 5]:
            config = GoogleDriveExporterConfig(link_depth=depth)
            assert config.link_depth == depth

        # Invalid depths
        with pytest.raises(ValueError):
            GoogleDriveExporterConfig(link_depth=-1)

        with pytest.raises(ValueError):
            GoogleDriveExporterConfig(link_depth=6)


class TestDocumentType:
    """Tests for DocumentType enum."""

    def test_document_types(self):
        """Test document type values."""
        assert DocumentType.DOCUMENT.value == "document"
        assert DocumentType.SPREADSHEET.value == "spreadsheet"
        assert DocumentType.PRESENTATION.value == "presentation"
        assert DocumentType.UNKNOWN.value == "unknown"


class TestExportFormat:
    """Tests for ExportFormat model."""

    def test_export_format_creation(self):
        """Test creating an ExportFormat."""
        fmt = ExportFormat(
            extension="pdf",
            mime_type="application/pdf",
            description="Portable Document Format",
        )

        assert fmt.extension == "pdf"
        assert fmt.mime_type == "application/pdf"
        assert fmt.description == "Portable Document Format"

    def test_export_format_optional_description(self):
        """Test ExportFormat with optional description."""
        fmt = ExportFormat(extension="txt", mime_type="text/plain")

        assert fmt.extension == "txt"
        assert fmt.description is None


class TestDocumentConfig:
    """Tests for DocumentConfig dataclass."""

    def test_document_config_defaults(self):
        """Test default values."""
        doc = DocumentConfig(url="https://example.com", document_id="abc123")

        assert doc.url == "https://example.com"
        assert doc.document_id == "abc123"
        assert doc.depth == 0
        assert doc.comment == ""

    def test_document_config_full(self):
        """Test with all values."""
        doc = DocumentConfig(
            url="https://docs.google.com/document/d/abc123/edit",
            document_id="abc123",
            depth=2,
            comment="Important document",
        )

        assert doc.depth == 2
        assert doc.comment == "Important document"
