from __future__ import annotations

import logging
from collections.abc import Callable, Mapping

from quick_input.backends.base import HotkeyBackend

LOGGER = logging.getLogger(__name__)


class HotkeyManager:
    def __init__(self, backend: HotkeyBackend) -> None:
        self._backend = backend

    def run(self, shortcuts: Mapping[str, Callable[[str], None]]) -> None:
        LOGGER.info("Registering shortcuts: %s", ", ".join(shortcuts))
        self._backend.run(shortcuts)

    def stop(self) -> None:
        LOGGER.info("Stopping hotkey listener")
        self._backend.stop()
