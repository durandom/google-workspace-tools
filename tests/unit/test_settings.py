"""Tests for settings management with TOML config file support."""

import pytest

from google_workspace_tools.settings import (
    _TOML_FIELD_MAP,
    CONFIG_FILE,
    DEFAULT_CONFIG_TOML,
    Settings,
    TomlConfigSettingsSource,
)


class TestTomlConfigSettingsSource:
    """Tests for TOML config file loading."""

    def test_missing_config_file(self, tmp_path):
        """Missing config file should produce no values."""
        source = TomlConfigSettingsSource(Settings, toml_file=tmp_path / "nonexistent.toml")
        assert source() == {}

    def test_load_storage_backend(self, tmp_path):
        """TOML [storage] backend should map to storage_backend."""
        config = tmp_path / "config.toml"
        config.write_text('[storage]\nbackend = "keyring"\n')
        source = TomlConfigSettingsSource(Settings, toml_file=config)
        result = source()
        assert result["storage_backend"] == "keyring"

    def test_load_multiple_sections(self, tmp_path):
        """Values from multiple TOML sections should be loaded."""
        config = tmp_path / "config.toml"
        config.write_text(
            '[storage]\nbackend = "file"\n\n'
            '[export]\nformat = "html"\ntarget_directory = "/tmp/out"\n\n'
            '[logging]\nlevel = "DEBUG"\n'
        )
        source = TomlConfigSettingsSource(Settings, toml_file=config)
        result = source()
        assert result["storage_backend"] == "file"
        assert result["export_format"] == "html"
        assert result["target_directory"] == "/tmp/out"
        assert result["log_level"] == "DEBUG"

    def test_partial_config(self, tmp_path):
        """Only specified values should be returned, not missing ones."""
        config = tmp_path / "config.toml"
        config.write_text('[storage]\nbackend = "auto"\n')
        source = TomlConfigSettingsSource(Settings, toml_file=config)
        result = source()
        assert "storage_backend" in result
        assert "export_format" not in result

    def test_vault_mapping(self, tmp_path):
        """TOML [storage] vault should map to onepassword_vault."""
        config = tmp_path / "config.toml"
        config.write_text('[storage]\nvault = "Work"\n')
        source = TomlConfigSettingsSource(Settings, toml_file=config)
        result = source()
        assert result["onepassword_vault"] == "Work"

    def test_invalid_toml_syntax(self, tmp_path):
        """Malformed TOML should raise ValueError with helpful message."""
        config = tmp_path / "config.toml"
        config.write_text('[storage\nbackend = "keyring"')  # Missing closing bracket
        with pytest.raises(ValueError, match="Invalid TOML syntax"):
            TomlConfigSettingsSource(Settings, toml_file=config)


class TestSettingsPriority:
    """Tests for settings source priority."""

    def test_toml_overrides_default(self, tmp_path, monkeypatch):
        """TOML config should override default values."""
        config = tmp_path / "config.toml"
        config.write_text('[storage]\nbackend = "keyring"\n')
        # Patch CONFIG_FILE to use our temp file
        monkeypatch.setattr("google_workspace_tools.settings.CONFIG_FILE", config)
        s = Settings()
        assert s.storage_backend == "keyring"

    def test_env_overrides_toml(self, tmp_path, monkeypatch):
        """Environment variable should override TOML config."""
        config = tmp_path / "config.toml"
        config.write_text('[storage]\nbackend = "keyring"\n')
        monkeypatch.setattr("google_workspace_tools.settings.CONFIG_FILE", config)
        monkeypatch.setenv("GWT_STORAGE_BACKEND", "file")
        s = Settings()
        assert s.storage_backend == "file"

    def test_defaults_without_config(self, tmp_path, monkeypatch):
        """Without a config file, defaults should be used."""
        # Must patch the default parameter in TomlConfigSettingsSource.__init__
        nonexistent = tmp_path / "nope.toml"
        monkeypatch.setattr("google_workspace_tools.settings.CONFIG_FILE", nonexistent)
        # Clear any env vars that might interfere
        monkeypatch.delenv("GWT_STORAGE_BACKEND", raising=False)
        # Create Settings with explicit toml_file override via init
        source = TomlConfigSettingsSource(Settings, toml_file=nonexistent)
        assert source() == {}
        # Verify the default value is used when no sources provide it
        assert Settings.model_fields["storage_backend"].default == "1password"


class TestDefaultConfigToml:
    """Tests for the default config template."""

    def test_template_is_valid_toml(self):
        """The default template should be parseable as TOML (comments only)."""
        import tomllib

        data = tomllib.loads(DEFAULT_CONFIG_TOML)
        # All values are commented out, so sections should be empty dicts
        assert data["storage"] == {}
        assert data["oauth"] == {}
        assert data["export"] == {}
        assert data["logging"] == {}

    def test_config_file_path_is_in_home(self):
        """Config file should be under ~/.config/gwt/."""
        assert ".config" in str(CONFIG_FILE)
        assert "gwt" in str(CONFIG_FILE)
        assert str(CONFIG_FILE).endswith("config.toml")

    def test_toml_field_map_matches_settings_fields(self):
        """All _TOML_FIELD_MAP values must correspond to actual Settings fields."""
        field_names = set(Settings.model_fields.keys())
        mapped_names = set(_TOML_FIELD_MAP.values())
        invalid = mapped_names - field_names
        assert not invalid, f"Invalid TOML mappings: {invalid}"
