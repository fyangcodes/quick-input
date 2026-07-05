from __future__ import annotations

import logging
from collections.abc import Callable, Mapping

LOGGER = logging.getLogger(__name__)


class MacOSDevHotkeyBackend:
    """Local development fallback using pynput.

    This backend is intentionally scoped to macOS development. Production
    Windows deployment should use the native Win32 backends.
    """

    def __init__(self) -> None:
        self._listener = None

    def run(self, shortcuts: Mapping[str, Callable[[str], None]]) -> None:
        from pynput import keyboard

        mapping = {
            _to_pynput_hotkey(hotkey): _callback_for(hotkey, callback)
            for hotkey, callback in shortcuts.items()
        }
        for hotkey in shortcuts:
            LOGGER.info("Registered macOS development hotkey %s", hotkey)
        with keyboard.GlobalHotKeys(mapping) as listener:
            self._listener = listener
            listener.join()

    def stop(self) -> None:
        if self._listener is not None:
            self._listener.stop()


class MacOSDevTypingBackend:
    def __init__(self, inter_key_delay: float = 0.0) -> None:
        from pynput.keyboard import Controller

        self._controller = Controller()
        self._inter_key_delay = inter_key_delay

    def type_text(self, text: str) -> None:
        self._controller.type(text)


def _callback_for(hotkey: str, callback: Callable[[str], None]) -> Callable[[], None]:
    def wrapped() -> None:
        callback(hotkey)

    return wrapped


def _to_pynput_hotkey(hotkey: str) -> str:
    parts = []
    for part in hotkey.split("+"):
        if part in {"ctrl", "control"}:
            parts.append("<ctrl>")
        elif part == "alt":
            parts.append("<alt>")
        elif part == "shift":
            parts.append("<shift>")
        elif part in {"cmd", "command", "meta", "win", "windows"}:
            parts.append("<cmd>")
        else:
            parts.append(part)
    return "+".join(parts)
