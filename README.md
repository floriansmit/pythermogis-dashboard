# Pythermogis Dashboard

![GO-Forward project logo](dashboard/GO-Forward-transparent.png)

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

## License

The original dashboard source code and documentation in this repository are
open-source software licensed under the [MIT License](LICENSE). You may use,
study, modify, merge, publish, distribute, sublicense, and sell copies of the
covered dashboard code, subject to the copyright and license notice requirements
in that license. Contributions accepted into this repository are licensed under
the same terms; see [CONTRIBUTING.md](CONTRIBUTING.md).

The MIT License does not relicense separately distributed dependencies or
third-party materials. In particular, Pythermogis, the ThermoGIS Java backend,
third-party packages, names, logos, and externally sourced data retain their own
copyright, license, and disclaimer terms.

## Repository layout

```text
pythermogis-dashboard/
├─ install_dashboard.py
├─ run_dashboard.py
├─ pyproject.toml
├─ uv.lock
├─ dashboard/
│  ├─ app.py
│  ├─ GO-Forward-transparent.png
│  └─ src/workflow.py
├─ data/
│  └─ demo-project/       # compact example inputs committed for evaluation
├─ docs/
└─ .venv/                 # created by UV; ignored by Git
```

There is no separate Pythermogis source folder required beside the dashboard.
UV installs the released `pythermogis`, `pygridsio`, and `pygridsio3d` packages
inside `.venv`. The environment is machine-generated and never committed.

## Install and run

### 1. Install UV once

On Windows:

```powershell
winget install --id astral-sh.uv -e
```

Close and reopen the terminal if `uv` is not immediately available.

### 2. Clone and install

These commands work from any parent directory:

```powershell
git clone https://github.com/floriansmit/pythermogis-dashboard.git
cd pythermogis-dashboard
python install_dashboard.py
```

The root installer runs `uv sync --locked --system-certs`. It installs the
required Python version when needed, creates `.venv`, and installs the exact
versions in `uv.lock`, including Pythermogis 3.0.3 from TNO's registry. Manual
environment activation is not required.

The equivalent direct command is:

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

1. Create or open a project in the sidebar, or use the included `demo-project`.
2. In **Geology**, select deterministic/probabilistic classic 2D grids, one
   best-fit GRDECL, or multiple GRDECL scenarios.
3. Import, inspect, and map the required properties. GRDECL workflows expose
   editable facies definitions and map, section, 3D, and table viewers.
4. Optionally resample the grids, compare original and preview side by side, and
   validate the version that should be passed to Pythermogis.
5. Choose the Netherlands or Denmark screening preset in the sidebar. Stage
   project-specific changes in **Well design**, **Costs**, and **Economics**,
   then use each section's **Apply settings** button. The Costs tab also exposes
   direct-heat/heat-pump conversion settings. The interface shows units,
   explanations, suggested country ranges, sources, and deviations.
6. In **Simulation**, choose a unique result name and run the deterministic or
   requested-percentile calculation. The NetCDF is saved automatically.
7. In **Results**, open a project or external NetCDF, inspect result definitions,
   maps, statistics, percentiles, and location analysis, or export ZMAP grids.
8. New results embed validated inputs and applied settings. Use **Restore
   simulation setup from this result** to return the other tabs to that state.

## Project data layout

```text
data/<project>/
├─ input_data/
│  ├─ 2d_grid_best_fit/
│  ├─ 2d_grid_probabilistic/
│  ├─ 3d_grdecl_best_fit/
│  ├─ 3d_grdecl_multi_realization/
│  └─ boundaries/
└─ output_data/
   ├─ 2d_grid_best_fit/
   ├─ 2d_grid_probabilistic/
   ├─ 3d_grdecl_best_fit/
   └─ 3d_grdecl_multi_realization/
```

Normal project contents and all generated outputs are ignored by Git because
geological models and results can be large or confidential. The repository makes
one deliberate exception for compact inputs under `data/demo-project/input_data`:

- 2.5 km deterministic and probabilistic Gassum ZMAP grids;
- one reduced best-fit GRDECL with `FACIES`, `PORO50`, and `PERM50`;
- five reduced multi-scenario GRDECL files with facies-based porosity and
  permeability values;
- editable facies-definition JSON files; and
- a Danish coastline shapefile for boundary-overlay testing.

The demo project's generated outputs remain ignored. Back up all local project
data separately when required.

## Result provenance and ZMAP export

Each new NetCDF result stores dashboard provenance: validated simulation grids,
field mapping, geology-source mode, applied well/cost/economic settings,
temperature assumptions, project, and requested percentiles. Older or external
NetCDF files remain viewable but can restore only information they contain.

**Export ZMAP grids** writes supported rectilinear result slices and embedded
validated inputs to a sibling folder named `<result-stem>_Zmap`. Probabilistic
outputs are separated into files labelled with their actual percentile, such as
`P10`, `P50`, and `P90`. Unsupported geometry and non-2D variables are reported
as skipped.

## Installed geology dependencies

| Package | Dashboard use |
|---|---|
| `pythermogis` | Aquifer objects, settings, and Java-backed doublet simulation |
| `pygridsio` | Reading/writing 2D grids and resampling |
| `pygridsio3d` | Reading, inspecting, and aggregating GRDECL models |

The dashboard uses installed packages, not neighbouring source directories. See
[Dependency architecture](docs/DEPENDENCIES.md) for the exact boundary.

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
uv run --locked python -m compileall -q dashboard
uv run --locked python -c "import pythermogis, pygridsio, pygridsio3d; print('Dependencies available')"
```

The first calculation may install/start Java 17 and take longer than subsequent
runs. The Simulation tab reports Java startup and cell/chunk progress.

## Scope

This is a research decision-support interface for indicative geothermal
assessment. It is not a substitute for site-specific reservoir engineering,
well design, cost estimation, permitting, or investment due diligence.

## Documentation

- [User guide](docs/USER_GUIDE.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Dependency architecture](docs/DEPENDENCIES.md)
- [License](LICENSE)
- [Contributing](CONTRIBUTING.md)
