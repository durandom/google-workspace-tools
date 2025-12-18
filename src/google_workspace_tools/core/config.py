"""Configuration models for Google Workspace Tools."""

from pathlib import Path
from typing import Any, Literal

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
            "https://www.googleapis.com/auth/drive.readonly",
            "https://www.googleapis.com/auth/documents.readonly",
            "https://www.googleapis.com/auth/spreadsheets.readonly",
            "https://www.googleapis.com/auth/presentations.readonly",
        ]
    )
    # Frontmatter configuration
    enable_frontmatter: bool = Field(default=False, description="Enable YAML frontmatter in markdown files")
    frontmatter_fields: dict[str, Any] = Field(default_factory=dict, description="Custom frontmatter fields to inject")
    # Spreadsheet export configuration
    spreadsheet_export_mode: Literal["combined", "separate", "csv"] = Field(
        default="combined",
        description="How to export spreadsheets: 'combined' (single .md with all sheets), "
        "'separate' (one .md per sheet), 'csv' (legacy CSV export)",
    )
    keep_intermediate_xlsx: bool = Field(
        default=True, description="Keep intermediate XLSX files when converting to markdown"
    )

    @field_validator("target_directory", mode="before")
    @classmethod
    def ensure_path(cls, v):
        """Ensure target_directory is a Path object."""
        return Path(v) if not isinstance(v, Path) else v
