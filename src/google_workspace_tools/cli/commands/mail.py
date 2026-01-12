"""Mail export command for Google Workspace Tools."""

from datetime import datetime
from pathlib import Path
from typing import Annotated, Literal, cast

import typer

from ... import __version__
from ...core.config import GoogleDriveExporterConfig
from ...core.exporter import GoogleDriveExporter
from ...core.filters import GmailSearchFilter
from ..formatters import get_formatter
from ..output import OutputMode, get_output_mode
from ..schemas import EmailThreadExport, MailOutput
from ..utils import cli_error_handler, print_next_steps


def mail(
    query: Annotated[str, typer.Option("--query", "-q", help="Gmail search query")] = "",
    after: Annotated[str | None, typer.Option("--after", "-a", help="After date (YYYY-MM-DD)")] = None,
    before: Annotated[str | None, typer.Option("--before", "-b", help="Before date (YYYY-MM-DD)")] = None,
    labels: Annotated[str | None, typer.Option("--labels", "-l", help="Comma-separated labels")] = None,
    max_results: Annotated[int, typer.Option("--max", "-n", help="Maximum messages to fetch")] = 100,
    export_format: Annotated[str, typer.Option("--format", "-f", help="Export format (json, md)")] = "md",
    mode: Annotated[str, typer.Option("--mode", "-m", help="Export mode (thread, individual)")] = "thread",
    output: Annotated[Path, typer.Option("--output", "-o", help="Output directory")] = Path("exports/emails"),
    stdout: Annotated[bool, typer.Option("--stdout", help="Output to stdout instead of files")] = False,
    depth: Annotated[int, typer.Option("--depth", "-d", help="Link following depth")] = 0,
    credentials: Annotated[Path, typer.Option("--credentials", "-c", help="Path to credentials file")] = Path(
        ".client_secret.googleusercontent.com.json"
    ),
    token: Annotated[Path, typer.Option("--token", "-t", help="Path to token file")] = Path("tmp/token_drive.json"),
) -> None:
    """Export Gmail messages to JSON or Markdown.

    Examples:
        gwt mail -q "from:boss@example.com" -f md

        gwt mail -q "subject:weekly" --stdout

        gwt mail -a 2024-01-01 -l work,important

        gwt mail -q "has:attachment" -d 2
    """
    # Get formatter for output mode
    formatter = get_formatter(get_output_mode())

    with cli_error_handler(formatter):
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

        # Handle stdout mode - output directly and exit
        if stdout:
            import sys

            content = exporter.format_emails_as_string(
                filters=filters,
                export_format=export_format,
                export_mode=cast(Literal["thread", "individual"], mode),
            )
            sys.stdout.write(content)
            if content and not content.endswith("\n"):
                sys.stdout.write("\n")
            return

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

        # Print next-step hints (only for human output mode)
        if get_output_mode() == OutputMode.HUMAN:
            # Check if any Drive links were found in exported threads
            drive_links_found = sum(t.drive_links_found for t in threads)
            hints: list[tuple[str, str]] = []

            if drive_links_found > 0:
                hints.append(
                    (
                        f"gwt download <URL> -d {depth or 1}",
                        f"Download {drive_links_found} linked Drive doc(s)",
                    )
                )

            hints.extend(
                [
                    ("gwt calendar -a YYYY-MM-DD", "Export related calendar events"),
                    ("gwt download <URL>", "Download a specific document"),
                ]
            )
            print_next_steps(formatter, hints)
