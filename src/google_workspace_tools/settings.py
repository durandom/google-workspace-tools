"""Settings management for Google Workspace Tools."""

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with environment variable support.

    Environment variables are prefixed with GWT_ and use __ for nested values.
    Example: GWT_CREDENTIALS_PATH=/path/to/creds.json
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        env_prefix="GWT_",
    )

    # Google OAuth settings
    credentials_path: Path = Field(
        default=Path(".client_secret.googleusercontent.com.json"),
        description="Path to Google OAuth credentials file",
    )
    token_path: Path = Field(
        default=Path("tmp/token_drive.json"),
        description="Path to cached OAuth token",
    )

    # Credential storage settings
    storage_backend: str = Field(
        default="auto",
        description="Storage backend: 'auto', '1password', 'keyring', or 'file'",
    )
    use_keyring: bool = Field(
        default=True,
        description="Use keyring for credential storage if available (legacy, use storage_backend)",
    )
    keyring_service_name: str = Field(
        default="google-workspace-tools",
        description="Service name used for keyring/1Password storage",
    )
    onepassword_vault: str | None = Field(
        default=None,
        description="1Password vault name (default: 'Private')",
    )

    # Export settings
    target_directory: Path = Field(
        default=Path("exports"),
        description="Default export directory",
    )
    export_format: str = Field(
        default="md",
        description="Default export format (md, pdf, docx, html, etc.)",
    )

    # Logging settings
    log_level: str = Field(
        default="WARNING",
        description="Logging level (DEBUG, INFO, WARNING, ERROR)",
    )
    log_format: str = Field(
        default="pretty",
        description="Log format: 'pretty' for colored output, 'json' for structured",
    )


# Global settings instance
settings = Settings()
