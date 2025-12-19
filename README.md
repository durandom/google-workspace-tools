# Google Workspace Tools

[![PyPI version](https://img.shields.io/pypi/v/google-workspace-tools.svg)](https://pypi.org/project/google-workspace-tools/)
[![Python versions](https://img.shields.io/pypi/pyversions/google-workspace-tools.svg)](https://pypi.org/project/google-workspace-tools/)
[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![CI](https://github.com/durandom/google-workspace-tools/actions/workflows/ci.yml/badge.svg)](https://github.com/durandom/google-workspace-tools/actions/workflows/ci.yml)

A Python toolkit for exporting and managing Google Drive documents with CLI and optional AI agent integration.

## Features

- **Multi-format Export**: Export Google Docs, Sheets, and Slides to various formats (PDF, DOCX, Markdown, CSV, XLSX, PPTX, etc.)
- **Gmail Export**: Export email threads to JSON or Markdown with search, filters, and date ranges
- **Calendar Export**: Export Google Calendar events to JSON or Markdown with time ranges and queries
- **HTML to Markdown**: Automatic conversion of Google Docs to clean Markdown (using html-to-markdown 2.14+)
- **Spreadsheet → Markdown**: Export Google Sheets as LLM-optimized markdown tables (using Microsoft MarkItDown)
- **Frontmatter Support**: Add YAML frontmatter to markdown files with custom metadata
- **Custom Output Paths**: Export to specific file paths with custom names
- **Link Following**: Recursively export linked documents (including from emails/calendar) up to configurable depth
- **Mirror Configuration**: Batch export documents from a configuration file
- **CLI Tool**: Full-featured command-line interface (`gwt`)
- **Agent Integration**: Optional Agno toolkit for AI assistant workflows

## Installation

```bash
# Core library and CLI
pip install google-workspace-tools

# With Agno toolkit support for AI agents
pip install google-workspace-tools[agno]
```

## Quick Start

### CLI Usage

```bash
# Authenticate with Google
gwt auth

# Download a document as Markdown
gwt download https://docs.google.com/document/d/abc123/edit -f md

# Download multiple documents
gwt download abc123 def456 -f pdf -o ./downloads

# Follow links 2 levels deep
gwt download https://docs.google.com/.../edit -d 2

# Mirror documents from config file
gwt mirror sources.txt -o ./mirror

# Show authenticated user
gwt whoami

# List supported formats
gwt formats -t spreadsheet

# Export Gmail messages
gwt mail --query "from:boss@example.com" -f md

# Export calendar events
gwt calendar --after 2024-01-01 --before 2024-12-31

# List calendars
gwt calendar  # No filters = list mode

# Machine-readable JSON output (for automation/LLMs)
gwt --json download URL -f md
gwt --json mail --query "project alpha"
gwt --json calendar --after 2024-01-01
```

### Machine-Readable Output (JSON)

All data export commands support a global `--json` flag for structured, machine-readable output. This is ideal for:
- **CI/CD pipelines** and automation scripts
- **LLM consumption** (Claude, GPT, etc.) for document processing
- **Integration** with other tools and workflows
- **Programmatic parsing** without regex or text manipulation

```bash
# Download with JSON output
gwt --json download https://docs.google.com/.../edit -f md

# Export calendar events as JSON
gwt --json calendar --after 2024-01-01 --before 2024-12-31

# Mirror documents with structured output
gwt --json mirror sources.txt -o ./exports

# List calendars in JSON format
gwt --json calendar
```

**Example JSON output (download command):**
```json
{
  "command": "download",
  "success": true,
  "timestamp": "2024-01-15T10:30:00Z",
  "version": "0.3.0",
  "errors": [],
  "documents": [
    {
      "document_id": "abc123",
      "title": "Project Documentation",
      "source_url": "https://docs.google.com/document/d/abc123/edit",
      "doc_type": "document",
      "files": [
        {
          "format": "md",
          "path": "/absolute/path/to/exports/Project_Documentation.md",
          "size_bytes": 15420
        }
      ],
      "link_following_depth": 2,
      "linked_documents_count": 3,
      "errors": []
    }
  ],
  "total_files_exported": 4,
  "output_directory": "/absolute/path/to/exports",
  "link_following_enabled": true,
  "max_link_depth": 2
}
```

**Example JSON output (calendar list):**
```json
{
  "command": "calendar",
  "success": true,
  "timestamp": "2024-01-15T10:30:00Z",
  "version": "0.3.0",
  "errors": [],
  "calendars": [
    {
      "id": "primary",
      "summary": "My Calendar",
      "primary": true
    },
    {
      "id": "work@company.com",
      "summary": "Work Calendar",
      "primary": false
    }
  ],
  "total_count": 2
}
```

**JSON output characteristics:**
- **Flat structure**: Minimal nesting for easier parsing
- **Self-documenting**: Clear field names and types
- **Complete metadata**: Timestamps, versions, file sizes, error tracking
- **Absolute paths**: Full file paths for reliable access
- **Error handling**: Valid JSON even on failures with error details

**Supported commands:**
- `download` - Document export results
- `mail` - Email thread/message export
- `calendar` - Calendar events or calendar list
- `mirror` - Batch document mirroring

**Note:** The `--json` flag outputs structured data to stdout while suppressing progress messages. Errors and warnings are logged to stderr.

### Frontmatter Support

Add YAML frontmatter to markdown files for integration with static site generators, note-taking apps, or automation workflows:

```bash
# Enable frontmatter with custom fields
gwt download URL -o meetings/2024-01-15.md --enable-frontmatter \
  -m "date=2024-01-15" \
  -m "meeting_type=weekly-sync" \
  -m "tags=ai,planning"

# Load frontmatter from YAML file
cat > metadata.yaml <<EOF
date: 2024-01-15
meeting_type: weekly-sync
tags:
  - ai
  - planning
attendees:
  - Alice
  - Bob
EOF

gwt download URL -o notes.md --frontmatter-file metadata.yaml
```

**Auto-injected fields** (always included when frontmatter is enabled):
- `title`: Document title from Google Drive
- `source`: Original Google Drive URL
- `synced_at`: ISO timestamp when document was downloaded

**Output example:**
```markdown
---
title: Weekly AI Sync - Jan 15
source: https://docs.google.com/document/d/abc123/edit
synced_at: 2024-01-15T10:30:00Z
date: 2024-01-15
meeting_type: weekly-sync
tags:
  - ai
  - planning
---

# Meeting Notes
...document content...
```

**Custom fields override auto fields** - if you provide a `title` in frontmatter, it will replace the auto-detected title.

### Spreadsheet Export Options (LLM-Optimized)

Google Sheets can be exported as Markdown tables optimized for LLM consumption using Microsoft's MarkItDown library:

```bash
# Export spreadsheet as single markdown file with all sheets (default)
gwt download SPREADSHEET_URL -f md

# Export each sheet as separate markdown file
gwt download SPREADSHEET_URL -f md -s separate

# Legacy CSV export (one CSV per sheet)
gwt download SPREADSHEET_URL -f md -s csv

# Control intermediate XLSX file retention
gwt download SPREADSHEET_URL -f md --keep-xlsx    # Keep (default)
gwt download SPREADSHEET_URL -f md --no-keep-xlsx  # Remove after conversion
```

**Export modes:**
- **`combined`** (default): Single `.md` file with all sheets as H2 sections with markdown tables
- **`separate`**: Each sheet exported as individual `.md` file in a `{name}_sheets/` directory
- **`csv`**: Legacy mode - individual CSV files (loses formatting)

**Example output (combined mode):**
```markdown
## Sales Data

| Product | Q1 | Q2 | Q3 | Q4 |
|---------|----|----|----|----|
| Widget A | 100 | 150 | 200 | 175 |
| Widget B | 50 | 75 | 100 | 125 |

## Summary

| Metric | Value |
|--------|-------|
| Total Revenue | $450,000 |
| Growth Rate | 23% |
```

**Why markdown for spreadsheets?**
- **Lower token count**: Research shows Markdown uses significantly fewer tokens than HTML/XML for LLMs
- **Better structure**: Tables preserved in LLM-friendly format
- **Multi-sheet support**: All sheets in one context-ready document
- **Intermediate XLSX preserved**: Keep the original Excel file for manual review

### Gmail Export

Export Gmail messages with full search capabilities and flexible output formats:

```bash
# Export by search query
gwt mail --query "from:boss@example.com subject:meeting"

# Export by date range
gwt mail --after 2024-01-01 --before 2024-12-31

# Filter by labels
gwt mail --labels work,important

# Export with attachments query
gwt mail --query "has:attachment" -n 50

# Export as JSON (thread-aware)
gwt mail --query "project alpha" -f json

# Follow Google Drive links in emails
gwt mail --query "has:attachment" --depth 2
```

**Export modes:**
- **`thread`** (default): Groups messages by conversation thread
- **`individual`**: Each message exported separately

**Output organization:**
```
exports/emails/
├── threads/
│   └── 2024-01/
│       ├── thread_abc123_meeting-notes.md
│       └── thread_def456_budget-review.json
└── messages/  # (individual mode)
    └── 2024-01/
        └── msg_xyz789_invoice.md
```

**Markdown format includes:**
- YAML frontmatter with thread metadata, participants, labels
- Message-by-message breakdown with headers (From, To, Cc, Date)
- HTML→Markdown conversion for email bodies
- Attachment metadata (filename, size)
- Extracted Google Drive links

**JSON format includes:**
- Complete thread structure with all messages
- Full headers, bodies (text + HTML), attachment metadata
- Automatically extracted Drive links for link following

### Google Calendar Export

Export calendar events with flexible time ranges and formatting:

```bash
# Export events from date range
gwt calendar --after 2024-01-01 --before 2024-03-31

# Export from specific calendar
gwt calendar --calendar work@company.com --after 2024-01-01

# Search events by keyword
gwt calendar --query "sprint planning" -n 100

# Export as JSON
gwt calendar -f json --after 2024-01-01

# List all accessible calendars
gwt calendar  # No filters = list mode

# Follow Drive links in event descriptions
gwt calendar --depth 2 --after 2024-01-01
```

**Output organization:**
```
exports/calendar/
├── primary/
│   └── 2024-01/
│       ├── event_abc123_team-meeting_2024-01-15.md
│       └── event_def456_planning-session_2024-01-20.md
└── work_company_com/
    └── 2024-02/
        └── event_xyz789_all-hands_2024-02-01.json
```

**Markdown format includes:**
- YAML frontmatter with event metadata (ID, calendar, start/end times, attendee count)
- Event details (when, where, organizer)
- Attendee list with RSVP status and optional/organizer flags
- HTML→Markdown conversion for descriptions
- Attachment links (Google Drive documents)

**JSON format includes:**
- Complete event data from Calendar API
- Full attendee details, recurrence rules, attachments
- Automatically extracted Drive links

### Custom Output Paths

Export to specific file paths instead of using auto-generated names:

```bash
# Single document to specific path
gwt download URL -o meetings/2024/jan/weekly-sync.md

# Multiple documents to directory (standard behavior)
gwt download URL1 URL2 -o meetings/archive/
```

### Library Usage

```python
from pathlib import Path
from google_workspace_tools import GoogleDriveExporter, GoogleDriveExporterConfig

# Configure the exporter
config = GoogleDriveExporterConfig(
    export_format="md",
    target_directory=Path("./exports"),
    credentials_path=Path(".client_secret.googleusercontent.com.json"),
)

# Create exporter and download documents
exporter = GoogleDriveExporter(config)
results = exporter.export_document("https://docs.google.com/document/d/abc123/edit")

# Export with link following
config.follow_links = True
config.link_depth = 2
exporter.export_document("https://docs.google.com/document/d/abc123/edit")

# Export with frontmatter
config_with_frontmatter = GoogleDriveExporterConfig(
    export_format="md",
    enable_frontmatter=True,
    frontmatter_fields={
        "date": "2024-01-15",
        "meeting_type": "weekly-sync",
        "tags": ["ai", "planning"]
    }
)
exporter = GoogleDriveExporter(config_with_frontmatter)
exporter.export_document(
    "https://docs.google.com/document/d/abc123/edit",
    output_path=Path("meetings/2024-01-15.md")
)

# Export spreadsheet as markdown (LLM-optimized)
spreadsheet_config = GoogleDriveExporterConfig(
    export_format="md",
    spreadsheet_export_mode="combined",  # or "separate", "csv"
    keep_intermediate_xlsx=True,  # Keep XLSX file
)
exporter = GoogleDriveExporter(spreadsheet_config)
exporter.export_document("https://docs.google.com/spreadsheets/d/xyz789/edit")

# Mirror from config file
exporter.mirror_documents(Path("sources.txt"))

# Export Gmail messages
from google_workspace_tools import GmailSearchFilter

gmail_filter = GmailSearchFilter(
    query="from:boss@example.com",
    after_date=datetime(2024, 1, 1),
    labels=["work", "important"],
    max_results=100
)

config = GoogleDriveExporterConfig(
    credentials_path=Path(".client_secret.googleusercontent.com.json"),
    target_directory=Path("./exports"),
)
exporter = GoogleDriveExporter(config)

# Export emails as markdown (thread mode by default)
exported_emails = exporter.export_emails(
    filters=gmail_filter,
    export_format="md",
    export_mode="thread",  # or "individual"
    output_directory=Path("./exports/emails"),
)

# Export Google Calendar events
from google_workspace_tools import CalendarEventFilter

calendar_filter = CalendarEventFilter(
    time_min=datetime(2024, 1, 1),
    time_max=datetime(2024, 12, 31),
    calendar_ids=["work@company.com", "personal@gmail.com"],
    query="sprint planning",
    max_results=250
)

exported_events = exporter.export_calendar_events(
    filters=calendar_filter,
    export_format="md",
    output_directory=Path("./exports/calendar"),
)

# List all calendars
calendars = exporter.list_calendars()
for cal in calendars:
    print(f"{cal['summary']}: {cal['id']}")

# Export with link following from emails/calendar
config_with_links = GoogleDriveExporterConfig(
    follow_links=True,
    link_depth=2
)
exporter = GoogleDriveExporter(config_with_links)

# Gmail links will be followed (Drive docs attached or linked in emails)
exported = exporter.export_emails(
    filters=GmailSearchFilter(query="has:attachment"),
    export_format="md"
)

# Calendar links will be followed (Drive docs attached or in descriptions)
exported = exporter.export_calendar_events(
    filters=CalendarEventFilter(query="meeting"),
    export_format="md"
)
```

### Agno Toolkit (for AI Agents)

```python
from google_workspace_tools.toolkit import GoogleDriveTools

# Create toolkit for agent use
toolkit = GoogleDriveTools(
    workspace_dir=Path("./workspace"),
    credentials_path=Path(".client_secret.googleusercontent.com.json"),
)

# Use in an Agno agent
from agno import Agent

agent = Agent(tools=[toolkit])
```

## Configuration

### Mirror Config File Format

Create a text file with document URLs:

```
# Comments start with #
# Format: URL [depth=N] [# comment]
https://docs.google.com/document/d/abc123/edit depth=2 # Main documentation
https://docs.google.com/spreadsheets/d/xyz789/edit # Data spreadsheet
https://docs.google.com/document/d/def456/edit depth=1 # Related docs
```

### Environment Variables

All settings can be configured via environment variables with `GWT_` prefix:

```bash
export GWT_CREDENTIALS_PATH=/path/to/credentials.json
export GWT_TARGET_DIRECTORY=./exports
export GWT_EXPORT_FORMAT=md
export GWT_LOG_LEVEL=DEBUG
```

## Supported Export Formats

### Google Docs
- `md` - Markdown (default)
- `pdf` - PDF
- `docx` - Microsoft Word
- `html` - HTML
- `txt` - Plain text
- `odt` - OpenDocument
- `rtf` - Rich Text Format
- `epub` - EPUB eBook

### Google Sheets
- `xlsx` - Microsoft Excel
- `csv` - CSV (exports all sheets)
- `tsv` - Tab-separated values
- `pdf` - PDF
- `ods` - OpenDocument Spreadsheet

### Google Slides
- `pptx` - Microsoft PowerPoint
- `pdf` - PDF
- `odp` - OpenDocument Presentation
- `txt` - Plain text

## Comment Export Support

Comments, suggestions, and reactions are **automatically preserved** in most export formats without any configuration required. The Google Drive API includes comment data based on each format's capabilities.

### Comment Support by Format

| Format | Google Docs | Google Sheets | Google Slides | Features Preserved |
|--------|-------------|---------------|---------------|-------------------|
| **DOCX/XLSX/PPTX** | ✅ Full | ✅ Full | ✅ Full | Author, timestamp, reactions, threading, position |
| **ODT/ODS/ODP** | ✅ Full | ✅ Full | ✅ Full | Author, timestamp, position |
| **HTML** | ✅ Full | N/A | N/A | Styled divs with anchor links |
| **Markdown** | ✅ Full | N/A | N/A | Footnote-style with anchor links |
| **TXT** | ✅ Footnotes | N/A | ❌ No | Simple footnote references |
| **EPUB** | ✅ Full | N/A | N/A | Embedded in HTML content |
| **PDF** | ❌ No | ❌ No | ❌ No | **Not supported by Drive API** |
| **RTF** | ❌ No | N/A | N/A | Stripped during export |
| **CSV/TSV** | N/A | ❌ No | N/A | Format doesn't support comments |

### Key Points

- **Microsoft Office formats** (DOCX, XLSX, PPTX): Full comment preservation including threaded replies, emoji reactions, and author metadata
- **OpenDocument formats** (ODT, ODS, ODP): Full comment preservation with structured XML annotations
- **Markdown & HTML** (Docs only): Comments exported as footnotes with anchor links, including reactions (e.g., 👍)
- **PDF exports**: Comments are **never** included in PDF exports across all document types (Google Drive API limitation)

### Example: Markdown with Comments

When exporting a Google Doc with comments to Markdown:

```markdown
Document text with a comment marker[[a]](#cmnt1)

[[a]](#cmnt_ref1)This is the comment text
1 total reaction
Jane Doe reacted with 👍 at 2024-01-15 10:30 AM
```

### Example: Spreadsheet Comment Threading

XLSX exports preserve full comment threads:

```
Cell A1 comment:
  Initial comment text
    -Jane Doe
  Reply to comment
    -John Smith
```

### Recommendations

**Best formats for preserving comments:**
- Collaboration with Microsoft Office: DOCX, XLSX, PPTX
- Open format archival: ODT, ODS, ODP
- LLM/AI processing: Markdown, HTML (for Google Docs)

**Avoid if comments are important:**
- PDF (comments not exported)
- CSV/TSV (format limitation)
- RTF (comments stripped)

## Authentication

1. Create a project in [Google Cloud Console](https://console.cloud.google.com/)
2. Enable the following APIs:
   - Google Drive API
   - Google Docs API
   - Google Sheets API
   - Google Slides API
   - **Gmail API** (for email export)
   - **Google Calendar API** (for calendar export)
3. Create OAuth 2.0 credentials (**Web application**, not Desktop)
   - Add authorized redirect URI: `http://localhost:47621/`
4. Download the credentials JSON file
5. Run `gwt auth -c /path/to/credentials.json`

The tool will open a browser for OAuth authentication and save the token for future use.

### OAuth Scopes

The tool requests the following read-only scopes:
- `drive.readonly` - Access to Google Drive files
- `documents.readonly` - Access to Google Docs
- `spreadsheets.readonly` - Access to Google Sheets
- `presentations.readonly` - Access to Google Slides
- **`gmail.readonly`** - Access to Gmail messages (for email export)
- **`calendar.readonly`** - Access to Google Calendar events (for calendar export)

### Re-authentication After Scope Changes

If you've already authenticated and then upgrade to a version with new scopes (e.g., Gmail/Calendar support), you'll need to re-authenticate:

```bash
# Delete existing token
rm tmp/token_drive.json

# Re-authenticate with new scopes
gwt auth
```

The tool will automatically detect scope mismatches and prompt for re-authentication when needed.

## Development

```bash
# Clone and install
git clone https://github.com/yourusername/google-workspace-tools
cd google-workspace-tools
uv sync --group dev

# Run tests
uv run pytest

# Run linting
uv run ruff check
uv run ruff format

# Type checking
uv run mypy src/
```

## License

Apache-2.0
