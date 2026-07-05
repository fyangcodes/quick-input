from __future__ import annotations

import sys
import types
import ctypes

import pytest

from quick_input.backends.pynput_typing import PynputTypingBackend
from quick_input.backends.pywinauto_typing import PywinautoTypingBackend
from quick_input.backends.select import select_backends
from quick_input.backends.windows_hotkeys import MOD_CONTROL, MOD_NOREPEAT, parse_windows_hotkey
from quick_input.backends.windows_typing import (
    EXPECTED_INPUT_SIZE,
    INPUT,
    KEYBDINPUT,
    KEYEVENTF_KEYUP,
    KEYEVENTF_UNICODE,
    ULONG_PTR,
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


def test_select_backends_for_windows_uses_pywinauto_typing(monkeypatch):
    pywinauto = types.ModuleType("pywinauto")
    keyboard = types.ModuleType("pywinauto.keyboard")
    keyboard.send_keys = lambda *_args, **_kwargs: None
    pywinauto.keyboard = keyboard
    monkeypatch.setitem(sys.modules, "pywinauto", pywinauto)
    monkeypatch.setitem(sys.modules, "pywinauto.keyboard", keyboard)

    backends = select_backends("Windows")

    assert backends.hotkeys.__class__.__name__ == "WindowsHotkeyBackend"
    assert backends.typing.__class__.__name__ == "PywinautoTypingBackend"


def test_select_backends_for_windows_can_use_pynput_typing(monkeypatch):
    pynput = types.ModuleType("pynput")
    keyboard = types.ModuleType("pynput.keyboard")

    class Controller:
        def type(self, text: str) -> None:
            self.text = text

    keyboard.Controller = Controller
    pynput.keyboard = keyboard
    monkeypatch.setitem(sys.modules, "pynput", pynput)
    monkeypatch.setitem(sys.modules, "pynput.keyboard", keyboard)

    backends = select_backends("Windows", windows_typing_backend="pynput")

    assert backends.hotkeys.__class__.__name__ == "WindowsHotkeyBackend"
    assert backends.typing.__class__.__name__ == "PynputTypingBackend"


def test_select_backends_for_windows_can_use_win32_typing():
    backends = select_backends("Windows", windows_typing_backend="win32")

    assert backends.hotkeys.__class__.__name__ == "WindowsHotkeyBackend"
    assert backends.typing.__class__.__name__ == "WindowsTypingBackend"


class FakeUser32:
    def __init__(self) -> None:
        self.calls = []
        self.key_state = 0
        self.key_states = []

    def SendInput(self, count: int, inputs, size: int) -> int:
        self.calls.append((count, inputs, size))
        return count

    def GetAsyncKeyState(self, virtual_key: int) -> int:
        if self.key_states:
            return self.key_states.pop(0)
        return self.key_state


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


def test_windows_typing_sends_space_as_unicode_after_modifier_release():
    user32 = FakeUser32()
    backend = WindowsTypingBackend.__new__(WindowsTypingBackend)
    backend._user32 = user32
    backend._inter_key_delay = 0

    backend.type_text("A B")

    assert len(user32.calls) == 3
    _, space_inputs, size = user32.calls[1]
    assert size == ctypes.sizeof(INPUT)
    assert space_inputs[0].union.ki.wVk == 0
    assert space_inputs[0].union.ki.wScan == ord(" ")
    assert space_inputs[0].union.ki.dwFlags == KEYEVENTF_UNICODE
    assert space_inputs[1].union.ki.wScan == ord(" ")
    assert space_inputs[1].union.ki.dwFlags == KEYEVENTF_UNICODE | KEYEVENTF_KEYUP


def test_windows_typing_waits_for_modifier_release_before_typing(monkeypatch):
    user32 = FakeUser32()
    user32.key_states = [0x8000, 0x8000, 0x8000, 0]
    backend = WindowsTypingBackend.__new__(WindowsTypingBackend)
    backend._user32 = user32
    backend._inter_key_delay = 0
    sleeps = []
    monkeypatch.setattr("quick_input.backends.windows_typing.time.sleep", sleeps.append)

    backend.type_text("A")

    assert len(user32.calls) == 1
    assert sleeps == [0.01, 0.01, 0.01]


def test_windows_typing_dw_extra_info_is_pointer_sized_integer():
    assert dict(KEYBDINPUT._fields_)["dwExtraInfo"] is ULONG_PTR


def test_pywinauto_typing_uses_packet_mode_to_preserve_literal_text():
    calls = []
    backend = PywinautoTypingBackend.__new__(PywinautoTypingBackend)
    backend._send_keys = lambda *args, **kwargs: calls.append((args, kwargs))
    backend._inter_key_delay = 0.03
    backend._wait_for_modifier_release = lambda: None

    backend.type_text("A B")

    assert calls == [
        (
            ("A B",),
            {
                "pause": 0.03,
                "with_spaces": True,
                "vk_packet": True,
            },
        )
    ]


class FakeController:
    def __init__(self) -> None:
        self.typed = []

    def type(self, text: str) -> None:
        self.typed.append(text)


def test_pynput_typing_types_text_after_modifier_release():
    controller = FakeController()
    backend = PynputTypingBackend.__new__(PynputTypingBackend)
    backend._controller = controller
    backend._wait_for_modifier_release = lambda: None

    backend.type_text("A B")

    assert controller.typed == ["A B"]
