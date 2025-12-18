"""Tests for spreadsheet to markdown conversion."""

from unittest.mock import MagicMock, patch

import pytest

from google_workspace_tools.core.config import GoogleDriveExporterConfig
from google_workspace_tools.core.exporter import GoogleDriveExporter


class TestSpreadsheetMarkdownExport:
    """Tests for spreadsheet markdown export functionality."""

    @pytest.fixture
    def exporter(self, tmp_path):
        """Create an exporter instance with test configuration."""
        config = GoogleDriveExporterConfig(
            target_directory=tmp_path,
            export_format="md",
            spreadsheet_export_mode="combined",
            keep_intermediate_xlsx=True,
        )
        return GoogleDriveExporter(config)

    @pytest.fixture
    def mock_markitdown(self):
        """Mock MarkItDown library."""
        with patch("markitdown.MarkItDown") as mock:
            mock_instance = MagicMock()
            mock_instance.convert.return_value = MagicMock(
                text_content="# Test Sheet\n\n| A | B |\n|---|---|\n| 1 | 2 |\n"
            )
            mock.return_value = mock_instance
            yield mock

    def test_config_spreadsheet_export_mode_default(self):
        """Test that spreadsheet_export_mode defaults to 'combined'."""
        config = GoogleDriveExporterConfig()
        assert config.spreadsheet_export_mode == "combined"

    def test_config_spreadsheet_export_mode_options(self):
        """Test valid spreadsheet_export_mode values."""
        for mode in ["combined", "separate", "csv"]:
            config = GoogleDriveExporterConfig(spreadsheet_export_mode=mode)
            assert config.spreadsheet_export_mode == mode

    def test_config_keep_intermediate_xlsx_default(self):
        """Test that keep_intermediate_xlsx defaults to True."""
        config = GoogleDriveExporterConfig()
        assert config.keep_intermediate_xlsx is True

    def test_config_keep_intermediate_xlsx_false(self):
        """Test setting keep_intermediate_xlsx to False."""
        config = GoogleDriveExporterConfig(keep_intermediate_xlsx=False)
        assert config.keep_intermediate_xlsx is False

    @patch.object(GoogleDriveExporter, "_export_single_format")
    def test_export_spreadsheet_as_markdown_success(self, mock_export, exporter, tmp_path, mock_markitdown):
        """Test successful spreadsheet to markdown conversion."""
        mock_export.return_value = True

        output_path = tmp_path / "test.md"
        result = exporter.export_spreadsheet_as_markdown(
            spreadsheet_id="abc123",
            output_path=output_path,
            spreadsheet_title="Test Spreadsheet",
            source_url="https://docs.google.com/spreadsheets/d/abc123",
        )

        assert result is True
        assert output_path.exists()
        content = output_path.read_text()
        assert "# Test Sheet" in content
        assert "| A | B |" in content

    @patch.object(GoogleDriveExporter, "_export_single_format")
    def test_export_spreadsheet_as_markdown_with_frontmatter(self, mock_export, tmp_path, mock_markitdown):
        """Test spreadsheet markdown export with frontmatter enabled."""
        config = GoogleDriveExporterConfig(
            target_directory=tmp_path,
            export_format="md",
            enable_frontmatter=True,
        )
        exporter = GoogleDriveExporter(config)
        mock_export.return_value = True

        output_path = tmp_path / "test.md"
        result = exporter.export_spreadsheet_as_markdown(
            spreadsheet_id="abc123",
            output_path=output_path,
            spreadsheet_title="Test Spreadsheet",
            source_url="https://docs.google.com/spreadsheets/d/abc123",
        )

        assert result is True
        content = output_path.read_text()
        assert "---" in content
        assert "title: Test Spreadsheet" in content
        assert "source: https://docs.google.com/spreadsheets/d/abc123" in content
        assert "synced_at:" in content

    @patch.object(GoogleDriveExporter, "_export_single_format")
    def test_export_spreadsheet_as_markdown_removes_xlsx(self, mock_export, tmp_path, mock_markitdown):
        """Test that intermediate XLSX is removed when keep_intermediate_xlsx=False."""
        config = GoogleDriveExporterConfig(
            target_directory=tmp_path,
            export_format="md",
            keep_intermediate_xlsx=False,
        )
        exporter = GoogleDriveExporter(config)
        mock_export.return_value = True

        output_path = tmp_path / "test.md"
        xlsx_path = output_path.with_suffix(".xlsx")

        # Create dummy XLSX file to simulate export
        xlsx_path.write_text("dummy xlsx content")

        result = exporter.export_spreadsheet_as_markdown(
            spreadsheet_id="abc123",
            output_path=output_path,
            spreadsheet_title="Test Spreadsheet",
        )

        assert result is True
        assert output_path.exists()
        assert not xlsx_path.exists()  # Should be removed

    @patch.object(GoogleDriveExporter, "_export_single_format")
    def test_export_spreadsheet_as_markdown_keeps_xlsx(self, mock_export, tmp_path, mock_markitdown):
        """Test that intermediate XLSX is kept when keep_intermediate_xlsx=True."""
        config = GoogleDriveExporterConfig(
            target_directory=tmp_path,
            export_format="md",
            keep_intermediate_xlsx=True,
        )
        exporter = GoogleDriveExporter(config)
        mock_export.return_value = True

        output_path = tmp_path / "test.md"
        xlsx_path = output_path.with_suffix(".xlsx")

        # Create dummy XLSX file to simulate export
        xlsx_path.write_text("dummy xlsx content")

        result = exporter.export_spreadsheet_as_markdown(
            spreadsheet_id="abc123",
            output_path=output_path,
            spreadsheet_title="Test Spreadsheet",
        )

        assert result is True
        assert output_path.exists()
        assert xlsx_path.exists()  # Should be kept

    @patch.object(GoogleDriveExporter, "_export_single_format")
    def test_export_spreadsheet_as_markdown_export_failure(self, mock_export, exporter, tmp_path, mock_markitdown):
        """Test handling of XLSX export failure."""
        mock_export.return_value = False

        output_path = tmp_path / "test.md"
        result = exporter.export_spreadsheet_as_markdown(
            spreadsheet_id="abc123",
            output_path=output_path,
            spreadsheet_title="Test Spreadsheet",
        )

        assert result is False
        assert not output_path.exists()

    def test_export_spreadsheet_as_markdown_missing_library(self, exporter, tmp_path):
        """Test handling when MarkItDown is not installed."""
        with patch("builtins.__import__", side_effect=ImportError("No module named 'markitdown'")):
            output_path = tmp_path / "test.md"
            result = exporter.export_spreadsheet_as_markdown(
                spreadsheet_id="abc123",
                output_path=output_path,
                spreadsheet_title="Test Spreadsheet",
            )

            assert result is False


class TestSpreadsheetExportModes:
    """Tests for different spreadsheet export modes."""

    def test_combined_mode_default(self):
        """Test that 'combined' is the default mode."""
        config = GoogleDriveExporterConfig()
        assert config.spreadsheet_export_mode == "combined"

    def test_separate_mode(self):
        """Test 'separate' mode configuration."""
        config = GoogleDriveExporterConfig(spreadsheet_export_mode="separate")
        assert config.spreadsheet_export_mode == "separate"

    def test_csv_mode(self):
        """Test 'csv' mode configuration."""
        config = GoogleDriveExporterConfig(spreadsheet_export_mode="csv")
        assert config.spreadsheet_export_mode == "csv"
