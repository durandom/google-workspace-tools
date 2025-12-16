# Google Workspace Tools

A Python toolkit for exporting and managing Google Drive documents with CLI and optional AI agent integration.

## Features

- **Multi-format Export**: Export Google Docs, Sheets, and Slides to various formats (PDF, DOCX, Markdown, CSV, XLSX, PPTX, etc.)
- **HTML to Markdown**: Automatic conversion of Google Docs to clean Markdown
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
