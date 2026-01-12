"""Utility commands for Google Workspace Tools."""

import json
from pathlib import Path
from typing import Annotated, Any

import click
import typer
import yaml
from rich.console import Console
from rich.table import Table

from ... import __version__
from ...core.exporter import GoogleDriveExporter

console = Console()


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

        # Print next-step hints
        console.print("\n[dim]Next steps:[/dim]")
        console.print(f"[dim]  {'gwt download <URL> -f md':<40} Download as Markdown[/dim]")
        console.print(f"[dim]  {'gwt download <URL> -f pdf':<40} Download as PDF[/dim]")


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


def dump_schema(
    output_format: Annotated[
        str,
        typer.Option("--format", "-f", help="Output format (json, yaml)"),
    ] = "json",
    app: typer.Typer | None = None,
) -> None:
    """Dump CLI schema showing all commands and options.

    Useful for documentation generation and shell completion debugging.

    Examples:
        gwt dump-schema
        gwt dump-schema -f yaml
    """
    if app is None:
        console.print("[red]Error: No app provided for schema dump[/red]")
        raise typer.Exit(1)

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


def version() -> None:
    """Show version information."""
    console.print(f"[bold blue]google-workspace-tools[/bold blue] version [green]{__version__}[/green]")
