"""Start the GO-Forward Streamlit dashboard without PowerShell."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path


DEFAULT_VENV_DIR = (
    Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    / "pythermogis-dashboard"
    / ".venv"
)
DEFAULT_PORT = 8502


def venv_python(venv_dir: Path) -> Path:
    if os.name == "nt":
        return venv_dir / "Scripts" / "python.exe"
    return venv_dir / "bin" / "python"


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the GO-Forward Streamlit dashboard.")
    parser.add_argument(
        "--venv-dir",
        type=Path,
        default=DEFAULT_VENV_DIR,
        help=f"Virtual environment directory. Default: {DEFAULT_VENV_DIR}",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=DEFAULT_PORT,
        help=f"Streamlit server port. Default: {DEFAULT_PORT}",
    )
    args = parser.parse_args()

    dashboard_dir = Path(__file__).resolve().parent
    python_exe = venv_python(args.venv_dir)

    if not python_exe.exists():
        raise FileNotFoundError(
            f"Virtual environment not found at {args.venv_dir}. "
            "Run `python install_dashboard.py` first."
        )

    command = [
        str(python_exe),
        "-m",
        "streamlit",
        "run",
        str(dashboard_dir / "app.py"),
        "--server.port",
        str(args.port),
    ]
    print(f"Starting dashboard on http://localhost:{args.port}")
    print("> " + " ".join(command))
    subprocess.run(command, cwd=dashboard_dir, check=True)


if __name__ == "__main__":
    sys.exit(main())
