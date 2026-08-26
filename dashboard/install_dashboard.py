"""Install the GO-Forward Streamlit dashboard without PowerShell.

Run from any shell:

    python install_dashboard.py

The script creates a machine-local virtual environment by default, installs the
dashboard requirements, and installs the local project packages in editable mode.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path


DEFAULT_PYTHON_VERSION = "3.13"
TNO_PACKAGE_INDEX = "https://ci.tno.nl/gitlab/api/v4/projects/18271/packages/pypi/simple"
DEFAULT_VENV_DIR = (
    Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    / "pythermogis-dashboard"
    / ".venv"
)


def run(command: list[str | Path], *, cwd: Path | None = None) -> None:
    printable = " ".join(str(part) for part in command)
    print(f"\n> {printable}")
    subprocess.run([str(part) for part in command], cwd=cwd, check=True)


def venv_python(venv_dir: Path) -> Path:
    if os.name == "nt":
        return venv_dir / "Scripts" / "python.exe"
    return venv_dir / "bin" / "python"


def create_venv(venv_dir: Path, python_version: str) -> None:
    python_exe = venv_python(venv_dir)
    if python_exe.exists():
        return

    print(f"Creating virtual environment at {venv_dir}")

    if os.name == "nt":
        candidates = [
            ["py", f"-{python_version}", "-m", "venv", str(venv_dir)],
            [sys.executable, "-m", "venv", str(venv_dir)],
        ]
    else:
        candidates = [
            [f"python{python_version}", "-m", "venv", str(venv_dir)],
            [sys.executable, "-m", "venv", str(venv_dir)],
        ]

    last_error: Exception | None = None
    for command in candidates:
        try:
            run(command)
            if python_exe.exists():
                return
        except (FileNotFoundError, subprocess.CalledProcessError) as exc:
            last_error = exc

    raise RuntimeError(
        f"Could not create virtual environment at {venv_dir}. "
        f"Install Python {python_version} and retry."
    ) from last_error


def install_editable_if_present(python_exe: Path, package_path: Path, label: str) -> None:
    if package_path.exists():
        run([python_exe, "-m", "pip", "install", "-e", package_path])
    else:
        print(f"Warning: skipping {label}; not found at {package_path}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Create/update the virtual environment for the GO-Forward dashboard."
    )
    parser.add_argument(
        "--python-version",
        default=DEFAULT_PYTHON_VERSION,
        help=f"Python version to use when creating the venv. Default: {DEFAULT_PYTHON_VERSION}",
    )
    parser.add_argument(
        "--venv-dir",
        type=Path,
        default=DEFAULT_VENV_DIR,
        help=f"Virtual environment directory. Default: {DEFAULT_VENV_DIR}",
    )
    parser.add_argument(
        "--source-root",
        type=Path,
        default=None,
        help=(
            "Optional local Pythermogis source checkout. If omitted, the installer first "
            "looks for a sibling 'pythermogis' folder and otherwise installs the public package."
        ),
    )
    args = parser.parse_args()

    dashboard_dir = Path(__file__).resolve().parent
    project_root = dashboard_dir.parent
    python_exe = venv_python(args.venv_dir)

    print(f"Dashboard folder: {dashboard_dir}")
    print(f"Project root:     {project_root}")
    print(f"Virtual env:      {args.venv_dir}")

    synced_venv = dashboard_dir / ".venv"
    if synced_venv.exists():
        print(
            f"Warning: {synced_venv} exists inside the dashboard folder. "
            f"This installer uses {args.venv_dir} instead."
        )

    create_venv(args.venv_dir, args.python_version)

    requirements = dashboard_dir / "requirements.txt"
    if not requirements.exists():
        raise FileNotFoundError(f"Dashboard requirements file not found: {requirements}")

    run([python_exe, "-m", "pip", "install", "--upgrade", "pip"])
    run([python_exe, "-m", "pip", "install", "-r", requirements])
    source_root = args.source_root
    if source_root is None:
        sibling_source = project_root.parent / "pythermogis"
        source_root = sibling_source if (sibling_source / "pyproject.toml").exists() else None

    if source_root is not None:
        source_root = source_root.resolve()
        if not (source_root / "pyproject.toml").exists():
            raise FileNotFoundError(
                f"Pythermogis source root does not contain pyproject.toml: {source_root}"
            )
        print(f"Installing local Pythermogis source: {source_root}")
        run([python_exe, "-m", "pip", "install", "-e", source_root])
        install_editable_if_present(
            python_exe, source_root / "pygridsio-1.1.4", "local pygridsio-1.1.4"
        )
    else:
        print("No local source checkout detected; installing public Pythermogis package.")
        run(
            [
                python_exe,
                "-m",
                "pip",
                "install",
                "pythermogis==3.0.3",
                "--index-url",
                TNO_PACKAGE_INDEX,
            ]
        )

    print("\nInstall complete. Start the dashboard with:")
    print(f"  python {dashboard_dir / 'run_dashboard.py'}")


if __name__ == "__main__":
    main()
