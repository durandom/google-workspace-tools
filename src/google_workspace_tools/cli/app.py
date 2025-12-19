"""CLI application for Google Workspace Tools."""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated, Any, Literal, cast

import typer
import yaml
from loguru import logger
from rich.console import Console
from rich.table import Table

from .. import __version__
from ..core.config import GoogleDriveExporterConfig
from ..core.exporter import GoogleDriveExporter
from ..core.filters import CalendarEventFilter, GmailSearchFilter
from ..settings import settings
from .formatters import get_formatter
from .output import OutputMode, get_output_mode, set_output_mode
from .schemas import (
    CalendarEventExport,
    CalendarInfo,
    CalendarListOutput,
    CalendarOutput,
    DocumentExport,
    DownloadOutput,
    EmailThreadExport,
    ExportedFile,
    MailOutput,
    MirrorDocumentResult,
    MirrorOutput,
)
from .utils import format_relative_path, get_file_size

console = Console()

app = typer.Typer(
    name="gwt",
    help="Google Workspace Tools - Export and manage Google Drive documents",
    add_completion=True,
    rich_markup_mode="rich",
)


def version_callback(value: bool) -> None:
    """Print version and exit."""
    if value:
        console.print(f"[bold blue]google-workspace-tools[/bold blue] version [green]{__version__}[/green]")
        raise typer.Exit()


@app.callback()
def main_callback(
    verbose: Annotated[
        int,
        typer.Option(
            "-v",
            "--verbose",
            count=True,
            help="Increase verbosity. Use -v for DEBUG, -vv for TRACE.",
        ),
    ] = 0,
    log_level: Annotated[
        str | None,
        typer.Option("--log-level", help="Set log level (DEBUG, INFO, WARNING, ERROR)"),
    ] = None,
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Output in JSON format (machine-readable)"),
    ] = False,
    version: Annotated[
        bool,
        typer.Option("--version", callback=version_callback, is_eager=True, help="Show version and exit"),
    ] = False,
) -> None:
    """Google Workspace Tools - Export and manage Google Drive documents."""
    # Set output mode
    mode = OutputMode.JSON if json_output else OutputMode.HUMAN
    set_output_mode(mode)

    # Determine log level
    if log_level:
        level = log_level.upper()
    elif verbose >= 2:
        level = "TRACE"
    elif verbose == 1:
        level = "DEBUG"
    else:
        level = settings.log_level

    # Reconfigure logger if needed
    if level != settings.log_level:
        import sys

        logger.remove()
        logger.add(
            sys.stderr,
            format=(
                "<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | "
                "<cyan>{name}</cyan> - <level>{message}</level>"
            ),
            level=level,
            colorize=True,
        )


@app.command()
def download(
    documents: Annotated[
        list[str],
        typer.Argument(help="Google Drive URLs or document IDs to download"),
    ],
    output: Annotated[
        Path | None,
        typer.Option("--output", "-o", help="Output directory or full path (with extension for single document)"),
    ] = None,
    format: Annotated[
        str,
        typer.Option("--format", "-f", help="Export format (md, pdf, docx, html, xlsx, csv, pptx, etc.)"),
    ] = "md",
    depth: Annotated[
        int,
        typer.Option("--depth", "-d", help="Link following depth (0-5). 0 disables link following."),
    ] = 0,
    credentials: Annotated[
        Path,
        typer.Option("--credentials", "-c", help="Path to Google OAuth credentials file"),
    ] = Path(".client_secret.googleusercontent.com.json"),
    frontmatter: Annotated[
        list[str] | None,
        typer.Option(
            "--frontmatter", "-m", help="Add frontmatter field (format: key=value). Can be used multiple times."
        ),
    ] = None,
    frontmatter_file: Annotated[
        Path | None,
        typer.Option("--frontmatter-file", help="Path to YAML file containing frontmatter fields"),
    ] = None,
    enable_frontmatter: Annotated[
        bool,
        typer.Option("--enable-frontmatter", help="Enable YAML frontmatter in markdown files"),
    ] = False,
    spreadsheet_mode: Annotated[
        str,
        typer.Option(
            "--spreadsheet-mode",
            "-s",
            help="Spreadsheet export mode: 'combined' (single .md), 'separate' (one .md per sheet), 'csv' (legacy)",
        ),
    ] = "combined",
    keep_xlsx: Annotated[
        bool,
        typer.Option("--keep-xlsx", help="Keep intermediate XLSX files when converting spreadsheets to markdown"),
    ] = True,
) -> None:
    """Download one or more Google Drive documents.

    Examples:
        gwt download https://docs.google.com/document/d/abc123/edit
        gwt download abc123 def456 -f pdf -o ./downloads
        gwt download https://docs.google.com/.../edit -d 2  # Follow links 2 levels deep
        gwt download URL -o meetings/notes.md --enable-frontmatter -m "date=2024-01-15" -m "type=meeting"
        gwt download URL -o notes.md --enable-frontmatter --frontmatter-file meta.yaml
        gwt download SPREADSHEET_URL -f md -s combined  # Single markdown with all sheets
        gwt download SPREADSHEET_URL -f md -s separate  # One markdown per sheet
        gwt download SPREADSHEET_URL -f md -s csv  # Legacy CSV export
    """
    # Get formatter for output mode
    formatter = get_formatter(get_output_mode())

    # Parse frontmatter fields
    frontmatter_fields: dict[str, Any] = {}

    # Load from file if provided
    if frontmatter_file:
        if not frontmatter_file.exists():
            formatter.print_error(f"Frontmatter file not found: {frontmatter_file}")
            raise typer.Exit(1)
        try:
            with open(frontmatter_file) as f:
                file_data = yaml.safe_load(f)
                if isinstance(file_data, dict):
                    frontmatter_fields.update(file_data)
        except Exception as e:
            formatter.print_error(f"Error loading frontmatter file: {e}")
            raise typer.Exit(1) from e

    # Parse command-line frontmatter options
    if frontmatter:
        for item in frontmatter:
            if "=" not in item:
                formatter.print_warning(f"Invalid frontmatter format '{item}'. Expected key=value")
                continue
            key, value = item.split("=", 1)
            frontmatter_fields[key.strip()] = value.strip()

    # Determine if output is a directory or full path
    output_dir = Path("exports")
    output_path = None
    is_single_document = len(documents) == 1

    if output:
        if is_single_document and output.suffix:
            # Full path provided for single document
            output_path = output
            output_dir = output.parent
        else:
            # Directory path
            output_dir = output

    config = GoogleDriveExporterConfig(
        credentials_path=credentials,
        target_directory=output_dir,
        export_format=format,  # type: ignore[arg-type]
        follow_links=depth > 0,
        link_depth=depth,
        enable_frontmatter=enable_frontmatter or bool(frontmatter_fields),
        frontmatter_fields=frontmatter_fields,
        spreadsheet_export_mode=spreadsheet_mode,  # type: ignore[arg-type]
        keep_intermediate_xlsx=keep_xlsx,
    )

    exporter = GoogleDriveExporter(config)

    # Progress messages
    formatter.print_progress(f"[bold]Downloading {len(documents)} document(s) to {output_dir}[/bold]")
    formatter.print_progress(f"Format: [cyan]{format}[/cyan], Link depth: [cyan]{depth}[/cyan]")
    if config.enable_frontmatter:
        formatter.print_progress(f"Frontmatter: [cyan]enabled[/cyan] ({len(frontmatter_fields)} custom fields)")
    formatter.print_progress("")

    # Track results for schema
    document_exports: list[DocumentExport] = []
    errors: list[str] = []
    total_files = 0

    try:
        if is_single_document and output_path:
            # Export single document with custom path
            result = exporter.export_document(documents[0], output_path=output_path)
            if result:
                # Build document export
                doc_id = exporter.extract_document_id(documents[0])
                doc_type = exporter.detect_document_type(documents[0])
                metadata = exporter.get_document_metadata(doc_id)

                files = [ExportedFile.from_path(fmt, Path(path)) for fmt, path in result.items()]
                total_files += len(files)

                document_exports.append(
                    DocumentExport(
                        document_id=doc_id,
                        title=metadata.get("title", "Unknown") if metadata else "Unknown",
                        source_url=documents[0],
                        doc_type=doc_type.value,
                        files=files,
                        link_following_depth=depth,
                        linked_documents_count=0,
                    )
                )
            else:
                errors.append(f"Document {documents[0]} was not exported")
        else:
            # Export multiple documents
            results = exporter.export_multiple(documents)

            for doc_url in documents:
                try:
                    doc_id = exporter.extract_document_id(doc_url)
                    doc_type = exporter.detect_document_type(doc_url)
                    metadata = exporter.get_document_metadata(doc_id)

                    if doc_id in results:
                        files = [ExportedFile.from_path(fmt, Path(path)) for fmt, path in results[doc_id].items()]
                        total_files += len(files)

                        document_exports.append(
                            DocumentExport(
                                document_id=doc_id,
                                title=metadata.get("title", "Unknown") if metadata else "Unknown",
                                source_url=doc_url,
                                doc_type=doc_type.value,
                                files=files,
                                link_following_depth=depth,
                                linked_documents_count=0,
                            )
                        )
                    else:
                        errors.append(f"Document {doc_url} was not exported")
                except Exception as e:
                    errors.append(f"Error processing {doc_url}: {str(e)}")

        # Build output schema
        output_schema = DownloadOutput(
            command="download",
            success=len(errors) == 0,
            version=__version__,
            errors=errors,
            documents=document_exports,
            total_files_exported=total_files,
            output_directory=str(output_dir.absolute()),
            link_following_enabled=depth > 0,
            max_link_depth=depth,
        )

        # Print result
        formatter.print_result(output_schema)

        # Exit with error if there were any errors
        if errors:
            raise typer.Exit(1)

    except FileNotFoundError as e:
        formatter.print_error(f"Error: {e}")
        formatter.print_info("Run 'gwt auth' to set up authentication")
        raise typer.Exit(1) from e
    except typer.Exit:
        raise
    except Exception as e:
        formatter.print_error(f"Error: {e}")
        raise typer.Exit(1) from e


@app.command()
def mirror(
    config_file: Annotated[
        Path,
        typer.Argument(help="Mirror configuration file (YAML or text format)"),
    ],
    output: Annotated[
        Path,
        typer.Option("--output", "-o", help="Output directory"),
    ] = Path("exports"),
    format: Annotated[
        str,
        typer.Option("--format", "-f", help="Override export format from config"),
    ] = "md",
    credentials: Annotated[
        Path,
        typer.Option("--credentials", "-c", help="Path to Google OAuth credentials file"),
    ] = Path(".client_secret.googleusercontent.com.json"),
) -> None:
    """Mirror documents from a configuration file.

    The config file uses a simple text format:
        # Comments start with #
        https://docs.google.com/document/d/ID/edit depth=2 # Optional comment
        https://docs.google.com/document/d/ID/edit # Uses default depth=0

    Examples:
        gwt mirror sources.txt
        gwt mirror documents.yaml -o ./mirror -f pdf
    """
    # Get formatter for output mode
    formatter = get_formatter(get_output_mode())

    if not config_file.exists():
        formatter.print_error(f"Configuration file not found: {config_file}")
        raise typer.Exit(1)

    config = GoogleDriveExporterConfig(
        credentials_path=credentials,
        target_directory=output,
        export_format=format,  # type: ignore[arg-type]
    )

    exporter = GoogleDriveExporter(config)

    # Progress messages
    formatter.print_progress(f"[bold]Mirroring documents from {config_file}[/bold]")
    formatter.print_progress(f"Output: [cyan]{output}[/cyan], Format: [cyan]{format}[/cyan]\n")

    try:
        results = exporter.mirror_documents(config_file)

        # Build document results (simplified - we don't have detailed per-document tracking)
        document_results: list[MirrorDocumentResult] = []
        total_files = 0

        if results:
            for doc_id, files in results.items():
                exported_files = [ExportedFile.from_path(fmt, Path(path)) for fmt, path in files.items()]
                total_files += len(exported_files)

                document_results.append(
                    MirrorDocumentResult(
                        document_id=doc_id,
                        source_url=f"https://docs.google.com/document/d/{doc_id}/edit",
                        configured_depth=0,  # Would need to parse from config file
                        files_exported=exported_files,
                        linked_documents_count=0,
                        errors=[],
                    )
                )

        # Build output schema
        output_schema = MirrorOutput(
            command="mirror",
            success=len(results) > 0,
            version=__version__,
            config_file=str(config_file.absolute()),
            documents_configured=len(results),  # Simplified - would need to parse config
            documents=document_results,
            total_files_exported=total_files,
            output_directory=str(output.absolute()),
            export_format=format,
        )

        # Print result
        formatter.print_result(output_schema)

        # Exit with error if no documents mirrored
        if not results:
            raise typer.Exit(1)

    except FileNotFoundError as e:
        formatter.print_error(f"Error: {e}")
        raise typer.Exit(1) from e
    except typer.Exit:
        raise
    except Exception as e:
        formatter.print_error(f"Error: {e}")
        raise typer.Exit(1) from e


@app.command()
def auth(
    credentials: Annotated[
        Path,
        typer.Option("--credentials", "-c", help="Path to Google OAuth credentials file"),
    ] = Path(".client_secret.googleusercontent.com.json"),
    token_path: Annotated[
        Path,
        typer.Option("--token", "-t", help="Path to save OAuth token"),
    ] = Path("tmp/token_drive.json"),
) -> None:
    """Authenticate with Google Drive API.

    This will open a browser window for OAuth authentication.
    The token will be saved for future use.

    Examples:
        gwt auth
        gwt auth -c /path/to/credentials.json
    """
    if not credentials.exists():
        console.print(f"[red]Error: Credentials file not found: {credentials}[/red]")
        console.print("\n[dim]Download OAuth credentials from Google Cloud Console:[/dim]")
        console.print("[dim]https://console.cloud.google.com/apis/credentials[/dim]")
        console.print("\n[yellow]Important:[/yellow] Create a [cyan]Web application[/cyan] credential (not Desktop)")
        console.print("[dim]When configuring, add this authorized redirect URI:[/dim]")
        console.print("[cyan]http://localhost:47621/[/cyan]")
        raise typer.Exit(1)

    config = GoogleDriveExporterConfig(
        credentials_path=credentials,
        token_path=token_path,
    )

    exporter = GoogleDriveExporter(config)

    console.print("[bold]Starting Google OAuth authentication...[/bold]")
    console.print("[dim]A browser window will open for authentication[/dim]\n")

    try:
        # Trigger authentication by accessing the service
        _ = exporter.service

        # Get user info to confirm
        user_info = exporter.get_authenticated_user_info()
        if user_info:
            console.print("[green]Authentication successful![/green]")
            console.print(f"  User: [cyan]{user_info.get('displayName', 'Unknown')}[/cyan]")
            console.print(f"  Email: [cyan]{user_info.get('emailAddress', 'Unknown')}[/cyan]")
            console.print(f"  Token saved to: [blue]{token_path}[/blue]")
        else:
            console.print("[green]Authentication successful![/green]")
            console.print(f"  Token saved to: [blue]{token_path}[/blue]")

    except Exception as e:
        console.print(f"[red]Authentication failed: {e}[/red]")
        raise typer.Exit(1) from e


@app.command()
def whoami(
    credentials: Annotated[
        Path,
        typer.Option("--credentials", "-c", help="Path to Google OAuth credentials file"),
    ] = Path(".client_secret.googleusercontent.com.json"),
    token_path: Annotated[
        Path,
        typer.Option("--token", "-t", help="Path to OAuth token"),
    ] = Path("tmp/token_drive.json"),
) -> None:
    """Show the currently authenticated Google user.

    Examples:
        gwt whoami
    """
    config = GoogleDriveExporterConfig(
        credentials_path=credentials,
        token_path=token_path,
    )

    try:
        exporter = GoogleDriveExporter(config)
        user_info = exporter.get_authenticated_user_info()

        if user_info:
            console.print("[bold]Authenticated User[/bold]")
            console.print(f"  Name:  [cyan]{user_info.get('displayName', 'Unknown')}[/cyan]")
            console.print(f"  Email: [cyan]{user_info.get('emailAddress', 'Unknown')}[/cyan]")
            if user_info.get("photoLink"):
                console.print(f"  Photo: [dim]{user_info.get('photoLink')}[/dim]")
        else:
            console.print("[yellow]No user information available[/yellow]")
            console.print("[dim]Run 'gwt auth' to authenticate[/dim]")

    except FileNotFoundError as e:
        console.print("[yellow]Not authenticated[/yellow]")
        console.print("[dim]Run 'gwt auth' to set up authentication[/dim]")
        raise typer.Exit(1) from e
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1) from e


@app.command()
def formats(
    doc_type: Annotated[
        str,
        typer.Option("--type", "-t", help="Document type (document, spreadsheet, presentation)"),
    ] = "document",
    output_json: Annotated[
        bool,
        typer.Option("--json", "-j", help="Output as JSON"),
    ] = False,
) -> None:
    """List supported export formats for different document types.

    Examples:
        gwt formats
        gwt formats -t spreadsheet
        gwt formats -t presentation --json
    """
    doc_type_lower = doc_type.lower()

    if doc_type_lower == "spreadsheet":
        formats_dict = GoogleDriveExporter.SPREADSHEET_EXPORT_FORMATS
    elif doc_type_lower == "presentation":
        formats_dict = GoogleDriveExporter.PRESENTATION_EXPORT_FORMATS
    else:
        formats_dict = GoogleDriveExporter.DOCUMENT_EXPORT_FORMATS

    if output_json:
        result = {
            "document_type": doc_type_lower,
            "formats": {
                key: {
                    "extension": fmt.extension,
                    "mime_type": fmt.mime_type,
                    "description": fmt.description,
                }
                for key, fmt in formats_dict.items()
            },
        }
        console.print(json.dumps(result, indent=2))
    else:
        table = Table(title=f"Export Formats for {doc_type.capitalize()}")
        table.add_column("Format", style="cyan")
        table.add_column("Extension", style="green")
        table.add_column("Description", style="dim")

        for key, fmt in formats_dict.items():
            table.add_row(key, f".{fmt.extension}", fmt.description or "")

        console.print(table)


@app.command()
def extract_id(
    url: Annotated[
        str,
        typer.Argument(help="Google Drive URL to extract ID from"),
    ],
) -> None:
    """Extract document ID from a Google Drive URL.

    Examples:
        gwt extract-id https://docs.google.com/document/d/abc123/edit
        gwt extract-id "https://docs.google.com/spreadsheets/d/xyz789/edit#gid=0"
    """
    try:
        exporter = GoogleDriveExporter()
        doc_id = exporter.extract_document_id(url)
        doc_type = exporter.detect_document_type(url)

        console.print(f"[bold]Document ID:[/bold] [cyan]{doc_id}[/cyan]")
        console.print(f"[bold]Type:[/bold] [green]{doc_type.value}[/green]")

    except ValueError as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1) from e


@app.command()
def mail(
    query: Annotated[str, typer.Option("--query", "-q", help="Gmail search query")] = "",
    after: Annotated[str | None, typer.Option("--after", "-a", help="After date (YYYY-MM-DD)")] = None,
    before: Annotated[str | None, typer.Option("--before", "-b", help="Before date (YYYY-MM-DD)")] = None,
    labels: Annotated[str | None, typer.Option("--labels", "-l", help="Comma-separated labels")] = None,
    max_results: Annotated[int, typer.Option("--max", "-n", help="Maximum messages to fetch")] = 100,
    export_format: Annotated[str, typer.Option("--format", "-f", help="Export format (json, md)")] = "md",
    mode: Annotated[str, typer.Option("--mode", "-m", help="Export mode (thread, individual)")] = "thread",
    output: Annotated[Path, typer.Option("--output", "-o", help="Output directory")] = Path("exports/emails"),
    depth: Annotated[int, typer.Option("--depth", "-d", help="Link following depth")] = 0,
    credentials: Annotated[
        Path, typer.Option("--credentials", "-c", help="Path to credentials file")
    ] = Path(".client_secret.googleusercontent.com.json"),
    token: Annotated[Path, typer.Option("--token", "-t", help="Path to token file")] = Path("tmp/token_drive.json"),
) -> None:
    """Export Gmail messages to JSON or Markdown.

    Examples:
        gwt mail -q "from:boss@example.com" -f md

        gwt mail -a 2024-01-01 -l work,important

        gwt mail -q "has:attachment" -d 2
    """
    # Get formatter for output mode
    formatter = get_formatter(get_output_mode())

    try:
        # Parse dates
        after_date = datetime.fromisoformat(after) if after else None
        before_date = datetime.fromisoformat(before) if before else None

        # Parse labels
        label_list = [lbl.strip() for lbl in labels.split(",")] if labels else []

        # Create filter
        filters = GmailSearchFilter(
            query=query,
            after_date=after_date,
            before_date=before_date,
            labels=label_list,
            max_results=max_results,
        )

        # Create config
        config = GoogleDriveExporterConfig(
            credentials_path=credentials,
            token_path=token,
            target_directory=output.parent,
            follow_links=(depth > 0),
            link_depth=depth,
        )

        exporter = GoogleDriveExporter(config)

        # Progress messages
        formatter.print_progress("[bold]Exporting Gmail messages...[/bold]")
        formatter.print_progress(f"Query: {filters.build_query() or '(all messages)'}")
        formatter.print_progress(f"Format: {export_format}, Mode: {mode}")

        exported = exporter.export_emails(
            filters=filters,
            export_format=export_format,
            export_mode=cast(Literal["thread", "individual"], mode),
            output_directory=output,
        )

        # Build thread export list (simplified - we don't have detailed thread metadata from export)
        threads: list[EmailThreadExport] = []
        for thread_id, file_path in exported.items():
            threads.append(
                EmailThreadExport(
                    thread_id=thread_id,
                    subject="Exported Thread",  # Would need API call to get actual subject
                    message_count=1,
                    participants=[],
                    export_path=str(file_path.absolute()),
                    date_range={},
                    has_attachments=False,
                    drive_links_found=0,
                )
            )

        # Build output schema
        output_schema = MailOutput(
            command="mail",
            success=True,
            version=__version__,
            export_mode=mode,
            export_format=export_format,
            filters_applied={
                "query": query,
                "after": after,
                "before": before,
                "labels": label_list,
                "max_results": max_results,
            },
            threads=threads,
            total_exported=len(exported),
            output_directory=str(output.absolute()),
            link_following_enabled=depth > 0,
        )

        # Print result
        formatter.print_result(output_schema)

    except Exception as e:
        logger.error(f"Failed to export Gmail: {e}")
        formatter.print_error(f"Error: {e}")
        raise typer.Exit(1) from e


def _list_calendars(exporter: GoogleDriveExporter, formatter: Any) -> CalendarListOutput:
    """List accessible calendars and return schema.

    Args:
        exporter: GoogleDriveExporter instance
        formatter: Output formatter

    Returns:
        CalendarListOutput schema
    """
    calendars = exporter.list_calendars()

    # Build schema
    calendar_infos = [
        CalendarInfo(
            id=cal.get("id", ""),
            summary=cal.get("summary", "(No name)"),
            primary=cal.get("primary", False),
        )
        for cal in calendars
    ]

    return CalendarListOutput(
        command="calendar",
        success=True,
        version=__version__,
        calendars=calendar_infos,
        total_count=len(calendars),
    )


@app.command()
def calendar(
    calendar_id: Annotated[str, typer.Option("--calendar", help="Calendar ID")] = "primary",
    event_id: Annotated[str | None, typer.Option("--event-id", "-e", help="Specific event ID to fetch")] = None,
    after: Annotated[str | None, typer.Option("--after", "-a", help="After date (YYYY-MM-DD)")] = None,
    before: Annotated[str | None, typer.Option("--before", "-b", help="Before date (YYYY-MM-DD)")] = None,
    query: Annotated[str, typer.Option("--query", "-q", help="Search query")] = "",
    max_results: Annotated[int, typer.Option("--max", "-n", help="Maximum events to fetch")] = 250,
    export_format: Annotated[str, typer.Option("--format", "-f", help="Export format (json, md)")] = "md",
    output: Annotated[Path, typer.Option("--output", "-o", help="Output directory")] = Path("exports/calendar"),
    depth: Annotated[int, typer.Option("--depth", "-d", help="Link following depth")] = 0,
    credentials: Annotated[
        Path, typer.Option("--credentials", "-c", help="Path to credentials file")
    ] = Path(".client_secret.googleusercontent.com.json"),
    token: Annotated[Path, typer.Option("--token", "-t", help="Path to token file")] = Path("tmp/token_drive.json"),
) -> None:
    """Export Google Calendar events to JSON or Markdown.

    If no filters are provided, lists all accessible calendars.

    Examples:
        gwt calendar                              # List calendars

        gwt calendar -e EVENT_ID                  # Fetch single event by ID

        gwt calendar -a 2024-01-01 -b 2024-12-31  # Export events

        gwt calendar --calendar work -q "sprint"

        gwt calendar -d 2                         # Follow links in events
    """
    # Get formatter for output mode
    formatter = get_formatter(get_output_mode())

    try:
        config = GoogleDriveExporterConfig(
            credentials_path=credentials,
            token_path=token,
            target_directory=output.parent,
            follow_links=(depth > 0),
            link_depth=depth,
        )

        exporter = GoogleDriveExporter(config)

        # If event_id is provided, fetch single event
        if event_id:
            formatter.print_progress(f"[bold]Fetching event {event_id}...[/bold]")
            event = exporter.get_calendar_event(event_id, calendar_id)

            if not event:
                formatter.print_error(f"Event {event_id} not found")
                raise typer.Exit(1)

            # Export the single event
            summary = event.get("summary", "no-title")
            safe_summary = "".join(c if c.isalnum() or c in (" ", "-", "_") else "_" for c in summary)[:50]

            # Get start date for organization
            start = event.get("start", {})
            start_time = start.get("dateTime", start.get("date", ""))
            if start_time:
                try:
                    if "T" in start_time:
                        date_obj = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
                    else:
                        date_obj = datetime.fromisoformat(start_time)
                    date_dir = date_obj.strftime("%Y-%m")
                except Exception:
                    date_dir = datetime.now(timezone.utc).strftime("%Y-%m")
            else:
                date_dir = datetime.now(timezone.utc).strftime("%Y-%m")

            safe_calendar_id = calendar_id.replace("@", "_at_").replace(".", "_")
            event_dir = output / safe_calendar_id / date_dir
            filename = f"event_{event_id}_{safe_summary}.{export_format}"
            output_path = event_dir / filename

            # Export based on format
            if export_format == "json":
                success = exporter._export_calendar_event_as_json(event, output_path)
            else:  # md
                success = exporter._export_calendar_event_as_markdown(event, output_path)

            if success:
                # Build output schema for single event
                event_export = CalendarEventExport(
                    event_id=event_id,
                    calendar_id=calendar_id,
                    summary=summary,
                    start_time=start_time,
                    end_time=event.get("end", {}).get("dateTime", event.get("end", {}).get("date", "")),
                    location=event.get("location"),
                    attendees_count=len(event.get("attendees", [])),
                    export_path=str(output_path.absolute()),
                    has_attachments=bool(event.get("attachments")),
                    drive_links_found=0,
                )

                output_schema = CalendarOutput(
                    command="calendar",
                    success=True,
                    version=__version__,
                    export_format=export_format,
                    filters_applied={"event_id": event_id},
                    calendars_queried=[calendar_id],
                    events=[event_export],
                    total_exported=1,
                    output_directory=str(output.absolute()),
                    link_following_enabled=depth > 0,
                )

                formatter.print_result(output_schema)
            else:
                formatter.print_error("Failed to export event")
                raise typer.Exit(1)

            return

        # If no filters provided, list calendars
        has_filters = after or before or query
        if not has_filters:
            list_schema = _list_calendars(exporter, formatter)
            formatter.print_result(list_schema)
            return

        # Parse dates
        after_date = datetime.fromisoformat(after) if after else None
        before_date = datetime.fromisoformat(before) if before else None

        # Create filter
        filters = CalendarEventFilter(
            time_min=after_date,
            time_max=before_date,
            calendar_ids=[calendar_id],
            query=query,
            max_results=max_results,
        )

        # Progress messages
        formatter.print_progress("[bold]Exporting Calendar events...[/bold]")
        formatter.print_progress(f"Calendar: {calendar_id}")
        if after:
            formatter.print_progress(f"After: {after}")
        if before:
            formatter.print_progress(f"Before: {before}")
        formatter.print_progress(f"Format: {export_format}")

        exported = exporter.export_calendar_events(
            filters=filters,
            export_format=export_format,
            output_directory=output,
        )

        # Build event export list (simplified - we don't have detailed event metadata from export)
        events: list[CalendarEventExport] = []
        for event_id, file_path in exported.items():
            events.append(
                CalendarEventExport(
                    event_id=event_id,
                    calendar_id=calendar_id,
                    summary="Exported Event",  # Would need API call to get actual summary
                    start_time=datetime.now(timezone.utc).isoformat(),
                    end_time=datetime.now(timezone.utc).isoformat(),
                    location=None,
                    attendees_count=0,
                    export_path=str(file_path.absolute()),
                    has_attachments=False,
                    drive_links_found=0,
                )
            )

        # Build output schema
        export_schema = CalendarOutput(
            command="calendar",
            success=True,
            version=__version__,
            export_format=export_format,
            filters_applied={
                "after": after,
                "before": before,
                "query": query,
                "max_results": max_results,
            },
            calendars_queried=[calendar_id],
            events=events,
            total_exported=len(exported),
            output_directory=str(output.absolute()),
            link_following_enabled=depth > 0,
        )

        # Print result
        formatter.print_result(export_schema)

    except Exception as e:
        logger.error(f"Failed: {e}")
        formatter.print_error(f"Error: {e}")
        raise typer.Exit(1) from e


@app.command()
def dump_schema(
    output_format: Annotated[
        str,
        typer.Option("--format", "-f", help="Output format (json, yaml)"),
    ] = "json",
) -> None:
    """Dump CLI schema showing all commands and options.

    Useful for documentation generation and shell completion debugging.

    Examples:
        gwt dump-schema
        gwt dump-schema -f yaml
    """
    import click

    schema: dict[str, Any] = {
        "name": "gwt",
        "version": __version__,
        "description": "Google Workspace Tools - Export and manage Google Drive documents",
        "commands": {},
    }

    # Get the click command from typer app
    click_app = typer.main.get_command(app)

    # Iterate through all commands (click_app is a Group/TyperGroup)
    if not isinstance(click_app, click.Group):
        console.print("[red]Error: CLI app is not a command group[/red]")
        raise typer.Exit(1)

    for cmd_name, cmd in click_app.commands.items():
        if not isinstance(cmd, click.Command):
            continue

        cmd_info: dict[str, Any] = {
            "name": cmd_name,
            "help": cmd.help or "",
            "options": [],
            "arguments": [],
        }

        # Extract options and arguments
        for param in cmd.params:
            param_info = {
                "name": param.name,
                "type": str(param.type),
                "required": param.required,
                "help": getattr(param, "help", "") or "",
            }

            if isinstance(param, click.Option):
                param_info["flags"] = param.opts
                # Convert Path objects to strings for JSON serialization
                default_value = param.default
                if isinstance(default_value, Path):
                    default_value = str(default_value)
                param_info["default"] = default_value
                param_info["multiple"] = param.multiple
                cmd_info["options"].append(param_info)
            elif isinstance(param, click.Argument):
                param_info["multiple"] = param.multiple
                cmd_info["arguments"].append(param_info)

        schema["commands"][cmd_name] = cmd_info

    # Output in requested format
    if output_format == "yaml":
        output = yaml.dump(schema, default_flow_style=False, sort_keys=False)
        console.print(output)
    else:
        output = json.dumps(schema, indent=2)
        console.print(output)


@app.command()
def version() -> None:
    """Show version information."""
    console.print(f"[bold blue]google-workspace-tools[/bold blue] version [green]{__version__}[/green]")


if __name__ == "__main__":
    app()
