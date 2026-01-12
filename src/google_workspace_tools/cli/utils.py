"""Common CLI utilities."""

from contextlib import contextmanager
from pathlib import Path
from typing import TYPE_CHECKING, Generator

import typer
from loguru import logger

from ..core.config import GoogleDriveExporterConfig
from ..core.exporter import GoogleDriveExporter

if TYPE_CHECKING:
    from .formatters import BaseOutputFormatter


@contextmanager
def cli_error_handler(
    formatter: "BaseOutputFormatter",
    *,
    auth_hint: bool = True,
) -> Generator[None, None, None]:
    """Context manager for consistent CLI error handling.

    Provides standardized error handling across all CLI commands:
    - FileNotFoundError: Suggests authentication if auth_hint=True
    - typer.Exit: Re-raised unchanged (intentional exits)
    - Exception: Logs and prints error, exits with code 1

    Args:
        formatter: Output formatter for printing errors
        auth_hint: If True, show auth hint on FileNotFoundError

    Yields:
        None

    Raises:
        typer.Exit: On any error (code 1) or re-raised from inner code

    Example:
        with cli_error_handler(formatter):
            exporter = GoogleDriveExporter(config)
            exporter.export_emails(...)
    """
    try:
        yield
    except FileNotFoundError as e:
        logger.error(f"File not found: {e}")
        formatter.print_error(f"Error: {e}")
        if auth_hint:
            formatter.print_info("Run 'gwt credentials login' to authenticate")
        raise typer.Exit(1) from e
    except typer.Exit:
        # Re-raise intentional exits unchanged
        raise
    except Exception as e:
        logger.error(f"Command failed: {e}")
        formatter.print_error(f"Error: {e}")
        raise typer.Exit(1) from e


def init_exporter(
    credentials: Path,
    token_path: Path | None = None,
    config: GoogleDriveExporterConfig | None = None,
) -> GoogleDriveExporter:
    """Initialize GoogleDriveExporter with standardized configuration.

    Args:
        credentials: Path to Google OAuth credentials file
        token_path: Optional path to save/load OAuth token
        config: Optional GoogleDriveExporterConfig (will be created if None)

    Returns:
        Configured GoogleDriveExporter instance

    Raises:
        FileNotFoundError: If credentials file doesn't exist
        Exception: For other authentication/initialization errors
    """
    if config is None:
        config = GoogleDriveExporterConfig(
            credentials_path=credentials,
            token_path=token_path or Path("tmp/token_drive.json"),
        )

    return GoogleDriveExporter(config)


def format_relative_path(path: Path, base: Path | None = None) -> str:
    """Format a path relative to a base directory.

    Args:
        path: Path to format
        base: Base directory (defaults to current working directory)

    Returns:
        Relative path as string if possible, otherwise absolute path
    """
    if base is None:
        base = Path.cwd()

    try:
        # Try to make it relative
        if base.exists() and path.is_relative_to(base):
            return str(path.relative_to(base))
    except (ValueError, OSError):
        pass

    # Fall back to absolute path
    return str(path.absolute())


def get_file_size(path: Path) -> int | None:
    """Get file size in bytes safely.

    Args:
        path: Path to file

    Returns:
        File size in bytes, or None if unable to determine
    """
    if not path.exists():
        return None

    try:
        return path.stat().st_size
    except (OSError, PermissionError):
        return None


def sanitize_filename(filename: str, max_length: int = 200) -> str:
    """Sanitize a string to be safe for use as a filename.

    Args:
        filename: Original filename
        max_length: Maximum length for the sanitized filename

    Returns:
        Sanitized filename
    """
    # Replace unsafe characters with underscores
    safe_chars = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 -_")
    sanitized = "".join(c if c in safe_chars else "_" for c in filename)

    # Trim to max length
    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length]

    # Remove trailing/leading whitespace and underscores
    sanitized = sanitized.strip(" _")

    return sanitized or "untitled"


def print_next_steps(formatter: "BaseOutputFormatter", hints: list[tuple[str, str]]) -> None:
    """Print next-step hints for agentic CLI.

    This follows the agentic CLI pattern where every command output suggests
    logical next actions, helping both AI agents and humans discover workflows.

    Args:
        formatter: Output formatter instance
        hints: List of (command, description) tuples
    """
    if not hints:
        return

    formatter.print_info("\nNext steps:")
    for cmd, desc in hints:
        formatter.print_info(f"  {cmd:<40} {desc}")
