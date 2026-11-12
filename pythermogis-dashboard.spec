# PyInstaller one-folder build for the Windows desktop launcher.
from pathlib import Path

from PyInstaller.utils.hooks import collect_all, collect_submodules


ROOT = Path(SPECPATH)

datas = [
    (str(ROOT / "dashboard"), "dashboard"),
    (str(ROOT / "data" / "demo-project"), "data/demo-project"),
]
binaries = []
hiddenimports = []

for package in (
    "pythermogis",
    "pygridsio",
    "pygridsio3d",
    "streamlit",
    "webview",
):
    try:
        package_datas, package_binaries, package_hiddenimports = collect_all(package)
    except Exception:
        package_datas, package_binaries, package_hiddenimports = [], [], collect_submodules(package)
    datas += package_datas
    binaries += package_binaries
    hiddenimports += package_hiddenimports

hiddenimports += [
    "dashboard.src.workflow",
    "jpype",
    "matplotlib.backends.backend_agg",
]

a = Analysis(
    [str(ROOT / "desktop_launcher.py")],
    pathex=[str(ROOT)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    [],
    name="PythermogisDashboard",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    exclude_binaries=True,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="PythermogisDashboard",
)
