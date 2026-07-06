# Quick Input Python App TODO

## Goal

Build a small Python desktop app that listens for global hotkeys such as `Ctrl+1` and types configured text into the currently focused cursor location by simulating keyboard input. The app must not use copy/paste or depend on the system clipboard, because the target use case includes remote desktop sessions where clipboard sync is unreliable.

## Core Decisions

- Use Python as the main implementation language.
- Design for Windows deployment first; macOS is only the development environment.
- Use a platform adapter layer so each OS can choose its own hotkey and typing implementation.
- Use a global hotkey listener so the app can run in the background.
- Inject text as real keyboard events, character by character or key by key.
- Avoid all clipboard APIs for text insertion.
- Keep the first version simple: local config file, tray/background process, fixed shortcuts.

## Development And Deployment Context

- Development machine: macOS.
- Target deployment machine: Windows.
- The first production test must happen on Windows, especially inside the actual remote desktop client.
- macOS support is useful for development only; it does not need to be production-perfect in the MVP.
- Remote desktop clipboard sync is assumed unreliable or disabled, so the app must type through keyboard events.

## Library And API Decision

- Confirmed current approach: use `pynput` for global hotkeys and Windows typing by default.
- Optional Windows typing path: `pywinauto`, selectable with `--typing-backend pywinauto`.
- Preferred macOS development fallback: `pynput`, only to exercise config, hotkey routing, and basic typing locally.
- Avoid using `keyboard` as the main app dependency even though its API is convenient, because its latest PyPI release is old and macOS support is experimental.
- Avoid using `pyautogui` as the hotkey layer; it can type, but it is not the right primitive for global hotkeys.

Decision summary: build the app around our own `HotkeyBackend` and `TypingBackend` interfaces. Use `pynput` for hotkeys and typing by default, with `pywinauto` kept as an alternate typing backend.

## Confirmed Background Behavior

- The Quick Input app can run in the background without a visible window.
- The app only receives registered hotkeys such as `Ctrl+1`; it is not a general keylogger.
- When `Ctrl+1` fires, the app dispatches typing work to a worker queue after a short delay.
- The currently focused window receives the generated keystrokes, including a remote desktop window if that is focused.
- If another app already owns the same hotkey, registration may fail and should be logged clearly.

## Platform Notes

- macOS requires Accessibility permission for apps that monitor hotkeys or synthesize keyboard input.
- Windows remote desktop should receive synthetic keystrokes if the remote window is focused.
- Windows input injection can be blocked by integrity-level/UIPI restrictions; test normal and elevated target apps separately.
- Linux support may vary by desktop session, especially Wayland.
- Some remote desktop apps may filter synthetic events, so verification must include the actual target remote desktop client.

## MVP Scope

- [x] Create a Python project structure.
- [x] Add dependency management with `requirements.txt` or `pyproject.toml`.
- [x] Implement a background hotkey listener.
- [x] Register `Ctrl+1` as the first shortcut.
- [x] Store shortcut text in a simple config file.
- [x] Type configured text into the currently focused field using keyboard events.
- [x] Add a small delay before typing so the hotkey release does not leak into the output.
- [x] Add a kill switch or pause shortcut.
- [x] Add logging for startup, registered shortcuts, and typing failures.
- [x] Document required OS permissions.

## No-Clipboard Acceptance Criteria

- [x] The app never calls copy, paste, `Ctrl+V`, `Cmd+V`, or clipboard APIs.
- [ ] The app still works when clipboard sharing is disabled in a remote desktop session.
- [ ] Existing clipboard contents remain unchanged after using `Ctrl+1`.
- [ ] Text appears as if typed from a keyboard in the active focused input.

## First Prototype Design

1. Start a background Python process.
2. Detect the current platform.
3. Load shortcuts from `shortcuts.json`.
4. Select a platform backend:
   - Windows: `pynput` hotkeys plus `pynput` typing by default.
   - macOS development: `pynput` hotkeys plus `pynput` typing.
5. Listen for `Ctrl+1`.
6. When triggered, dispatch the action onto a worker queue rather than doing work inside the hotkey callback.
7. Wait around 100-200 ms so the hotkey release does not leak into output.
8. Type the mapped text using synthetic keyboard events.
9. Continue listening until the user exits.

Example config:

```json
{
  "ctrl+1": "Hello from Quick Input",
  "ctrl+2": "Thanks, I will check and follow up."
}
```

## Implementation Tasks

- [x] Create `quick_input/` package.
- [x] Create `quick_input/app.py` for startup and shutdown.
- [x] Create `quick_input/config.py` for loading shortcut mappings.
- [x] Create `quick_input/backends/base.py` with `HotkeyBackend` and `TypingBackend` protocols.
- [x] Create `quick_input/backends/pynput_hotkeys.py` using `pynput`.
- [x] Create `quick_input/backends/pynput_typing.py` for default Windows typing.
- [x] Create `quick_input/backends/pywinauto_typing.py` for optional Windows typing.
- [x] Create `quick_input/backends/macos_dev.py` using `pynput` for local development only.
- [x] Create `quick_input/hotkeys.py` for backend-independent hotkey registration.
- [x] Create `quick_input/typer.py` for backend-independent text typing.
- [x] Create `shortcuts.json` sample config.
- [x] Add a command such as `python -m quick_input`.
- [x] Add basic tests for config parsing.
- [x] Add unit tests for backend selection.
- [x] Add a manual test checklist for local apps and remote desktop.

## Risks To Validate Early

- [ ] Confirm the chosen library can type into the specific remote desktop client.
- [ ] Confirm special characters work correctly with the active keyboard layout.
- [ ] Confirm `Ctrl+1` does not conflict with important app shortcuts.
- [ ] Confirm hotkey listener does not repeatedly trigger while keys are held down.
- [ ] Confirm multiline text handling works where supported.
- [ ] Confirm elevated Windows apps do or do not accept input from a non-elevated Quick Input process.

## Nice-To-Have Later

- [ ] Tray icon with pause/resume.
- [ ] Small settings window for editing shortcuts.
- [ ] Per-app shortcut profiles.
- [ ] Import/export shortcut sets.
- [ ] Optional typing speed control.
- [ ] Optional sound or visual confirmation after typing.
- [ ] Packaged app build for macOS and Windows.

## Manual Test Checklist

- [ ] On macOS development machine, run the `pynput` fallback and confirm config/hotkey routing works. See `MANUAL_TEST_CHECKLIST.md`.
- [ ] On Windows, run the app and confirm `Ctrl+1` is registered.
- [ ] Open a local text editor and press `Ctrl+1`; configured text is typed.
- [ ] Put unique text in the clipboard, press `Ctrl+1`, then paste elsewhere; clipboard text is unchanged.
- [ ] Connect to the remote desktop, focus a text field, press `Ctrl+1`; text is typed inside the remote session.
- [ ] Test punctuation, uppercase letters, spaces, and newlines.
- [ ] Test repeated use without restarting the app.
- [ ] Test pause/exit behavior.
