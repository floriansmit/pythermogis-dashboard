"""Create the locked UV environment for the Pythermogis dashboard."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parent


def main() -> int:
    """Install the locked project dependencies with UV."""
    uv = shutil.which("uv")
    if uv is None:
        print("UV is not installed or is not available on PATH.")
        print("Install it on Windows with: winget install --id astral-sh.uv -e")
        return 1

    command = [uv, "sync", "--locked", "--system-certs"]
    print(f"Installing the dashboard environment in: {ROOT / '.venv'}")
    print("> " + " ".join(command))
    return subprocess.call(command, cwd=ROOT)


if __name__ == "__main__":
    raise SystemExit(main())
