"""Configuration models for Google Workspace Tools."""

from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


def _default_storage_backend() -> str:
    """Get default storage backend from settings."""
    from ..settings import settings

    return settings.storage_backend


def _default_keyring_service_name() -> str:
    """Get default keyring service name from settings."""
    from ..settings import settings

    return settings.keyring_service_name


def _default_onepassword_vault() -> str | None:
    """Get default 1Password vault from settings."""
    from ..settings import settings

    return settings.onepassword_vault


def _default_credentials_path() -> Path:
    """Get default credentials path from settings."""
    from ..settings import settings

    return settings.credentials_path


def _default_token_path() -> Path:
    """Get default token path from settings."""
    from ..settings import settings

    return settings.token_path


class GoogleDriveExporterConfig(BaseModel):
    """Configuration for GoogleDriveExporter."""

    credentials_path: Path = Field(default_factory=_default_credentials_path)
    token_path: Path = Field(default_factory=_default_token_path)
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
            "https://www.googleapis.com/auth/gmail.readonly",
            "https://www.googleapis.com/auth/calendar.readonly",
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
    # Google Docs comments & suggestions
    include_comments: bool = Field(default=True, description="Include Google Docs comments in markdown exports")
    include_suggestions: bool = Field(default=True, description="Include Google Docs suggestions in markdown exports")
    # Credential storage configuration — defaults come from settings (config.toml / env vars)
    storage_backend: Literal["auto", "1password", "keyring", "file"] = Field(
        default_factory=_default_storage_backend,  # type: ignore[arg-type]
        description="Storage backend: 'auto' (1Password→keyring→file), '1password', 'keyring', or 'file'",
    )
    use_keyring: bool = Field(
        default=True,
        description="Use keyring for credential storage if available (legacy, use storage_backend)",
    )
    keyring_service_name: str = Field(
        default_factory=_default_keyring_service_name,
        description="Service name used for keyring/1Password storage",
    )
    keyring_fallback_to_file: bool = Field(
        default=True,
        description="Fall back to file storage if preferred backend is unavailable",
    )
    onepassword_vault: str | None = Field(
        default_factory=_default_onepassword_vault,
        description="1Password vault name (default: 'Private')",
    )

    @field_validator("target_directory", mode="before")
    @classmethod
    def ensure_path(cls, v):
        """Ensure target_directory is a Path object."""
        return Path(v) if not isinstance(v, Path) else v
