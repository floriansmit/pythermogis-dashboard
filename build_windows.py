"""Build the portable Windows desktop package."""

from __future__ import annotations

import argparse
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile


ROOT = Path(__file__).resolve().parent
DIST = ROOT / "dist"
PACKAGE_NAME = "PythermogisDashboard"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--zip", action="store_true", help="Also create a portable ZIP archive.")
    parser.add_argument("--skip-build", action="store_true", help="Package an existing PyInstaller output.")
    args = parser.parse_args()

    if not args.skip_build:
        try:
            import PyInstaller  # noqa: F401
        except ModuleNotFoundError:
            print("PyInstaller is missing. Run: uv sync --extra desktop")
            return 1

        command = [
            sys.executable,
            "-m",
            "PyInstaller",
            "--noconfirm",
            "--clean",
            str(ROOT / "pythermogis-dashboard.spec"),
        ]
        result = subprocess.run(command, cwd=ROOT)
        if result.returncode:
            return result.returncode

    package_dir = DIST / PACKAGE_NAME
    executable = package_dir / f"{PACKAGE_NAME}.exe"
    if not executable.exists():
        executable = DIST / f"{PACKAGE_NAME}.exe"
    if not executable.exists():
        print(f"Expected executable was not created in {DIST}")
        return 1

    if args.zip:
        archive = DIST / f"{PACKAGE_NAME}-windows.zip"
        if archive.exists():
            archive.unlink()
        with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as handle:
            if package_dir.exists():
                for path in package_dir.rglob("*"):
                    if path.is_file():
                        handle.write(path, Path(PACKAGE_NAME) / path.relative_to(package_dir))
            else:
                handle.write(executable, Path(PACKAGE_NAME) / executable.name)
        print(f"Portable package: {archive}")
    print(f"Executable: {executable}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
