from __future__ import annotations

import logging

from quick_input.backends.base import TypingBackend

LOGGER = logging.getLogger(__name__)


class TextTyper:
    def __init__(self, backend: TypingBackend) -> None:
        self._backend = backend

    def type_text(self, text: str) -> None:
        LOGGER.debug("Typing %s characters", len(text))
        self._backend.type_text(text)
