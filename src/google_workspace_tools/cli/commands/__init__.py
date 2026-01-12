"""CLI commands for Google Workspace Tools."""

from .calendar import calendar_app
from .credentials import credentials
from .download import download, mirror
from .mail import mail
from .utility import dump_schema, extract_id, formats, version

__all__ = [
    "calendar_app",
    "credentials",
    "download",
    "dump_schema",
    "extract_id",
    "formats",
    "mail",
    "mirror",
    "version",
]
