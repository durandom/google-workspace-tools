"""Configuration models for Google Workspace Tools."""

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class GoogleDriveExporterConfig(BaseModel):
    """Configuration for GoogleDriveExporter."""

    credentials_path: Path = Field(default=Path(".client_secret.googleusercontent.com.json"))
    token_path: Path = Field(default=Path("tmp/token_drive.json"))
    target_directory: Path = Field(default=Path("exports"))
    export_format: Literal[
        "pdf",
        "docx",
        "odt",
        "rtf",
        "txt",
        "html",
        "epub",
        "zip",
        "md",
        "xlsx",
        "ods",
        "csv",
        "tsv",
        "pptx",
        "odp",
        "all",
    ] = "html"
    link_depth: int = Field(default=0, ge=0, le=5)
    follow_links: bool = Field(default=False)
    scopes: list[str] = Field(
        default_factory=lambda: [
            "https://www.googleapis.com/auth/drive",
            "https://www.googleapis.com/auth/documents",
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/presentations",
        ]
    )

    @field_validator("target_directory", mode="before")
    @classmethod
    def ensure_path(cls, v):
        """Ensure target_directory is a Path object."""
        return Path(v) if not isinstance(v, Path) else v
