# Quick Input Python App TODO

## Goal

Build a small Python desktop app that listens for global hotkeys such as `Ctrl+1` and types configured text into the currently focused cursor location by simulating keyboard input. The app must not use copy/paste or depend on the system clipboard, because the target use case includes remote desktop sessions where clipboard sync is unreliable.

## Core Decisions

- Use Python as the main implementation language.
- Design for Windows deployment first; macOS is only the development environment.
- Use a platform adapter layer so Windows can use native APIs while macOS can use a lightweight development fallback.
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

- Confirmed current approach: use native Win32 APIs from Python for the Windows production backend.
- Preferred Windows hotkey path: native Win32 `RegisterHotKey` through `ctypes`.
- Preferred Windows typing path: native Win32 `SendInput` through `ctypes`.
- Preferred macOS development fallback: `pynput`, only to exercise config, hotkey routing, and basic typing locally.
- Avoid using `keyboard` as the main app dependency even though its API is convenient, because its latest PyPI release is old and macOS support is experimental.
- Avoid using `pyautogui` as the hotkey layer; it can type, but it is not the right primitive for global hotkeys.

Decision summary: build the app around our own `HotkeyBackend` and `TypingBackend` interfaces. Use Win32 APIs for the real Windows implementation, and use `pynput` only as a macOS-friendly development backend.

## Confirmed Windows Background Behavior

- `RegisterHotKey` registers specific hotkey combinations system-wide.
- The Quick Input app can run in the background without a visible window.
- If `hWnd=None`, Windows posts `WM_HOTKEY` messages to the registering thread's message queue.
- The app must keep a Windows message loop alive to receive hotkey events.
- The app only receives registered hotkeys such as `Ctrl+1`; it is not a general keylogger.
- When `Ctrl+1` fires, the app should dispatch typing work to a worker queue, wait briefly for key release, then call `SendInput`.
- The currently focused window receives the generated keystrokes, including a remote desktop window if that is focused.
- If another app already owns the same hotkey, registration may fail and should be logged clearly.
- Use `MOD_NOREPEAT` so holding the hotkey does not repeatedly trigger insertion.

## Platform Notes

- macOS requires Accessibility permission for apps that monitor hotkeys or synthesize keyboard input.
- Windows remote desktop should receive synthetic keystrokes if the remote window is focused.
- Windows native hotkey registration can use a message loop and `WM_HOTKEY`.
- Windows hotkeys should use `MOD_NOREPEAT` where available to avoid repeated triggers while keys are held.
- Windows text injection should use `SendInput` with Unicode keyboard events where possible.
- Windows input injection can be blocked by integrity-level/UIPI restrictions; test normal and elevated target apps separately.
- Linux support may vary by desktop session, especially Wayland.
- Some remote desktop apps may filter synthetic events, so verification must include the actual target remote desktop client.

## MVP Scope

- [x] Create a Python project structure.
- [x] Add dependency management with `requirements.txt` or `pyproject.toml`.
- [ ] Implement a background hotkey listener.
- [ ] Register `Ctrl+1` as the first shortcut.
- [ ] Store shortcut text in a simple config file.
- [ ] Type configured text into the currently focused field using keyboard events.
- [ ] Add a small delay before typing so the hotkey release does not leak into the output.
- [ ] Add a kill switch or pause shortcut.
- [ ] Add logging for startup, registered shortcuts, and typing failures.
- [ ] Document required OS permissions.

## No-Clipboard Acceptance Criteria

- [ ] The app never calls copy, paste, `Ctrl+V`, `Cmd+V`, or clipboard APIs.
- [ ] The app still works when clipboard sharing is disabled in a remote desktop session.
- [ ] Existing clipboard contents remain unchanged after using `Ctrl+1`.
- [ ] Text appears as if typed from a keyboard in the active focused input.

## First Prototype Design

1. Start a background Python process.
2. Detect the current platform.
3. Load shortcuts from `shortcuts.json`.
4. Select a platform backend:
   - Windows: Win32 `RegisterHotKey` plus `SendInput`.
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

- [ ] Create `quick_input/` package.
- [ ] Create `quick_input/app.py` for startup and shutdown.
- [ ] Create `quick_input/config.py` for loading shortcut mappings.
- [ ] Create `quick_input/backends/base.py` with `HotkeyBackend` and `TypingBackend` protocols.
- [ ] Create `quick_input/backends/windows_hotkeys.py` using Win32 `RegisterHotKey`.
- [ ] Create `quick_input/backends/windows_typing.py` using Win32 `SendInput`.
- [ ] Create `quick_input/backends/macos_dev.py` using `pynput` for local development only.
- [ ] Create `quick_input/hotkeys.py` for backend-independent hotkey registration.
- [ ] Create `quick_input/typer.py` for backend-independent text typing.
- [ ] Create `shortcuts.json` sample config.
- [ ] Add a command such as `python -m quick_input`.
- [ ] Add basic tests for config parsing.
- [ ] Add unit tests for backend selection.
- [ ] Add a manual test checklist for local apps and remote desktop.

## Risks To Validate Early

- [ ] Confirm Windows native `RegisterHotKey` works without administrator permissions.
- [ ] Confirm Windows native `SendInput` types into the chosen remote desktop client.
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

- [ ] On macOS development machine, run the `pynput` fallback and confirm config/hotkey routing works.
- [ ] On Windows, run the Win32 backend and confirm `Ctrl+1` is registered.
- [ ] Open a local text editor and press `Ctrl+1`; configured text is typed.
- [ ] Put unique text in the clipboard, press `Ctrl+1`, then paste elsewhere; clipboard text is unchanged.
- [ ] Connect to the remote desktop, focus a text field, press `Ctrl+1`; text is typed inside the remote session.
- [ ] Test punctuation, uppercase letters, spaces, and newlines.
- [ ] Test repeated use without restarting the app.
- [ ] Test pause/exit behavior.
