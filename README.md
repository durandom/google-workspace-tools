# Google Workspace Tools

A Python toolkit for exporting and managing Google Drive documents with CLI and optional AI agent integration.

## Features

- **Multi-format Export**: Export Google Docs, Sheets, and Slides to various formats (PDF, DOCX, Markdown, CSV, XLSX, PPTX, etc.)
- **HTML to Markdown**: Automatic conversion of Google Docs to clean Markdown
- **Frontmatter Support**: Add YAML frontmatter to markdown files with custom metadata
- **Custom Output Paths**: Export to specific file paths with custom names
- **Link Following**: Recursively export linked documents up to configurable depth
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
```

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

# Mirror from config file
exporter.mirror_documents(Path("sources.txt"))
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

## Authentication

1. Create a project in [Google Cloud Console](https://console.cloud.google.com/)
2. Enable the Google Drive API, Docs API, Sheets API, and Slides API
3. Create OAuth 2.0 credentials (Desktop app)
4. Download the credentials JSON file
5. Run `gwt auth -c /path/to/credentials.json`

The tool will open a browser for OAuth authentication and save the token for future use.

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
