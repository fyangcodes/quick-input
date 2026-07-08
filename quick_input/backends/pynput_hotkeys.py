from __future__ import annotations

import logging
import threading
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

LOGGER = logging.getLogger(__name__)
HOTKEY_RELEASE_SETTLE_SECONDS = 0.25
STALE_HOTKEY_RELEASE_TIMEOUT_SECONDS = 1.0
PYNPUT_NAMED_KEYS = {
    "esc": "<esc>",
    "escape": "<esc>",
    "enter": "<enter>",
    "return": "<enter>",
    "space": "<space>",
    "tab": "<tab>",
}


class PynputHotkeyBackend:
    def __init__(self) -> None:
        self._listener = None
        self._pressed_keys: set[Any] = set()
        self._pending_callbacks: list[Callable[[], None]] = []
        self._lock = threading.Lock()

    def run(self, shortcuts: Mapping[str, Callable[[str], None]]) -> None:
        from pynput import keyboard

        registrations = []
        for hotkey, callback in shortcuts.items():
            parsed_keys = keyboard.HotKey.parse(_to_pynput_hotkey(hotkey))
            wrapped_callback = _callback_for(hotkey, callback)
            registrations.append(
                _HotkeyRegistration(
                    key_set=set(parsed_keys),
                    hotkey=keyboard.HotKey(parsed_keys, self._defer_callback(wrapped_callback)),
                    callback=wrapped_callback,
                )
            )

        for hotkey in shortcuts:
            LOGGER.info("Registered pynput hotkey %s", hotkey)

        def on_press(key: Any, injected: bool = False) -> None:
            if injected:
                return
            canonical_key = listener.canonical(key)
            with self._lock:
                self._pressed_keys.add(canonical_key)
                for registration in registrations:
                    registration.hotkey.press(canonical_key)

        def on_release(key: Any, injected: bool = False) -> None:
            if injected:
                return
            callbacks = []
            canonical_key = listener.canonical(key)
            with self._lock:
                self._pressed_keys.discard(canonical_key)
                for registration in registrations:
                    registration.hotkey.release(canonical_key)
                ready, pending = _split_ready_callbacks(
                    self._pending_callbacks,
                    registrations,
                    self._pressed_keys,
                )
                callbacks = ready
                self._pending_callbacks = pending
            for callback in callbacks:
                threading.Timer(HOTKEY_RELEASE_SETTLE_SECONDS, callback).start()

        with keyboard.Listener(on_press=on_press, on_release=on_release) as listener:
            self._listener = listener
            listener.join()

    def stop(self) -> None:
        if self._listener is not None:
            self._listener.stop()

    def _defer_callback(self, callback: Callable[[], None]) -> Callable[[], None]:
        def wrapped() -> None:
            with self._lock:
                self._pending_callbacks.append(callback)
            threading.Timer(
                STALE_HOTKEY_RELEASE_TIMEOUT_SECONDS,
                self._run_stale_callback,
                args=(callback,),
            ).start()

        return wrapped

    def _run_stale_callback(self, callback: Callable[[], None]) -> None:
        with self._lock:
            try:
                self._pending_callbacks.remove(callback)
            except ValueError:
                return
        LOGGER.warning(
            "Hotkey release events were not fully observed; triggering shortcut after %.1fs",
            STALE_HOTKEY_RELEASE_TIMEOUT_SECONDS,
        )
        threading.Timer(HOTKEY_RELEASE_SETTLE_SECONDS, callback).start()


@dataclass(frozen=True)
class _HotkeyRegistration:
    key_set: set[Any]
    hotkey: Any
    callback: Callable[[], None]


def _callback_for(hotkey: str, callback: Callable[[str], None]) -> Callable[[], None]:
    def wrapped() -> None:
        callback(hotkey)

    return wrapped


def _split_ready_callbacks(
    pending_callbacks: list[Callable[[], None]],
    registrations: list[_HotkeyRegistration],
    pressed_keys: set[Any],
) -> tuple[list[Callable[[], None]], list[Callable[[], None]]]:
    ready = []
    still_pending = []
    pending_sets = {
        registration.callback: registration.key_set
        for registration in registrations
    }
    for callback in pending_callbacks:
        key_set = pending_sets[callback]
        if key_set.isdisjoint(pressed_keys):
            ready.append(callback)
        else:
            still_pending.append(callback)
    return ready, still_pending


def _to_pynput_hotkey(hotkey: str) -> str:
    parts = []
    for part in hotkey.split("+"):
        if part in {"ctrl", "control"}:
            parts.append("<ctrl>")
        elif part == "alt":
            parts.append("<alt>")
        elif part == "shift":
            parts.append("<shift>")
        elif part in {"cmd", "command", "meta", "win", "windows"}:
            parts.append("<cmd>")
        elif part in PYNPUT_NAMED_KEYS:
            parts.append(PYNPUT_NAMED_KEYS[part])
        else:
            parts.append(part)
    return "+".join(parts)
