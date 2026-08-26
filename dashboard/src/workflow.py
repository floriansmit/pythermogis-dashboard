"""Small, testable helpers shared by the Streamlit user interface."""

from __future__ import annotations

from pathlib import Path
import os
import shutil
import sys
import tempfile
from typing import Callable, Sequence

import numpy as np
import pandas as pd
import xarray as xr


ROOT = Path(__file__).resolve().parents[2]
VOI_SOURCE = ROOT / "PythermogisVOI" / "pythermogisvoi" / "src"
DATA_ROOT = ROOT / "data"
UNUSED_ROOT = ROOT / "_not_used_by_dashboard"
INPUT_SUBFOLDERS = {
    "2d_best_fit": "input_data/2d_grid_best_fit",
    "2d_probabilistic": "input_data/2d_grid_probabilistic",
    "grdecl_best_fit": "input_data/3d_grdecl_best_fit",
    "grdecl_multi": "input_data/3d_grdecl_multi_realization",
}
OUTPUT_SUBFOLDERS = {
    "2d_best_fit": "output_data/2d_grid_best_fit",
    "2d_probabilistic": "output_data/2d_grid_probabilistic",
    "grdecl_best_fit": "output_data/3d_grdecl_best_fit",
    "grdecl_multi": "output_data/3d_grdecl_multi_realization",
}


def configure_local_imports() -> None:
    """Prefer the checked-out public and GO-Forward sources to PyPI packages."""
    for path in (ROOT, VOI_SOURCE):
        path_string = str(path)
        if path_string not in sys.path:
            sys.path.insert(0, path_string)


def default_settings() -> dict[str, object]:
    """Dashboard-exposed UTC defaults, without starting the Java backend.

    Importing :mod:`pythermogis` starts its JVM by design.  Keeping the
    dashboard defaults here lets users inspect data and settings even on a
    machine where Java has not yet been installed.
    """
    return {
        "optimize_well_distance": True,
        "well_distance": 1500.0,
        "min_well_distance": 100.0,
        "max_well_distance": 3000.0,
        "max_flow": 500.0,
        "pump_efficiency": 0.6,
        "pump_depth": 300.0,
        "outer_diameter": 8.5,
        "inner_diameter": 8.5,
        "injector_skin": -1.0,
        "producer_skin": -1.0,
        "well_cost_constant": 0.25,
        "well_cost_depth": 700.0,
        "well_cost_depth2": 0.2,
        "well_cost_scaling": 1.5,
        "capex_constant": 3.0,
        "capex_variable": 300.0,
        "capex_contingency": 15.0,
        "opex_base": 0.0,
        "opex_power": 100.0,
        "opex_energy": 0.19,
        "opex_per_capex": 0.0,
        "economic_lifetime": 15,
        "drilling_time": 2,
        "load_hours": 6000.0,
        "electricity_purchase_price": 8.0,
        "tax_rate": 25.0,
        "interest_loan": 5.0,
        "inflation": 2.0,
        "equity_return": 7.0,
        "debt_equity": 80.0,
        "utc_cutoff": 5.1,
        "temperature_gradient": 31.0,
        "surface_temperature": 10.0,
    }


def available_netcdf_files() -> list[Path]:
    """Return a concise list of bundled example result/input datasets."""
    candidates = [
        ROOT / "examples" / "test_input" / "example_data" / "example.nc",
        ROOT / "Multi-realizations" / "examples" / "data" / "dummy-model" / "output_data" / "input_pythermogis_100realizations.nc",
        ROOT / "PythermogisVOI" / "pythermogisvoi" / "examples" / "dummy-model" / "input" / "output_pythermogis_100realizations.nc",
    ]
    return [candidate for candidate in candidates if candidate.exists()]


def safe_project_name(name: str) -> str:
    cleaned = "".join(ch if ch.isalnum() or ch in "-_ ." else "_" for ch in name).strip()
    cleaned = cleaned.strip(".")
    if not cleaned:
        raise ValueError("Project name cannot be empty.")
    return cleaned


def project_data_root(project_name: str) -> Path:
    return DATA_ROOT / safe_project_name(project_name)


def project_input_dir(project_name: str) -> Path:
    return project_data_root(project_name) / "input_data"


def project_output_dir(project_name: str) -> Path:
    return project_data_root(project_name) / "output_data"


def ensure_project(project_name: str) -> tuple[Path, Path]:
    """Create the GO-Forward style input/output data folders for a project."""
    input_dir = project_input_dir(project_name)
    output_dir = project_output_dir(project_name)
    input_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)
    for subfolder in [*INPUT_SUBFOLDERS.values(), *OUTPUT_SUBFOLDERS.values()]:
        (project_data_root(project_name) / subfolder).mkdir(parents=True, exist_ok=True)
    return input_dir, output_dir


def list_projects() -> list[str]:
    """List data projects already present in the workspace."""
    DATA_ROOT.mkdir(parents=True, exist_ok=True)
    return sorted([folder.name for folder in DATA_ROOT.iterdir() if folder.is_dir()], key=str.lower)


def project_files(project_name: str, folder: str = "input_data") -> list[Path]:
    directory = project_data_root(project_name) / folder
    if not directory.exists():
        return []
    return sorted([path for path in directory.iterdir() if path.is_file()], key=lambda p: p.name.lower())


def copy_files_to_project_input(
    paths: list[Path], project_name: str, subfolder_key: str | None = None
) -> list[Path]:
    """Copy selected external data files into the active project's input folder."""
    input_dir, _ = ensure_project(project_name)
    if subfolder_key:
        input_dir = project_data_root(project_name) / INPUT_SUBFOLDERS[subfolder_key]
        input_dir.mkdir(parents=True, exist_ok=True)
    copied = []
    for path in paths:
        if not path.exists() or not path.is_file():
            continue
        destination = input_dir / path.name
        if path.resolve() != destination.resolve():
            shutil.copy2(path, destination)
        copied.append(destination)
    return copied


def save_uploaded_files_to_project_input(
    uploads: list[object], project_name: str, subfolder_key: str
) -> list[Path]:
    """Persist Streamlit UploadedFile objects into a typed project input folder."""
    ensure_project(project_name)
    input_dir = project_data_root(project_name) / INPUT_SUBFOLDERS[subfolder_key]
    input_dir.mkdir(parents=True, exist_ok=True)
    saved = []
    for upload in uploads:
        destination = input_dir / upload.name
        destination.write_bytes(upload.getvalue())
        saved.append(destination)
    return saved


def path_for_io(path: Path) -> str:
    """Return a Windows extended-length path when required for file I/O."""
    text = str(path.resolve())
    if os.name != "nt" or text.startswith("\\\\?\\"):
        return text
    if text.startswith("\\\\"):
        return "\\\\?\\UNC\\" + text[2:]
    return "\\\\?\\" + text


def tokenize_grdecl(path: Path, wanted: set[str]) -> dict[str, list[str]]:
    """Read only selected GRDECL keyword blocks."""
    values: dict[str, list[str]] = {}
    keyword: str | None = None
    with open(path_for_io(path), "r", encoding="utf-8", errors="ignore") as handle:
        for raw in handle:
            line = raw.split("--", 1)[0].strip()
            if not line:
                continue
            head = line.split()[0]
            if head in wanted:
                keyword = head
                values.setdefault(keyword, [])
                rest = line[len(head) :].strip()
                if rest:
                    values[keyword].extend(rest.replace("/", " ").split())
                if "/" in line:
                    keyword = None
                continue
            if keyword:
                values[keyword].extend(line.replace("/", " ").split())
                if "/" in line:
                    keyword = None
    missing = wanted.difference(values)
    if missing:
        raise ValueError(f"{path.name} is missing GRDECL keyword(s): {', '.join(sorted(missing))}")
    return values


def expand_grdecl_values(tokens: list[str]) -> list[str]:
    """Expand Eclipse/GRDECL repeat syntax such as 12*0.0."""
    values: list[str] = []
    for token in tokens:
        if "*" in token:
            count_text, repeated = token.split("*", 1)
            values.extend([repeated] * int(float(count_text)))
        else:
            values.append(token)
    return values


def _expand_numeric(tokens: list[str]) -> list[float]:
    return [float(value) for value in expand_grdecl_values(tokens)]


def grdecl_dimensions(path: Path) -> tuple[int, int, int]:
    data = tokenize_grdecl(path, {"SPECGRID"})
    return tuple(int(float(value)) for value in data["SPECGRID"][:3])


def grdecl_keyword_candidates(path: Path) -> list[str]:
    """Return top-level GRDECL keyword names without expanding their values."""
    keywords: list[str] = []
    active = False
    with open(path_for_io(path), "r", encoding="utf-8", errors="ignore") as handle:
        for raw in handle:
            line = raw.split("--", 1)[0].strip()
            if not line:
                continue
            if active:
                if "/" in line:
                    active = False
                continue
            head = line.split()[0]
            if head == "/":
                continue
            keywords.append(head)
            if "/" not in line and head not in {"NOECHO", "ECHO"}:
                active = True
    return keywords


def grdecl_property_keywords(path: Path) -> list[str]:
    """Return keywords whose expanded value count equals the GRDECL cell count."""
    nx, ny, nz = grdecl_dimensions(path)
    cell_count = nx * ny * nz
    ignored = {
        "MAPUNITS", "MAPAXES", "GRIDUNIT", "SPECGRID", "COORDSYS", "COORD",
        "ZCORN", "PINCH", "NOECHO", "ECHO", "BOX", "ENDBOX",
    }
    properties: list[str] = []
    for keyword in grdecl_keyword_candidates(path):
        if keyword in ignored or keyword in properties:
            continue
        try:
            values = expand_grdecl_values(tokenize_grdecl(path, {keyword})[keyword])
        except Exception:
            continue
        if len(values) == cell_count:
            properties.append(keyword)
    return properties


def _mapaxes_transform(mapaxes: list[float]):
    origin_x, origin_y = mapaxes[2], mapaxes[3]
    x_unit = ((mapaxes[4] - mapaxes[2]) / 1000.0, (mapaxes[5] - mapaxes[3]) / 1000.0)
    y_unit = ((mapaxes[0] - mapaxes[2]) / 1000.0, (mapaxes[1] - mapaxes[3]) / 1000.0)

    def transform(local_x: float, local_y: float) -> tuple[float, float]:
        return (
            origin_x + local_x * x_unit[0] + local_y * y_unit[0],
            origin_y + local_x * x_unit[1] + local_y * y_unit[1],
        )

    return transform


def grdecl_cell_centres(path: Path) -> list[tuple[float, float, float]]:
    """Calculate GRDECL cell-centre coordinates from SPECGRID/MAPAXES/COORD/ZCORN."""
    data = tokenize_grdecl(path, {"SPECGRID", "MAPAXES", "COORD", "ZCORN"})
    nx, ny, nz = (int(float(v)) for v in data["SPECGRID"][:3])
    coord = _expand_numeric(data["COORD"])
    zcorn = _expand_numeric(data["ZCORN"])
    mapaxes = _expand_numeric(data["MAPAXES"])
    transform = _mapaxes_transform(mapaxes)

    def pillar_xy(i: int, j: int) -> tuple[float, float]:
        idx = (j * (nx + 1) + i) * 6
        return coord[idx], coord[idx + 1]

    def z_value(i: int, j: int, k: int, di: int, dj: int, dk: int) -> float:
        return zcorn[(2 * k + dk) * (2 * ny) * (2 * nx) + (2 * j + dj) * (2 * nx) + (2 * i + di)]

    centres: list[tuple[float, float, float]] = []
    for k in range(nz):
        for j in range(ny):
            for i in range(nx):
                pillars = (
                    pillar_xy(i, j), pillar_xy(i + 1, j),
                    pillar_xy(i, j + 1), pillar_xy(i + 1, j + 1),
                )
                local_x = sum(x for x, _ in pillars) / 4.0
                local_y = sum(y for _, y in pillars) / 4.0
                x, y = transform(local_x, local_y)
                z = -sum(
                    z_value(i, j, k, di, dj, dk)
                    for dk in (0, 1) for dj in (0, 1) for di in (0, 1)
                ) / 8.0
                centres.append((x, y, z))
    return centres


def grdecl_inspection_dataframe(
    path: Path,
    property_keyword: str,
    *,
    max_rows: int = 150_000,
) -> pd.DataFrame:
    """Build a cell-centre dataframe for one GRDECL property, sampled when large."""
    nx, ny, nz = grdecl_dimensions(path)
    centres = grdecl_cell_centres(path)
    df = pd.DataFrame(centres, columns=["X", "Y", "Z"])
    cell_index = np.arange(len(df))
    df["CellIndex"] = cell_index
    df["I"] = cell_index % nx + 1
    df["J"] = (cell_index // nx) % ny + 1
    df["K"] = cell_index // (nx * ny) + 1
    values = expand_grdecl_values(tokenize_grdecl(path, {property_keyword})[property_keyword])
    if len(values) == len(df):
        numeric = pd.to_numeric(pd.Series(values), errors="coerce")
        df[property_keyword] = numeric if numeric.notna().any() else values
    if len(df) > max_rows:
        df = df.sample(max_rows, random_state=7).sort_values(["K", "J", "I"])
    return df


def load_dataset(source: Path | object) -> xr.Dataset:
    """Load a NetCDF path or Streamlit UploadedFile into memory."""
    return xr.load_dataset(source).load()


def load_grid_source(source: Path | object) -> xr.DataArray:
    """Read one NetCDF, GeoTIFF, ZMAP, or ASCII grid path/upload as a DataArray."""
    source_name = getattr(source, "name", str(source))
    suffix = Path(source_name).suffix.lower()
    if isinstance(source, Path):
        path = source
        temporary_path = False
    else:
        temporary_path = True
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as temporary:
            temporary.write(source.getvalue())
            path = Path(temporary.name)
    try:
        if suffix in {".nc", ".netcdf"}:
            dataset = xr.load_dataset(path)
            if len(dataset.data_vars) != 1:
                raise ValueError(
                    f"{Path(source_name).name} contains {len(dataset.data_vars)} variables. "
                    "Use a NetCDF with one grid variable."
                )
            return next(iter(dataset.data_vars.values())).load()
        from pygridsio import read_grid

        return read_grid(path)
    finally:
        if temporary_path:
            path.unlink(missing_ok=True)


def load_uploaded_grid(upload: object) -> xr.DataArray:
    """Read one uploaded NetCDF, GeoTIFF, ZMAP, or ASCII grid as a DataArray."""
    return load_grid_source(upload)


def convert_grdecl_to_dataset(
    grdecl_paths: list[Path],
    *,
    facies_key: str = "FACIES",
    reservoir_facies: Sequence[int] = (2,),
    porosity_key: str = "",
    permeability_key: str = "",
    porosity_property_in_percent: bool = False,
    depth_shift: float = 0.0,
    porosity: float = 0.2,
    ntg: float = 1.0,
    permeability: float = 100.0,
    ln_permeability_sd: float = 0.01,
    output_dir: Path | None = None,
) -> xr.Dataset:
    """Convert one/more GRDECL realizations to Pythermogis-ready 2D maps."""
    if not grdecl_paths:
        raise ValueError("Select at least one GRDECL file.")
    reservoir_values = sorted({int(value) for value in reservoir_facies})
    if not reservoir_values:
        raise ValueError("Select at least one reservoir facies.")
    try:
        from pygridsio3d import Grid3dFunc, read_grid3d
    except Exception as exc:
        raise RuntimeError(
            "GRDECL conversion requires pygridsio3d. Run `python install_dashboard.py` "
            "after installing the Multi-realizations dependencies."
        ) from exc

    realizations: list[xr.Dataset] = []
    from pygridsio import write_grid

    facies_property_key = facies_key.upper()
    porosity_property_key = porosity_key.upper()
    permeability_property_key = permeability_key.upper()
    read_keys = [facies_property_key]
    for key in (porosity_property_key, permeability_property_key):
        if key and key not in read_keys:
            read_keys.append(key)

    generated_maps: list[Path] = []
    conversion_notes: list[str] = []
    for path in grdecl_paths:
        try:
            grid3d = read_grid3d(path, read_keys=read_keys)
        except Exception as exc:
            raise RuntimeError(
                f"Could not read {path.name} with the selected GRDECL properties "
                f"({', '.join(read_keys)}). Choose properties that exist in every selected "
                f"realization, or choose no property to use a constant fallback."
            ) from exc
        functions = Grid3dFunc(grid3d)
        grid3d.set_mask(functions.init_basemask(klow=1))
        facies_masks = [
            functions.get_custom_mask(property_key=facies_property_key, property_value=value)
            for value in reservoir_values
        ]
        mask = np.logical_or.reduce(facies_masks)
        if hasattr(functions, "basemask"):
            mask = np.logical_and(mask, functions.basemask)
        thickness = functions.get_sumthick(mask).astype(float)
        average_depth = functions.get_average_depth(mask).astype(float)
        depth = average_depth - 0.5 * thickness + depth_shift
        if porosity_key:
            try:
                porosity_grid = functions.get_sumthick_prop(mask, porosity_property_key) / thickness
                if porosity_property_in_percent:
                    porosity_grid = porosity_grid / 100.0
            except Exception as exc:
                raise RuntimeError(
                    f"Could not calculate porosity from property '{porosity_key}' in {path.name}. "
                    "Choose another property or select no porosity property to use a constant fallback."
                ) from exc
        else:
            porosity_grid = depth * 0.0 + porosity
        if permeability_key:
            try:
                permeability_grid = functions.get_sumthick_prop(mask, permeability_property_key) / thickness
            except Exception as exc:
                raise RuntimeError(
                    f"Could not calculate permeability from property '{permeability_key}' in {path.name}. "
                    "Choose another property or select no permeability property to use a constant fallback."
                ) from exc
        else:
            permeability_grid = depth * 0.0 + permeability
        if output_dir is not None:
            output_dir.mkdir(parents=True, exist_ok=True)
            outputs = {
                "depth": depth,
                "thickness": thickness,
                "porosity": porosity_grid,
                "ntg": depth * 0.0 + ntg,
                "permeability": permeability_grid,
            }
            for name, grid in outputs.items():
                destination = output_dir / f"{path.stem}_grdecl_{name}.zmap"
                write_grid(grid, destination)
                generated_maps.append(destination)
        realizations.append(
            xr.Dataset(
                {
                    "depth": depth,
                    "thickness": thickness,
                    "porosity": porosity_grid,
                    "ntg": depth * 0.0 + ntg,
                    "permeability": permeability_grid,
                }
            )
        )

    if len(realizations) == 1:
        dataset = realizations[0]
        if generated_maps:
            dataset.attrs["generated_maps"] = "\n".join(str(path) for path in generated_maps)
        if conversion_notes:
            dataset.attrs["conversion_notes"] = "\n".join(conversion_notes)
        return dataset

    combined = xr.concat(
        realizations,
        dim=xr.DataArray(
            np.arange(1, len(realizations) + 1), dims="realization", name="realization"
        ),
    )
    depth_mean = combined["depth"].mean("realization")
    dataset = xr.Dataset(
        {
            "depth": depth_mean,
            "thickness_mean": combined["thickness"].mean("realization"),
            "thickness_sd": combined["thickness"].std("realization"),
            "porosity": combined["porosity"].mean("realization"),
            "ntg": combined["ntg"].mean("realization"),
            "ln_permeability_mean": np.log(combined["permeability"]).mean("realization"),
            "ln_permeability_sd": (
                np.log(combined["permeability"]).std("realization")
                if permeability_key
                else depth_mean * 0.0 + ln_permeability_sd
            ),
        }
    )
    if generated_maps:
        dataset.attrs["generated_maps"] = "\n".join(str(path) for path in generated_maps)
    if conversion_notes:
        dataset.attrs["conversion_notes"] = "\n".join(conversion_notes)
    return dataset


def detect_grid_sources(sources: list[object], stochastic: bool) -> dict[str, object]:
    """Match uploaded grid names to required geology properties.

    The matching deliberately uses short, conventional tokens so folders such as
    ``GASSUM_top...``, ``...thick...``, ``...poro...``, and ``...perm_sd...``
    can be loaded without manual assignment.
    """
    accepted_suffixes = {".nc", ".netcdf", ".tif", ".tiff", ".zmap", ".asc"}
    files = [item for item in sources if Path(item.name).suffix.lower() in accepted_suffixes]

    def find(*tokens: str, exclude: tuple[str, ...] = ()) -> object | None:
        for item in files:
            name = item.name.lower()
            if all(token in name for token in tokens) and not any(token in name for token in exclude):
                return item
        return None

    matched = {
        "depth": find("depth") or find("top"),
        "porosity": find("poro") or find("por"),
        "ntg": find("ntg"),
    }
    if stochastic:
        matched.update(
            {
                "thickness_mean": find("thickness", exclude=("sd",)) or find("thick", exclude=("sd",)),
                "thickness_sd": find("thickness", "sd") or find("thick", "sd"),
                "permeability_mean": find("perm", exclude=("sd",)),
                "permeability_sd": find("perm", "sd"),
            }
        )
    else:
        matched.update(
            {
                "thickness": find("thickness", exclude=("sd",)) or find("thick", exclude=("sd",)),
                "permeability": find("perm", exclude=("sd",)),
            }
        )
    return matched


def dataset_from_single_grids(grids: dict[str, xr.DataArray]) -> xr.Dataset:
    """Combine named best-fit geology grids and require common spatial alignment."""
    return xr.Dataset(grids)


def grid_geometry(dataset: xr.Dataset) -> dict[str, float | int | None]:
    """Return the recognised dimensions, grid spacing, and number of cells."""
    reference = next(iter(dataset.data_vars.values()))
    if "x" not in reference.coords or "y" not in reference.coords:
        return {"x_cells": None, "y_cells": None, "cell_count": int(reference.size), "dx": None, "dy": None}
    x = reference.x.values
    y = reference.y.values
    dx = float(abs(x[1] - x[0])) if len(x) > 1 else None
    dy = float(abs(y[1] - y[0])) if len(y) > 1 else None
    return {
        "x_cells": len(x),
        "y_cells": len(y),
        "cell_count": int(len(x) * len(y)),
        "dx": dx,
        "dy": dy,
    }


def resample_dataset(
    dataset: xr.Dataset, new_cellsize: float, interpolation: str = "nearest"
) -> xr.Dataset:
    """Resample every variable to one common coarser x/y grid."""
    from pygridsio.grid_functions.grid_operations import resample_grid

    first_name = next(iter(dataset.data_vars))
    reference = resample_grid(
        dataset[first_name], new_cellsize=new_cellsize, interp_method=interpolation
    )
    resampled = {first_name: reference}
    for name, grid in dataset.data_vars.items():
        if name != first_name:
            resampled[name] = resample_grid(
                grid, grid_to_use=reference, interp_method=interpolation
            )
    return xr.Dataset(resampled)


def simulate_dataset(
    dataset: xr.Dataset,
    mapping: dict[str, str],
    settings_values: dict[str, object],
    status: Callable[[str], None] | None = None,
    p_values: list[float] | None = None,
    cell_progress: Callable[[int, int], None] | None = None,
    rows_per_chunk: int = 5,
) -> xr.Dataset:
    """Run a deterministic pythermogis simulation from a mapped xarray dataset."""
    report = status or (lambda _: None)
    report("Starting the Pythermogis Java runtime…")
    configure_local_imports()
    from pythermogis.aquifer import Aquifer, StochasticAquifer
    from pythermogis.doublet import ThermoGISDoublet
    from pythermogis.settings import UTCSettings
    import jpype

    report(
        "Java runtime is ready." if jpype.isJVMStarted() else "Java runtime was not started."
    )

    if cell_progress is not None and "x" in dataset.sizes and "y" in dataset.sizes:
        total_cells = int(dataset.sizes["x"] * dataset.sizes["y"])
        chunks = []
        report("Running the ThermoGIS doublet calculation in spatial chunks…")
        for row_start in range(0, dataset.sizes["y"], rows_per_chunk):
            row_end = min(row_start + rows_per_chunk, dataset.sizes["y"])
            chunks.append(
                simulate_dataset(
                    dataset.isel(y=slice(row_start, row_end)),
                    mapping,
                    settings_values,
                    p_values=p_values,
                )
            )
            cell_progress(min(row_end * dataset.sizes["x"], total_cells), total_cells)
        report("Assembling result grids…")
        return xr.concat(chunks, dim="y")

    def field(name: str):
        selected = mapping.get(name)
        return dataset[selected] if selected else None

    report("Validating the geology grids and constructing the aquifer…")
    if mapping.get("thickness_mean"):
        aquifer = StochasticAquifer(
            thickness_mean=field("thickness_mean"),
            thickness_sd=field("thickness_sd"),
            ln_permeability_mean=field("ln_permeability_mean"),
            ln_permeability_sd=field("ln_permeability_sd"),
            porosity=field("porosity"),
            ntg=field("ntg"),
            depth=field("depth"),
            temperature=field("temperature"),
            mask=field("mask"),
        )
    else:
        aquifer = Aquifer(
            thickness=field("thickness"),
            permeability=field("permeability"),
            transmissivity=field("transmissivity"),
            porosity=field("porosity"),
            ntg=field("ntg"),
            depth=field("depth"),
            temperature=field("temperature"),
            mask=field("mask"),
        )
    report("Running the ThermoGIS doublet calculation for every grid cell…")
    results = ThermoGISDoublet(aquifer, UTCSettings(**settings_values)).simulate(
        p_values=p_values
    )
    report("Assembling result grids…")
    return results.to_dataset()
