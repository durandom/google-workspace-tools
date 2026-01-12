"""Output schemas for CLI commands."""

import contextlib
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class CommandOutput(BaseModel):
    """Base output schema for all commands."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "command": "download",
                "success": True,
                "timestamp": "2024-01-15T10:30:00Z",
                "version": "0.1.0",
                "errors": [],
            }
        }
    )

    command: str = Field(..., description="Command name (download, mail, calendar, mirror)")
    success: bool = Field(..., description="Overall success status")
    timestamp: str = Field(default_factory=lambda: datetime.now(UTC).isoformat(), description="ISO 8601 timestamp")
    version: str = Field(..., description="CLI version")
    errors: list[str] = Field(default_factory=list, description="List of error messages")


# Download command schemas


class ExportedFile(BaseModel):
    """Single exported file information."""

    format: str = Field(..., description="Export format (md, pdf, docx, etc.)")
    path: str = Field(..., description="Absolute path to exported file")
    size_bytes: int | None = Field(None, description="File size in bytes (if available)")

    @classmethod
    def from_path(cls, format: str, path: Path) -> "ExportedFile":
        """Create ExportedFile from a Path object.

        Args:
            format: Export format
            path: Path to the file

        Returns:
            ExportedFile instance
        """
        size = None
        if path.exists():
            with contextlib.suppress(OSError, PermissionError):
                size = path.stat().st_size
        return cls(format=format, path=str(path.absolute()), size_bytes=size)


class DocumentExport(BaseModel):
    """Single document export result."""

    document_id: str = Field(..., description="Google Drive document ID")
    title: str = Field(..., description="Document title")
    source_url: str = Field(..., description="Original Google Drive URL")
    doc_type: str = Field(..., description="Document type (document, spreadsheet, presentation)")
    files: list[ExportedFile] = Field(default_factory=list, description="List of exported files")
    link_following_depth: int = Field(0, description="Link following depth used")
    linked_documents_count: int = Field(0, description="Number of linked documents found")
    errors: list[str] = Field(default_factory=list, description="Document-specific errors")


class DownloadOutput(CommandOutput):
    """Output schema for download command."""

    documents: list[DocumentExport] = Field(default_factory=list, description="List of document exports")
    total_files_exported: int = Field(0, description="Total number of files exported")
    output_directory: str = Field(..., description="Output directory path")
    link_following_enabled: bool = Field(False, description="Whether link following was enabled")
    max_link_depth: int = Field(0, description="Maximum link following depth")


# Mail command schemas


class EmailThreadExport(BaseModel):
    """Single email thread/message export result."""

    thread_id: str = Field(..., description="Gmail thread ID")
    subject: str = Field(..., description="Email subject")
    message_count: int = Field(..., description="Number of messages in thread")
    participants: list[str] = Field(default_factory=list, description="Email participants")
    export_path: str = Field(..., description="Path to exported file")
    date_range: dict[str, str] = Field(default_factory=dict, description="First and last message dates (ISO 8601)")
    has_attachments: bool = Field(False, description="Whether thread has attachments")
    drive_links_found: int = Field(0, description="Number of Google Drive links discovered")


class MailOutput(CommandOutput):
    """Output schema for mail command."""

    export_mode: str = Field(..., description="Export mode (thread or individual)")
    export_format: str = Field(..., description="Export format (json or md)")
    filters_applied: dict[str, Any] = Field(default_factory=dict, description="Filters applied to search")
    threads: list[EmailThreadExport] = Field(default_factory=list, description="List of exported threads")
    total_exported: int = Field(0, description="Total threads/messages exported")
    output_directory: str = Field(..., description="Output directory path")
    link_following_enabled: bool = Field(False, description="Whether link following was enabled")


# Calendar command schemas


class CalendarInfo(BaseModel):
    """Calendar information for listing."""

    id: str = Field(..., description="Calendar ID")
    summary: str = Field(..., description="Calendar name/summary")
    primary: bool = Field(False, description="Whether this is the primary calendar")


class CalendarListOutput(CommandOutput):
    """Output schema for calendar list (no filters)."""

    calendars: list[CalendarInfo] = Field(default_factory=list, description="List of calendars")
    total_count: int = Field(0, description="Total number of calendars")


class CalendarEventExport(BaseModel):
    """Single calendar event export result."""

    event_id: str = Field(..., description="Calendar event ID")
    calendar_id: str = Field(..., description="Calendar ID this event belongs to")
    summary: str = Field(..., description="Event summary/title")
    start_time: str = Field(..., description="Event start time (ISO 8601)")
    end_time: str = Field(..., description="Event end time (ISO 8601)")
    location: str | None = Field(None, description="Event location")
    attendees_count: int = Field(0, description="Number of attendees")
    export_path: str = Field(..., description="Path to exported file")
    has_attachments: bool = Field(False, description="Whether event has attachments")
    drive_links_found: int = Field(0, description="Number of Google Drive links discovered")


class CalendarOutput(CommandOutput):
    """Output schema for calendar export."""

    export_format: str = Field(..., description="Export format (json or md)")
    filters_applied: dict[str, Any] = Field(default_factory=dict, description="Filters applied")
    calendars_queried: list[str] = Field(default_factory=list, description="Calendar IDs queried")
    events: list[CalendarEventExport] = Field(default_factory=list, description="List of exported events")
    total_exported: int = Field(0, description="Total events exported")
    output_directory: str = Field(..., description="Output directory path")
    link_following_enabled: bool = Field(False, description="Whether link following was enabled")


# Mirror command schemas


class MirrorDocumentResult(BaseModel):
    """Result of mirroring a single document."""

    document_id: str = Field(..., description="Google Drive document ID")
    source_url: str = Field(..., description="Original URL from config")
    configured_depth: int = Field(0, description="Link following depth configured for this document")
    files_exported: list[ExportedFile] = Field(default_factory=list, description="Files exported")
    linked_documents_count: int = Field(0, description="Number of linked documents followed")
    errors: list[str] = Field(default_factory=list, description="Document-specific errors")


class MirrorOutput(CommandOutput):
    """Output schema for mirror command."""

    config_file: str = Field(..., description="Path to mirror configuration file")
    documents_configured: int = Field(0, description="Number of documents in config")
    documents: list[MirrorDocumentResult] = Field(default_factory=list, description="List of mirrored documents")
    total_files_exported: int = Field(0, description="Total files exported across all documents")
    output_directory: str = Field(..., description="Output directory path")
    export_format: str = Field(..., description="Export format used")
