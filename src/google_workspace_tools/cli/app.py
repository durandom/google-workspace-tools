"""CLI application for Google Workspace Tools."""

import json
from pathlib import Path
from typing import Annotated, Optional

import typer
from loguru import logger
from rich.console import Console
from rich.table import Table

from .. import __version__
from ..core.config import GoogleDriveExporterConfig
from ..core.exporter import GoogleDriveExporter
from ..settings import settings

console = Console()

app = typer.Typer(
    name="gwt",
    help="Google Workspace Tools - Export and manage Google Drive documents",
    add_completion=False,
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
        Optional[str],
        typer.Option("--log-level", help="Set log level (DEBUG, INFO, WARNING, ERROR)"),
    ] = None,
    version: Annotated[
        bool,
        typer.Option("--version", callback=version_callback, is_eager=True, help="Show version and exit"),
    ] = False,
) -> None:
    """Google Workspace Tools - Export and manage Google Drive documents."""
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
            format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan> - <level>{message}</level>",
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
        Path,
        typer.Option("--output", "-o", help="Output directory"),
    ] = Path("exports"),
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
) -> None:
    """Download one or more Google Drive documents.

    Examples:
        gwt download https://docs.google.com/document/d/abc123/edit
        gwt download abc123 def456 -f pdf -o ./downloads
        gwt download https://docs.google.com/.../edit -d 2  # Follow links 2 levels deep
    """
    config = GoogleDriveExporterConfig(
        credentials_path=credentials,
        target_directory=output,
        export_format=format,  # type: ignore[arg-type]
        follow_links=depth > 0,
        link_depth=depth,
    )

    exporter = GoogleDriveExporter(config)

    console.print(f"[bold]Downloading {len(documents)} document(s) to {output}[/bold]")
    console.print(f"Format: [cyan]{format}[/cyan], Link depth: [cyan]{depth}[/cyan]\n")

    try:
        results = exporter.export_multiple(documents)

        if results:
            console.print(f"\n[green]Successfully exported {len(results)} document(s)[/green]")
            for doc_id, files in results.items():
                console.print(f"  [dim]{doc_id}[/dim]")
                for fmt, path in files.items():
                    console.print(f"    {fmt}: [blue]{path}[/blue]")
        else:
            console.print("[yellow]No documents were exported[/yellow]")

    except FileNotFoundError as e:
        console.print(f"[red]Error: {e}[/red]")
        console.print("\n[dim]Run 'gwt auth' to set up authentication[/dim]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


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
    if not config_file.exists():
        console.print(f"[red]Error: Configuration file not found: {config_file}[/red]")
        raise typer.Exit(1)

    config = GoogleDriveExporterConfig(
        credentials_path=credentials,
        target_directory=output,
        export_format=format,  # type: ignore[arg-type]
    )

    exporter = GoogleDriveExporter(config)

    console.print(f"[bold]Mirroring documents from {config_file}[/bold]")
    console.print(f"Output: [cyan]{output}[/cyan], Format: [cyan]{format}[/cyan]\n")

    try:
        results = exporter.mirror_documents(config_file)

        if results:
            console.print(f"\n[green]Successfully mirrored {len(results)} document(s)[/green]")
        else:
            console.print("[yellow]No documents were mirrored[/yellow]")

    except FileNotFoundError as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


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
        raise typer.Exit(1)


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

    except FileNotFoundError:
        console.print("[yellow]Not authenticated[/yellow]")
        console.print("[dim]Run 'gwt auth' to set up authentication[/dim]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


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
        raise typer.Exit(1)


@app.command()
def version() -> None:
    """Show version information."""
    console.print(f"[bold blue]google-workspace-tools[/bold blue] version [green]{__version__}[/green]")


if __name__ == "__main__":
    app()
