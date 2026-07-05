from __future__ import annotations

import ctypes
import time
from ctypes import wintypes

MODIFIER_RELEASE_POLL_SECONDS = 0.01
VK_CONTROL = 0x11
VK_MENU = 0x12
VK_SHIFT = 0x10
VK_LWIN = 0x5B
VK_RWIN = 0x5C
MODIFIER_KEYS = (VK_CONTROL, VK_MENU, VK_SHIFT, VK_LWIN, VK_RWIN)


class PywinautoTypingBackend:
    def __init__(self, inter_key_delay: float = 0.01) -> None:
        from pywinauto.keyboard import send_keys

        self._send_keys = send_keys
        self._inter_key_delay = inter_key_delay
        self._user32 = ctypes.WinDLL("user32", use_last_error=True)
        self._user32.GetAsyncKeyState.argtypes = [ctypes.c_int]
        self._user32.GetAsyncKeyState.restype = wintypes.SHORT

    def type_text(self, text: str) -> None:
        self._wait_for_modifier_release()
        self._send_keys(
            text,
            pause=self._inter_key_delay,
            with_spaces=True,
            vk_packet=True,
        )

    def _wait_for_modifier_release(self) -> None:
        while True:
            if not any(self._is_virtual_key_down(key) for key in MODIFIER_KEYS):
                return
            time.sleep(MODIFIER_RELEASE_POLL_SECONDS)

    def _is_virtual_key_down(self, virtual_key: int) -> bool:
        return bool(self._user32.GetAsyncKeyState(virtual_key) & 0x8000)
