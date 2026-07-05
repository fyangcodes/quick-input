from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"
CONFIG = ROOT / "shortcuts.json"


def main() -> int:
    command = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--clean",
        "--noconfirm",
        "--onefile",
        "--name",
        "quick-input",
        str(ROOT / "main.py"),
    ]
    subprocess.run(command, cwd=ROOT, check=True)

    if CONFIG.exists():
        shutil.copy2(CONFIG, DIST / CONFIG.name)

    print(f"Built {DIST / 'quick-input.exe'}")
    print(f"Editable config: {DIST / CONFIG.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
