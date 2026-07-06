# Quick Input

Quick Input is a small background Python app that listens for global hotkeys and
types configured text into the currently focused field using keyboard events. It
does not use copy, paste, or the system clipboard.

## Run

Create or edit `shortcuts.json`:

```json
{
  "ctrl+1": "Hello from Quick Input",
  "ctrl+2": "Thanks, I will check and follow up."
}
```

Start the app:

```bash
python -m quick_input --config shortcuts.json
```

## Build EXE

PyInstaller is included as a development dependency. Build a one-file Windows
executable with:

```bash
uv run python scripts/build_exe.py
```

The build writes `dist/quick-input.exe` and copies `shortcuts.json` beside it.
Edit `dist/shortcuts.json` directly to change shortcuts without rebuilding.

Useful controls:

- `Ctrl+1`, `Ctrl+2`, etc. type configured snippets.
- `Ctrl+Alt+P` pauses or resumes snippet typing.
- `Ctrl+Alt+Q` exits the app.
- `--delay 0.15` controls the delay between hotkey detection and typing.
- `--verbose` enables debug logging.

## Platform Backends

- Windows: `pynput` for global hotkeys and typing by default.
  `pywinauto` typing is also available with `--typing-backend pywinauto`.
- macOS: `pynput` development fallback for local config and routing checks.

## Required OS Permissions

Windows may block synthetic input into elevated applications from a non-elevated
Quick Input process.

macOS requires Accessibility permission for the terminal or packaged app that
runs Quick Input. Grant it in System Settings, Privacy & Security,
Accessibility. Depending on the environment, Input Monitoring permission may
also be required.

Remote desktop clients vary. The target remote desktop window must be focused,
and the actual client should be tested because some clients filter synthetic
keyboard events.
