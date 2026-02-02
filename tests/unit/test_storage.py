"""Tests for credential storage backends."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from google_workspace_tools.core.storage import (
    FileCredentialStorage,
    KeyringCredentialStorage,
    OnePasswordCredentialStorage,
    StoredCredentials,
    get_credential_storage,
)


@pytest.mark.unit
class TestStoredCredentials:
    """Tests for StoredCredentials dataclass."""

    def test_creation_with_all_fields(self):
        """Test creating StoredCredentials with all fields."""
        creds = StoredCredentials(
            token_data={"refresh_token": "test_token", "scopes": ["scope1"]},
            client_id="client123",
            client_secret="secret456",
            email="user@example.com",
        )
        assert creds.token_data["refresh_token"] == "test_token"
        assert creds.client_id == "client123"
        assert creds.client_secret == "secret456"
        assert creds.email == "user@example.com"

    def test_creation_with_defaults(self):
        """Test creating StoredCredentials with defaults."""
        creds = StoredCredentials()
        assert creds.token_data == {}
        assert creds.client_id is None
        assert creds.client_secret is None
        assert creds.email is None

    def test_creation_partial(self):
        """Test creating StoredCredentials with partial data."""
        creds = StoredCredentials(
            token_data={"access_token": "abc"},
            email="test@example.com",
        )
        assert creds.token_data["access_token"] == "abc"
        assert creds.email == "test@example.com"
        assert creds.client_id is None


@pytest.mark.unit
class TestFileCredentialStorage:
    """Tests for file-based storage."""

    def test_save_and_load(self, tmp_path: Path):
        """Test saving and loading credentials."""
        token_path = tmp_path / "token.json"
        storage = FileCredentialStorage(token_path)

        creds = StoredCredentials(
            token_data={"refresh_token": "abc123", "scopes": ["scope1", "scope2"]},
            client_id="client_id",
            client_secret="client_secret",
        )

        assert storage.save(creds)
        assert token_path.exists()

        loaded = storage.load()
        assert loaded is not None
        assert loaded.token_data["refresh_token"] == "abc123"
        assert loaded.token_data["scopes"] == ["scope1", "scope2"]

    def test_load_nonexistent(self, tmp_path: Path):
        """Test loading from non-existent file returns None."""
        storage = FileCredentialStorage(tmp_path / "missing.json")
        assert storage.load() is None

    def test_load_invalid_json(self, tmp_path: Path):
        """Test loading invalid JSON returns None."""
        token_path = tmp_path / "invalid.json"
        token_path.write_text("not valid json {{{")

        storage = FileCredentialStorage(token_path)
        assert storage.load() is None

    def test_delete(self, tmp_path: Path):
        """Test deleting token file."""
        token_path = tmp_path / "token.json"
        token_path.write_text("{}")

        storage = FileCredentialStorage(token_path)
        assert storage.delete()
        assert not token_path.exists()

    def test_delete_nonexistent(self, tmp_path: Path):
        """Test deleting non-existent file returns False."""
        storage = FileCredentialStorage(tmp_path / "missing.json")
        assert not storage.delete()

    def test_list_accounts_with_token(self, tmp_path: Path):
        """Test listing accounts when token exists."""
        token_path = tmp_path / "token.json"
        token_path.write_text("{}")

        storage = FileCredentialStorage(token_path)
        accounts = storage.list_accounts()
        assert accounts == ["default"]

    def test_list_accounts_no_token(self, tmp_path: Path):
        """Test listing accounts when no token exists."""
        storage = FileCredentialStorage(tmp_path / "missing.json")
        accounts = storage.list_accounts()
        assert accounts == []

    def test_is_available(self, tmp_path: Path):
        """Test file storage is always available."""
        storage = FileCredentialStorage(tmp_path / "token.json")
        assert storage.is_available()

    def test_save_creates_parent_directories(self, tmp_path: Path):
        """Test that save creates parent directories."""
        token_path = tmp_path / "nested" / "dir" / "token.json"
        storage = FileCredentialStorage(token_path)

        creds = StoredCredentials(token_data={"test": "data"})
        assert storage.save(creds)
        assert token_path.exists()


@pytest.mark.unit
class TestKeyringCredentialStorage:
    """Tests for keyring-based storage."""

    @patch("google_workspace_tools.core.storage.KeyringCredentialStorage.keyring")
    def test_save_and_load(self, mock_keyring):
        """Test saving and loading credentials from keyring."""
        storage = KeyringCredentialStorage()

        creds = StoredCredentials(
            token_data={"refresh_token": "xyz789"},
            client_id="client",
            client_secret="secret",
            email="test@example.com",
        )

        # Mock save
        storage.save(creds)
        mock_keyring.set_password.assert_called()

        # Setup mock for load
        stored_data = {
            "token": {"refresh_token": "xyz789"},
            "client_id": "client",
            "client_secret": "secret",
            "email": "test@example.com",
        }
        mock_keyring.get_password.return_value = json.dumps(stored_data)

        loaded = storage.load("test@example.com")
        assert loaded is not None
        assert loaded.token_data["refresh_token"] == "xyz789"
        assert loaded.email == "test@example.com"

    @patch("google_workspace_tools.core.storage.KeyringCredentialStorage.keyring")
    def test_load_nonexistent(self, mock_keyring):
        """Test loading non-existent credentials returns None."""
        mock_keyring.get_password.return_value = None

        storage = KeyringCredentialStorage()
        assert storage.load("nobody@example.com") is None

    @patch("google_workspace_tools.core.storage.KeyringCredentialStorage.keyring")
    def test_delete(self, mock_keyring):
        """Test deleting credentials from keyring."""
        storage = KeyringCredentialStorage()
        assert storage.delete("test@example.com")
        mock_keyring.delete_password.assert_called()

    @patch("google_workspace_tools.core.storage.KeyringCredentialStorage.keyring")
    def test_list_accounts(self, mock_keyring):
        """Test listing accounts from keyring."""
        mock_keyring.get_password.return_value = json.dumps(["user1@example.com", "user2@example.com"])

        storage = KeyringCredentialStorage()
        accounts = storage.list_accounts()
        assert "user1@example.com" in accounts
        assert "user2@example.com" in accounts

    @patch("google_workspace_tools.core.storage.KeyringCredentialStorage.keyring")
    def test_list_accounts_empty(self, mock_keyring):
        """Test listing accounts when none stored."""
        mock_keyring.get_password.return_value = None

        storage = KeyringCredentialStorage()
        accounts = storage.list_accounts()
        assert accounts == []

    @patch("google_workspace_tools.core.storage.KeyringCredentialStorage.keyring")
    def test_is_available_success(self, mock_keyring):
        """Test keyring availability check succeeds."""
        mock_keyring.get_keyring.return_value = MagicMock()

        storage = KeyringCredentialStorage()
        assert storage.is_available()

    @patch("google_workspace_tools.core.storage.KeyringCredentialStorage.keyring")
    def test_is_available_failure(self, mock_keyring):
        """Test keyring availability check fails."""
        mock_keyring.get_keyring.side_effect = Exception("No keyring")

        storage = KeyringCredentialStorage()
        assert not storage.is_available()

    @patch("google_workspace_tools.core.storage.KeyringCredentialStorage.keyring")
    def test_default_account_key(self, mock_keyring):
        """Test using default account key when no email provided."""
        mock_keyring.get_password.return_value = json.dumps({"token": {}})

        storage = KeyringCredentialStorage()
        storage.load()  # No account email

        # Should use default account key
        mock_keyring.get_password.assert_called_with("google-workspace-tools", "_default")

    def test_custom_service_name(self):
        """Test using custom service name."""
        storage = KeyringCredentialStorage(service_name="custom-service")
        assert storage.service_name == "custom-service"


@pytest.mark.unit
class TestOnePasswordCredentialStorage:
    """Tests for 1Password CLI-based storage."""

    def test_init_defaults(self):
        """Test initialization with default values."""
        storage = OnePasswordCredentialStorage()
        assert storage.service_name == "google-workspace-tools"
        assert storage.vault == "Private"

    def test_init_custom_vault(self):
        """Test initialization with custom vault."""
        storage = OnePasswordCredentialStorage(vault="Work")
        assert storage.vault == "Work"

    def test_token_item_name_with_email(self):
        """Test item name generation with email."""
        storage = OnePasswordCredentialStorage()
        assert storage._token_item_name("user@example.com") == "Google Workspace Tools - OAuth Token (user@example.com)"

    def test_token_item_name_default(self):
        """Test item name generation without email."""
        storage = OnePasswordCredentialStorage()
        assert storage._token_item_name(None) == "Google Workspace Tools - OAuth Token (Default)"

    @patch("shutil.which")
    def test_op_path_found(self, mock_which):
        """Test op CLI path detection when available."""
        mock_which.return_value = "/opt/homebrew/bin/op"
        storage = OnePasswordCredentialStorage()
        assert storage.op_path == "/opt/homebrew/bin/op"

    @patch("shutil.which")
    def test_op_path_not_found(self, mock_which):
        """Test op CLI path detection when not available."""
        mock_which.return_value = None
        storage = OnePasswordCredentialStorage()
        storage._op_path = None  # Reset cached value
        assert storage.op_path is None

    @patch("shutil.which")
    def test_is_available_no_op(self, mock_which):
        """Test availability check when op not installed."""
        mock_which.return_value = None
        storage = OnePasswordCredentialStorage()
        storage._op_path = None  # Reset cached value
        assert not storage.is_available()

    @patch("subprocess.run")
    @patch("shutil.which")
    def test_is_available_op_not_signed_in(self, mock_which, mock_run):
        """Test availability check when op not signed in."""
        mock_which.return_value = "/opt/homebrew/bin/op"
        mock_run.return_value = MagicMock(returncode=1)
        storage = OnePasswordCredentialStorage()
        assert not storage.is_available()

    @patch("subprocess.run")
    @patch("shutil.which")
    def test_is_available_op_signed_in(self, mock_which, mock_run):
        """Test availability check when op is signed in."""
        mock_which.return_value = "/opt/homebrew/bin/op"
        mock_run.return_value = MagicMock(returncode=0, stdout="[]")
        storage = OnePasswordCredentialStorage()
        assert storage.is_available()

    @patch("subprocess.run")
    @patch("shutil.which")
    def test_load_not_found(self, mock_which, mock_run):
        """Test loading non-existent credentials."""
        mock_which.return_value = "/opt/homebrew/bin/op"
        mock_run.return_value = MagicMock(returncode=1)
        storage = OnePasswordCredentialStorage()
        assert storage.load("user@example.com") is None

    @patch("subprocess.run")
    @patch("shutil.which")
    def test_load_success(self, mock_which, mock_run):
        """Test loading credentials successfully."""
        mock_which.return_value = "/opt/homebrew/bin/op"

        item_data = {
            "notesPlain": json.dumps(
                {
                    "token": {"refresh_token": "xyz789"},
                    "client_id": "client",
                    "client_secret": "secret",
                    "email": "test@example.com",
                }
            )
        }
        mock_run.return_value = MagicMock(returncode=0, stdout=json.dumps(item_data))

        storage = OnePasswordCredentialStorage()
        loaded = storage.load("test@example.com")

        assert loaded is not None
        assert loaded.token_data["refresh_token"] == "xyz789"
        assert loaded.email == "test@example.com"

    @patch("subprocess.run")
    @patch("shutil.which")
    def test_save_creates_new_item(self, mock_which, mock_run):
        """Test saving creates new item when it doesn't exist."""
        mock_which.return_value = "/opt/homebrew/bin/op"

        # First call: item doesn't exist, second call: create succeeds
        mock_run.side_effect = [
            MagicMock(returncode=1),  # _item_exists check
            MagicMock(returncode=0),  # create
            MagicMock(returncode=1),  # accounts list doesn't exist
            MagicMock(returncode=0),  # create accounts list
        ]

        storage = OnePasswordCredentialStorage()
        creds = StoredCredentials(
            token_data={"refresh_token": "test"},
            email="user@example.com",
        )
        assert storage.save(creds)

    @patch("subprocess.run")
    @patch("shutil.which")
    def test_delete_success(self, mock_which, mock_run):
        """Test deleting credentials."""
        mock_which.return_value = "/opt/homebrew/bin/op"
        mock_run.return_value = MagicMock(returncode=0)

        storage = OnePasswordCredentialStorage()
        assert storage.delete("user@example.com")


@pytest.mark.unit
class TestGetCredentialStorage:
    """Tests for storage factory function."""

    def test_file_storage_when_explicitly_selected(self, tmp_path: Path):
        """Test getting file storage when explicitly selected."""
        storage = get_credential_storage(
            storage_backend="file",
            token_path=tmp_path / "token.json",
        )
        assert isinstance(storage, FileCredentialStorage)

    def test_file_fallback_when_keyring_unavailable(self, tmp_path: Path):
        """Test falling back to file storage when keyring unavailable."""
        with (
            patch(
                "google_workspace_tools.core.storage.OnePasswordCredentialStorage.is_available",
                return_value=False,
            ),
            patch(
                "google_workspace_tools.core.storage.KeyringCredentialStorage.is_available",
                return_value=False,
            ),
        ):
            storage = get_credential_storage(
                use_keyring=True,
                fallback_to_file=True,
                token_path=tmp_path / "token.json",
            )
            assert isinstance(storage, FileCredentialStorage)

    def test_raises_when_keyring_required_but_unavailable(self):
        """Test raising error when keyring required but unavailable."""
        with (
            patch(
                "google_workspace_tools.core.storage.KeyringCredentialStorage.is_available",
                return_value=False,
            ),
            pytest.raises(RuntimeError, match="Keyring unavailable"),
        ):
            get_credential_storage(
                storage_backend="keyring",
                fallback_to_file=False,
            )

    def test_keyring_storage_when_explicitly_selected(self):
        """Test getting keyring storage when explicitly selected."""
        with patch(
            "google_workspace_tools.core.storage.KeyringCredentialStorage.is_available",
            return_value=True,
        ):
            storage = get_credential_storage(storage_backend="keyring")
            assert isinstance(storage, KeyringCredentialStorage)

    def test_default_token_path(self):
        """Test default token path is used when not specified."""
        storage = get_credential_storage(storage_backend="file")
        assert isinstance(storage, FileCredentialStorage)
        assert storage.token_path == Path("tmp/token_drive.json")

    def test_keyring_import_error_fallback(self, tmp_path: Path):
        """Test fallback when keyring module not installed."""
        with (
            patch(
                "google_workspace_tools.core.storage.OnePasswordCredentialStorage.is_available",
                return_value=False,
            ),
            patch(
                "google_workspace_tools.core.storage.KeyringCredentialStorage.__init__",
                side_effect=ImportError("No module named 'keyring'"),
            ),
        ):
            storage = get_credential_storage(
                use_keyring=True,
                fallback_to_file=True,
                token_path=tmp_path / "token.json",
            )
            assert isinstance(storage, FileCredentialStorage)

    def test_1password_storage_when_explicitly_selected(self):
        """Test getting 1Password storage when explicitly selected."""
        with patch(
            "google_workspace_tools.core.storage.OnePasswordCredentialStorage.is_available",
            return_value=True,
        ):
            from google_workspace_tools.core.storage import OnePasswordCredentialStorage

            storage = get_credential_storage(storage_backend="1password")
            assert isinstance(storage, OnePasswordCredentialStorage)

    def test_auto_prefers_1password_when_available(self):
        """Test that auto mode prefers 1Password when available."""
        with patch(
            "google_workspace_tools.core.storage.OnePasswordCredentialStorage.is_available",
            return_value=True,
        ):
            from google_workspace_tools.core.storage import OnePasswordCredentialStorage

            storage = get_credential_storage(storage_backend="auto")
            assert isinstance(storage, OnePasswordCredentialStorage)

    def test_auto_falls_back_to_keyring(self):
        """Test that auto mode falls back to keyring when 1Password unavailable."""
        with (
            patch(
                "google_workspace_tools.core.storage.OnePasswordCredentialStorage.is_available",
                return_value=False,
            ),
            patch(
                "google_workspace_tools.core.storage.KeyringCredentialStorage.is_available",
                return_value=True,
            ),
        ):
            storage = get_credential_storage(storage_backend="auto")
            assert isinstance(storage, KeyringCredentialStorage)
