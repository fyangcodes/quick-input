from __future__ import annotations

import sys
import types

import pytest

from quick_input.backends.pynput_typing import PynputTypingBackend
from quick_input.backends.pynput_hotkeys import _to_pynput_hotkey
from quick_input.backends.pywinauto_typing import PywinautoTypingBackend
from quick_input.backends.select import select_backends


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

    assert backends.hotkeys.__class__.__name__ == "PynputHotkeyBackend"
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

    assert backends.hotkeys.__class__.__name__ == "PynputHotkeyBackend"
    assert backends.typing.__class__.__name__ == "PynputTypingBackend"


def test_select_backends_for_windows_rejects_unknown_typing_backend():
    with pytest.raises(ValueError, match="Unsupported Windows typing backend"):
        select_backends("Windows", windows_typing_backend="unknown")


def test_pynput_hotkey_converter_wraps_named_keys():
    assert _to_pynput_hotkey("ctrl+alt+esc") == "<ctrl>+<alt>+<esc>"
    assert _to_pynput_hotkey("ctrl+enter") == "<ctrl>+<enter>"


def test_pywinauto_typing_uses_packet_mode_to_preserve_literal_text():
    calls = []
    backend = PywinautoTypingBackend.__new__(PywinautoTypingBackend)
    backend._send_keys = lambda *args, **kwargs: calls.append((args, kwargs))
    backend._inter_key_delay = 0.03

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


def test_pynput_typing_types_text():
    controller = FakeController()
    backend = PynputTypingBackend.__new__(PynputTypingBackend)
    backend._controller = controller

    backend.type_text("A B")

    assert controller.typed == ["A B"]
