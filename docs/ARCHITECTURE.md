# Architecture

## Runtime components

```text
Streamlit UI (dashboard/app.py)
        │
        ├─ project, file, grid, GRDECL and simulation orchestration
        │  (dashboard/src/workflow.py)
        │
        ├─ pygridsio / pygridsio3d
        │  grid reading, writing, resampling and GRDECL conversion
        │
        └─ Pythermogis Python API
                  │
                  └─ ThermoGIS Java backend through JPype / Java 17
```

`app.py` owns Streamlit state and presentation. `workflow.py` contains filesystem,
geology conversion, xarray preparation, resampling, and model-execution helpers.

## Data flow

```text
external files
    → typed project input folder
    → detected/converted xarray Dataset
    → optional resampling preview
    → validated Dataset in session state
    → Aquifer or StochasticAquifer
    → ThermoGISDoublet simulation
    → named NetCDF in typed project output folder
    → result maps and location analysis
```

GRDECL-derived 2D maps remain below their GRDECL output type and are not
auto-selected as traditional 2D inputs.

## State model

The application distinguishes the raw selected dataset, optional resampled
preview, validated simulation dataset, staged/applied settings, latest results,
active project, and geology type. Settings forms stage multiple edits and replace
the applied configuration only after **Apply settings**.

## Local source preference

`install_dashboard.py` supports either of these relative layouts:

```text
workspace/pythermogis/dashboard/
```

or:

```text
workspace/
├─ pythermogis/
└─ pythermogis_dashboard/
```

It first checks the repository containing the dashboard and then an adjacent
`pythermogis` checkout. A detected source is installed in editable mode. If none
is present, Pythermogis 3.0.3 is installed from TNO's package registry.
`pygridsio==1.1.4` and `pygridsio3d` are pinned for repeatable grid behaviour.

## Version-control boundary

Git tracks application code, configuration, documentation, and the logo. It
excludes project data/results, geoscience artifacts, virtual environments,
credentials, non-public GO-Forward packages, the separate Pythermogis checkout,
and the ThermoGIS JAR. This keeps the repository small and reduces the risk of
publishing licensed, confidential, or machine-specific material.
