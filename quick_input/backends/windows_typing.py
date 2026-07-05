from __future__ import annotations

import ctypes
import logging
import time
from ctypes import wintypes

LOGGER = logging.getLogger(__name__)

INPUT_KEYBOARD = 1
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_UNICODE = 0x0004
MODIFIER_RELEASE_POLL_SECONDS = 0.01
VK_CONTROL = 0x11
VK_MENU = 0x12
VK_SHIFT = 0x10
VK_LWIN = 0x5B
VK_RWIN = 0x5C
ULONG_PTR = wintypes.WPARAM
MODIFIER_KEYS = (VK_CONTROL, VK_MENU, VK_SHIFT, VK_LWIN, VK_RWIN)


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", wintypes.WORD),
        ("wScan", wintypes.WORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ULONG_PTR),
    ]


class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", wintypes.LONG),
        ("dy", wintypes.LONG),
        ("mouseData", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ULONG_PTR),
    ]


class HARDWAREINPUT(ctypes.Structure):
    _fields_ = [
        ("uMsg", wintypes.DWORD),
        ("wParamL", wintypes.WORD),
        ("wParamH", wintypes.WORD),
    ]


class INPUT_UNION(ctypes.Union):
    _fields_ = [
        ("mi", MOUSEINPUT),
        ("ki", KEYBDINPUT),
        ("hi", HARDWAREINPUT),
    ]


EXPECTED_INPUT_SIZE = 40 if ctypes.sizeof(ctypes.c_void_p) == 8 else 28


class INPUT(ctypes.Structure):
    _fields_ = [
        ("type", wintypes.DWORD),
        ("union", INPUT_UNION),
    ]


class WindowsTypingBackend:
    def __init__(self, inter_key_delay: float = 0.0) -> None:
        self._user32 = ctypes.WinDLL("user32", use_last_error=True)
        self._user32.SendInput.argtypes = [
            wintypes.UINT,
            ctypes.POINTER(INPUT),
            ctypes.c_int,
        ]
        self._user32.SendInput.restype = wintypes.UINT
        self._user32.GetAsyncKeyState.argtypes = [ctypes.c_int]
        self._user32.GetAsyncKeyState.restype = wintypes.SHORT
        self._inter_key_delay = inter_key_delay

    def type_text(self, text: str) -> None:
        self._wait_for_modifier_release()
        for char in text:
            self._send_unicode_char(char)
            if self._inter_key_delay:
                time.sleep(self._inter_key_delay)

    def _wait_for_modifier_release(self) -> None:
        while True:
            if not any(self._is_virtual_key_down(key) for key in MODIFIER_KEYS):
                return
            time.sleep(MODIFIER_RELEASE_POLL_SECONDS)

    def _is_virtual_key_down(self, virtual_key: int) -> bool:
        return bool(self._user32.GetAsyncKeyState(virtual_key) & 0x8000)

    def _send_unicode_char(self, char: str) -> None:
        codepoint = ord(char)
        if codepoint > 0xFFFF:
            for surrogate in _surrogate_pair(codepoint):
                self._send_utf16_unit(surrogate)
            return
        self._send_utf16_unit(codepoint)

    def _send_utf16_unit(self, unit: int) -> None:
        inputs = (INPUT * 2)(
            _keyboard_input(unit, KEYEVENTF_UNICODE),
            _keyboard_input(unit, KEYEVENTF_UNICODE | KEYEVENTF_KEYUP),
        )
        sent = self._user32.SendInput(len(inputs), inputs, ctypes.sizeof(INPUT))
        if sent != len(inputs):
            raise OSError(ctypes.get_last_error(), "SendInput failed while typing text")


def _keyboard_input(scan: int, flags: int, use_virtual_key: bool = False) -> INPUT:
    return INPUT(
        type=INPUT_KEYBOARD,
        union=INPUT_UNION(
            ki=KEYBDINPUT(
                wVk=scan if use_virtual_key else 0,
                wScan=0 if use_virtual_key else scan,
                dwFlags=flags,
                time=0,
                dwExtraInfo=0,
            )
        ),
    )


def _surrogate_pair(codepoint: int) -> tuple[int, int]:
    value = codepoint - 0x10000
    high = 0xD800 + (value >> 10)
    low = 0xDC00 + (value & 0x3FF)
    return high, low
