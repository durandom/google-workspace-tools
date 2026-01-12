"""Calendar export command for Google Workspace Tools.

Provides subcommands for interacting with Google Calendar:
- list: List accessible calendars
- get: Fetch a single event by ID
- export: Batch export events with filters
"""

from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated

import typer

from ... import __version__
from ...core.config import GoogleDriveExporterConfig
from ...core.exporter import GoogleDriveExporter
from ...core.filters import CalendarEventFilter
from ..formatters import get_formatter
from ..output import OutputMode, get_output_mode
from ..schemas import (
    CalendarEventExport,
    CalendarInfo,
    CalendarListOutput,
    CalendarOutput,
)
from ..utils import cli_error_handler, print_next_steps

# Create subcommand app
calendar_app = typer.Typer(
    name="calendar",
    help="Google Calendar operations - list calendars, fetch events, export",
    rich_markup_mode="rich",
)


# Common options as defaults
DEFAULT_CREDENTIALS = Path(".client_secret.googleusercontent.com.json")
DEFAULT_TOKEN = Path("tmp/token_drive.json")
DEFAULT_OUTPUT = Path("exports/calendar")


def _create_exporter(
    credentials: Path,
    token: Path,
    output: Path,
    depth: int = 0,
) -> GoogleDriveExporter:
    """Create a configured GoogleDriveExporter instance.

    Args:
        credentials: Path to credentials file
        token: Path to token file
        output: Output directory (used for target_directory)
        depth: Link following depth

    Returns:
        Configured GoogleDriveExporter
    """
    config = GoogleDriveExporterConfig(
        credentials_path=credentials,
        token_path=token,
        target_directory=output.parent,
        follow_links=(depth > 0),
        link_depth=depth,
    )
    return GoogleDriveExporter(config)


@calendar_app.command(name="list")
def calendar_list(
    credentials: Annotated[
        Path, typer.Option("--credentials", "-c", help="Path to credentials file")
    ] = DEFAULT_CREDENTIALS,
    token: Annotated[
        Path, typer.Option("--token", "-t", help="Path to token file")
    ] = DEFAULT_TOKEN,
) -> None:
    """List all accessible Google Calendars.

    Shows calendar IDs which can be used with other calendar commands.

    Examples:
        gwt calendar list
        gwt calendar list --credentials my_creds.json
    """
    formatter = get_formatter(get_output_mode())

    with cli_error_handler(formatter):
        exporter = _create_exporter(credentials, token, DEFAULT_OUTPUT)
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

        output_schema = CalendarListOutput(
            command="calendar list",
            success=True,
            version=__version__,
            calendars=calendar_infos,
            total_count=len(calendars),
        )

        formatter.print_result(output_schema)

        # Print next-step hints (only for human output mode)
        if get_output_mode() == OutputMode.HUMAN:
            print_next_steps(
                formatter,
                [
                    ("gwt calendar export -a YYYY-MM-DD -b YYYY-MM-DD", "Export events in date range"),
                    ("gwt calendar export --calendar <ID>", "Export from specific calendar"),
                    ("gwt calendar get -e <EVENT_ID>", "Fetch a specific event"),
                ],
            )


@calendar_app.command(name="get")
def calendar_get(
    event_id: Annotated[
        str, typer.Option("--event-id", "-e", help="Event ID to fetch")
    ],
    calendar_id: Annotated[
        str, typer.Option("--calendar", help="Calendar ID")
    ] = "primary",
    export_format: Annotated[
        str, typer.Option("--format", "-f", help="Export format (json, md)")
    ] = "md",
    output: Annotated[
        Path, typer.Option("--output", "-o", help="Output directory")
    ] = DEFAULT_OUTPUT,
    depth: Annotated[
        int, typer.Option("--depth", "-d", help="Link following depth")
    ] = 0,
    credentials: Annotated[
        Path, typer.Option("--credentials", "-c", help="Path to credentials file")
    ] = DEFAULT_CREDENTIALS,
    token: Annotated[
        Path, typer.Option("--token", "-t", help="Path to token file")
    ] = DEFAULT_TOKEN,
) -> None:
    """Fetch and export a single calendar event by ID.

    Retrieves a specific event and exports it to the specified format.

    Examples:
        gwt calendar get -e abc123def456
        gwt calendar get -e EVENT_ID --calendar work@group.calendar.google.com
        gwt calendar get -e EVENT_ID -f json -d 2
    """
    formatter = get_formatter(get_output_mode())

    with cli_error_handler(formatter):
        exporter = _create_exporter(credentials, token, output, depth)

        formatter.print_progress(f"[bold]Fetching event {event_id}...[/bold]")
        event = exporter.get_calendar_event(event_id, calendar_id)

        if not event:
            formatter.print_error(f"Event {event_id} not found")
            raise typer.Exit(1)

        # Export the single event
        summary = event.get("summary", "no-title")
        safe_summary = "".join(c if c.isalnum() or c in (" ", "-", "_") else "_" for c in summary)[:50]

        # Get start date for directory organization
        start = event.get("start", {})
        start_time = start.get("dateTime", start.get("date", ""))
        date_dir = _parse_date_dir(start_time)

        safe_calendar_id = calendar_id.replace("@", "_at_").replace(".", "_")
        event_dir = output / safe_calendar_id / date_dir
        filename = f"event_{event_id}_{safe_summary}.{export_format}"
        output_path = event_dir / filename

        # Export based on format
        if export_format == "json":
            success = exporter._export_calendar_event_as_json(event, output_path)
        else:  # md
            success = exporter._export_calendar_event_as_markdown(event, output_path)

        if not success:
            formatter.print_error("Failed to export event")
            raise typer.Exit(1)

        # Build output schema
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
            command="calendar get",
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

        # Print next-step hints (only for human output mode)
        if get_output_mode() == OutputMode.HUMAN:
            print_next_steps(
                formatter,
                [
                    ("gwt calendar export -a YYYY-MM-DD", "Export more events"),
                    ("gwt mail -q 'from:...'", "Export related Gmail messages"),
                    ("gwt download <URL>", "Download a linked document"),
                ],
            )


@calendar_app.command(name="export")
def calendar_export(
    calendar_id: Annotated[
        str, typer.Option("--calendar", help="Calendar ID")
    ] = "primary",
    after: Annotated[
        str | None, typer.Option("--after", "-a", help="After date (YYYY-MM-DD)")
    ] = None,
    before: Annotated[
        str | None, typer.Option("--before", "-b", help="Before date (YYYY-MM-DD)")
    ] = None,
    query: Annotated[
        str, typer.Option("--query", "-q", help="Search query")
    ] = "",
    max_results: Annotated[
        int, typer.Option("--max", "-n", help="Maximum events to fetch")
    ] = 250,
    export_format: Annotated[
        str, typer.Option("--format", "-f", help="Export format (json, md)")
    ] = "md",
    output: Annotated[
        Path, typer.Option("--output", "-o", help="Output directory")
    ] = DEFAULT_OUTPUT,
    depth: Annotated[
        int, typer.Option("--depth", "-d", help="Link following depth")
    ] = 0,
    credentials: Annotated[
        Path, typer.Option("--credentials", "-c", help="Path to credentials file")
    ] = DEFAULT_CREDENTIALS,
    token: Annotated[
        Path, typer.Option("--token", "-t", help="Path to token file")
    ] = DEFAULT_TOKEN,
) -> None:
    """Export Google Calendar events with optional filters.

    Batch exports events from a calendar, optionally filtered by date range
    and search query.

    Examples:
        gwt calendar export -a 2024-01-01 -b 2024-12-31
        gwt calendar export --calendar work -q "sprint"
        gwt calendar export -d 2  # Follow links in event descriptions
    """
    formatter = get_formatter(get_output_mode())

    with cli_error_handler(formatter):
        exporter = _create_exporter(credentials, token, output, depth)

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

        # Build event export list
        events: list[CalendarEventExport] = []
        for evt_id, file_path in exported.items():
            events.append(
                CalendarEventExport(
                    event_id=evt_id,
                    calendar_id=calendar_id,
                    summary="Exported Event",  # Would need API call to get actual summary
                    start_time=datetime.now(UTC).isoformat(),
                    end_time=datetime.now(UTC).isoformat(),
                    location=None,
                    attendees_count=0,
                    export_path=str(file_path.absolute()),
                    has_attachments=False,
                    drive_links_found=0,
                )
            )

        # Build output schema
        export_schema = CalendarOutput(
            command="calendar export",
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

        formatter.print_result(export_schema)

        # Print next-step hints (only for human output mode)
        if get_output_mode() == OutputMode.HUMAN:
            drive_links_found = sum(e.drive_links_found for e in events)
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
                    ("gwt mail -q 'from:...'", "Export related Gmail messages"),
                    ("gwt download <URL>", "Download a specific document"),
                ]
            )
            print_next_steps(formatter, hints)


def _parse_date_dir(start_time: str) -> str:
    """Parse start time to get date directory name (YYYY-MM format).

    Args:
        start_time: ISO format datetime or date string

    Returns:
        Directory name in YYYY-MM format
    """
    if not start_time:
        return datetime.now(UTC).strftime("%Y-%m")

    try:
        if "T" in start_time:
            date_obj = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
        else:
            date_obj = datetime.fromisoformat(start_time)
        return date_obj.strftime("%Y-%m")
    except Exception:
        return datetime.now(UTC).strftime("%Y-%m")
