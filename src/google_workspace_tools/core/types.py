"""Core type definitions for Google Workspace Tools."""

from dataclasses import dataclass
from enum import Enum

from pydantic import BaseModel


class DocumentType(Enum):
    """Google Drive document types."""

    DOCUMENT = "document"
    SPREADSHEET = "spreadsheet"
    PRESENTATION = "presentation"
    EMAIL = "email"
    CALENDAR_EVENT = "calendar"
    UNKNOWN = "unknown"


@dataclass
class DocumentConfig:
    """Configuration for a single document to mirror."""

    url: str
    document_id: str
    depth: int = 0
    comment: str = ""


class ExportFormat(BaseModel):
    """Represents an export format configuration."""

    extension: str
    mime_type: str
    description: str | None = None
