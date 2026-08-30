# Architecture

## Repository layout

```text
pythermogis-dashboard/
├─ install_dashboard.py            # runs the locked UV installation
├─ run_dashboard.py                # starts Streamlit through UV
├─ pyproject.toml                  # direct dependency constraints
├─ uv.lock                         # exact cross-platform resolution
├─ dashboard/
│  ├─ app.py                       # Streamlit state and presentation
│  ├─ GO-Forward-transparent.png   # sidebar brand asset
│  └─ src/workflow.py              # preparation, simulation, and export helpers
├─ data/
│  └─ demo-project/input_data/     # intentionally committed compact examples
└─ docs/
```

Normal project data and every `output_data` folder are ignored by Git. Only the
explicit demo input paths listed in `.gitignore` are versioned.

## Runtime flow

```text
external files
    → typed project input folder
    → detected 2D grids or GRDECL-derived xarray Dataset
    → property/unit normalization and boundary overlay
    → optional resampling preview
    → validated Dataset
    → Aquifer or StochasticAquifer
    → ThermoGISDoublet Java-backed simulation
    → named, provenance-bearing NetCDF result
    → maps, statistics, location analysis, setup restoration, or ZMAP export
```

## Geology-source boundary

Four UI choices map directly to typed input/output pairs:

| UI source | Internal key | Input folder | Output folder |
|---|---|---|---|
| Classic 2D Grids — Deterministic | `2d_best_fit` | `input_data/2d_grid_best_fit` | `output_data/2d_grid_best_fit` |
| Classic 2D Grids — Probabilistic | `2d_probabilistic` | `input_data/2d_grid_probabilistic` | `output_data/2d_grid_probabilistic` |
| Best-fit Model 3D GRDECL → Deterministic 2D Maps | `grdecl_best_fit` | `input_data/3d_grdecl_best_fit` | `output_data/3d_grdecl_best_fit` |
| Multi-Scenario 3D GRDECLs → Probabilistic 2D Maps | `grdecl_multi` | `input_data/3d_grdecl_multi_realization` | `output_data/3d_grdecl_multi_realization` |

Generated GRDECL-derived maps are stored below the matching output folder, so
they cannot be confused with unrelated classic 2D inputs.

## Environment boundary

UV creates `.venv` at the repository root. Pythermogis, pygridsio,
pygridsio3d, Python entry points, native libraries, and the ThermoGIS JAR all
live there. The environment is generated from `pyproject.toml` and `uv.lock` and
is ignored by Git.

The application does not load neighbouring source checkouts. This keeps
execution reproducible and prevents an unrelated local source folder from
silently overriding the locked package versions. The only local import-path
addition is the dashboard-owned `dashboard/src` helper directory.

## State boundaries

The UI keeps these concepts separate:

- selected raw geology;
- optional resampling preview;
- validated simulation grid;
- staged and applied model settings;
- latest/open result dataset;
- active project and geology source.

Only the validated grid and applied settings are passed to a simulation. The
sticky tab bar is presentation state only and does not alter calculation state.

## Result provenance

Before saving, the workflow copies validated geology variables into the result
dataset with the reserved `dashboard_input__` prefix and serializes exposed
dashboard settings and field mapping into NetCDF attributes. Source-folder key,
project name, and requested percentiles are also recorded.

Restoration reads only this explicit provenance. An older result without these
fields can still be inspected, downloaded, and exported, but the dashboard does
not infer missing settings.

## Export boundary

ZMAP export is intentionally limited to rectilinear two-dimensional slices.
Dimensions such as `p_value` are expanded into separately labelled files. The
exporter writes embedded validated inputs when available and returns a report of
skipped variables rather than silently flattening unsupported geometry.
