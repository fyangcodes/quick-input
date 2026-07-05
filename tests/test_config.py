from __future__ import annotations

import json

import pytest

from quick_input.config import ConfigError, load_config, normalize_hotkey


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
