# User guide

## Projects

Create or select a project in the sidebar. Each project receives typed input and
output directories under `data/<project>`. Imported files are copied into the
matching input directory; generated maps and NetCDF results are written to the
matching output directory.

Project data is ignored by Git and must be backed up separately when required.

## Geology modes

### Deterministic 2D grids

Required properties are reservoir depth/top, thickness, net-to-gross, porosity,
and permeability. Temperature is optional because it can be calculated from a
surface temperature and geothermal gradient.

### Probabilistic 2D grids

Thickness and permeability standard deviations are added to the deterministic
inputs. Missing SD maps can be generated as:

- a constant absolute SD;
- a percentage of each local mean value;
- a percentage of the spatial mean, producing a constant map.

Use local percentages when uncertainty should scale with local reservoir
magnitude. Use a constant when an interpreted or measured absolute uncertainty
applies everywhere. Inspect permeability statistics before selecting raw mD or
already-logarithmic input.

### GRDECL input

One GRDECL produces deterministic 2D maps. Multiple GRDECL realizations produce
probabilistic statistics. Inspect properties and facies first, optionally load a
facies-definition JSON, select all reservoir facies, and map porosity and
permeability properties. Fallback constants are available only when a property
is absent.

## Boundary and grid validation

Upload all shapefile components together. When CRS metadata is unavailable for
legacy Danish ZMAPs, the configured fallback is ED50 / UTM zone 32N
(`EPSG:23032`). Undefined sentinels such as `-7777` are excluded from map scaling
and statistics.

Resampling is optional. The original viewer stays on the left and the resampled
preview appears on the right when enabled. The single validation button uses the
original grid when resampling is off and the resampled grid when it is on.

## Model settings

Well, cost, economic, and calculated-temperature values are staged in forms.
Change several values and then choose **Apply settings**. Orange labels identify
deviations from model defaults; the return control restores a field default.

## Simulation and results

Validate geology, choose a unique output filename, and run the calculation. The
status reports Java startup and cell/chunk progress. The result NetCDF is saved
under the active project.

Open a saved or uploaded NetCDF in the results tab. Inspect maps and statistics,
or select coordinates/an address for NPV-versus-p-value and
probability-of-success analysis.

## Troubleshooting

### UV is not installed

```powershell
winget install --id astral-sh.uv -e
```

Restart the terminal, then run `python install_dashboard.py` again.

### Corporate certificate error

The root installer already enables UV's operating-system certificate store. The
equivalent direct command is:

```powershell
uv sync --locked --system-certs
```

### PowerShell blocks environment activation

Activation is not needed. Use the root scripts:

```powershell
python install_dashboard.py
python run_dashboard.py
```

### Computation is too large

Inspect the active cell count and validate a coarser grid before running.
Computation time scales strongly with cell count and probabilistic samples.
