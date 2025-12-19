"""Common CLI utilities."""

from pathlib import Path

from ..core.config import GoogleDriveExporterConfig
from ..core.exporter import GoogleDriveExporter


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
