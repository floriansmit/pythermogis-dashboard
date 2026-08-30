# Dependency architecture

## What lives in this repository

The repository contains dashboard-owned material only:

- Streamlit interface in `dashboard/app.py`;
- reusable workflow functions in `dashboard/src/workflow.py`;
- UV project metadata and lockfile;
- configuration, documentation, and the transparent GO-Forward logo;
- compact, non-confidential demo inputs; and
- a local `data` workspace whose non-demo inputs and all outputs are ignored.

## What UV installs

Running `python install_dashboard.py` creates `.venv` through UV. The installer
and runner live in the repository root, like the GeoDecision launch scripts.

### Pythermogis

The dashboard imports `Aquifer`, `StochasticAquifer`, `ThermoGISDoublet`, and
`UTCSettings`. Version 3.0.3 comes from TNO's Python package registry. Its Python
files and ThermoGIS JAR are stored under `.venv`, not as a visible source
checkout in the repository.

### pygridsio

The installed `pygridsio==1.1.4` package supplies 2D grid reading, writing, and
resampling functions.

### pygridsio3d

The installed `pygridsio3d` package supplies the GRDECL reader and `Grid3dFunc`
operations used for inspection and conversion.

The dashboard does not import code directly from historical neighbouring source
directories. Those folders are not required for a clone to run.

## Why `.venv` is not source code

`.venv` is UV's generated runtime environment. It contains third-party packages,
entry points, native libraries, and the Java backend. It can be deleted and
recreated from `pyproject.toml` and `uv.lock` with `uv sync --locked`. It is
ignored by Git and is never uploaded to GitHub.

## Locked runtime

The project currently targets Python `>=3.13,<3.14`. Direct constraints are in
`pyproject.toml`; `uv.lock` records the complete resolved environment.

| Dependency | Purpose |
|---|---|
| `streamlit` | Dashboard UI and session state |
| `pythermogis==3.0.3` | Aquifer models and ThermoGIS/DoubletCalc simulation bridge |
| `pygridsio==1.1.4` | 2D grid reading, writing, and resampling |
| `pygridsio3d` | GRDECL reading, inspection, and aggregation |
| `xarray`, `netcdf4`, `dask` | Labelled datasets, persistence, and array handling |
| `numpy`, `pandas` | Numerical and tabular transformations |
| `matplotlib`, `plotly` | Static and interactive viewers |
| `geopandas`, `pyproj`, `rioxarray` | Boundaries, CRS handling, and georeferencing |
| `geopy` | Optional address geocoding for location analysis |
| `jpype1`, `install-jdk` | Java bridge and Java 17 provisioning |

Do not install these packages one by one. Use the locked setup:

```powershell
python install_dashboard.py
```

The installer uses `--system-certs`, which helps on managed networks with a
corporate certificate store. Manual environment activation is unnecessary.

For an intentional dependency refresh, a maintainer should run:

```powershell
uv lock --upgrade
uv sync
```

Test the dashboard and commit both `pyproject.toml` and `uv.lock`.

## Licensing boundary

This repository's license does not replace the terms of separately installed
packages or the ThermoGIS Java backend. Review the
[Pythermogis documentation](https://pythermogis-15909e.ci.tno.nl/) and
[ThermoGIS disclaimer](https://www.thermogis.nl/en/disclaimer) before use or
redistribution.
