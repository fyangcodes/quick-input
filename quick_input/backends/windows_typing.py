from __future__ import annotations

import ctypes
import logging
import time
from ctypes import wintypes

LOGGER = logging.getLogger(__name__)

INPUT_KEYBOARD = 1
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_UNICODE = 0x0004
ULONG_PTR = wintypes.WPARAM


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
        self._inter_key_delay = inter_key_delay

    def type_text(self, text: str) -> None:
        for char in text:
            self._send_unicode_char(char)
            if self._inter_key_delay:
                time.sleep(self._inter_key_delay)

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


def _keyboard_input(scan: int, flags: int) -> INPUT:
    return INPUT(
        type=INPUT_KEYBOARD,
        union=INPUT_UNION(
            ki=KEYBDINPUT(
                wVk=0,
                wScan=scan,
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
