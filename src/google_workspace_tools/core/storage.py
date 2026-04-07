"""Credential storage backends for OAuth tokens and client secrets."""

from __future__ import annotations

import json
import shutil
import subprocess
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from loguru import logger


@dataclass
class StoredCredentials:
    """Container for stored credential data."""

    token_data: dict[str, Any] = field(default_factory=dict)
    client_id: str | None = None
    client_secret: str | None = None
    email: str | None = None


class CredentialStorage(ABC):
    """Abstract base class for credential storage backends."""

    @abstractmethod
    def load(self, account_email: str | None = None) -> StoredCredentials | None:
        """Load credentials for the given account or default account."""

    @abstractmethod
    def save(self, credentials: StoredCredentials) -> bool:
        """Save credentials. Returns True on success."""

    @abstractmethod
    def delete(self, account_email: str | None = None) -> bool:
        """Delete credentials for the given account."""

    @abstractmethod
    def list_accounts(self) -> list[str]:
        """List all stored account emails."""

    @abstractmethod
    def is_available(self) -> bool:
        """Check if this storage backend is available."""

    @abstractmethod
    def save_client_credentials(self, client_credentials: dict[str, Any]) -> bool:
        """Save OAuth client credentials (from .client_secret file).

        Args:
            client_credentials: The full client credentials dict (with 'web' or 'installed' key)

        Returns:
            True on success, False on failure
        """


class FileCredentialStorage(CredentialStorage):
    """File-based credential storage."""

    def __init__(self, token_path: Path, credentials_path: Path | None = None):
        self.token_path = token_path
        self.credentials_path = credentials_path

    def load(self, account_email: str | None = None) -> StoredCredentials | None:
        """Load credentials from file."""
        if not self.token_path.exists():
            return None

        try:
            with open(self.token_path) as f:
                token_data = json.load(f)

            return StoredCredentials(
                token_data=token_data,
                client_id=token_data.get("client_id"),
                client_secret=token_data.get("client_secret"),
                email=token_data.get("account"),
            )
        except (json.JSONDecodeError, OSError) as e:
            logger.warning(f"Failed to load token file: {e}")
            return None

    def save(self, credentials: StoredCredentials) -> bool:
        """Save credentials to file."""
        try:
            self.token_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.token_path, "w") as f:
                json.dump(credentials.token_data, f, indent=2)
            return True
        except OSError as e:
            logger.error(f"Failed to save token file: {e}")
            return False

    def delete(self, account_email: str | None = None) -> bool:
        """Delete the token file."""
        if self.token_path.exists():
            try:
                self.token_path.unlink()
                return True
            except OSError as e:
                logger.error(f"Failed to delete token file: {e}")
                return False
        return False

    def list_accounts(self) -> list[str]:
        """File storage doesn't support multi-account."""
        return ["default"] if self.token_path.exists() else []

    def is_available(self) -> bool:
        """File storage is always available."""
        return True

    def save_client_credentials(self, client_credentials: dict[str, Any]) -> bool:
        """Save client credentials to the credentials file path.

        If no credentials_path was provided, defaults to ~/.config/gwt/client_secret.json.
        """
        target = self.credentials_path or (Path.home() / ".config" / "gwt" / "client_secret.json")
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            with open(target, "w") as f:
                json.dump(client_credentials, f, indent=2)
            logger.debug(f"Client credentials saved to {target}")
            return True
        except OSError as e:
            logger.error(f"Failed to save client credentials to {target}: {e}")
            return False


class KeyringCredentialStorage(CredentialStorage):
    """Keyring-based secure credential storage."""

    DEFAULT_SERVICE_NAME = "google-workspace-tools"
    DEFAULT_ACCOUNT = "_default"
    ACCOUNT_LIST_KEY = "_accounts"
    CLIENT_CREDENTIALS_KEY = "_client_credentials"

    def __init__(self, service_name: str = DEFAULT_SERVICE_NAME):
        self.service_name = service_name
        self._keyring = None

    @property
    def keyring(self):
        """Lazy import keyring module."""
        if self._keyring is None:
            import keyring

            self._keyring = keyring
        return self._keyring

    def _get_key(self, account_email: str | None) -> str:
        """Get the keyring key for an account."""
        return account_email or self.DEFAULT_ACCOUNT

    def load(self, account_email: str | None = None) -> StoredCredentials | None:
        """Load credentials from keyring."""
        key = self._get_key(account_email)

        try:
            data = self.keyring.get_password(self.service_name, key)

            # If no specific account and _default not found, try first account from list
            if not data and not account_email:
                accounts = self.list_accounts()
                if accounts:
                    data = self.keyring.get_password(self.service_name, accounts[0])
                    logger.debug(f"Loaded credentials for {accounts[0]}")

            if not data:
                return None

            parsed = json.loads(data)
            return StoredCredentials(
                token_data=parsed.get("token", {}),
                client_id=parsed.get("client_id"),
                client_secret=parsed.get("client_secret"),
                email=parsed.get("email"),
            )
        except (json.JSONDecodeError, Exception) as e:
            logger.warning(f"Failed to load from keyring: {e}")
            return None

    def save(self, credentials: StoredCredentials) -> bool:
        """Save credentials to keyring."""
        email = credentials.email
        key = self._get_key(email)

        data = {
            "token": credentials.token_data,
            "client_id": credentials.client_id,
            "client_secret": credentials.client_secret,
            "email": email,
        }

        try:
            self.keyring.set_password(self.service_name, key, json.dumps(data))

            # Update account list if we have an email
            if email:
                self._add_to_account_list(email)

            return True
        except Exception as e:
            logger.error(f"Failed to save to keyring: {e}")
            return False

    def delete(self, account_email: str | None = None) -> bool:
        """Delete credentials from keyring."""
        key = self._get_key(account_email)

        try:
            self.keyring.delete_password(self.service_name, key)
            if account_email:
                self._remove_from_account_list(account_email)
            return True
        except Exception as e:
            logger.debug(f"Failed to delete from keyring: {e}")
            return False

    def list_accounts(self) -> list[str]:
        """List all stored account emails."""
        try:
            data = self.keyring.get_password(self.service_name, self.ACCOUNT_LIST_KEY)
            if not data:
                return []
            result = json.loads(data)
            return list(result) if isinstance(result, list) else []
        except Exception:
            return []

    def is_available(self) -> bool:
        """Check if keyring is functional."""
        try:
            # Test that keyring is actually functional
            self.keyring.get_keyring()
            return True
        except Exception:
            return False

    def _add_to_account_list(self, email: str) -> None:
        """Add email to the account list."""
        if not email:
            return
        accounts = set(self.list_accounts())
        accounts.add(email)
        try:
            self.keyring.set_password(self.service_name, self.ACCOUNT_LIST_KEY, json.dumps(list(accounts)))
        except Exception as e:
            logger.debug(f"Failed to update account list: {e}")

    def _remove_from_account_list(self, email: str) -> None:
        """Remove email from the account list."""
        if not email:
            return
        accounts = set(self.list_accounts())
        accounts.discard(email)
        try:
            self.keyring.set_password(self.service_name, self.ACCOUNT_LIST_KEY, json.dumps(list(accounts)))
        except Exception as e:
            logger.debug(f"Failed to update account list: {e}")

    def save_client_credentials(self, client_credentials: dict[str, Any]) -> bool:
        """Save OAuth client credentials (from .client_secret file) to keyring.

        Args:
            client_credentials: The full client credentials dict (with 'web' or 'installed' key)

        Returns:
            True if successful, False otherwise
        """
        try:
            self.keyring.set_password(
                self.service_name,
                self.CLIENT_CREDENTIALS_KEY,
                json.dumps(client_credentials),
            )
            logger.debug("Client credentials saved to keyring")
            return True
        except Exception as e:
            logger.error(f"Failed to save client credentials to keyring: {e}")
            return False

    def load_client_credentials(self) -> dict[str, Any] | None:
        """Load OAuth client credentials from keyring.

        Returns:
            Client credentials dict or None if not found
        """
        try:
            data = self.keyring.get_password(self.service_name, self.CLIENT_CREDENTIALS_KEY)
            if not data:
                return None
            result = json.loads(data)
            return dict(result) if isinstance(result, dict) else None
        except Exception as e:
            logger.warning(f"Failed to load client credentials from keyring: {e}")
            return None

    def delete_client_credentials(self) -> bool:
        """Delete client credentials from keyring.

        Returns:
            True if successful, False otherwise
        """
        try:
            self.keyring.delete_password(self.service_name, self.CLIENT_CREDENTIALS_KEY)
            logger.debug("Client credentials deleted from keyring")
            return True
        except Exception as e:
            logger.debug(f"Failed to delete client credentials from keyring: {e}")
            return False

    def has_client_credentials(self) -> bool:
        """Check if client credentials are stored in keyring.

        Returns:
            True if client credentials exist, False otherwise
        """
        try:
            data = self.keyring.get_password(self.service_name, self.CLIENT_CREDENTIALS_KEY)
            return data is not None
        except Exception:
            return False


class OnePasswordCredentialStorage(CredentialStorage):
    """1Password CLI-based credential storage with Touch ID support.

    Uses the 1Password CLI (`op`) to store and retrieve credentials.
    When integrated with the 1Password desktop app, this enables
    Touch ID authentication for credential access.

    Prerequisites:
        1. Install 1Password CLI: brew install 1password-cli
        2. In 1Password app: Settings > Developer > "Integrate with 1Password CLI"
        3. In 1Password app: Settings > Security > Enable Touch ID
    """

    DEFAULT_VAULT = "Private"
    # Item name prefixes (machine-readable, used for lookup)
    ITEM_PREFIX = "GWT"
    # Human-readable titles
    TITLE_PREFIX = "Google Workspace Tools"
    TAG = "google-workspace-tools"

    def __init__(
        self,
        service_name: str = "google-workspace-tools",
        vault: str | None = None,
    ):
        """Initialize 1Password storage.

        Args:
            service_name: Used for item categorization
            vault: 1Password vault name (defaults to "Private")
        """
        self.service_name = service_name
        self.vault = vault or self.DEFAULT_VAULT
        self._op_path: str | None = None

    @property
    def op_path(self) -> str | None:
        """Lazily find the op CLI path."""
        if self._op_path is None:
            self._op_path = shutil.which("op")
        return self._op_path

    def _token_item_name(self, account_email: str | None = None) -> str:
        """Generate 1Password item title for OAuth token."""
        if account_email:
            return f"{self.TITLE_PREFIX} - OAuth Token ({account_email})"
        return f"{self.TITLE_PREFIX} - OAuth Token (Default)"

    def _client_creds_item_name(self) -> str:
        """Item title for client credentials."""
        return f"{self.TITLE_PREFIX} - OAuth Client Credentials"

    def _accounts_list_item_name(self) -> str:
        """Item title for accounts list."""
        return f"{self.TITLE_PREFIX} - Account List"

    def _run_op(
        self,
        args: list[str],
        capture_output: bool = True,
        check: bool = False,
    ) -> subprocess.CompletedProcess[str]:
        """Run an op CLI command.

        Args:
            args: Arguments to pass to op
            capture_output: Whether to capture stdout/stderr
            check: Whether to raise on non-zero exit

        Returns:
            CompletedProcess result
        """
        if not self.op_path:
            raise RuntimeError("1Password CLI (op) not found")

        cmd = [self.op_path, *args, "--format=json"]
        logger.debug(f"Running: op {' '.join(args)}")

        return subprocess.run(
            cmd,
            capture_output=capture_output,
            text=True,
            check=check,
        )

    def _item_exists(self, item_name: str) -> bool:
        """Check if a 1Password item exists."""
        result = self._run_op(["item", "get", item_name, f"--vault={self.vault}"])
        return result.returncode == 0

    def _extract_credential_field(self, item_data: dict[str, Any]) -> str | None:
        """Extract credential value from 1Password item data.

        For API Credential items, the secret is in the 'credential' field.
        Falls back to 'notesPlain' for backward compatibility with Secure Notes.
        """
        for item_field in item_data.get("fields", []):
            # API Credential items use 'credential' field
            if item_field.get("id") == "credential":
                value = item_field.get("value")
                return str(value) if value is not None else None

        # Fallback to notesPlain for backward compatibility
        for item_field in item_data.get("fields", []):
            if item_field.get("id") == "notesPlain" or item_field.get("purpose") == "NOTES":
                value = item_field.get("value")
                return str(value) if value is not None else None

        notes_value = item_data.get("notesPlain")
        return str(notes_value) if notes_value is not None else None

    def load(self, account_email: str | None = None) -> StoredCredentials | None:
        """Load credentials from 1Password."""
        item_name = self._token_item_name(account_email)

        try:
            result = self._run_op(["item", "get", item_name, f"--vault={self.vault}"])

            if result.returncode != 0:
                # If no specific account, try first from accounts list
                if not account_email:
                    accounts = self.list_accounts()
                    if accounts:
                        return self.load(accounts[0])
                return None

            item_data = json.loads(result.stdout)

            # Extract credential from notesPlain field
            credential_json = self._extract_credential_field(item_data)

            if not credential_json:
                logger.warning(f"No credential data found in 1Password item: {item_name}")
                return None

            parsed = json.loads(credential_json)
            return StoredCredentials(
                token_data=parsed.get("token", {}),
                client_id=parsed.get("client_id"),
                client_secret=parsed.get("client_secret"),
                email=parsed.get("email"),
            )

        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse 1Password item: {e}")
            return None
        except Exception as e:
            logger.warning(f"Failed to load from 1Password: {e}")
            return None

    def save(self, credentials: StoredCredentials) -> bool:
        """Save credentials to 1Password."""
        email = credentials.email
        item_name = self._token_item_name(email)

        data = {
            "token": credentials.token_data,
            "client_id": credentials.client_id,
            "client_secret": credentials.client_secret,
            "email": email,
        }
        credential_json = json.dumps(data)

        try:
            if self._item_exists(item_name):
                # Update existing item
                result = self._run_op(
                    [
                        "item",
                        "edit",
                        item_name,
                        f"--vault={self.vault}",
                        f"credential={credential_json}",
                    ]
                )
            else:
                # Create new item as API Credential with proper fields
                result = self._run_op(
                    [
                        "item",
                        "create",
                        "--category=API Credential",
                        f"--title={item_name}",
                        f"--vault={self.vault}",
                        f"--tags={self.TAG}",
                        f"username={email or 'default'}",
                        "hostname=googleapis.com",
                        f"credential={credential_json}",
                        "notesPlain=OAuth token for Google Workspace Tools CLI",
                    ]
                )

            if result.returncode != 0:
                logger.error(f"Failed to save to 1Password: {result.stderr}")
                return False

            # Update accounts list
            if email:
                self._add_to_account_list(email)

            logger.debug(f"Saved credentials to 1Password: {item_name}")
            return True

        except Exception as e:
            logger.error(f"Failed to save to 1Password: {e}")
            return False

    def delete(self, account_email: str | None = None) -> bool:
        """Delete credentials from 1Password."""
        item_name = self._token_item_name(account_email)

        try:
            result = self._run_op(
                [
                    "item",
                    "delete",
                    item_name,
                    f"--vault={self.vault}",
                ]
            )

            if result.returncode == 0:
                if account_email:
                    self._remove_from_account_list(account_email)
                return True

            return False
        except Exception as e:
            logger.debug(f"Failed to delete from 1Password: {e}")
            return False

    def list_accounts(self) -> list[str]:
        """List all stored account emails."""
        item_name = self._accounts_list_item_name()

        try:
            result = self._run_op(["item", "get", item_name, f"--vault={self.vault}"])

            if result.returncode != 0:
                return []

            item_data = json.loads(result.stdout)
            accounts_json = self._extract_credential_field(item_data) or "[]"
            accounts = json.loads(accounts_json)
            return list(accounts) if isinstance(accounts, list) else []

        except Exception:
            return []

    def is_available(self) -> bool:
        """Check if 1Password CLI is available and authenticated."""
        if not self.op_path:
            return False

        try:
            # Check if op is functional and we're signed in
            result = self._run_op(["account", "list"])
            return result.returncode == 0
        except Exception:
            return False

    def _add_to_account_list(self, email: str) -> None:
        """Add email to the accounts list."""
        if not email:
            return

        accounts = set(self.list_accounts())
        accounts.add(email)
        self._save_accounts_list(list(accounts))

    def _remove_from_account_list(self, email: str) -> None:
        """Remove email from the accounts list."""
        if not email:
            return

        accounts = set(self.list_accounts())
        accounts.discard(email)
        self._save_accounts_list(list(accounts))

    def _save_accounts_list(self, accounts: list[str]) -> None:
        """Save the accounts list to 1Password."""
        item_name = self._accounts_list_item_name()
        accounts_json = json.dumps(accounts)

        try:
            if self._item_exists(item_name):
                self._run_op(
                    [
                        "item",
                        "edit",
                        item_name,
                        f"--vault={self.vault}",
                        f"notesPlain={accounts_json}",
                    ]
                )
            else:
                self._run_op(
                    [
                        "item",
                        "create",
                        "--category=Secure Note",
                        f"--title={item_name}",
                        f"--vault={self.vault}",
                        f"--tags={self.TAG}",
                        f"notesPlain={accounts_json}",
                    ]
                )
        except Exception as e:
            logger.debug(f"Failed to update accounts list: {e}")

    def save_client_credentials(self, client_credentials: dict[str, Any]) -> bool:
        """Save OAuth client credentials to 1Password.

        Args:
            client_credentials: The full client credentials dict

        Returns:
            True if successful, False otherwise
        """
        item_name = self._client_creds_item_name()
        credential_json = json.dumps(client_credentials)

        # Extract project info for better labeling
        cred_info = client_credentials.get("web", client_credentials.get("installed", {}))
        project_id = cred_info.get("project_id", "unknown")

        try:
            if self._item_exists(item_name):
                result = self._run_op(
                    [
                        "item",
                        "edit",
                        item_name,
                        f"--vault={self.vault}",
                        f"credential={credential_json}",
                    ]
                )
            else:
                result = self._run_op(
                    [
                        "item",
                        "create",
                        "--category=API Credential",
                        f"--title={item_name}",
                        f"--vault={self.vault}",
                        f"--tags={self.TAG}",
                        f"username={project_id}",
                        "hostname=console.cloud.google.com",
                        f"credential={credential_json}",
                        "notesPlain=Google Cloud OAuth client credentials for Google Workspace Tools CLI. "
                        "Created via: gwt credentials import",
                    ]
                )

            if result.returncode == 0:
                logger.debug("Client credentials saved to 1Password")
                return True

            logger.error(f"Failed to save client credentials: {result.stderr}")
            return False

        except Exception as e:
            logger.error(f"Failed to save client credentials to 1Password: {e}")
            return False

    def load_client_credentials(self) -> dict[str, Any] | None:
        """Load OAuth client credentials from 1Password.

        Returns:
            Client credentials dict or None if not found
        """
        # Try new naming first, then fall back to old naming for compatibility
        for item_name in [self._client_creds_item_name(), "gwt-client-credentials"]:
            try:
                result = self._run_op(["item", "get", item_name, f"--vault={self.vault}"])

                if result.returncode != 0:
                    continue

                item_data = json.loads(result.stdout)
                credential_json = self._extract_credential_field(item_data)

                if not credential_json:
                    logger.debug(f"No notesPlain found in 1Password item: {item_name}")
                    continue

                result_data = json.loads(credential_json)
                return dict(result_data) if isinstance(result_data, dict) else None

            except Exception as e:
                logger.debug(f"Failed to load from {item_name}: {e}")
                continue

        return None

    def delete_client_credentials(self) -> bool:
        """Delete client credentials from 1Password."""
        item_name = self._client_creds_item_name()

        try:
            result = self._run_op(
                [
                    "item",
                    "delete",
                    item_name,
                    f"--vault={self.vault}",
                ]
            )
            if result.returncode == 0:
                logger.debug("Client credentials deleted from 1Password")
                return True
            return False
        except Exception as e:
            logger.debug(f"Failed to delete client credentials from 1Password: {e}")
            return False

    def has_client_credentials(self) -> bool:
        """Check if client credentials are stored in 1Password."""
        # Check both new and old naming
        for item_name in [self._client_creds_item_name(), "gwt-client-credentials"]:
            if self._item_exists(item_name):
                return True
        return False


# Storage backend type for explicit selection
StorageBackend = str  # "auto", "1password", "keyring", "file"


def get_credential_storage(
    use_keyring: bool = True,
    fallback_to_file: bool = True,
    service_name: str = KeyringCredentialStorage.DEFAULT_SERVICE_NAME,
    token_path: Path | None = None,
    credentials_path: Path | None = None,
    storage_backend: StorageBackend = "auto",
    onepassword_vault: str | None = None,
) -> CredentialStorage:
    """Factory function to get appropriate credential storage backend.

    Args:
        use_keyring: Whether to attempt using keyring (legacy, use storage_backend instead)
        fallback_to_file: Whether to fall back to file storage if preferred backend unavailable
        service_name: Service name for keyring/1Password
        token_path: Path for file-based token storage
        credentials_path: Path to client credentials file
        storage_backend: Explicit backend selection:
            - "auto": Try 1Password → keyring → file (default)
            - "1password": Use 1Password CLI (requires op CLI + app integration for Touch ID)
            - "keyring": Use system keyring (macOS Keychain, etc.)
            - "file": Use file-based storage
        onepassword_vault: 1Password vault name (default: "Private")

    Returns:
        Appropriate CredentialStorage implementation

    Raises:
        RuntimeError: If required backend is unavailable and fallback is disabled
    """
    # Handle explicit backend selection
    if storage_backend == "1password":
        op_storage = OnePasswordCredentialStorage(service_name, vault=onepassword_vault)
        if op_storage.is_available():
            logger.debug("Using 1Password for credential storage")
            return op_storage
        if not fallback_to_file:
            raise RuntimeError("1Password CLI unavailable and fallback disabled")
        logger.debug("1Password CLI not available, falling back")

    elif storage_backend == "keyring":
        try:
            kr_storage = KeyringCredentialStorage(service_name)
            if kr_storage.is_available():
                logger.debug("Using keyring for credential storage")
                return kr_storage
        except ImportError:
            pass
        if not fallback_to_file:
            raise RuntimeError("Keyring unavailable and fallback disabled")
        logger.debug("Keyring not available, falling back")

    elif storage_backend == "file":
        if token_path is None:
            token_path = Path("tmp/token_drive.json")
        logger.debug(f"Using file-based credential storage at {token_path}")
        return FileCredentialStorage(token_path, credentials_path)

    elif storage_backend == "auto":
        # Try backends in order: 1Password → keyring → file

        # 1. Try 1Password first (best UX with Touch ID)
        try:
            op_storage = OnePasswordCredentialStorage(service_name, vault=onepassword_vault)
            if op_storage.is_available():
                logger.debug("Using 1Password for credential storage (Touch ID enabled)")
                return op_storage
            logger.debug("1Password CLI not available")
        except Exception as e:
            logger.debug(f"1Password unavailable: {e}")

        # 2. Try keyring (if enabled)
        if use_keyring:
            try:
                kr_storage = KeyringCredentialStorage(service_name)
                if kr_storage.is_available():
                    logger.debug("Using keyring for credential storage")
                    return kr_storage
                logger.debug("Keyring not available")
            except ImportError:
                logger.debug("Keyring module not installed")
            except Exception as e:
                logger.debug(f"Keyring unavailable: {e}")

            if not fallback_to_file:
                raise RuntimeError("No secure storage available and fallback disabled")

    # 3. Fall back to file storage
    if token_path is None:
        token_path = Path("tmp/token_drive.json")

    logger.debug(f"Using file-based credential storage at {token_path}")
    return FileCredentialStorage(token_path, credentials_path)
