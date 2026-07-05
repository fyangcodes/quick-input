from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Protocol


HotkeyCallback = Callable[[str], None]


class HotkeyBackend(Protocol):
    """Backend capable of registering and listening for global hotkeys."""

    def run(self, shortcuts: Mapping[str, HotkeyCallback]) -> None:
        """Register shortcuts and block until the backend stops."""

    def stop(self) -> None:
        """Ask the backend to stop listening and clean up registrations."""


class TypingBackend(Protocol):
    """Backend capable of typing text through keyboard events."""

    def type_text(self, text: str) -> None:
        """Type text into the currently focused input target."""
