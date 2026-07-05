# Manual Test Checklist

## macOS Development

- Grant Accessibility permission to the terminal or app running Quick Input.
- Run `python -m quick_input --config shortcuts.json --verbose`.
- Focus a local text editor and press `Ctrl+1`; configured text is typed.
- Press `Ctrl+Alt+P`; confirm snippets are ignored while paused.
- Press `Ctrl+Alt+P` again; confirm snippets work after resume.
- Press `Ctrl+Alt+Q`; confirm the process exits.

## Windows Production

- Run `python -m quick_input --config shortcuts.json --verbose`.
- Confirm `Ctrl+1` registers without administrator permissions.
- Focus a local text editor and press `Ctrl+1`; configured text is typed.
- Put unique text in the clipboard, press `Ctrl+1`, then paste elsewhere;
  clipboard text is unchanged.
- Hold `Ctrl+1`; confirm the hotkey does not repeatedly trigger.
- Test punctuation, uppercase letters, spaces, newlines, and repeated use.
- Focus the target remote desktop client and press `Ctrl+1`; text is typed into
  the remote session.
- Test whether elevated target apps accept input from a non-elevated Quick Input
  process.
