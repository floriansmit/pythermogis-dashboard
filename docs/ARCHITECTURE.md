# Architecture

## Repository layout

```text
pythermogis-dashboard/
├─ install_dashboard.py      # runs the locked UV installation
├─ run_dashboard.py          # starts Streamlit through UV
├─ pyproject.toml            # direct dependency constraints
├─ uv.lock                   # exact cross-platform resolution
├─ dashboard/
│  ├─ app.py                 # Streamlit state and presentation
│  └─ src/workflow.py        # data preparation and simulation helpers
├─ data/                     # local project data; ignored by Git
└─ docs/
```

## Runtime flow

```text
external files
    → typed project input folder
    → detected or GRDECL-derived xarray Dataset
    → optional resampling preview
    → validated Dataset
    → Aquifer or StochasticAquifer
    → ThermoGISDoublet Java-backed simulation
    → named NetCDF result
    → maps and location-level analysis
```

## Environment boundary

UV creates `.venv` at the repository root. Pythermogis, pygridsio,
pygridsio3d, Python entry points, native libraries, and the ThermoGIS JAR all
live there. The environment is generated from `pyproject.toml` and `uv.lock` and
is ignored by Git.

The application does not alter `sys.path` to load neighboring source checkouts.
This keeps execution reproducible and prevents an unrelated local source folder
from silently overriding the locked package versions.

## State boundaries

The UI keeps these concepts separate:

- selected raw geology;
- optional resampling preview;
- validated simulation grid;
- staged and applied model settings;
- latest result dataset;
- active project and geology mode.

Only the validated grid and applied settings are passed to a simulation.
