from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


def default_config_path() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).with_name("shortcuts.json")
    return Path("shortcuts.json")


DEFAULT_CONFIG_PATH = default_config_path()


class ConfigError(ValueError):
    """Raised when the shortcut configuration is invalid."""


@dataclass(frozen=True)
class ShortcutConfig:
    shortcuts: dict[str, str]


def normalize_hotkey(hotkey: str) -> str:
    parts = [part.strip().lower() for part in hotkey.split("+")]
    if not parts or any(not part for part in parts):
        raise ConfigError(f"Invalid hotkey: {hotkey!r}")
    return "+".join(parts)


def load_config(path: Path | str = DEFAULT_CONFIG_PATH) -> ShortcutConfig:
    config_path = Path(path)
    try:
        raw = json.loads(config_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ConfigError(f"Shortcut config not found: {config_path}") from exc
    except json.JSONDecodeError as exc:
        raise ConfigError(f"Shortcut config is not valid JSON: {config_path}") from exc

    if not isinstance(raw, dict):
        raise ConfigError("Shortcut config must be a JSON object")

    shortcuts: dict[str, str] = {}
    for hotkey, text in raw.items():
        if not isinstance(hotkey, str):
            raise ConfigError("Shortcut keys must be strings")
        if not isinstance(text, str):
            raise ConfigError(f"Shortcut value for {hotkey!r} must be a string")
        normalized = normalize_hotkey(hotkey)
        if normalized in shortcuts:
            raise ConfigError(f"Duplicate shortcut after normalization: {normalized}")
        shortcuts[normalized] = text

    if not shortcuts:
        raise ConfigError("Shortcut config must contain at least one shortcut")

    return ShortcutConfig(shortcuts=shortcuts)


def dump_sample_config() -> dict[str, Any]:
    return {
        "ctrl+1": "Hello from Quick Input",
        "ctrl+2": "Thanks, I will check and follow up.",
    }
