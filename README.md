# Pythermogis Dashboard

![GO-Forward project logo](dashboard/GO-Forward.png)

A project-based Streamlit dashboard for preparing geological inputs, configuring
Pythermogis doublet calculations, running deterministic or probabilistic
simulations, and inspecting spatial and location-specific results.

> **Important**
>
> This repository contains the dashboard integration code. Pythermogis and its
> ThermoGIS Java backend remain separate dependencies and retain their own
> licensing and disclaimer terms. Review the
> [Pythermogis documentation](https://pythermogis-15909e.ci.tno.nl/) and the
> [ThermoGIS disclaimer](https://www.thermogis.nl/en/disclaimer) before use.

## Folder structure

The repository keeps the Streamlit application in a dedicated `dashboard`
folder, with its starters and project data at the root:

```text
pythermogis-dashboard/
├─ install_dashboard.py
├─ run_dashboard.py
├─ pyproject.toml
├─ uv.lock
├─ dashboard/
│  ├─ app.py
│  ├─ GO-Forward.png
│  └─ src/workflow.py
├─ data/                  # local project inputs and outputs; ignored by Git
├─ docs/
└─ .venv/                 # created by UV; ignored by Git
```

There is no separate Pythermogis source folder required beside the dashboard.
UV installs the released `pythermogis`, `pygridsio`, and `pygridsio3d` packages
inside `.venv`. The `.venv` folder is machine-generated and never committed.

## Install and run

### 1. Install UV once

On Windows:

```powershell
winget install --id astral-sh.uv -e
```

Close and reopen the terminal if the `uv` command is not immediately available.

### 2. Clone and install the dashboard

These commands work from any parent directory:

```powershell
git clone https://github.com/floriansmit/pythermogis-dashboard.git
cd pythermogis-dashboard
python install_dashboard.py
```

The root-level installer runs `uv sync --locked --system-certs`, which:

- installs the correct Python version when needed;
- creates `.venv` in the dashboard folder;
- installs the exact versions recorded in `uv.lock`;
- installs Pythermogis 3.0.3 from TNO's package registry;
- installs the grid and GRDECL libraries from their package registries.

Do not activate the environment manually. The equivalent direct UV command is:

```powershell
uv sync --locked --system-certs
```

### 3. Start the dashboard

```powershell
python run_dashboard.py
```

Open <http://localhost:8502>. To use another port:

```powershell
python run_dashboard.py --port 8503
```

## Dashboard workflow

1. Create or open a project in the sidebar.
2. Select deterministic/probabilistic 2D grids, one GRDECL, or multiple GRDECLs.
3. Import and inspect the required files in **Geology input**.
4. Optionally resample, preview, and validate the simulation grid.
5. Apply settings in **Well design**, **Cost model**, and **Economic model**.
6. Name and run the calculation in **Geothermal simulation**.
7. Open the saved NetCDF file in **Geothermal results**.

## Data layout

Each project is isolated under the local `data` directory:

```text
data/<project>/
├─ input_data/
│  ├─ 2d_grid_best_fit/
│  ├─ 2d_grid_probabilistic/
│  ├─ 3d_grdecl_best_fit/
│  └─ 3d_grdecl_multi_realization/
└─ output_data/
   ├─ 2d_grid_best_fit/
   ├─ 2d_grid_probabilistic/
   ├─ 3d_grdecl_best_fit/
   └─ 3d_grdecl_multi_realization/
```

The contents of `data` are ignored by Git because geological models and results
can be large or confidential. Back up project data separately when required.

## Geology dependencies

The dashboard uses installed packages, not neighboring source folders:

| Package | Dashboard use |
|---|---|
| `pythermogis` | Aquifer objects, model settings, Java-backed doublet simulation |
| `pygridsio` | Reading/writing grids and resampling |
| `pygridsio3d` | Reading and converting GRDECL models |

GRDECL inspection and conversion are implemented through `pygridsio3d` in
`dashboard/src/workflow.py`.

See [Dependency architecture](docs/DEPENDENCIES.md) for the exact boundary.

## Updating dependencies

Normal users should retain the lockfile and run:

```powershell
uv sync --locked
```

Maintainers can intentionally refresh allowed versions with:

```powershell
uv lock --upgrade
uv sync
```

Review and commit both `pyproject.toml` and `uv.lock` when dependencies change.

## Verification

```powershell
uv run python -m py_compile dashboard/app.py dashboard/src/workflow.py install_dashboard.py run_dashboard.py
uv run python -c "import pythermogis, pygridsio, pygridsio3d; print('Dependencies available')"
```

The first actual calculation may install/start Java 17 and take longer than
subsequent runs. The simulation tab reports Java startup and cell/chunk progress.

## Scope

This is a research decision-support interface for indicative geothermal
assessment. It is not a substitute for site-specific reservoir engineering,
well design, cost estimation, permitting, or investment due diligence.
