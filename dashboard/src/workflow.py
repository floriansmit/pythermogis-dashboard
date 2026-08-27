"""Small, testable helpers shared by the Streamlit user interface."""

from __future__ import annotations

from pathlib import Path
import os
import shutil
import tempfile
from typing import Callable, Sequence

import numpy as np
import pandas as pd
import xarray as xr


ROOT = Path(__file__).resolve().parents[2]
DATA_ROOT = ROOT / "data"
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


def lognormal_parameters_from_mean_sd(mean: float, standard_deviation: float) -> tuple[float, float]:
    """Convert an arithmetic mean and SD to normal parameters in log space."""
    if mean <= 0:
        raise ValueError("The permeability mean must be greater than zero.")
    if standard_deviation < 0:
        raise ValueError("The permeability standard deviation cannot be negative.")
    log_variance = np.log1p((standard_deviation / mean) ** 2)
    return float(np.log(mean) - 0.5 * log_variance), float(np.sqrt(log_variance))


def available_netcdf_files() -> list[Path]:
    """Return NetCDF datasets stored in dashboard projects."""
    if not DATA_ROOT.exists():
        return []
    return sorted(DATA_ROOT.rglob("*.nc"), key=lambda path: str(path).lower())


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


def _validated_project_root(project_name: str) -> Path:
    """Return a direct child of DATA_ROOT, suitable for destructive operations."""
    data_root = DATA_ROOT.resolve()
    project_root = project_data_root(project_name).resolve()
    if project_root.parent != data_root:
        raise ValueError("Project data must be a direct child of the dashboard data folder.")
    return project_root


def ensure_project(project_name: str) -> tuple[Path, Path]:
    """Create the GO-Forward style input/output data folders for a project."""
    input_dir = project_input_dir(project_name)
    output_dir = project_output_dir(project_name)
    input_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)
    for subfolder in [*INPUT_SUBFOLDERS.values(), *OUTPUT_SUBFOLDERS.values()]:
        (project_data_root(project_name) / subfolder).mkdir(parents=True, exist_ok=True)
    return input_dir, output_dir


def remove_project_outputs(project_name: str) -> int:
    """Remove every output file for a project and recreate its empty folder layout."""
    project_root = _validated_project_root(project_name)
    output_dir = project_root / "output_data"
    removed_files = sum(1 for path in output_dir.rglob("*") if path.is_file()) if output_dir.exists() else 0
    if output_dir.exists():
        shutil.rmtree(output_dir)
    ensure_project(project_name)
    return removed_files


def remove_project_inputs_and_outputs(project_name: str) -> int:
    """Clear a project's input and output data while retaining the project itself."""
    project_root = _validated_project_root(project_name)
    removed_files = 0
    for folder_name in ("input_data", "output_data"):
        folder = project_root / folder_name
        if folder.exists():
            removed_files += sum(1 for path in folder.rglob("*") if path.is_file())
            shutil.rmtree(folder)
    ensure_project(project_name)
    return removed_files


def remove_project_result(project_name: str, output_subfolder: str, result_path: Path) -> None:
    """Remove one NetCDF result, after verifying that it belongs to the selected project."""
    project_root = _validated_project_root(project_name)
    if output_subfolder not in OUTPUT_SUBFOLDERS.values():
        raise ValueError("Unknown project output folder.")
    expected_folder = (project_root / output_subfolder).resolve()
    target = Path(result_path).resolve()
    if target.parent != expected_folder:
        raise ValueError("The selected result is outside the active project output folder.")
    if target.suffix.lower() not in {".nc", ".netcdf"}:
        raise ValueError("Only NetCDF result files can be removed here.")
    if not target.is_file():
        raise FileNotFoundError(f"Result file does not exist: {target.name}")
    target.unlink()


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
    x_vector = (mapaxes[4] - mapaxes[2], mapaxes[5] - mapaxes[3])
    y_vector = (mapaxes[0] - mapaxes[2], mapaxes[1] - mapaxes[3])
    x_length = float(np.hypot(*x_vector))
    y_length = float(np.hypot(*y_vector))
    if x_length == 0.0 or y_length == 0.0:
        raise ValueError("MAPAXES contains a zero-length axis.")
    x_unit = (x_vector[0] / x_length, x_vector[1] / x_length)
    y_unit = (y_vector[0] / y_length, y_vector[1] / y_length)

    def transform(local_x: float, local_y: float) -> tuple[float, float]:
        return (
            origin_x + local_x * x_unit[0] + local_y * y_unit[0],
            origin_y + local_x * x_unit[1] + local_y * y_unit[1],
        )

    return transform


def grdecl_xy_centres(path: Path) -> tuple[np.ndarray, np.ndarray]:
    """Return true global X/Y coordinates for every GRDECL column centre."""
    data = tokenize_grdecl(path, {"SPECGRID", "MAPAXES", "COORD"})
    nx, ny = (int(float(value)) for value in data["SPECGRID"][:2])
    coord = _expand_numeric(data["COORD"])
    transform = _mapaxes_transform(_expand_numeric(data["MAPAXES"]))

    def pillar_xy(i: int, j: int) -> tuple[float, float]:
        index = (j * (nx + 1) + i) * 6
        return coord[index], coord[index + 1]

    map_x = np.empty((ny, nx), dtype=float)
    map_y = np.empty((ny, nx), dtype=float)
    for j in range(ny):
        for i in range(nx):
            pillars = (
                pillar_xy(i, j), pillar_xy(i + 1, j),
                pillar_xy(i, j + 1), pillar_xy(i + 1, j + 1),
            )
            local_x = sum(x for x, _ in pillars) / 4.0
            local_y = sum(y for _, y in pillars) / 4.0
            map_x[j, i], map_y[j, i] = transform(local_x, local_y)
    return map_x, map_y


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
    permeability_sd: float = 25.0,
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
            "GRDECL conversion requires pygridsio3d. Run `uv sync` from the dashboard folder."
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
        map_x, map_y = grdecl_xy_centres(path)
        # Grid3dFunc mirrors the GRDECL J axis when it creates each 2D array.
        # Mirror the global centres identically so every value keeps its cell.
        geographic_coordinates = {
            "map_x": (("y", "x"), np.flip(map_x, axis=0)),
            "map_y": (("y", "x"), np.flip(map_y, axis=0)),
        }
        depth = depth.assign_coords(geographic_coordinates)
        thickness = thickness.assign_coords(geographic_coordinates)
        porosity_grid = porosity_grid.assign_coords(geographic_coordinates)
        permeability_grid = permeability_grid.assign_coords(geographic_coordinates)
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
    if permeability_key:
        ln_permeability_mean = np.log(combined["permeability"]).mean("realization")
        ln_permeability_sd = np.log(combined["permeability"]).std("realization")
    else:
        fallback_ln_mean, fallback_ln_sd = lognormal_parameters_from_mean_sd(
            permeability, permeability_sd
        )
        ln_permeability_mean = depth_mean * 0.0 + fallback_ln_mean
        ln_permeability_sd = depth_mean * 0.0 + fallback_ln_sd
    dataset = xr.Dataset(
        {
            "depth": depth_mean,
            "thickness_mean": combined["thickness"].mean("realization"),
            "thickness_sd": combined["thickness"].std("realization"),
            "porosity": combined["porosity"].mean("realization"),
            "ntg": combined["ntg"].mean("realization"),
            "ln_permeability_mean": ln_permeability_mean,
            "ln_permeability_sd": ln_permeability_sd,
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


def suggested_result_filename(project_name: str, dataset: xr.Dataset | None) -> str:
    """Build a readable result filename from the project and validated grid size."""
    project_token = "_".join(safe_project_name(project_name).replace(".", "_").split())
    if dataset is None:
        return f"pythermogis_results_{project_token}.nc"

    geometry = grid_geometry(dataset)
    if geometry["dx"] is None or geometry["dy"] is None:
        return f"pythermogis_results_{project_token}.nc"

    def spacing_token(spacing: float) -> str:
        if spacing >= 1000.0:
            return f"{spacing / 1000.0:.6g}km"
        return f"{spacing:.6g}m"

    grid_size = (
        f"{spacing_token(float(geometry['dx']))}_x_"
        f"{spacing_token(float(geometry['dy']))}"
    )
    return f"pythermogis_results_{project_token}_{grid_size}.nc"


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
    result = xr.Dataset(resampled, attrs=dataset.attrs)
    if "map_x" in dataset.coords and "map_y" in dataset.coords:
        original_x, original_y = np.meshgrid(dataset.x.values, dataset.y.values)
        design = np.column_stack(
            [np.ones(original_x.size), original_x.ravel(), original_y.ravel()]
        )
        map_x_coefficients = np.linalg.lstsq(
            design, dataset.coords["map_x"].values.ravel(), rcond=None
        )[0]
        map_y_coefficients = np.linalg.lstsq(
            design, dataset.coords["map_y"].values.ravel(), rcond=None
        )[0]
        resampled_x, resampled_y = np.meshgrid(result.x.values, result.y.values)
        resampled_design = np.stack(
            [np.ones_like(resampled_x), resampled_x, resampled_y], axis=-1
        )
        result = result.assign_coords(
            map_x=(("y", "x"), resampled_design @ map_x_coefficients),
            map_y=(("y", "x"), resampled_design @ map_y_coefficients),
        )
    return result


def utc_settings_from_dashboard(settings_values: dict[str, object]):
    """Create Pythermogis settings from the dashboard's simplified inputs.

    Pythermogis 3.0.3 represents the commercial UTC cutoff as one or more
    depth- and power-dependent ``CutoffClass`` objects.  The dashboard exposes
    one cutoff value, so translate it to a class that covers every finite
    simulated depth and power.
    """
    from pythermogis.settings import CutoffClass, UTCSettings

    translated = settings_values.copy()
    if "utc_cutoff" in translated:
        utc_cutoff = float(translated.pop("utc_cutoff"))
        translated["cutoff_classes"] = [
            CutoffClass(
                min_depth=float("-inf"),
                max_depth=float("inf"),
                min_power=float("-inf"),
                max_power=float("inf"),
                cutoff=utc_cutoff,
            )
        ]
    return UTCSettings(**translated)


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
    from pythermogis.aquifer import Aquifer, StochasticAquifer
    from pythermogis.doublet import ThermoGISDoublet
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
    results = ThermoGISDoublet(
        aquifer, utc_settings_from_dashboard(settings_values)
    ).simulate(
        p_values=p_values
    )
    report("Assembling result grids…")
    return results.to_dataset()
