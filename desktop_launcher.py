"""Launch the dashboard as a self-contained local desktop application.

The packaged executable starts Streamlit in a child process and hosts the local
page in a native WebView2 window. In a source checkout, run this file through
the optional ``desktop`` dependency extra.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import threading
import time
from urllib.error import URLError
from urllib.request import urlopen


DEFAULT_PORT = 8502
APP_TITLE = "Pythermogis dashboard"


def resource_root() -> Path:
    """Return the read-only directory containing bundled application assets."""
    return Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))


def default_data_root() -> Path:
    """Return a writable per-user data directory for the packaged app."""
    if not getattr(sys, "frozen", False):
        return Path(__file__).resolve().parent
    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        return Path(local_app_data) / "PythermogisDashboard"
    return Path.home() / ".pythermogis-dashboard"


def prepare_data_root(data_root: Path) -> None:
    """Create the writable data directory and seed the compact demo project once."""
    data_root.mkdir(parents=True, exist_ok=True)
    bundled_demo = resource_root() / "data" / "demo-project"
    target_demo = data_root / "data" / "demo-project"
    if bundled_demo.exists() and not target_demo.exists():
        target_demo.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(bundled_demo, target_demo)


def choose_port(requested: int) -> int:
    """Return the requested port when available, otherwise an ephemeral port."""
    if requested > 0:
        with socket.socket() as probe:
            probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                probe.bind(("127.0.0.1", requested))
            except OSError:
                pass
            else:
                return requested
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return int(probe.getsockname()[1])


def streamlit_child(app_path: Path, port: int, data_root: Path) -> int:
    """Run Streamlit inside the packaged child process."""
    os.environ["PYTHERMOGIS_DATA_ROOT"] = str(data_root)
    # PyInstaller places Streamlit outside ``site-packages``; its default
    # development-mode detection would otherwise reject an explicit port.
    os.environ["STREAMLIT_GLOBAL_DEVELOPMENTMODE"] = "false"
    from streamlit.web import bootstrap

    streamlit_options = {
        "server.address": "127.0.0.1",
        "server.port": port,
        "server.headless": True,
        "server.fileWatcherType": "none",
        "browser.gatherUsageStats": False,
        "global.developmentMode": False,
    }
    bootstrap.load_config_options(streamlit_options)

    bootstrap.run(
        str(app_path),
        False,
        [],
        streamlit_options,
    )
    return 0


def wait_for_server(url: str, process: subprocess.Popen[bytes], timeout: float = 45.0) -> None:
    """Wait until Streamlit accepts connections or the child exits."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError(f"The Streamlit server exited with code {process.returncode}.")
        try:
            with urlopen(url, timeout=1.5):
                return
        except (OSError, URLError):
            time.sleep(0.25)
    raise TimeoutError(f"Timed out while starting the dashboard at {url}.")


def start_child(app_path: Path, port: int, data_root: Path) -> subprocess.Popen[bytes]:
    """Start the Streamlit child, hiding its console in a Windows build."""
    if getattr(sys, "frozen", False):
        command = [sys.executable, "--streamlit-child", "--port", str(port), "--data-dir", str(data_root)]
    else:
        command = [sys.executable, str(Path(__file__).resolve()), "--streamlit-child", "--port", str(port), "--data-dir", str(data_root)]
    creation_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    return subprocess.Popen(
        command,
        cwd=resource_root(),
        env={**os.environ, "PYTHERMOGIS_DATA_ROOT": str(data_root)},
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=creation_flags,
    )


def desktop_main(port: int, data_root: Path) -> int:
    """Start the local server and show it in a native browser window."""
    try:
        import webview
    except ModuleNotFoundError:
        print("The desktop dependencies are missing. Run: uv sync --extra desktop")
        return 1

    app_path = resource_root() / "dashboard" / "app.py"
    if not app_path.exists():
        print(f"Bundled dashboard entry point not found: {app_path}")
        return 1

    prepare_data_root(data_root)
    selected_port = choose_port(port)
    url = f"http://127.0.0.1:{selected_port}"
    child = start_child(app_path, selected_port, data_root)
    try:
        wait_for_server(url, child)
        window = webview.create_window(
            APP_TITLE,
            url,
            width=1500,
            height=950,
            min_size=(1050, 700),
            text_select=True,
        )

        def stop_child() -> None:
            if child.poll() is None:
                child.terminate()
                try:
                    child.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    child.kill()

        window.events.closed += stop_child
        try:
            webview.start(gui="edgechromium", debug=False)
        except Exception as exc:
            print(f"Embedded WebView2 could not start: {exc}")
            print(f"Open this local dashboard in a browser instead: {url}")
            import webbrowser

            webbrowser.open(url)
            while child.poll() is None:
                time.sleep(0.5)
    finally:
        if child.poll() is None:
            child.terminate()
            try:
                child.wait(timeout=5)
            except subprocess.TimeoutExpired:
                child.kill()
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Start the Pythermogis dashboard desktop app.")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--data-dir", type=Path, default=None)
    parser.add_argument("--streamlit-child", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    data_root = (args.data_dir or default_data_root()).expanduser().resolve()
    if args.streamlit_child:
        return streamlit_child(resource_root() / "dashboard" / "app.py", args.port, data_root)
    return desktop_main(args.port, data_root)


if __name__ == "__main__":
    raise SystemExit(main())
