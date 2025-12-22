"""Credential storage backends for OAuth tokens and client secrets."""

from __future__ import annotations

import json
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
                email=None,  # File storage doesn't track email separately
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


def get_credential_storage(
    use_keyring: bool = True,
    fallback_to_file: bool = True,
    service_name: str = KeyringCredentialStorage.DEFAULT_SERVICE_NAME,
    token_path: Path | None = None,
    credentials_path: Path | None = None,
) -> CredentialStorage:
    """Factory function to get appropriate credential storage backend.

    Args:
        use_keyring: Whether to attempt using keyring
        fallback_to_file: Whether to fall back to file storage if keyring unavailable
        service_name: Service name for keyring
        token_path: Path for file-based token storage
        credentials_path: Path to client credentials file

    Returns:
        Appropriate CredentialStorage implementation

    Raises:
        RuntimeError: If keyring is required but unavailable and fallback is disabled
    """
    if use_keyring:
        try:
            storage = KeyringCredentialStorage(service_name)
            if storage.is_available():
                logger.debug("Using keyring for credential storage")
                return storage
            logger.debug("Keyring not available")
        except ImportError:
            logger.debug("Keyring module not installed")
        except Exception as e:
            logger.debug(f"Keyring unavailable: {e}")

        if not fallback_to_file:
            raise RuntimeError("Keyring unavailable and fallback to file storage disabled")

    if token_path is None:
        token_path = Path("tmp/token_drive.json")

    logger.debug(f"Using file-based credential storage at {token_path}")
    return FileCredentialStorage(token_path, credentials_path)
