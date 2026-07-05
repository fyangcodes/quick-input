from __future__ import annotations

import platform
from dataclasses import dataclass

from quick_input.backends.base import HotkeyBackend, TypingBackend

WINDOWS_TYPING_BACKENDS = ("pywinauto", "pynput", "win32")


@dataclass(frozen=True)
class BackendPair:
    hotkeys: HotkeyBackend
    typing: TypingBackend


def select_backends(system: str | None = None, windows_typing_backend: str = "pywinauto") -> BackendPair:
    platform_name = system or platform.system()

    if platform_name == "Windows":
        from quick_input.backends.windows_hotkeys import WindowsHotkeyBackend

        typing_backend = _select_windows_typing_backend(windows_typing_backend)
        return BackendPair(
            hotkeys=WindowsHotkeyBackend(),
            typing=typing_backend,
        )

    if platform_name == "Darwin":
        from quick_input.backends.macos_dev import MacOSDevHotkeyBackend, MacOSDevTypingBackend

        return BackendPair(
            hotkeys=MacOSDevHotkeyBackend(),
            typing=MacOSDevTypingBackend(),
        )

    raise RuntimeError(f"Unsupported platform: {platform_name}")


def _select_windows_typing_backend(name: str) -> TypingBackend:
    if name == "pywinauto":
        from quick_input.backends.pywinauto_typing import PywinautoTypingBackend

        return PywinautoTypingBackend()
    if name == "pynput":
        from quick_input.backends.pynput_typing import PynputTypingBackend

        return PynputTypingBackend()
    if name == "win32":
        from quick_input.backends.windows_typing import WindowsTypingBackend

        return WindowsTypingBackend()
    raise ValueError(f"Unsupported Windows typing backend: {name!r}")
