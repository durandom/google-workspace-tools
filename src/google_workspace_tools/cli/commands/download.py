"""Download and mirror commands for Google Workspace Tools."""

from pathlib import Path
from typing import Annotated, Any

import typer
import yaml

from ... import __version__
from ...core.config import GoogleDriveExporterConfig
from ...core.exporter import GoogleDriveExporter
from ..formatters import get_formatter
from ..output import OutputMode, get_output_mode
from ..schemas import (
    DocumentExport,
    DownloadOutput,
    ExportedFile,
    MirrorDocumentResult,
    MirrorOutput,
)
from ..utils import cli_error_handler, print_next_steps


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

    with cli_error_handler(formatter):
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

        # Print next-step hints (only for human output mode)
        if get_output_mode() == OutputMode.HUMAN:
            print_next_steps(
                formatter,
                [
                    ("gwt mail -q 'from:...'", "Export related Gmail messages"),
                    ("gwt calendar -a YYYY-MM-DD", "Export related calendar events"),
                ],
            )

        # Exit with error if there were any errors
        if errors:
            raise typer.Exit(1)


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

    with cli_error_handler(formatter):
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

        # Print next-step hints (only for human output mode)
        if get_output_mode() == OutputMode.HUMAN:
            print_next_steps(
                formatter,
                [
                    ("gwt mail -q 'from:...'", "Export related Gmail messages"),
                    ("gwt calendar -a YYYY-MM-DD", "Export related calendar events"),
                ],
            )

        # Exit with error if no documents mirrored
        if not results:
            raise typer.Exit(1)
