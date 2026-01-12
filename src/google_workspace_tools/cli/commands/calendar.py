"""Calendar export command for Google Workspace Tools."""

from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Any

import typer
from loguru import logger

from ... import __version__
from ...core.config import GoogleDriveExporterConfig
from ...core.exporter import GoogleDriveExporter
from ...core.filters import CalendarEventFilter
from ..formatters import get_formatter
from ..output import get_output_mode
from ..schemas import (
    CalendarEventExport,
    CalendarInfo,
    CalendarListOutput,
    CalendarOutput,
)


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
    credentials: Annotated[Path, typer.Option("--credentials", "-c", help="Path to credentials file")] = Path(
        ".client_secret.googleusercontent.com.json"
    ),
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
            _export_single_event(exporter, formatter, event_id, calendar_id, export_format, output, depth)
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


def _export_single_event(
    exporter: GoogleDriveExporter,
    formatter: Any,
    event_id: str,
    calendar_id: str,
    export_format: str,
    output: Path,
    depth: int,
) -> None:
    """Export a single calendar event by ID.

    Args:
        exporter: GoogleDriveExporter instance
        formatter: Output formatter
        event_id: Event ID to fetch
        calendar_id: Calendar ID containing the event
        export_format: Export format (json or md)
        output: Output directory
        depth: Link following depth
    """
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
            date_dir = datetime.now(UTC).strftime("%Y-%m")
    else:
        date_dir = datetime.now(UTC).strftime("%Y-%m")

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
