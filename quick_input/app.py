from __future__ import annotations

import argparse
import logging
import queue
import signal
import sys
import threading
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path

from quick_input.backends.base import HotkeyBackend, TypingBackend
from quick_input.backends.select import select_backends
from quick_input.config import DEFAULT_CONFIG_PATH, ConfigError, load_config
from quick_input.hotkeys import HotkeyManager
from quick_input.typer import TextTyper

LOGGER = logging.getLogger(__name__)
DEFAULT_TYPE_DELAY_SECONDS = 0.15
PAUSE_HOTKEY = "ctrl+alt+p"
QUIT_HOTKEY = "ctrl+alt+q"


@dataclass(frozen=True)
class AppOptions:
    config_path: Path = DEFAULT_CONFIG_PATH
    type_delay_seconds: float = DEFAULT_TYPE_DELAY_SECONDS


class QuickInputApp:
    def __init__(
        self,
        shortcuts: Mapping[str, str],
        hotkey_backend: HotkeyBackend,
        typing_backend: TypingBackend,
        type_delay_seconds: float = DEFAULT_TYPE_DELAY_SECONDS,
    ) -> None:
        self._shortcuts = dict(shortcuts)
        self._hotkeys = HotkeyManager(hotkey_backend)
        self._typer = TextTyper(typing_backend)
        self._type_delay_seconds = type_delay_seconds
        self._queue: queue.Queue[str | None] = queue.Queue()
        self._stop_event = threading.Event()
        self._paused = False
        self._worker = threading.Thread(target=self._worker_loop, name="quick-input-typer")

    def run(self) -> None:
        LOGGER.info("Quick Input starting")
        LOGGER.info("Pause shortcut: %s; quit shortcut: %s", PAUSE_HOTKEY, QUIT_HOTKEY)
        self._worker.start()
        try:
            self._hotkeys.run(self._callbacks())
        finally:
            self.stop()

    def stop(self) -> None:
        if self._stop_event.is_set():
            return
        LOGGER.info("Quick Input shutting down")
        self._stop_event.set()
        self._hotkeys.stop()
        self._queue.put(None)
        self._worker.join(timeout=2)

    def _callbacks(self) -> dict[str, Callable[[str], None]]:
        callbacks = {hotkey: self._make_type_callback(hotkey) for hotkey in self._shortcuts}
        callbacks[PAUSE_HOTKEY] = self._toggle_pause
        callbacks[QUIT_HOTKEY] = self._quit
        return callbacks

    def _make_type_callback(self, hotkey: str) -> Callable[[str], None]:
        def callback(_hotkey: str) -> None:
            if self._paused:
                LOGGER.info("Ignoring %s because Quick Input is paused", hotkey)
                return
            LOGGER.debug("Queued shortcut %s", hotkey)
            self._queue.put(hotkey)

        return callback

    def _toggle_pause(self, *_args: object) -> None:
        self._paused = not self._paused
        LOGGER.info("Quick Input %s", "paused" if self._paused else "resumed")

    def _quit(self, *_args: object) -> None:
        self.stop()

    def _worker_loop(self) -> None:
        while True:
            hotkey = self._queue.get()
            if hotkey is None:
                return
            text = self._shortcuts.get(hotkey)
            if text is None:
                LOGGER.warning("No configured text for hotkey %s", hotkey)
                continue
            try:
                time.sleep(self._type_delay_seconds)
                self._typer.type_text(text)
            except Exception:
                LOGGER.exception("Failed to type configured text for %s", hotkey)


def build_app(options: AppOptions) -> QuickInputApp:
    config = load_config(options.config_path)
    backends = select_backends()
    return QuickInputApp(
        shortcuts=config.shortcuts,
        hotkey_backend=backends.hotkeys,
        typing_backend=backends.typing,
        type_delay_seconds=options.type_delay_seconds,
    )


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    configure_logging(args.verbose)

    options = AppOptions(
        config_path=args.config,
        type_delay_seconds=args.delay,
    )

    try:
        app = build_app(options)
    except (ConfigError, RuntimeError, ImportError) as exc:
        LOGGER.error("%s", exc)
        return 2

    def handle_signal(_signum: int, _frame: object) -> None:
        app.stop()

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    app.run()
    return 0


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Type configured snippets with global hotkeys.")
    parser.add_argument(
        "--config",
        type=Path,
        default=DEFAULT_CONFIG_PATH,
        help="Path to shortcuts JSON config.",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=DEFAULT_TYPE_DELAY_SECONDS,
        help="Seconds to wait after a hotkey before typing.",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable debug logging.",
    )
    return parser.parse_args(argv)


def configure_logging(verbose: bool = False) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )


if __name__ == "__main__":
    sys.exit(main())
