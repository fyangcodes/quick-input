from __future__ import annotations


class PywinautoTypingBackend:
    def __init__(self, inter_key_delay: float = 0.01) -> None:
        from pywinauto.keyboard import send_keys

        self._send_keys = send_keys
        self._inter_key_delay = inter_key_delay

    def type_text(self, text: str) -> None:
        self._send_keys(
            text,
            pause=self._inter_key_delay,
            with_spaces=True,
            vk_packet=True,
        )
