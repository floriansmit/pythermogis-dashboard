# Pythermogis Dashboard

![GO-Forward project logo](dashboard/GO-Forward.png)

A project-based Streamlit interface for preparing geological input, configuring
Pythermogis doublet calculations, running deterministic or probabilistic
simulations, and exploring spatial and location-specific results.

The dashboard was developed in the GO-Forward workflow. It makes the calculation
chain visible: geology selection and validation, well design, cost assumptions,
economic assumptions, simulation progress, and result interpretation are kept in
separate tabs rather than hidden behind one run button.

> [!IMPORTANT]
> This repository contains the dashboard integration code. Pythermogis and its
> ThermoGIS Java backend remain separate dependencies and retain their own
> licensing and disclaimer terms. Review the
> [Pythermogis documentation](https://pythermogis-15909e.ci.tno.nl/) and the
> [ThermoGIS disclaimer](https://www.thermogis.nl/en/disclaimer) before use.

## What is included

- Project creator and selector with isolated input and output directories.
- Deterministic and probabilistic 2D-grid input.
- Single-GRDECL conversion to deterministic 2D maps.
- Multiple-GRDECL conversion to probabilistic 2D statistics.
- Editable facies definitions and GRDECL inspection before conversion.
- 2D map and histogram viewers with boundary overlays and grid statistics.
- Optional grid resampling and explicit validation of the simulation grid.
- Explained well, cost, and economic settings with staged **Apply settings**
  forms and per-field default restoration.
- Simulation progress reporting, named NetCDF output, result loading, spatial
  maps, and point-level NPV/probability-of-success analysis.

## Quick start on Windows

Requirements:

- Python 3.13
- Internet access during first installation
- Approximately 500 MB free for Pythermogis and its Java 17 runtime

```powershell
git clone https://github.com/floriansmit/pythermogis_dashboard.git
cd pythermogis_dashboard\dashboard
python install_dashboard.py
python run_dashboard.py
```

Open <http://localhost:8502>. Port 8502 is used so another Streamlit application
can remain on the default port 8501.

Use another port when needed:

```powershell
python run_dashboard.py --port 8503
```

The installer creates a machine-local environment at
`%LOCALAPPDATA%\pythermogis-dashboard\.venv`. It does not place thousands of
environment files in the repository or in OneDrive.

### Use the source checkout from `C:\GGS`

When these sibling directories exist, the installer automatically uses the
local source checkout in editable mode:

```text
C:\GGS
├─ pythermogis\
└─ pythermogis_dashboard\
```

You can also specify it explicitly:

```powershell
python install_dashboard.py --source-root C:\GGS\pythermogis
```

If no local source checkout is found, the installer installs Pythermogis 3.0.3
from TNO's package registry. This makes the GitHub checkout usable without
copying the separate Pythermogis source into this repository.

## Typical workflow

1. Create or open a project in the sidebar.
2. In **Geology input**, select one of the four input modes.
3. Import only the required files into the typed project input folder.
4. Inspect statistics, maps, histograms, facies, and the optional boundary.
5. Optionally preview a coarser resolution, then validate the original or
   resampled dataset.
6. Review and apply settings in **Well design**, **Cost model**, and
   **Economic model**.
7. Choose a unique result name in **Geothermal simulation**, then run.
8. Open the saved NetCDF file in **Geothermal results** and inspect maps or a
   selected location.

See [User guide](docs/USER_GUIDE.md) for input requirements, uncertainty rules,
and tab-by-tab guidance. See [Architecture](docs/ARCHITECTURE.md) for the code and
data layout.

## Repository layout

```text
pythermogis_dashboard/
├─ dashboard/
│  ├─ app.py
│  ├─ src/workflow.py
│  ├─ install_dashboard.py
│  ├─ run_dashboard.py
│  ├─ requirements.txt
│  └─ .streamlit/config.toml
├─ data/                  # local project data; ignored by Git
├─ docs/
└─ README.md
```

Large input grids, GRDECL files, shapefiles, NetCDF results, virtual environments,
and credentials are intentionally excluded from version control.

## Verification

For a lightweight source check:

```powershell
python -m py_compile dashboard\app.py dashboard\src\workflow.py `
  dashboard\install_dashboard.py dashboard\run_dashboard.py
```

The first real calculation can take longer because Pythermogis may install and
start Java 17. The simulation tab reports Java startup and cell/chunk progress.

## Status and scope

This is a research decision-support interface for indicative geothermal
assessment. It is not a substitute for site-specific reservoir engineering,
well design, cost estimation, permitting, or investment due diligence.
