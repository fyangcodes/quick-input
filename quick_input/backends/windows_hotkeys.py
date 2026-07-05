from __future__ import annotations

import ctypes
import logging
from collections.abc import Callable, Mapping
from ctypes import wintypes

LOGGER = logging.getLogger(__name__)

WM_HOTKEY = 0x0312
MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
MOD_WIN = 0x0008
MOD_NOREPEAT = 0x4000

_VK_DIGITS = {str(value): 0x30 + value for value in range(10)}
_VK_LETTERS = {chr(value): value for value in range(ord("a"), ord("z") + 1)}
_VK_NAMES = {
    "esc": 0x1B,
    "escape": 0x1B,
    "space": 0x20,
    "tab": 0x09,
    "enter": 0x0D,
    "return": 0x0D,
}


class MSG(ctypes.Structure):
    _fields_ = [
        ("hwnd", wintypes.HWND),
        ("message", wintypes.UINT),
        ("wParam", wintypes.WPARAM),
        ("lParam", wintypes.LPARAM),
        ("time", wintypes.DWORD),
        ("pt", wintypes.POINT),
    ]


class WindowsHotkeyBackend:
    def __init__(self) -> None:
        self._user32 = ctypes.WinDLL("user32", use_last_error=True)
        self._kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        self._callbacks: dict[int, tuple[str, Callable[[str], None]]] = {}
        self._stopped = False
        self._thread_id: int | None = None

    def run(self, shortcuts: Mapping[str, Callable[[str], None]]) -> None:
        self._thread_id = self._kernel32.GetCurrentThreadId()
        self._register_shortcuts(shortcuts)
        self._message_loop()

    def stop(self) -> None:
        self._stopped = True
        if self._thread_id is not None:
            self._user32.PostThreadMessageW(self._thread_id, 0x0012, 0, 0)

    def _register_shortcuts(self, shortcuts: Mapping[str, Callable[[str], None]]) -> None:
        for hotkey_id, (hotkey, callback) in enumerate(shortcuts.items(), start=1):
            modifiers, vk = parse_windows_hotkey(hotkey)
            ok = self._user32.RegisterHotKey(None, hotkey_id, modifiers, vk)
            if not ok:
                raise OSError(ctypes.get_last_error(), f"Could not register hotkey {hotkey!r}")
            LOGGER.info("Registered Windows hotkey %s", hotkey)
            self._callbacks[hotkey_id] = (hotkey, callback)

    def _message_loop(self) -> None:
        msg = MSG()
        try:
            while not self._stopped and self._user32.GetMessageW(ctypes.byref(msg), None, 0, 0) != 0:
                if msg.message == WM_HOTKEY:
                    hotkey_id = int(msg.wParam)
                    registered = self._callbacks.get(hotkey_id)
                    if registered is None:
                        LOGGER.warning("Received unknown hotkey id %s", hotkey_id)
                        continue
                    hotkey, callback = registered
                    callback(hotkey)
                else:
                    self._user32.TranslateMessage(ctypes.byref(msg))
                    self._user32.DispatchMessageW(ctypes.byref(msg))
        finally:
            self._unregister_all()

    def _unregister_all(self) -> None:
        for hotkey_id, (hotkey, _) in list(self._callbacks.items()):
            self._user32.UnregisterHotKey(None, hotkey_id)
            LOGGER.info("Unregistered Windows hotkey %s", hotkey)
        self._callbacks.clear()


def parse_windows_hotkey(hotkey: str) -> tuple[int, int]:
    parts = hotkey.lower().split("+")
    modifiers = MOD_NOREPEAT
    key: str | None = None

    for part in parts:
        if part in {"ctrl", "control"}:
            modifiers |= MOD_CONTROL
        elif part == "alt":
            modifiers |= MOD_ALT
        elif part == "shift":
            modifiers |= MOD_SHIFT
        elif part in {"win", "windows", "meta", "cmd", "command"}:
            modifiers |= MOD_WIN
        elif key is None:
            key = part
        else:
            raise ValueError(f"Hotkey has more than one non-modifier key: {hotkey!r}")

    if key is None:
        raise ValueError(f"Hotkey is missing a key: {hotkey!r}")

    vk = _VK_DIGITS.get(key) or _VK_LETTERS.get(key) or _VK_NAMES.get(key)
    if vk is None:
        raise ValueError(f"Unsupported Windows hotkey key: {key!r}")

    return modifiers, vk
