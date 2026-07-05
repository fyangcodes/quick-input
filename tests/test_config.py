from __future__ import annotations

import json

import pytest

from quick_input import config as config_module
from quick_input.config import ConfigError, default_config_path, load_config, normalize_hotkey


def test_load_config_normalizes_hotkeys(tmp_path):
    path = tmp_path / "shortcuts.json"
    path.write_text(json.dumps({" Ctrl + 1 ": "hello"}), encoding="utf-8")

    config = load_config(path)

    assert config.shortcuts == {"ctrl+1": "hello"}


def test_load_config_rejects_non_string_values(tmp_path):
    path = tmp_path / "shortcuts.json"
    path.write_text(json.dumps({"ctrl+1": 123}), encoding="utf-8")

    with pytest.raises(ConfigError, match="must be a string"):
        load_config(path)


def test_load_config_rejects_duplicate_normalized_hotkeys(tmp_path):
    path = tmp_path / "shortcuts.json"
    path.write_text(json.dumps({"CTRL+1": "one", "ctrl+1": "two"}), encoding="utf-8")

    with pytest.raises(ConfigError, match="Duplicate shortcut"):
        load_config(path)


def test_normalize_hotkey_rejects_empty_parts():
    with pytest.raises(ConfigError, match="Invalid hotkey"):
        normalize_hotkey("ctrl++1")


def test_default_config_path_uses_executable_directory_when_frozen(monkeypatch):
    monkeypatch.setattr(config_module.sys, "frozen", True, raising=False)
    monkeypatch.setattr(config_module.sys, "executable", r"C:\Apps\quick-input\quick-input.exe")

    assert default_config_path() == config_module.Path(r"C:\Apps\quick-input\shortcuts.json")
