"""Configuration management command for Google Workspace Tools."""

from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from ...settings import CONFIG_DIR, CONFIG_FILE, DEFAULT_CONFIG_TOML, Settings

console = Console()

config_app = typer.Typer(
    help="Manage gwt configuration - show, init, or locate config file",
    rich_markup_mode="rich",
)


@config_app.command()
def show() -> None:
    """Show active settings and their sources.

    Displays all current settings values and where each value comes from
    (default, config file, or environment variable).

    Examples:
        gwt config show
    """
    import os
    import tomllib

    # Load TOML values (if config exists)
    toml_values: dict[str, object] = {}
    if CONFIG_FILE.is_file():
        with open(CONFIG_FILE, "rb") as f:
            try:
                toml_data = tomllib.load(f)
            except tomllib.TOMLDecodeError as e:
                console.print(f"[red]Failed to parse config file: {CONFIG_FILE}[/red]")
                console.print(f"[dim]{e}[/dim]")
                raise typer.Exit(1) from None
        from ...settings import _TOML_FIELD_MAP

        for (section, key), field_name in _TOML_FIELD_MAP.items():
            if section in toml_data and key in toml_data[section]:
                toml_values[field_name] = toml_data[section][key]

    # Get current settings
    s = Settings()

    table = Table(title="Active Settings")
    table.add_column("Setting", style="cyan")
    table.add_column("Value", style="green")
    table.add_column("Source", style="dim")

    fields = [
        ("storage_backend", s.storage_backend),
        ("use_keyring", str(s.use_keyring)),
        ("onepassword_vault", s.onepassword_vault),
        ("keyring_service_name", s.keyring_service_name),
        ("credentials_path", str(s.credentials_path)),
        ("token_path", str(s.token_path)),
        ("target_directory", str(s.target_directory)),
        ("export_format", s.export_format),
        ("log_level", s.log_level),
        ("log_format", s.log_format),
    ]

    for field_name, value in fields:
        env_key = f"GWT_{field_name.upper()}"
        if os.environ.get(env_key):
            source = f"env ({env_key})"
        elif field_name in toml_values:
            source = "config.toml"
        else:
            source = "default"

        display_value = str(value) if value is not None else "[dim]not set[/dim]"
        table.add_row(field_name, display_value, source)

    console.print(table)
    console.print(f"\n[dim]Config file: {CONFIG_FILE}[/dim]")
    if not CONFIG_FILE.is_file():
        console.print("[dim]  (not found — run 'gwt config init' to create)[/dim]")


@config_app.command()
def init(
    force: Annotated[
        bool,
        typer.Option("--force", "-f", help="Overwrite existing config file"),
    ] = False,
) -> None:
    """Create a default config file at ~/.config/gwt/config.toml.

    Creates the config directory and a commented-out template config file.
    Use --force to overwrite an existing config file.

    Examples:
        gwt config init
        gwt config init --force
    """
    if CONFIG_FILE.exists() and not force:
        console.print(f"[yellow]Config file already exists: {CONFIG_FILE}[/yellow]")
        console.print("[dim]Use --force to overwrite[/dim]")
        raise typer.Exit(1)

    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(DEFAULT_CONFIG_TOML, encoding="utf-8")
    console.print(f"[green]Created config file: {CONFIG_FILE}[/green]")
    console.print("[dim]Edit it to customize your settings[/dim]")


@config_app.command()
def path() -> None:
    """Print the config file path.

    Examples:
        gwt config path
        vim $(gwt config path)
    """
    console.print(str(CONFIG_FILE))
