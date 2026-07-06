from __future__ import annotations

import time


class PynputTypingBackend:
    def __init__(self, inter_key_delay: float = 0.03) -> None:
        from pynput.keyboard import Controller

        self._controller = Controller()
        self._inter_key_delay = inter_key_delay

    def type_text(self, text: str) -> None:
        for char in text:
            self._controller.type(char)
            if self._inter_key_delay:
                time.sleep(self._inter_key_delay)
