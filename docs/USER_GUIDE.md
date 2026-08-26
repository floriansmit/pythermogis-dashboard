# User guide

## Projects and data isolation

Every dashboard project has the same typed directory structure:

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

The dashboard lists existing projects and creates these folders automatically.
Imported files are copied into the selected project's matching input folder.
Keeping the four input types separate prevents traditional ZMAP files from being
mistaken for maps generated from a GRDECL model.

Project data is ignored by Git. Back it up separately when it must be retained.

## Geology input modes

### Deterministic 2D grids

| Property | Recognized filename hints | Expected values |
|---|---|---|
| Reservoir top/depth | `depth`, `top` | metres |
| Gross thickness | `thickness`, `thick` | metres |
| Net-to-gross | `ntg` | fraction |
| Porosity | `porosity`, `poro`, `por` | fraction or percent, selected in the UI |
| Permeability | `permeability`, `perm` | mD |
| Temperature | `temperature`, `temp` | optional; otherwise calculated from gradient |

Supported 2D sources include ZMAP, NetCDF, GeoTIFF, and ASCII grids. Inspect the
detected file table before accepting automatic filename matching.

### Probabilistic 2D grids

The deterministic properties are required, plus thickness and permeability
standard-deviation grids. If an SD grid is unavailable, choose:

- **Constant SD** for one absolute uncertainty everywhere.
- **Percentage of local mean** for
  `SD(x,y) = abs(mean(x,y)) × percentage / 100`. This is generally most useful
  when uncertainty scales with the local reservoir magnitude.
- **Percentage of spatial mean** for a percentage of the valid map mean repeated
  everywhere. This is a convenient way to define a constant SD.

The permeability controls distinguish raw mD grids from grids already expressed
as `ln(permeability)`. Review displayed min, max, and mean values before choosing.
Do not apply the logarithm twice.

### Single GRDECL

Upload one GRDECL and, separately, a GO-Forward-style `facies_config.json` when
available. The compact facies editor allows names and colours to be checked or
changed. The point-based viewer shows properties and facies before conversion.

Conversion settings include one or more reservoir facies, porosity/permeability
property names or fallback constants, porosity units, depth shift, and NTG.
Generated maps are written beneath the matching GRDECL output folder and are not
mixed with traditional 2D inputs.

### Multiple GRDECL realizations

Select multiple realization files. The same facies and property mapping is
applied to each. The dashboard collapses the 3D models to reservoir-level 2D
properties and derives statistics for the probabilistic workflow.

## Boundary overlay

Upload all shapefile components together (`.shp`, `.shx`, `.dbf`, `.prj`, and
`.cpg` when present). The boundary is transformed to the grid CRS when metadata
exists. For legacy Danish ZMAP grids without stored CRS, the dashboard uses ED50
/ UTM zone 32N (`EPSG:23032`) as its configured fallback.

The overlay appears on geology previews and result maps. If it does not align,
verify both the shapefile CRS and grid coordinates.

## Inspect, resample, and validate

The viewer reports dimensions, cell size, total and active cells, statistics,
histograms, and a coordinate-correct 2D map. Undefined values such as `-7777` are
excluded from statistics and colour scaling. Depth scales run shallow-to-deep in
reverse.

Resampling is optional. The original viewer remains on the left; when enabled,
the resampled preview appears on the right. Presets range from 400 m to 10 km,
with a custom option. The single validation button validates the original grids
when resampling is off and the resampled grids when it is on. Only the validated
dataset is used by the simulation tab.

## Model settings

Well design, Cost model, Economic model, and calculated-temperature controls use
forms. Edit several fields without rerunning the application, then choose
**Apply settings**. Orange labels identify values different from model defaults.
Use the return arrow beside a field to restore its default or reset the complete
draft at the bottom.

## Simulation and saved results

Before running, validate geology, choose an output filename, resolve any existing
name conflict, and select probabilistic p-values where applicable. The status
reports Java startup, model construction, and cell/chunk progress. Results are
saved automatically as NetCDF in the active project's matching output folder.

## Result analysis

Open a project NetCDF file or upload a result. The tab reports variable
statistics, geometry, cell counts, dimensions, and descriptions. For
probabilistic results, choose a location by coordinates or address; the nearest
cell is used for NPV versus p-value and probability-of-success analysis. Address
lookup requires internet access.

## Troubleshooting

### PowerShell blocks activation

Manual activation is unnecessary:

```powershell
python install_dashboard.py
python run_dashboard.py
```

### Requirements file is not found

Run the installer from the repository root:

```powershell
python dashboard/install_dashboard.py
```

### Java startup is slow

The first calculation may install Java 17 and take several minutes. Later starts
reuse it. Corporate TLS inspection can block the download; install Java 17
locally or resolve the certificate chain in that case.

### Computation is too large

Inspect the cell count and validate a coarser grid before running. Computation
time scales strongly with active cells and probabilistic samples.
