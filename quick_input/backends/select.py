from __future__ import annotations

import platform
from dataclasses import dataclass

from quick_input.backends.base import HotkeyBackend, TypingBackend


@dataclass(frozen=True)
class BackendPair:
    hotkeys: HotkeyBackend
    typing: TypingBackend


def select_backends(system: str | None = None) -> BackendPair:
    platform_name = system or platform.system()

    if platform_name == "Windows":
        from quick_input.backends.windows_hotkeys import WindowsHotkeyBackend
        from quick_input.backends.windows_typing import WindowsTypingBackend

        return BackendPair(
            hotkeys=WindowsHotkeyBackend(),
            typing=WindowsTypingBackend(),
        )

    if platform_name == "Darwin":
        from quick_input.backends.macos_dev import MacOSDevHotkeyBackend, MacOSDevTypingBackend

        return BackendPair(
            hotkeys=MacOSDevHotkeyBackend(),
            typing=MacOSDevTypingBackend(),
        )

    raise RuntimeError(f"Unsupported platform: {platform_name}")
