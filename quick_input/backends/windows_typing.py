from __future__ import annotations

import ctypes
import logging
import time
from dataclasses import dataclass
from ctypes import wintypes

LOGGER = logging.getLogger(__name__)

CF_UNICODETEXT = 13
GMEM_MOVEABLE = 0x0002
INPUT_KEYBOARD = 1
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_UNICODE = 0x0004
PASTE_RESTORE_DELAY_SECONDS = 0.05
VK_CONTROL = 0x11
VK_V = 0x56
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


@dataclass(frozen=True)
class ClipboardSnapshot:
    text: str | None


class WindowsTypingBackend:
    def __init__(self, inter_key_delay: float = 0.0) -> None:
        self._user32 = ctypes.WinDLL("user32", use_last_error=True)
        self._kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        self._user32.SendInput.argtypes = [
            wintypes.UINT,
            ctypes.POINTER(INPUT),
            ctypes.c_int,
        ]
        self._user32.SendInput.restype = wintypes.UINT
        self._configure_clipboard_api()
        self._inter_key_delay = inter_key_delay

    def type_text(self, text: str) -> None:
        if any(char.isspace() for char in text):
            self._paste_text(text)
            return

        for char in text:
            self._send_unicode_char(char)
            if self._inter_key_delay:
                time.sleep(self._inter_key_delay)

    def _configure_clipboard_api(self) -> None:
        self._user32.OpenClipboard.argtypes = [wintypes.HWND]
        self._user32.OpenClipboard.restype = wintypes.BOOL
        self._user32.CloseClipboard.argtypes = []
        self._user32.CloseClipboard.restype = wintypes.BOOL
        self._user32.EmptyClipboard.argtypes = []
        self._user32.EmptyClipboard.restype = wintypes.BOOL
        self._user32.GetClipboardData.argtypes = [wintypes.UINT]
        self._user32.GetClipboardData.restype = wintypes.HANDLE
        self._user32.IsClipboardFormatAvailable.argtypes = [wintypes.UINT]
        self._user32.IsClipboardFormatAvailable.restype = wintypes.BOOL
        self._user32.SetClipboardData.argtypes = [wintypes.UINT, wintypes.HANDLE]
        self._user32.SetClipboardData.restype = wintypes.HANDLE
        self._kernel32.GlobalAlloc.argtypes = [wintypes.UINT, ctypes.c_size_t]
        self._kernel32.GlobalAlloc.restype = wintypes.HGLOBAL
        self._kernel32.GlobalLock.argtypes = [wintypes.HGLOBAL]
        self._kernel32.GlobalLock.restype = ctypes.c_void_p
        self._kernel32.GlobalUnlock.argtypes = [wintypes.HGLOBAL]
        self._kernel32.GlobalUnlock.restype = wintypes.BOOL

    def _paste_text(self, text: str) -> None:
        snapshot = self._read_clipboard_text()
        try:
            self._set_clipboard_text(text)
            self._send_ctrl_v()
            time.sleep(PASTE_RESTORE_DELAY_SECONDS)
        finally:
            self._restore_clipboard(snapshot)

    def _read_clipboard_text(self) -> ClipboardSnapshot:
        self._open_clipboard()
        try:
            if not self._user32.IsClipboardFormatAvailable(CF_UNICODETEXT):
                return ClipboardSnapshot(text=None)
            handle = self._user32.GetClipboardData(CF_UNICODETEXT)
            if not handle:
                return ClipboardSnapshot(text=None)
            locked = self._kernel32.GlobalLock(handle)
            if not locked:
                return ClipboardSnapshot(text=None)
            try:
                return ClipboardSnapshot(text=ctypes.wstring_at(locked))
            finally:
                self._kernel32.GlobalUnlock(handle)
        finally:
            self._user32.CloseClipboard()

    def _set_clipboard_text(self, text: str | None) -> None:
        self._open_clipboard()
        try:
            if not self._user32.EmptyClipboard():
                raise OSError(ctypes.get_last_error(), "EmptyClipboard failed while typing text")
            if text is None:
                return
            handle = self._global_alloc_unicode_text(text)
            if not self._user32.SetClipboardData(CF_UNICODETEXT, handle):
                raise OSError(ctypes.get_last_error(), "SetClipboardData failed while typing text")
        finally:
            self._user32.CloseClipboard()

    def _restore_clipboard(self, snapshot: ClipboardSnapshot) -> None:
        try:
            self._set_clipboard_text(snapshot.text)
        except OSError:
            LOGGER.warning("Could not restore clipboard text after paste", exc_info=True)

    def _global_alloc_unicode_text(self, text: str) -> int:
        data = (text + "\0").encode("utf-16-le")
        handle = self._kernel32.GlobalAlloc(GMEM_MOVEABLE, len(data))
        if not handle:
            raise OSError(ctypes.get_last_error(), "GlobalAlloc failed while typing text")
        locked = self._kernel32.GlobalLock(handle)
        if not locked:
            raise OSError(ctypes.get_last_error(), "GlobalLock failed while typing text")
        try:
            ctypes.memmove(locked, data, len(data))
        finally:
            self._kernel32.GlobalUnlock(handle)
        return handle

    def _open_clipboard(self) -> None:
        for _ in range(5):
            if self._user32.OpenClipboard(None):
                return
            time.sleep(0.02)
        raise OSError(ctypes.get_last_error(), "OpenClipboard failed while typing text")

    def _send_ctrl_v(self) -> None:
        inputs = (INPUT * 4)(
            _keyboard_input(VK_CONTROL, 0, use_virtual_key=True),
            _keyboard_input(VK_V, 0, use_virtual_key=True),
            _keyboard_input(VK_V, KEYEVENTF_KEYUP, use_virtual_key=True),
            _keyboard_input(VK_CONTROL, KEYEVENTF_KEYUP, use_virtual_key=True),
        )
        sent = self._user32.SendInput(len(inputs), inputs, ctypes.sizeof(INPUT))
        if sent != len(inputs):
            raise OSError(ctypes.get_last_error(), "SendInput failed while typing text")

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
