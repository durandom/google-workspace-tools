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


def credentials(
    action: Annotated[
        str,
        typer.Argument(help="Action: login, logout, status, import, list, migrate"),
    ],
    account: Annotated[
        str | None,
        typer.Option("--account", "-a", help="Account email (for logout)"),
    ] = None,
    use_keyring: Annotated[
        bool,
        typer.Option("--keyring/--no-keyring", help="Use keyring storage"),
    ] = True,
    token_path: Annotated[
        Path,
        typer.Option("--token", "-t", help="Path to token file (for file storage)"),
    ] = Path("tmp/token_drive.json"),
    credentials_file: Annotated[
        Path,
        typer.Option("--credentials", "-c", help="Path to client credentials file"),
    ] = Path(".client_secret.googleusercontent.com.json"),
) -> None:
    """Manage Google OAuth credentials.

    Actions:
        login   - Authenticate with Google (opens browser)
        logout  - Remove stored credentials
        status  - Show current authentication status
        import  - Import client credentials file into keyring
        list    - List all stored accounts
        migrate - Migrate file tokens to keyring

    Examples:
        gwt credentials login
        gwt credentials status
        gwt credentials import -c .client_secret.googleusercontent.com.json
        gwt credentials logout -a user@example.com
    """

    if action == "login":
        _handle_login(credentials_file, token_path, use_keyring)

    elif action == "logout":
        _handle_logout(account, use_keyring, token_path)

    elif action == "list":
        _handle_list(use_keyring, token_path)

    elif action == "migrate":
        _handle_migrate(token_path)

    elif action == "import":
        _handle_import(credentials_file)

    elif action == "status":
        _handle_status(credentials_file, token_path, use_keyring)

    else:
        console.print(f"[red]Unknown action: {action}[/red]")
        console.print("[dim]Valid actions: login, logout, status, import, list, migrate[/dim]")
        raise typer.Exit(1)


def _handle_login(credentials_file: Path, token_path: Path, use_keyring: bool) -> None:
    """Handle the login action."""
    config = GoogleDriveExporterConfig(
        credentials_path=credentials_file,
        token_path=token_path,
        use_keyring=use_keyring,
    )

    storage_type = "keyring" if use_keyring else "file"
    console.print("[bold]Starting Google OAuth authentication...[/bold]")
    console.print(f"[dim]Storage: {storage_type}[/dim]")
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
            if use_keyring:
                console.print("  Storage: [blue]keyring[/blue]")
            else:
                console.print(f"  Storage: [blue]file ({token_path})[/blue]")
        else:
            console.print("[green]Authentication successful![/green]")

    except FileNotFoundError as e:
        console.print(f"[red]Error: {e}[/red]")
        console.print("\n[dim]To authenticate, either:[/dim]")
        console.print(f"  1. Place credentials file at: [cyan]{credentials_file}[/cyan]")
        console.print("  2. Import to keyring: [cyan]gwt credentials import -c <file>[/cyan]")
        raise typer.Exit(1) from e
    except Exception as e:
        console.print(f"[red]Authentication failed: {e}[/red]")
        raise typer.Exit(1) from e


def _handle_logout(account: str | None, use_keyring: bool, token_path: Path) -> None:
    """Handle the logout action."""
    from ...core.storage import get_credential_storage

    storage = get_credential_storage(
        use_keyring=use_keyring,
        fallback_to_file=True,
        token_path=token_path,
    )

    if storage.delete(account):
        console.print(f"[green]Logged out {account or 'default account'}[/green]")
    else:
        console.print(f"[yellow]No credentials found for {account or 'default'}[/yellow]")


def _handle_list(use_keyring: bool, token_path: Path) -> None:
    """Handle the list action."""
    from ...core.storage import FileCredentialStorage, KeyringCredentialStorage

    table = Table(title="Stored Accounts")
    table.add_column("Account", style="cyan")
    table.add_column("Storage", style="green")

    found_any = False

    # Check file storage
    file_storage = FileCredentialStorage(token_path)
    if file_storage.is_available():
        file_accounts = file_storage.list_accounts()
        for acc in file_accounts:
            table.add_row(acc, "file")
            found_any = True

    # Check keyring storage if requested
    if use_keyring:
        try:
            keyring_storage = KeyringCredentialStorage()
            if keyring_storage.is_available():
                keyring_accounts = keyring_storage.list_accounts()
                for acc in keyring_accounts:
                    table.add_row(acc, "keyring")
                    found_any = True
        except ImportError:
            console.print("[dim]Keyring not installed (pip install keyring)[/dim]")
        except Exception as e:
            console.print(f"[dim]Keyring unavailable: {e}[/dim]")

    if found_any:
        console.print(table)
    else:
        console.print("[yellow]No stored accounts[/yellow]")


def _handle_migrate(token_path: Path) -> None:
    """Handle the migrate action."""
    from ...core.storage import FileCredentialStorage, KeyringCredentialStorage

    file_storage = FileCredentialStorage(token_path)
    stored = file_storage.load()

    if not stored:
        console.print("[yellow]No file-based credentials to migrate[/yellow]")
        raise typer.Exit(0)

    try:
        keyring_storage = KeyringCredentialStorage()
        if not keyring_storage.is_available():
            console.print("[red]Keyring is not available on this system[/red]")
            raise typer.Exit(1)

        if keyring_storage.save(stored):
            console.print("[green]Successfully migrated credentials to keyring[/green]")

            # Ask to remove file
            if typer.confirm("Remove file-based token?"):
                file_storage.delete()
                console.print("[dim]Removed old token file[/dim]")
        else:
            console.print("[red]Failed to save to keyring[/red]")
            raise typer.Exit(1)

    except ImportError as e:
        console.print("[red]Keyring not installed. Install with: pip install keyring[/red]")
        raise typer.Exit(1) from e
    except Exception as e:
        console.print(f"[red]Migration failed: {e}[/red]")
        raise typer.Exit(1) from e


def _handle_import(credentials_file: Path) -> None:
    """Handle the import action."""
    from ...core.storage import KeyringCredentialStorage

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

        keyring_storage = KeyringCredentialStorage()
        if not keyring_storage.is_available():
            console.print("[red]Keyring is not available on this system[/red]")
            raise typer.Exit(1)

        if keyring_storage.save_client_credentials(client_creds):
            cred_type = "web" if "web" in client_creds else "installed"
            console.print(f"[green]Successfully imported {cred_type} credentials to keyring[/green]")
            console.print("[dim]You can now delete the .client_secret file if desired[/dim]")
        else:
            console.print("[red]Failed to save client credentials to keyring[/red]")
            raise typer.Exit(1)

    except json.JSONDecodeError as e:
        console.print(f"[red]Invalid JSON in credentials file: {e}[/red]")
        raise typer.Exit(1) from e
    except ImportError as e:
        console.print("[red]Keyring not installed. Install with: pip install keyring[/red]")
        raise typer.Exit(1) from e
    except Exception as e:
        console.print(f"[red]Import failed: {e}[/red]")
        raise typer.Exit(1) from e


def _handle_status(credentials_file: Path, token_path: Path, use_keyring: bool) -> None:
    """Handle the status action."""
    from ...core.storage import FileCredentialStorage, KeyringCredentialStorage

    console.print("[bold]Credential Status[/bold]\n")

    # Try to get current user info
    try:
        config = GoogleDriveExporterConfig(
            credentials_path=credentials_file,
            token_path=token_path,
            use_keyring=use_keyring,
        )
        exporter = GoogleDriveExporter(config)
        user_info = exporter.get_authenticated_user_info()

        if user_info:
            console.print("  Logged in: [green]Yes[/green]")
            console.print(f"  User: [cyan]{user_info.get('displayName', 'Unknown')}[/cyan]")
            console.print(f"  Email: [cyan]{user_info.get('emailAddress', 'Unknown')}[/cyan]")
        else:
            console.print("  Logged in: [yellow]Unknown[/yellow]")
    except Exception:
        console.print("  Logged in: [red]No[/red]")

    console.print()

    # Show keyring status if available
    if use_keyring:
        try:
            keyring_storage = KeyringCredentialStorage()
            if keyring_storage.is_available():
                console.print("  Keyring: [green]available[/green]")

                # Check client credentials
                if keyring_storage.has_client_credentials():
                    client_creds = keyring_storage.load_client_credentials()
                    if client_creds:
                        cred_type = "web" if "web" in client_creds else "installed"
                        console.print(f"  Client Credentials: [green]stored[/green] ({cred_type})")
                else:
                    console.print("  Client Credentials: [yellow]not in keyring[/yellow]")

                # Check OAuth tokens
                accounts = keyring_storage.list_accounts()
                if accounts:
                    console.print(f"  OAuth Tokens: [green]{len(accounts)} account(s)[/green]")
                else:
                    console.print("  OAuth Tokens: [yellow]none in keyring[/yellow]")
            else:
                console.print("  Keyring: [yellow]not available[/yellow]")
        except ImportError:
            console.print("  Keyring: [dim]not installed[/dim]")
        except Exception as e:
            console.print(f"  Keyring: [red]error ({e})[/red]")

    # Check file storage
    if token_path.exists():
        console.print(f"  Token File: [green]exists[/green] ({token_path})")
    else:
        console.print("  Token File: [dim]not found[/dim]")

    if credentials_file.exists():
        console.print(f"  Credentials File: [green]exists[/green] ({credentials_file})")
    else:
        console.print("  Credentials File: [dim]not found[/dim]")
