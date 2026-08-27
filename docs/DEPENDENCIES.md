# Dependency architecture

## What lives in this repository

The repository contains only dashboard-owned material:

- Streamlit interface in `dashboard/app.py`;
- reusable workflow functions in `dashboard/src/workflow.py`;
- UV project metadata and lockfile;
- configuration, documentation, logo, and facies colours;
- a local, Git-ignored `data` directory for project input and output.

## What UV installs

Running `python install_dashboard.py` creates `.venv` through UV and installs the
following packages. Both installer and runner live in the repository root, like
the GeoDecision launch scripts.

### Pythermogis

The dashboard imports `Aquifer`, `StochasticAquifer`, `ThermoGISDoublet`, and
`UTCSettings`. Version 3.0.3 comes from TNO's Python package registry. Its Python
files and ThermoGIS JAR are stored under `.venv`, not as a visible source
checkout in the repository.

### pygridsio

The dashboard imports grid reading, writing, and resampling functions from the
installed `pygridsio==1.1.4` package.

### pygridsio3d

The installed `pygridsio3d` package supplies the GRDECL reader and `Grid3dFunc`
operations used for inspection and conversion.

All runtime dependencies are installed from package registries into `.venv`.
This lets a user clone one repository, run the installer, and start the
dashboard without arranging additional source trees.

## Why `.venv` is not source code

`.venv` is UV's generated runtime environment. It contains third-party packages,
entry points, and native libraries. It can be deleted and recreated from
`pyproject.toml` and `uv.lock` with `uv sync --locked`. Because `.venv` is listed
in `.gitignore`, it is never uploaded to GitHub.
