"""Output formatters for CLI commands."""

import json
import sys
from abc import ABC, abstractmethod
from typing import Any

from rich.console import Console
from rich.table import Table

from .output import OutputMode
from .schemas import (
    CalendarEventExport,
    CalendarInfo,
    CalendarListOutput,
    CalendarOutput,
    CommandOutput,
    DocumentExport,
    DownloadOutput,
    EmailThreadExport,
    MailOutput,
    MirrorDocumentResult,
    MirrorOutput,
)


class BaseOutputFormatter(ABC):
    """Abstract base class for output formatters."""

    @abstractmethod
    def print_progress(self, message: str) -> None:
        """Print a progress message.

        Args:
            message: Progress message to display
        """
        pass

    @abstractmethod
    def print_success(self, message: str) -> None:
        """Print a success message.

        Args:
            message: Success message to display
        """
        pass

    @abstractmethod
    def print_error(self, message: str) -> None:
        """Print an error message.

        Args:
            message: Error message to display
        """
        pass

    @abstractmethod
    def print_warning(self, message: str) -> None:
        """Print a warning message.

        Args:
            message: Warning message to display
        """
        pass

    @abstractmethod
    def print_info(self, message: str) -> None:
        """Print an informational message.

        Args:
            message: Info message to display
        """
        pass

    @abstractmethod
    def print_result(self, result: CommandOutput) -> None:
        """Print the final command result.

        Args:
            result: Command output schema to display
        """
        pass


class HumanOutputFormatter(BaseOutputFormatter):
    """Formatter for human-readable Rich console output."""

    def __init__(self) -> None:
        """Initialize the human output formatter."""
        self.console = Console()

    def print_progress(self, message: str) -> None:
        """Print a progress message with formatting."""
        self.console.print(message)

    def print_success(self, message: str) -> None:
        """Print a success message in green."""
        self.console.print(f"[green]{message}[/green]")

    def print_error(self, message: str) -> None:
        """Print an error message in red."""
        self.console.print(f"[red]{message}[/red]")

    def print_warning(self, message: str) -> None:
        """Print a warning message in yellow."""
        self.console.print(f"[yellow]{message}[/yellow]")

    def print_info(self, message: str) -> None:
        """Print an informational message in dim."""
        self.console.print(f"[dim]{message}[/dim]")

    def print_result(self, result: CommandOutput) -> None:
        """Print the final command result with Rich formatting."""
        if isinstance(result, DownloadOutput):
            self._print_download_result(result)
        elif isinstance(result, MailOutput):
            self._print_mail_result(result)
        elif isinstance(result, CalendarListOutput):
            self._print_calendar_list_result(result)
        elif isinstance(result, CalendarOutput):
            self._print_calendar_result(result)
        elif isinstance(result, MirrorOutput):
            self._print_mirror_result(result)
        else:
            # Fallback for unknown result types
            self.console.print(f"[dim]{result.model_dump_json(indent=2)}[/dim]")

    def _print_download_result(self, result: DownloadOutput) -> None:
        """Print download command result."""
        if result.success:
            self.console.print(f"\n[green]Successfully exported {len(result.documents)} document(s)[/green]")
            for doc in result.documents:
                self.console.print(f"  [dim]{doc.document_id}[/dim]")
                for file in doc.files:
                    self.console.print(f"    {file.format}: [blue]{file.path}[/blue]")
                if doc.errors:
                    for error in doc.errors:
                        self.console.print(f"    [yellow]Warning: {error}[/yellow]")
        else:
            self.console.print("[yellow]Export completed with errors[/yellow]")
            for error in result.errors:
                self.console.print(f"  [red]{error}[/red]")

    def _print_mail_result(self, result: MailOutput) -> None:
        """Print mail command result."""
        export_type = "threads" if result.export_mode == "thread" else "messages"
        if result.success:
            self.console.print(f"\n[green]✓ Exported {result.total_exported} {export_type}[/green]")
            if result.threads:
                for thread in result.threads:
                    self.console.print(f"  [blue]{thread.export_path}[/blue]")
            self.console.print(f"\n[dim]Output directory: {result.output_directory}[/dim]")
        else:
            self.console.print(f"[yellow]Export completed with errors[/yellow]")
            for error in result.errors:
                self.console.print(f"  [red]{error}[/red]")

    def _print_calendar_list_result(self, result: CalendarListOutput) -> None:
        """Print calendar list result."""
        if not result.calendars:
            self.console.print("[yellow]No calendars found[/yellow]")
            return

        table = Table(title="Google Calendars", show_header=True, header_style="bold cyan")
        table.add_column("Summary", style="green")
        table.add_column("ID", style="dim")
        table.add_column("Primary", style="yellow")

        for cal in result.calendars:
            table.add_row(cal.summary, cal.id, "✓" if cal.primary else "")

        self.console.print(table)
        self.console.print(f"\n[dim]Total: {result.total_count}[/dim]")

    def _print_calendar_result(self, result: CalendarOutput) -> None:
        """Print calendar export result."""
        if result.success:
            self.console.print(f"\n[green]✓ Exported {result.total_exported} events[/green]")
            if result.events:
                for event in result.events:
                    self.console.print(f"  [blue]{event.export_path}[/blue]")
            self.console.print(f"\n[dim]Output directory: {result.output_directory}[/dim]")
        else:
            self.console.print("[yellow]Export completed with errors[/yellow]")
            for error in result.errors:
                self.console.print(f"  [red]{error}[/red]")

    def _print_mirror_result(self, result: MirrorOutput) -> None:
        """Print mirror command result."""
        if result.success:
            self.console.print(f"\n[green]Successfully mirrored {len(result.documents)} document(s)[/green]")
            for doc in result.documents:
                self.console.print(f"  [dim]{doc.document_id}[/dim]")
                if doc.errors:
                    for error in doc.errors:
                        self.console.print(f"    [yellow]Warning: {error}[/yellow]")
        else:
            self.console.print("[yellow]Mirror completed with errors[/yellow]")
            for error in result.errors:
                self.console.print(f"  [red]{error}[/red]")


class JSONOutputFormatter(BaseOutputFormatter):
    """Formatter for machine-readable JSON output."""

    def __init__(self) -> None:
        """Initialize the JSON output formatter."""
        # Store messages that would normally be progress/status updates
        # but we'll suppress them in JSON mode
        self._suppressed_messages: list[dict[str, Any]] = []

    def print_progress(self, message: str) -> None:
        """Suppress progress messages in JSON mode (or log to stderr)."""
        # Option 1: Completely suppress
        pass
        # Option 2: Log to stderr if desired
        # print(message, file=sys.stderr)

    def print_success(self, message: str) -> None:
        """Suppress success messages in JSON mode."""
        pass

    def print_error(self, message: str) -> None:
        """Print errors to stderr in JSON mode."""
        print(f"ERROR: {message}", file=sys.stderr)

    def print_warning(self, message: str) -> None:
        """Print warnings to stderr in JSON mode."""
        print(f"WARNING: {message}", file=sys.stderr)

    def print_info(self, message: str) -> None:
        """Suppress info messages in JSON mode."""
        pass

    def print_result(self, result: CommandOutput) -> None:
        """Print the final command result as JSON to stdout."""
        # Convert Pydantic model to dict, then to JSON
        output = result.model_dump(mode="json", exclude_none=False)
        print(json.dumps(output, indent=2))


def get_formatter(mode: OutputMode) -> BaseOutputFormatter:
    """Get the appropriate formatter for the given output mode.

    Args:
        mode: The output mode (HUMAN or JSON)

    Returns:
        Formatter instance for the given mode
    """
    if mode == OutputMode.JSON:
        return JSONOutputFormatter()
    return HumanOutputFormatter()
