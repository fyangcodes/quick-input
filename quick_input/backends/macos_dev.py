from __future__ import annotations

from quick_input.backends.pynput_hotkeys import PynputHotkeyBackend


class MacOSDevHotkeyBackend(PynputHotkeyBackend):
    """Local development fallback using pynput."""


class MacOSDevTypingBackend:
    def __init__(self, inter_key_delay: float = 0.0) -> None:
        from pynput.keyboard import Controller

        self._controller = Controller()
        self._inter_key_delay = inter_key_delay

    def type_text(self, text: str) -> None:
        self._controller.type(text)

