from __future__ import annotations

import sys
import types
import ctypes

import pytest

from quick_input.backends.select import select_backends
from quick_input.backends.windows_hotkeys import MOD_CONTROL, MOD_NOREPEAT, parse_windows_hotkey
from quick_input.backends.windows_typing import (
    EXPECTED_INPUT_SIZE,
    INPUT,
    KEYBDINPUT,
    KEYEVENTF_KEYUP,
    KEYEVENTF_UNICODE,
    ULONG_PTR,
    VK_CONTROL,
    VK_V,
    WindowsTypingBackend,
    _surrogate_pair,
)


def test_parse_windows_hotkey_uses_control_digit_and_no_repeat():
    modifiers, vk = parse_windows_hotkey("ctrl+1")

    assert modifiers & MOD_CONTROL
    assert modifiers & MOD_NOREPEAT
    assert vk == 0x31


def test_parse_windows_hotkey_rejects_multiple_keys():
    with pytest.raises(ValueError, match="more than one"):
        parse_windows_hotkey("ctrl+1+2")


def test_select_backends_rejects_unsupported_platform():
    with pytest.raises(RuntimeError, match="Unsupported platform"):
        select_backends("Linux")


def test_select_backends_for_darwin(monkeypatch):
    pynput = types.ModuleType("pynput")
    keyboard = types.ModuleType("pynput.keyboard")

    class Controller:
        def type(self, text: str) -> None:
            self.text = text

    keyboard.Controller = Controller
    pynput.keyboard = keyboard
    monkeypatch.setitem(sys.modules, "pynput", pynput)
    monkeypatch.setitem(sys.modules, "pynput.keyboard", keyboard)

    backends = select_backends("Darwin")

    assert backends.hotkeys.__class__.__name__ == "MacOSDevHotkeyBackend"
    assert backends.typing.__class__.__name__ == "MacOSDevTypingBackend"


class FakeUser32:
    def __init__(self) -> None:
        self.calls = []

    def SendInput(self, count: int, inputs, size: int) -> int:
        self.calls.append((count, inputs, size))
        return count


def test_windows_typing_sendinput_uses_valid_input_shape():
    user32 = FakeUser32()
    backend = WindowsTypingBackend.__new__(WindowsTypingBackend)
    backend._user32 = user32
    backend._inter_key_delay = 0

    backend.type_text("A")

    assert len(user32.calls) == 1
    count, inputs, size = user32.calls[0]
    assert count == 2
    assert size == ctypes.sizeof(INPUT)
    assert size == EXPECTED_INPUT_SIZE
    assert inputs[0].union.ki.wVk == 0
    assert inputs[0].union.ki.wScan == ord("A")
    assert inputs[0].union.ki.dwFlags == KEYEVENTF_UNICODE
    assert inputs[0].union.ki.dwExtraInfo == 0
    assert inputs[1].union.ki.wScan == ord("A")
    assert inputs[1].union.ki.dwFlags == KEYEVENTF_UNICODE | KEYEVENTF_KEYUP


def test_windows_typing_sends_supplementary_characters_as_surrogate_units():
    user32 = FakeUser32()
    backend = WindowsTypingBackend.__new__(WindowsTypingBackend)
    backend._user32 = user32
    backend._inter_key_delay = 0

    backend.type_text("\U0001F680")

    assert len(user32.calls) == 2
    assert [call[1][0].union.ki.wScan for call in user32.calls] == list(_surrogate_pair(0x1F680))


def test_windows_typing_uses_paste_fallback_for_whitespace():
    backend = WindowsTypingBackend.__new__(WindowsTypingBackend)
    pasted = []
    backend._paste_text = pasted.append

    backend.type_text("A B")

    assert pasted == ["A B"]


def test_windows_typing_sends_ctrl_v_for_paste_fallback():
    user32 = FakeUser32()
    backend = WindowsTypingBackend.__new__(WindowsTypingBackend)
    backend._user32 = user32
    backend._inter_key_delay = 0

    backend._send_ctrl_v()

    assert len(user32.calls) == 1
    count, inputs, size = user32.calls[0]
    assert count == 4
    assert size == ctypes.sizeof(INPUT)
    assert [inputs[index].union.ki.wVk for index in range(4)] == [VK_CONTROL, VK_V, VK_V, VK_CONTROL]
    assert [inputs[index].union.ki.dwFlags for index in range(4)] == [0, 0, KEYEVENTF_KEYUP, KEYEVENTF_KEYUP]


def test_windows_typing_dw_extra_info_is_pointer_sized_integer():
    assert dict(KEYBDINPUT._fields_)["dwExtraInfo"] is ULONG_PTR
