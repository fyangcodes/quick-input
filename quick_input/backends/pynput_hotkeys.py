from __future__ import annotations

import logging
from collections.abc import Callable, Mapping

LOGGER = logging.getLogger(__name__)
PYNPUT_NAMED_KEYS = {
    "esc": "<esc>",
    "escape": "<esc>",
    "enter": "<enter>",
    "return": "<enter>",
    "space": "<space>",
    "tab": "<tab>",
}


class PynputHotkeyBackend:
    def __init__(self) -> None:
        self._listener = None

    def run(self, shortcuts: Mapping[str, Callable[[str], None]]) -> None:
        from pynput import keyboard

        mapping = {
            _to_pynput_hotkey(hotkey): _callback_for(hotkey, callback)
            for hotkey, callback in shortcuts.items()
        }
        for hotkey in shortcuts:
            LOGGER.info("Registered pynput hotkey %s", hotkey)
        with keyboard.GlobalHotKeys(mapping) as listener:
            self._listener = listener
            listener.join()

    def stop(self) -> None:
        if self._listener is not None:
            self._listener.stop()


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
        elif part in PYNPUT_NAMED_KEYS:
            parts.append(PYNPUT_NAMED_KEYS[part])
        else:
            parts.append(part)
    return "+".join(parts)
