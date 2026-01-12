"""CLI application for Google Workspace Tools.

This module assembles the CLI application by importing commands from the
commands subpackage and registering them with the main Typer app.
"""

from typing import Annotated

import typer
from rich.console import Console
from rich.panel import Panel

from .. import __version__
from ..core.storage import get_credential_storage
from ..settings import settings
from .commands.calendar import calendar_app
from .commands.credentials import credentials
from .commands.download import download, mirror
from .commands.mail import mail
from .commands.utility import dump_schema as _dump_schema
from .commands.utility import extract_id, formats, version
from .output import OutputMode, set_output_mode

console = Console()


def _get_auth_status() -> tuple[bool, str | None]:
    """Check authentication status without triggering OAuth flow.

    Returns:
        Tuple of (is_authenticated, email_or_None)
    """
    try:
        storage = get_credential_storage(
            use_keyring=settings.use_keyring,
            service_name=settings.keyring_service_name,
            token_path=settings.token_path,
        )
        creds = storage.load()
        if creds and creds.token_data:
            # Try to get email from stored credentials
            email = creds.email or creds.token_data.get("email")
            return True, email
        return False, None
    except Exception:
        return False, None


def _show_status() -> None:
    """Display status and next steps when gwt is run without arguments."""
    # Auth status
    is_authed, email = _get_auth_status()
    if is_authed:
        auth_line = f"[green]✓[/green] Logged in" + (f" as [cyan]{email}[/cyan]" if email else "")
    else:
        auth_line = "[yellow]○[/yellow] Not authenticated"

    # Build status content
    status_lines = [
        f"[bold blue]google-workspace-tools[/bold blue] v{__version__}",
        "",
        f"[bold]Authentication:[/bold] {auth_line}",
        f"[bold]Default output:[/bold]  [dim]{settings.target_directory}[/dim]",
    ]

    # Next steps
    next_steps = [
        "",
        "[bold]Next steps:[/bold]",
        "  [cyan]gwt download <URL>[/cyan]       Export a Google Doc/Sheet/Slides",
        '  [cyan]gwt mail -q "from:boss"[/cyan]  Export Gmail messages',
        "  [cyan]gwt calendar list[/cyan]        List your calendars",
        "  [cyan]gwt credentials[/cyan]          Manage authentication",
        "  [cyan]gwt --help[/cyan]               Show all commands",
    ]

    console.print(Panel("\n".join(status_lines + next_steps), border_style="blue"))

app = typer.Typer(
    name="gwt",
    help="Google Workspace Tools - Export and manage Google Drive documents",
    add_completion=True,
    rich_markup_mode="rich",
    invoke_without_command=True,
)


def version_callback(value: bool) -> None:
    """Print version and exit."""
    if value:
        console.print(f"[bold blue]google-workspace-tools[/bold blue] version [green]{__version__}[/green]")
        raise typer.Exit()


@app.callback()
def main_callback(
    ctx: typer.Context,
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

        from loguru import logger

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

    # Show status when no subcommand is invoked
    if ctx.invoked_subcommand is None:
        _show_status()


# Register commands
app.command()(download)
app.command()(mirror)
app.command()(formats)
app.command(name="extract-id")(extract_id)
app.command()(mail)
app.add_typer(calendar_app, name="calendar")
app.command()(credentials)
app.command()(version)


# Special handling for dump_schema - it needs access to the app
@app.command(name="dump-schema")
def dump_schema_cmd(
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
    _dump_schema(output_format=output_format, app=app)


if __name__ == "__main__":
    app()
