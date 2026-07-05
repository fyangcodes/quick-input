from __future__ import annotations

import sys
import types

import pytest

from quick_input.backends.select import select_backends
from quick_input.backends.windows_hotkeys import MOD_CONTROL, MOD_NOREPEAT, parse_windows_hotkey


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
