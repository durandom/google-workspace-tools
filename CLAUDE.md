# CLAUDE.md

This file provides guidance to Claude Code when working with code in this repository.

## Project Overview

`google-workspace-tools` is a Python library and CLI for exporting Google Drive documents (Docs, Sheets, Slides), Gmail messages, and Google Calendar events to various formats with link following capabilities and optional AI agent integration.

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
│   ├── types.py         # DocumentType (EMAIL, CALENDAR_EVENT added), ExportFormat, DocumentConfig
│   ├── config.py        # GoogleDriveExporterConfig (includes Gmail/Calendar scopes)
│   ├── filters.py       # GmailSearchFilter, CalendarEventFilter (NEW)
│   └── exporter.py      # GoogleDriveExporter (main logic + Gmail/Calendar methods)
├── cli/
│   └── app.py           # Typer CLI application (export-gmail, export-calendar, list-calendars)
└── toolkit/
    ├── __init__.py      # Import guard for optional agno
    └── gdrive.py        # GoogleDriveTools (Agno toolkit)
```

### Key Classes

- **GoogleDriveExporter**: Core class handling authentication, export, and link following for Drive docs, Gmail, and Calendar
- **GoogleDriveExporterConfig**: Pydantic config for credentials, formats, depths, OAuth scopes
- **GmailSearchFilter**: Pydantic model for Gmail message filtering (query, dates, labels, max_results)
- **CalendarEventFilter**: Pydantic model for Calendar event filtering (time ranges, calendars, query)
- **GoogleDriveTools**: Agno Toolkit wrapper (optional `[agno]` extra)

### Export Flow

**Drive Documents:**
1. `extract_document_id()` - Parse URL to get document ID
2. `detect_document_type()` - Determine if Doc, Sheet, or Slides
3. `get_document_metadata()` - Fetch title and mime type (multiple fallback methods)
4. `_export_single_format()` - Download and convert (HTML→MD if needed)
5. For spreadsheets with markdown format:
   - `export_spreadsheet_as_markdown()` - XLSX → MarkItDown → single .md file (all sheets)
   - `export_spreadsheet_sheets_separate()` - XLSX → MarkItDown → separate .md files (per sheet)
6. `_extract_links_from_html()` - Find linked documents from HTML files for recursive export
7. `_extract_links_from_text()` - Extract Drive links from HTML/text content (used by Gmail/Calendar)

**Gmail Export:**
1. `export_emails()` - Main entry point
2. `_fetch_messages_paginated()` - Generator for batch fetching messages with Gmail search query
3. `_fetch_message_content()` - Get full message (headers, body, attachments)
4. `_extract_message_body()` - Parse MIME parts to extract text/HTML bodies (BFS traversal)
5. `_extract_email_attachments()` - Extract attachment metadata (filename, size, mime_type)
6. `_group_messages_by_thread()` - Group by threadId, sort by internalDate
7. `_export_email_thread_as_json()` or `_export_email_thread_as_markdown()` - Export to files
8. `_extract_links_from_text()` - Find Drive links in email bodies for link following

**Calendar Export:**
1. `export_calendar_events()` - Main entry point
2. `list_calendars()` - List all accessible calendars
3. `_fetch_events_paginated()` - Generator for batch fetching events (supports multiple calendars)
4. `_export_calendar_event_as_json()` or `_export_calendar_event_as_markdown()` - Export to files
5. `_extract_links_from_text()` - Find Drive links in descriptions/attachments for link following

### Recent Updates (2025-12-18)

**1. Spreadsheet Markdown Export**: Added LLM-optimized spreadsheet export using Microsoft MarkItDown.

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

**2. Gmail and Calendar Export**: Added export capabilities for emails and calendar events.

- **New file**: `src/google_workspace_tools/core/filters.py` with Pydantic filter models
- **New DocumentType enum values**: `EMAIL`, `CALENDAR_EVENT`
- **New export formats**: `EMAIL_EXPORT_FORMATS`, `CALENDAR_EXPORT_FORMATS` (json, md)
- **New filter models**:
  - `GmailSearchFilter(query, after_date, before_date, labels, has_attachment, max_results, include_spam_trash)`
  - `CalendarEventFilter(time_min, time_max, calendar_ids, query, single_events, max_results, order_by)`
- **New methods in GoogleDriveExporter**:
  - Gmail: `export_emails()`, `_fetch_messages_paginated()`, `_fetch_message_content()`, `_extract_message_body()`, `_extract_email_attachments()`, `_group_messages_by_thread()`, `_export_email_thread_as_json()`, `_export_email_thread_as_markdown()`
  - Calendar: `export_calendar_events()`, `list_calendars()`, `_fetch_events_paginated()`, `_export_calendar_event_as_json()`, `_export_calendar_event_as_markdown()`
  - Shared: `_extract_links_from_text()` - Extract Drive links from HTML/text content
- **New service properties**: `gmail_service`, `calendar_service` (following existing pattern)
- **New CLI commands**:
  - `export-gmail` - Export Gmail messages with filters
  - `export-calendar` - Export Calendar events with filters
  - `list-calendars` - List accessible calendars
- **Link following**: Automatically extract and export Drive links from email bodies and calendar descriptions
- **Tests**: `tests/unit/test_gmail_export.py`, `tests/unit/test_calendar_export.py`, `tests/e2e/test_cli_gmail.py`, `tests/e2e/test_cli_calendar.py`

### Authentication

Uses OAuth 2.0 with `InstalledAppFlow`. Token is cached to avoid re-auth.
Multiple API fallbacks: Drive API → Docs/Sheets/Slides APIs.

**OAuth Scopes** (read-only):
- `drive.readonly` - Google Drive files
- `documents.readonly` - Google Docs
- `spreadsheets.readonly` - Google Sheets
- `presentations.readonly` - Google Slides
- **`gmail.readonly`** - Gmail messages (NEW)
- **`calendar.readonly`** - Google Calendar events (NEW)

**Scope mismatch detection**: The `_authenticate()` method automatically detects when requested scopes don't match cached credentials and triggers re-authentication.

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
