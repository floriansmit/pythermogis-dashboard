# User guide

## Projects

Create or select a project in the sidebar. Each project receives typed input and
output directories under `data/<project>`. Imported files are copied into the
matching input directory; generated maps and NetCDF results are written to the
matching output directory.

The repository includes a `demo-project` containing compact examples for every
geology source plus a Danish boundary. Other project inputs and all outputs are
ignored by Git and must be backed up separately when required. Importing data
copies selected external files into the project, so calculations do not depend
on the original external path.

## Geology sources

The Geology tab first selects one of four sources. Each source uses an isolated
input and output folder to avoid mixing classic maps with GRDECL-derived maps.

### Classic 2D Grids — Deterministic

Required properties are reservoir depth/top, thickness, net-to-gross, porosity,
and permeability. Temperature is optional because it can be calculated from a
surface temperature and geothermal gradient. Transmissivity can replace
permeability where the deterministic backend mapping supports it.

### Classic 2D Grids — Probabilistic

Thickness and permeability standard deviations are added to the deterministic
inputs. Missing SD maps can be generated as:

- a constant absolute SD;
- a percentage of each local mean value; or
- a percentage of the spatial mean, producing a constant map.

Use local percentages when uncertainty should scale with local reservoir
magnitude. Use a constant when an interpreted or measured absolute uncertainty
applies everywhere.

The detected-file table reports finite minimum, maximum, and mean values before
conversion. Porosity can be kept as a fraction or converted from percent.
Permeability controls distinguish arithmetic mD mean/SD from values already in
`ln(mD)`. Arithmetic mean and SD are converted to lognormal parameters as:

```text
sigma_ln² = ln(1 + (SD / mean)²)
mu_ln     = ln(mean) - 0.5 sigma_ln²
```

The dashboard suggests conversion when statistics resemble mD rather than
logarithmic values, but the user retains control.

### Best-fit Model 3D GRDECL → Deterministic 2D Maps

One GRDECL produces deterministic 2D property maps.

### Multi-Scenario 3D GRDECLs → Probabilistic 2D Maps

Multiple GRDECL scenarios produce mean and standard-deviation maps.

For both GRDECL modes, inspect properties and facies before conversion. An
optional `facies_config.json` supplies editable facies names, reservoir flags,
and colours. Viewer modes include map, I/J cross-sections, 3D, and data table.
Select one or more reservoir facies during conversion. Porosity and permeability
should use GRDECL properties when available; fallback constants are enabled only
when no usable property is selected.

Generated ZMAPs are written beneath the matching typed `output_data` folder,
which prevents them from being mistaken for classic 2D inputs.

## Boundary, viewers, and grid validation

Upload all shapefile components together (`.shp`, `.shx`, `.dbf`, `.prj`, and
`.cpg` where present). When CRS metadata is unavailable for legacy Danish ZMAPs,
the configured fallback is ED50 / UTM zone 32N (`EPSG:23032`). Undefined
sentinels such as `-7777` are excluded from map scaling and statistics. Depth
colour scales are reversed, and map axes use an equal spatial aspect ratio.

The selected boundary is drawn on original/resampled geology maps and result
maps when its CRS can be reconciled with the grid.

Resampling is optional. The original viewer stays on the left and the resampled
preview appears on the right when enabled. Preset target cell sizes are 400,
500, 1,000, 2,500, 5,000, and 10,000 m, with a custom-size option. The viewer
reports recognized cell dimensions, grid shape, total cells, and active cells.

The single validation button uses the original grid when resampling is off and
the resampled preview when it is on. Validation clearly states which version
became the simulation input.

## Model settings

Well, cost, economic, and calculated-temperature values are staged in forms, so
editing a field does not immediately change the active calculation setup. Change
several values and then choose **Apply settings**. Orange labels identify
deviations from defaults; each field has a return-to-default control.

Labels include units and expanded explanations. These cover producer–injector
distance optimization, wellbore and pump assumptions, the well-cost polynomial,
CAPEX/OPEX terms, and discounted economic assumptions.

## Simulation

Validate geology, choose a unique output filename, and run the calculation. If
the name exists, choose another name or explicitly enable overwrite. The status
reports Java startup and cell/chunk progress.

Probabilistic runs offer P1, P5, P10, P25, P50, P75, P90, P95, and P99;
P10/P50/P90 are selected initially. Detailed progress can be grouped by a chosen
number of grid rows per update. The result NetCDF is saved automatically under
the output folder matching the active geology source.

New results embed the validated input grids and active dashboard configuration.
This makes the result self-describing and enables setup restoration later.

## Results

Open a saved project result or upload an external NetCDF. Result maps show a
descriptive label and unit rather than only the backend variable name. For
probabilistic outputs, the selector and map title show the actual P-value, such
as P10, P50, or P90. The information panel explains the calculation, formula
terms, units, relevant result variables, and stored applied settings where
available.

Location analysis accepts a selected map point, explicit X/Y coordinates, or an
address. It plots NPV versus P-value and reports probability of success at the
nearest grid cell.

Use **Restore simulation setup from this result** to restore validated geology,
mapping, geology-source mode, and applied well/cost/economic/temperature
settings. Older results without embedded provenance remain viewable but cannot
fully reconstruct the previous state.

Use **Export ZMAP grids** beside the project-result selector to create
`<result-stem>_Zmap` beside the NetCDF. Supported result maps and embedded input
grids are exported; probabilistic slices are named with their actual percentile.
Unsupported non-2D or curvilinear variables are reported rather than discarded
silently.

## Troubleshooting

### UV is not installed

```powershell
winget install --id astral-sh.uv -e
```

Restart the terminal, then run `python install_dashboard.py` again.

### Corporate certificate error

The root installer enables UV's operating-system certificate store. The direct
equivalent is:

```powershell
uv sync --locked --system-certs
```

### PowerShell blocks environment activation

Activation is not needed. Use the Python starters:

```powershell
python install_dashboard.py
python run_dashboard.py
```

### Computation is too large

Inspect active cell count and validate a coarser grid before running. Computation
time scales strongly with cell count and probabilistic samples.

### The header or logo still shows an old style

After updating the repository, restart `python run_dashboard.py` and use
`Ctrl+F5` once to clear cached CSS/image assets. The tab bar remains sticky below
the Streamlit toolbar, and the GO-Forward logo is displayed in the sidebar with
a transparent background.

### A result cannot restore the setup

Only results containing dashboard provenance can restore the full state. Older
or external results can still be viewed and exported; configure and validate
their inputs manually if a rerun is required.
