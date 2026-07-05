from __future__ import annotations

from quick_input.app import QUIT_HOTKEYS, QuickInputApp


class FakeHotkeyBackend:
    def run(self, shortcuts):
        self.shortcuts = shortcuts

    def stop(self):
        self.stopped = True


class FakeTypingBackend:
    def type_text(self, text: str) -> None:
        self.text = text


def test_quit_callbacks_include_layout_safe_fallback(monkeypatch):
    app = QuickInputApp(
        shortcuts={"ctrl+1": "hello"},
        hotkey_backend=FakeHotkeyBackend(),
        typing_backend=FakeTypingBackend(),
    )
    stopped = []
    monkeypatch.setattr(app, "stop", lambda: stopped.append(True))

    callbacks = app._callbacks()

    assert set(QUIT_HOTKEYS) <= callbacks.keys()
    callbacks["ctrl+alt+esc"]("ctrl+alt+esc")
    assert stopped == [True]
