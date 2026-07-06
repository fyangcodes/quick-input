from __future__ import annotations


class PynputTypingBackend:
    def __init__(self) -> None:
        from pynput.keyboard import Controller

        self._controller = Controller()

    def type_text(self, text: str) -> None:
        self._controller.type(text)
