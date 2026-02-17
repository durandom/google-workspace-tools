"""Settings management for Google Workspace Tools."""

import tomllib
from pathlib import Path
from typing import Any

from pydantic import Field
from pydantic_settings import BaseSettings, PydanticBaseSettingsSource, SettingsConfigDict

# Config file location
CONFIG_DIR = Path.home() / ".config" / "gwt"
CONFIG_FILE = CONFIG_DIR / "config.toml"

# Mapping from nested TOML sections to flat pydantic field names
_TOML_FIELD_MAP: dict[tuple[str, str], str] = {
    ("storage", "backend"): "storage_backend",
    ("storage", "use_keyring"): "use_keyring",
    ("storage", "keyring_service_name"): "keyring_service_name",
    ("storage", "vault"): "onepassword_vault",
    ("oauth", "credentials_path"): "credentials_path",
    ("oauth", "token_path"): "token_path",
    ("export", "target_directory"): "target_directory",
    ("export", "format"): "export_format",
    ("logging", "level"): "log_level",
    ("logging", "format"): "log_format",
}


class TomlConfigSettingsSource(PydanticBaseSettingsSource):
    """Load settings from a TOML config file."""

    def __init__(self, settings_cls: type[BaseSettings], toml_file: Path | None = None):
        super().__init__(settings_cls)
        self.toml_file = toml_file if toml_file is not None else CONFIG_FILE
        self._toml_data: dict[str, Any] = {}
        self._flat_data: dict[str, Any] = {}
        if self.toml_file.is_file():
            with open(self.toml_file, "rb") as f:
                try:
                    self._toml_data = tomllib.load(f)
                except tomllib.TOMLDecodeError as e:
                    raise ValueError(
                        f"Invalid TOML syntax in config file {self.toml_file}: {e}"
                    ) from e
            # Flatten nested TOML into pydantic field names
            for (section, key), field_name in _TOML_FIELD_MAP.items():
                if section in self._toml_data and key in self._toml_data[section]:
                    self._flat_data[field_name] = self._toml_data[section][key]

    def get_field_value(self, field: Any, field_name: str) -> tuple[Any, str, bool]:
        value = self._flat_data.get(field_name)
        return value, field_name, value is not None

    def __call__(self) -> dict[str, Any]:
        return {k: v for k, v in self._flat_data.items() if v is not None}


class Settings(BaseSettings):
    """Application settings with environment variable support.

    Settings instance priority (highest first):
    1. Environment variables (GWT_ prefix)
    2. .env file (in current directory)
    3. Config file (~/.config/gwt/config.toml)
    4. Default values

    Note: CLI commands may explicitly override these settings when values are
    passed as arguments (for example, to GoogleDriveExporterConfig()).

    Environment variables are prefixed with GWT_ and use __ for nested values.
    Example: GWT_STORAGE_BACKEND=keyring
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
        default="1password",
        description="Storage backend: '1password', 'keyring', 'file', or 'auto'",
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

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        """Customize settings source priority.

        Order (highest priority first):
        1. init_settings - explicit constructor args
        2. env_settings - GWT_* environment variables
        3. dotenv_settings - .env file
        4. toml_settings - ~/.config/gwt/config.toml
        5. file_secret_settings - secrets files
        """
        return (
            init_settings,
            env_settings,
            dotenv_settings,
            TomlConfigSettingsSource(settings_cls),
            file_secret_settings,
        )


# Default TOML config template (used by `gwt config init`)
DEFAULT_CONFIG_TOML = """\
# Google Workspace Tools configuration
# See: gwt config show

[storage]
# backend = "1password"        # 1password, keyring, file, auto
# vault = "Private"            # 1Password vault name
# keyring_service_name = "google-workspace-tools"

[oauth]
# credentials_path = ".client_secret.googleusercontent.com.json"
# token_path = "tmp/token_drive.json"

[export]
# target_directory = "exports"
# format = "md"                # md, pdf, docx, html, etc.

[logging]
# level = "WARNING"            # DEBUG, INFO, WARNING, ERROR
# format = "pretty"            # pretty, json
"""


# Global settings instance
settings = Settings()
