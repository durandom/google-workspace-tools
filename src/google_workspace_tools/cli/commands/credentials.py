"""Credentials management command for Google Workspace Tools."""

import json
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from ...core.config import GoogleDriveExporterConfig
from ...core.exporter import GoogleDriveExporter

console = Console()


def _print_next_steps_console(hints: list[tuple[str, str]]) -> None:
    """Print next-step hints using console (credentials command uses console directly).

    Args:
        hints: List of (command, description) tuples
    """
    if not hints:
        return

    console.print("\n[dim]Next steps:[/dim]")
    for cmd, desc in hints:
        console.print(f"[dim]  {cmd:<40} {desc}[/dim]")


def credentials(
    action: Annotated[
        str,
        typer.Argument(help="Action: login, logout, status, import, list, migrate"),
    ],
    account: Annotated[
        str | None,
        typer.Option("--account", "-a", help="Account email (for logout)"),
    ] = None,
    storage: Annotated[
        str,
        typer.Option("--storage", "-s", help="Storage backend: 1password, keyring, file, auto"),
    ] = "1password",
    use_keyring: Annotated[
        bool,
        typer.Option("--keyring/--no-keyring", help="Use keyring storage (legacy, use --storage)"),
    ] = True,
    token_path: Annotated[
        Path,
        typer.Option("--token", "-t", help="Path to token file (for file storage)"),
    ] = Path("tmp/token_drive.json"),
    credentials_file: Annotated[
        Path,
        typer.Option("--credentials", "-c", help="Path to client credentials file"),
    ] = Path(".client_secret.googleusercontent.com.json"),
    vault: Annotated[
        str | None,
        typer.Option("--vault", "-V", help="1Password vault name (default: Private)"),
    ] = None,
) -> None:
    """Manage Google OAuth credentials.

    Actions:
        login   - Authenticate with Google (opens browser)
        logout  - Remove stored credentials
        status  - Show current authentication status
        import  - Import client credentials file into secure storage
        list    - List all stored accounts
        migrate - Migrate file tokens to keyring/1Password

    Storage backends (--storage):
        auto      - Try 1Password → keyring → file (default)
        1password - Use 1Password CLI (Touch ID enabled if app integrated)
        keyring   - Use system keyring (macOS Keychain)
        file      - Use file-based storage

    Examples:
        gwt credentials login
        gwt credentials login --storage=1password
        gwt credentials status
        gwt credentials import -c .client_secret.googleusercontent.com.json
        gwt credentials logout -a user@example.com
    """

    if action == "login":
        _handle_login(credentials_file, token_path, storage, vault)

    elif action == "logout":
        _handle_logout(account, storage, token_path, vault)

    elif action == "list":
        _handle_list(storage, token_path, vault)

    elif action == "migrate":
        _handle_migrate(token_path, storage, vault)

    elif action == "import":
        _handle_import(credentials_file, storage, vault)

    elif action == "status":
        _handle_status(credentials_file, token_path, storage, vault)

    else:
        console.print(f"[red]Unknown action: {action}[/red]")
        console.print("[dim]Valid actions: login, logout, status, import, list, migrate[/dim]")
        raise typer.Exit(1)


def _handle_login(credentials_file: Path, token_path: Path, storage_backend: str, vault: str | None) -> None:
    """Handle the login action."""
    config = GoogleDriveExporterConfig(
        credentials_path=credentials_file,
        token_path=token_path,
        storage_backend=storage_backend,  # type: ignore[arg-type]
        onepassword_vault=vault,
    )

    console.print("[bold]Starting Google OAuth authentication...[/bold]")
    console.print(f"[dim]Storage backend: {storage_backend}[/dim]")
    console.print("[dim]A browser window will open for authentication[/dim]\n")

    try:
        exporter = GoogleDriveExporter(config)
        # Trigger authentication by accessing the service
        _ = exporter.service

        # Get user info to confirm
        user_info = exporter.get_authenticated_user_info()
        if user_info:
            console.print("[green]Authentication successful![/green]")
            console.print(f"  User: [cyan]{user_info.get('displayName', 'Unknown')}[/cyan]")
            console.print(f"  Email: [cyan]{user_info.get('emailAddress', 'Unknown')}[/cyan]")
            console.print(f"  Storage: [blue]{storage_backend}[/blue]")
        else:
            console.print("[green]Authentication successful![/green]")

        # Print next-step hints
        _print_next_steps_console(
            [
                ("gwt download <URL>", "Download a Google Drive document"),
                ("gwt mail -q 'from:...'", "Export Gmail messages"),
                ("gwt calendar", "List your calendars"),
            ]
        )

    except FileNotFoundError as e:
        console.print(f"[red]Error: {e}[/red]")
        console.print("\n[dim]To authenticate, either:[/dim]")
        console.print(f"  1. Place credentials file at: [cyan]{credentials_file}[/cyan]")
        console.print("  2. Import to storage: [cyan]gwt credentials import -c <file>[/cyan]")
        raise typer.Exit(1) from e
    except Exception as e:
        console.print(f"[red]Authentication failed: {e}[/red]")
        raise typer.Exit(1) from e


def _handle_logout(account: str | None, storage_backend: str, token_path: Path, vault: str | None) -> None:
    """Handle the logout action."""
    from ...core.storage import get_credential_storage

    storage = get_credential_storage(
        fallback_to_file=True,
        token_path=token_path,
        storage_backend=storage_backend,
        onepassword_vault=vault,
    )

    if storage.delete(account):
        console.print(f"[green]Logged out {account or 'default account'}[/green]")
    else:
        console.print(f"[yellow]No credentials found for {account or 'default'}[/yellow]")


def _handle_list(storage_backend: str, token_path: Path, vault: str | None) -> None:
    """Handle the list action."""
    from ...core.storage import (
        FileCredentialStorage,
        KeyringCredentialStorage,
        OnePasswordCredentialStorage,
    )

    table = Table(title="Stored Accounts")
    table.add_column("Account", style="cyan")
    table.add_column("Storage", style="green")

    found_any = False

    # Check 1Password storage
    if storage_backend in ("auto", "1password"):
        try:
            op_storage = OnePasswordCredentialStorage(vault=vault)
            if op_storage.is_available():
                op_accounts = op_storage.list_accounts()
                for acc in op_accounts:
                    table.add_row(acc, "1password")
                    found_any = True
        except Exception as e:
            if storage_backend == "1password":
                console.print(f"[dim]1Password unavailable: {e}[/dim]")

    # Check keyring storage
    if storage_backend in ("auto", "keyring"):
        try:
            keyring_storage = KeyringCredentialStorage()
            if keyring_storage.is_available():
                keyring_accounts = keyring_storage.list_accounts()
                for acc in keyring_accounts:
                    table.add_row(acc, "keyring")
                    found_any = True
        except ImportError:
            if storage_backend == "keyring":
                console.print("[dim]Keyring not installed (pip install keyring)[/dim]")
        except Exception as e:
            if storage_backend == "keyring":
                console.print(f"[dim]Keyring unavailable: {e}[/dim]")

    # Check file storage
    if storage_backend in ("auto", "file"):
        file_storage = FileCredentialStorage(token_path)
        if file_storage.is_available():
            file_accounts = file_storage.list_accounts()
            for acc in file_accounts:
                table.add_row(acc, "file")
                found_any = True

    if found_any:
        console.print(table)
    else:
        console.print("[yellow]No stored accounts[/yellow]")


def _handle_migrate(token_path: Path, storage_backend: str, vault: str | None) -> None:
    """Handle the migrate action."""
    from ...core.storage import (
        CredentialStorage,
        FileCredentialStorage,
        KeyringCredentialStorage,
        OnePasswordCredentialStorage,
    )

    file_storage = FileCredentialStorage(token_path)
    stored = file_storage.load()

    if not stored:
        console.print("[yellow]No file-based credentials to migrate[/yellow]")
        raise typer.Exit(0)

    try:
        # Determine target storage
        target_storage: CredentialStorage | None = None
        target_name = ""

        if storage_backend in ("auto", "1password"):
            op_storage = OnePasswordCredentialStorage(vault=vault)
            if op_storage.is_available():
                target_storage = op_storage
                target_name = "1Password"

        if target_storage is None and storage_backend in ("auto", "keyring"):
            keyring_storage = KeyringCredentialStorage()
            if keyring_storage.is_available():
                target_storage = keyring_storage
                target_name = "keyring"

        if target_storage is None:
            console.print("[red]No secure storage backend available[/red]")
            console.print("[dim]Install 1Password CLI or keyring package[/dim]")
            raise typer.Exit(1)

        if target_storage.save(stored):
            console.print(f"[green]Successfully migrated credentials to {target_name}[/green]")

            # Ask to remove file
            if typer.confirm("Remove file-based token?"):
                file_storage.delete()
                console.print("[dim]Removed old token file[/dim]")
        else:
            console.print(f"[red]Failed to save to {target_name}[/red]")
            raise typer.Exit(1)

    except ImportError as e:
        console.print("[red]No secure storage available[/red]")
        raise typer.Exit(1) from e
    except Exception as e:
        console.print(f"[red]Migration failed: {e}[/red]")
        raise typer.Exit(1) from e


def _handle_import(credentials_file: Path, storage_backend: str, vault: str | None) -> None:
    """Handle the import action."""
    from ...core.storage import CredentialStorage, KeyringCredentialStorage, OnePasswordCredentialStorage

    if not credentials_file.exists():
        console.print(f"[red]Client credentials file not found: {credentials_file}[/red]")
        raise typer.Exit(1)

    try:
        # Read credentials file
        with open(credentials_file) as f:
            client_creds = json.load(f)

        # Validate it looks like a credentials file
        if "web" not in client_creds and "installed" not in client_creds:
            console.print("[red]Invalid credentials file format (missing 'web' or 'installed' key)[/red]")
            raise typer.Exit(1)

        # Determine target storage
        target_storage: CredentialStorage | None = None
        target_name = ""

        if storage_backend in ("auto", "1password"):
            op_storage = OnePasswordCredentialStorage(vault=vault)
            if op_storage.is_available():
                target_storage = op_storage
                target_name = "1Password"

        if target_storage is None and storage_backend in ("auto", "keyring"):
            try:
                keyring_storage = KeyringCredentialStorage()
                if keyring_storage.is_available():
                    target_storage = keyring_storage
                    target_name = "keyring"
            except ImportError:
                pass

        if target_storage is None:
            console.print("[red]No secure storage backend available[/red]")
            console.print("[dim]Install 1Password CLI or keyring package[/dim]")
            raise typer.Exit(1)

        assert target_storage is not None  # Type narrowing for mypy
        if target_storage.save_client_credentials(client_creds):
            cred_type = "web" if "web" in client_creds else "installed"
            console.print(f"[green]Successfully imported {cred_type} credentials to {target_name}[/green]")
            console.print("[dim]You can now delete the .client_secret file if desired[/dim]")
        else:
            console.print(f"[red]Failed to save client credentials to {target_name}[/red]")
            raise typer.Exit(1)

    except json.JSONDecodeError as e:
        console.print(f"[red]Invalid JSON in credentials file: {e}[/red]")
        raise typer.Exit(1) from e
    except Exception as e:
        console.print(f"[red]Import failed: {e}[/red]")
        raise typer.Exit(1) from e


def _handle_status(credentials_file: Path, token_path: Path, storage_backend: str, vault: str | None) -> None:
    """Handle the status action (read-only, no OAuth trigger)."""
    from ...core.storage import FileCredentialStorage, KeyringCredentialStorage, OnePasswordCredentialStorage

    console.print("[bold]Credential Status[/bold]\n")

    # Track if we found any stored credentials
    found_credentials = False
    logged_in_email: str | None = None

    # Show 1Password status
    if storage_backend in ("auto", "1password"):
        try:
            op_storage = OnePasswordCredentialStorage(vault=vault)
            if op_storage.is_available():
                console.print("  1Password: [green]available[/green] (Touch ID enabled)")

                # Check client credentials
                if op_storage.has_client_credentials():
                    client_creds = op_storage.load_client_credentials()
                    if client_creds:
                        cred_type = "web" if "web" in client_creds else "installed"
                        console.print(f"  1P Client Credentials: [green]stored[/green] ({cred_type})")
                else:
                    console.print("  1P Client Credentials: [yellow]not stored[/yellow]")

                # Check OAuth tokens
                accounts = op_storage.list_accounts()
                if accounts:
                    console.print(f"  1P OAuth Tokens: [green]{len(accounts)} account(s)[/green]")
                    for account in accounts:
                        console.print(f"    - [cyan]{account}[/cyan]")
                    if not logged_in_email:
                        logged_in_email = accounts[0]
                        found_credentials = True
                else:
                    console.print("  1P OAuth Tokens: [yellow]none stored[/yellow]")
            else:
                console.print("  1Password: [yellow]not available[/yellow]")
                console.print("    [dim]Install: brew install 1password-cli[/dim]")
                console.print("    [dim]Enable: 1Password app > Settings > Developer > Integrate with CLI[/dim]")
        except Exception as e:
            console.print(f"  1Password: [red]error ({e})[/red]")

    # Show keyring status
    if storage_backend in ("auto", "keyring"):
        try:
            keyring_storage = KeyringCredentialStorage()
            if keyring_storage.is_available():
                console.print("  Keyring: [green]available[/green]")

                # Check client credentials
                if keyring_storage.has_client_credentials():
                    client_creds = keyring_storage.load_client_credentials()
                    if client_creds:
                        cred_type = "web" if "web" in client_creds else "installed"
                        console.print(f"  Keyring Client Credentials: [green]stored[/green] ({cred_type})")
                else:
                    console.print("  Keyring Client Credentials: [yellow]not stored[/yellow]")

                # Check OAuth tokens
                accounts = keyring_storage.list_accounts()
                if accounts:
                    console.print(f"  Keyring OAuth Tokens: [green]{len(accounts)} account(s)[/green]")
                    for account in accounts:
                        console.print(f"    - [cyan]{account}[/cyan]")
                    if not logged_in_email:
                        logged_in_email = accounts[0]
                        found_credentials = True
                else:
                    console.print("  Keyring OAuth Tokens: [yellow]none stored[/yellow]")
            else:
                console.print("  Keyring: [yellow]not available[/yellow]")
        except ImportError:
            console.print("  Keyring: [dim]not installed[/dim]")
        except Exception as e:
            console.print(f"  Keyring: [red]error ({e})[/red]")

    # Check file storage
    if storage_backend in ("auto", "file"):
        if token_path.exists():
            console.print(f"  Token File: [green]exists[/green] ({token_path})")
            # Try to extract email from file token
            if not found_credentials:
                try:
                    file_storage = FileCredentialStorage(token_path, credentials_file)
                    stored = file_storage.load()
                    if stored and stored.email:
                        logged_in_email = stored.email
                        found_credentials = True
                except Exception:
                    pass
        else:
            console.print("  Token File: [dim]not found[/dim]")

    if credentials_file.exists():
        console.print(f"  Credentials File: [green]exists[/green] ({credentials_file})")
    else:
        console.print("  Credentials File: [dim]not found[/dim]")

    console.print()

    # Summary
    if found_credentials:
        console.print(f"  Logged in: [green]Yes[/green] as [cyan]{logged_in_email}[/cyan]")
        _print_next_steps_console(
            [
                ("gwt download <URL>", "Download a Google Drive document"),
                ("gwt mail -q 'from:...'", "Export Gmail messages"),
                ("gwt calendar", "List your calendars"),
            ]
        )
    else:
        console.print("  Logged in: [yellow]No[/yellow]")
        _print_next_steps_console(
            [
                ("gwt credentials login", "Authenticate with Google"),
            ]
        )
