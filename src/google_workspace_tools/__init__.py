"""Google Workspace Tools - Document export and management toolkit.

This package provides:
- GoogleDriveExporter: Core class for exporting Google Drive documents
- CLI tool (gwt): Command-line interface for document operations
- Optional Agno toolkit: Agent tools for AI assistants (install with [agno] extra)

Basic usage::

    from google_workspace_tools import GoogleDriveExporter, GoogleDriveExporterConfig

    config = GoogleDriveExporterConfig(
        export_format="md",
        target_directory=Path("./exports"),
    )
    exporter = GoogleDriveExporter(config)
    exporter.export_document("https://docs.google.com/document/d/...")

CLI usage::

    gwt download https://docs.google.com/document/d/... -f md
    gwt mirror config.yaml -o exports/
    gwt auth --credentials credentials.json
    gwt whoami
"""

from .core.config import GoogleDriveExporterConfig
from .core.exporter import GoogleDriveExporter
from .core.filters import CalendarEventFilter, GmailSearchFilter
from .core.types import DocumentConfig, DocumentType, ExportFormat

__version__ = "0.1.0"

__all__ = [
    "GoogleDriveExporter",
    "GoogleDriveExporterConfig",
    "DocumentType",
    "ExportFormat",
    "DocumentConfig",
    "GmailSearchFilter",
    "CalendarEventFilter",
    "__version__",
]


def main() -> None:
    """CLI entry point."""
    import sys

    from loguru import logger
    from rich.console import Console

    from .cli.app import app
    from .settings import settings

    # Configure logging
    logger.remove()
    if settings.log_format == "json":
        logger.add(sys.stderr, format="{message}", serialize=True, level=settings.log_level)
    else:
        logger.add(
            sys.stderr,
            format=(
                "<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | "
                "<cyan>{name}</cyan> - <level>{message}</level>"
            ),
            level=settings.log_level,
            colorize=True,
        )

    console = Console()

    try:
        app()
    except KeyboardInterrupt:
        console.print("\n[yellow]Operation cancelled by user[/yellow]")
        sys.exit(130)
    except Exception as e:
        logger.exception("Unexpected error occurred")
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)
