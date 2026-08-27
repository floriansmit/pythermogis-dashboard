"""Start the GO-Forward Streamlit dashboard without PowerShell."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path


DEFAULT_PORT = 8502


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the GO-Forward Streamlit dashboard.")
    parser.add_argument(
        "--port",
        type=int,
        default=DEFAULT_PORT,
        help=f"Streamlit server port. Default: {DEFAULT_PORT}",
    )
    args = parser.parse_args()

    root = Path(__file__).resolve().parent
    app_path = root / "dashboard" / "app.py"
    managed_environment = (root / ".venv").resolve()
    active_python = Path(sys.executable).resolve()
    if managed_environment not in active_python.parents:
        uv = shutil.which("uv")
        if uv is None:
            print("The UV-managed environment is not active and UV is unavailable on PATH.")
            print("Run python install_dashboard.py after installing UV.")
            return 1
        command = [
            uv, "run", "--locked", "python", str(Path(__file__).resolve()),
            "--port", str(args.port),
        ]
        print("Starting through the UV-managed environment.", flush=True)
        return subprocess.call(command, cwd=root)

    try:
        import streamlit  # noqa: F401
    except ModuleNotFoundError:
        print("Streamlit is missing from .venv. Run python install_dashboard.py.")
        return 1

    command = [
        sys.executable,
        "-m",
        "streamlit",
        "run",
        str(app_path),
        "--server.port",
        str(args.port),
    ]
    print(f"Starting dashboard on http://localhost:{args.port}")
    print("> " + " ".join(command))
    return subprocess.call(command, cwd=root)


if __name__ == "__main__":
    raise SystemExit(main())
