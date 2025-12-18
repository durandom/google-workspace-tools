# CLAUDE.md

This file provides guidance to Claude Code when working with code in this repository.

## Project Overview

`google-workspace-tools` is a Python library and CLI for exporting Google Drive documents (Docs, Sheets, Slides) to various formats with link following capabilities and optional AI agent integration.

## Development Commands

```bash
# Install dependencies
uv sync --group dev

# Run tests
uv run pytest

# Run tests with coverage
uv run pytest --cov=src --cov-report=term-missing

# Linting
uv run ruff check
uv run ruff format

# Type checking
uv run mypy src/

# Run CLI
uv run gwt --help
uv run gwt download https://docs.google.com/... -f md
uv run gwt formats
```

## Architecture

### Package Structure

```
src/google_workspace_tools/
├── __init__.py          # Public API exports, main() entry point
├── settings.py          # Pydantic settings (GWT_ env prefix)
├── core/
│   ├── types.py         # DocumentType, ExportFormat, DocumentConfig
│   ├── config.py        # GoogleDriveExporterConfig
│   └── exporter.py      # GoogleDriveExporter (main logic)
├── cli/
│   └── app.py           # Typer CLI application
└── toolkit/
    ├── __init__.py      # Import guard for optional agno
    └── gdrive.py        # GoogleDriveTools (Agno toolkit)
```

### Key Classes

- **GoogleDriveExporter**: Core class handling authentication, export, and link following
- **GoogleDriveExporterConfig**: Pydantic config for credentials, formats, depths
- **GoogleDriveTools**: Agno Toolkit wrapper (optional `[agno]` extra)

### Export Flow

1. `extract_document_id()` - Parse URL to get document ID
2. `detect_document_type()` - Determine if Doc, Sheet, or Slides
3. `get_document_metadata()` - Fetch title and mime type (multiple fallback methods)
4. `_export_single_format()` - Download and convert (HTML→MD if needed)
5. For spreadsheets with markdown format:
   - `export_spreadsheet_as_markdown()` - XLSX → MarkItDown → single .md file (all sheets)
   - `export_spreadsheet_sheets_separate()` - XLSX → MarkItDown → separate .md files (per sheet)
6. `_extract_links_from_html()` - Find linked documents for recursive export

### Recent Updates (2025-12-18)

**Spreadsheet Markdown Export**: Added LLM-optimized spreadsheet export using Microsoft MarkItDown.

- **New dependencies**: `markitdown>=0.1.0`, `openpyxl>=3.1.0`, `html-to-markdown>=2.14.0` (updated from 1.8.0)
- **New config options**:
  - `spreadsheet_export_mode: Literal["combined", "separate", "csv"]` (default: "combined")
  - `keep_intermediate_xlsx: bool` (default: True)
- **New methods in GoogleDriveExporter**:
  - `export_spreadsheet_as_markdown()` - Export all sheets as single markdown file
  - `export_spreadsheet_sheets_separate()` - Export each sheet as separate markdown file
- **CLI options**:
  - `--spreadsheet-mode/-s` (combined|separate|csv)
  - `--keep-xlsx/--no-keep-xlsx`
- **Export flow**: Google Sheets → XLSX (via Drive API) → MarkItDown → Markdown tables
- **Tests**: `tests/unit/test_spreadsheet_markdown.py`

### Authentication

Uses OAuth 2.0 with `InstalledAppFlow`. Token is cached to avoid re-auth.
Multiple API fallbacks: Drive API → Docs/Sheets/Slides APIs.

## Testing

- Unit tests in `tests/unit/` - Config, URL extraction, format detection
- E2E tests in `tests/e2e/` - CLI commands via `typer.testing.CliRunner`
- Most tests don't require actual Google credentials

## Key Dependencies

- `google-api-python-client` - Google Drive/Docs/Sheets/Slides APIs
- `html-to-markdown>=2.14.0` - Convert Google Docs HTML to Markdown (Rust-backed, fast)
- `markitdown>=0.1.0` - Convert XLSX/Office documents to Markdown (Microsoft, LLM-optimized)
- `openpyxl>=3.1.0` - Read/write XLSX files for sheet separation
- `typer` + `rich` - CLI framework
- `pydantic` + `pydantic-settings` - Configuration
- `loguru` - Logging
- `agno` (optional) - AI agent toolkit integration
