"""GO-Forward geothermal workflow dashboard."""

from __future__ import annotations

import hashlib
import importlib
import json
from pathlib import Path
import sys
import tempfile

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import xarray as xr

APP_DIR = Path(__file__).resolve().parent
LOGO_PATH = APP_DIR / "GO-Forward.png"
sys.path.insert(0, str(APP_DIR / "src"))
import workflow as workflow_module

# Streamlit reruns app.py without necessarily re-importing edited helper modules.
# Reloading prevents the UI and workflow function signatures from drifting apart.
importlib.reload(workflow_module)
from workflow import (
    INPUT_SUBFOLDERS,
    OUTPUT_SUBFOLDERS,
    ROOT,
    available_netcdf_files,
    convert_grdecl_to_dataset,
    dataset_from_single_grids,
    default_settings,
    detect_grid_sources,
    ensure_project,
    grdecl_dimensions,
    grdecl_inspection_dataframe,
    grdecl_property_keywords,
    grid_geometry,
    list_projects,
    load_dataset,
    load_grid_source,
    load_uploaded_grid,
    project_files,
    project_data_root,
    project_input_dir,
    project_output_dir,
    resample_dataset,
    safe_project_name,
    simulate_dataset,
)


st.set_page_config(page_title="GO-Forward geothermal workflows", layout="wide")


DEFAULT_SETTINGS = default_settings()
THEORY_URL = "https://pythermogis-15909e.ci.tno.nl/theory/introduction/"

SETTING_METADATA: dict[str, dict[str, str]] = {
    "optimize_well_distance": {
        "label": "Optimize producer–injector distance", "unit": "boolean",
        "help": "Let DoubletCalc choose the reservoir-level well spacing within the minimum and maximum bounds. The optimization limits thermal breakthrough so the production–injection temperature difference remains approximately 99% of its initial value at the end of the technical lifetime.",
    },
    "well_distance": {
        "label": "Fixed well distance", "unit": "m",
        "help": "Reservoir-level separation between producer and injector when distance optimization is disabled.",
    },
    "min_well_distance": {
        "label": "Minimum optimized well distance", "unit": "m",
        "help": "Lower bound searched when producer–injector distance optimization is enabled.",
    },
    "max_well_distance": {
        "label": "Maximum optimized well distance", "unit": "m",
        "help": "Upper bound searched when producer–injector distance optimization is enabled.",
    },
    "max_flow": {
        "label": "Maximum production flow", "unit": "m³/h",
        "help": "Operational upper limit on geothermal-brine production. Actual flow may be lower because of reservoir resistance, wellbore friction, thermosyphon effects, or pump-pressure limits.",
    },
    "pump_efficiency": {
        "label": "ESP pump-system efficiency", "unit": "fraction",
        "help": "Electrical submersible pump efficiency used to convert hydraulic demand into electricity consumption; the documented standard case is 0.6.",
    },
    "pump_depth": {
        "label": "Production pump depth", "unit": "m below surface",
        "help": "Vertical setting depth of the production ESP. It affects the pressure and energy balance through the production well.",
    },
    "outer_diameter": {
        "label": "Open-aquifer-section diameter", "unit": "inch",
        "help": "Flow diameter of the open reservoir/aquifer section of the wells. Diameter influences frictional pressure loss in the pressure-balance calculation.",
    },
    "inner_diameter": {
        "label": "Cased well-section inner diameter", "unit": "inch",
        "help": "Internal flow diameter of the cased section from surface to the top of the aquifer. Diameter controls wellbore friction; the theory standard is 8.5 inch.",
    },
    "injector_skin": {
        "label": "Injector skin factor", "unit": "dimensionless",
        "help": "Near-well hydraulic resistance. Negative skin improves injectivity; the theory describes −1 for a slanted completion and about −3 after stimulation or for horizontal/multilateral reservoir sections.",
    },
    "producer_skin": {
        "label": "Producer skin factor", "unit": "dimensionless",
        "help": "Near-well hydraulic resistance. Negative skin improves productivity; the theory describes −1 for a slanted completion and about −3 after stimulation or for horizontal/multilateral reservoir sections.",
    },
    "well_cost_constant": {
        "label": "Constant well-cost term wc₀", "unit": "million € per well",
        "help": "Depth-independent term in the cost of each well. Total doublet well CAPEX uses 2 × well-cost scaling × (wc₀ + wc₁·MD + wc₂·MD²).",
    },
    "well_cost_depth": {
        "label": "Linear well-depth cost coefficient wc₁", "unit": "€/m per well",
        "help": "Linear drilling-cost contribution multiplied by measured/along-hole depth. Measured depth is approximated as the well-trajectory curvature factor times reservoir-top depth.",
    },
    "well_cost_depth2": {
        "label": "Quadratic well-depth cost coefficient wc₂", "unit": "€/m² per well",
        "help": "Quadratic drilling-cost contribution wc₂·MD². It captures the nonlinear increase in drilling and completion cost with depth; this is why a second depth coefficient is present.",
    },
    "well_cost_scaling": {
        "label": "Overall well-cost scaling", "unit": "dimensionless",
        "help": "Multiplier applied to the constant, linear, and quadratic cost terms for both wells; use it for regional or project-specific cost-level adjustment.",
    },
    "capex_constant": {
        "label": "Fixed plant CAPEX", "unit": "million €",
        "help": "Depth- and capacity-independent surface-plant and other fixed capital expenditure, excluding the wells.",
    },
    "capex_variable": {
        "label": "Capacity-dependent plant CAPEX", "unit": "€/kW",
        "help": "Variable plant capital cost multiplied by net installed geothermal power in kW.",
    },
    "capex_contingency": {
        "label": "CAPEX contingency", "unit": "%",
        "help": "Contingency allowance applied to capital expenditure to represent scope and cost uncertainty.",
    },
    "opex_base": {
        "label": "Fixed annual OPEX", "unit": "million €/year",
        "help": "Annual fixed operating and maintenance expenditure independent of power and produced energy.",
    },
    "opex_power": {
        "label": "Power-dependent annual OPEX", "unit": "€/kW/year",
        "help": "Annual operating expenditure multiplied by net installed power capacity.",
    },
    "opex_energy": {
        "label": "Energy-dependent annual OPEX", "unit": "€/kWh",
        "help": "Variable operating expenditure multiplied by annual produced geothermal energy.",
    },
    "opex_per_capex": {
        "label": "Additional OPEX as share of CAPEX", "unit": "%/year",
        "help": "Optional annual operating-cost allowance calculated as a percentage of capital expenditure.",
    },
    "economic_lifetime": {
        "label": "Economic lifetime", "unit": "years",
        "help": "Cash-flow and loan term over which OPEX and energy production are accumulated and discounted.",
    },
    "drilling_time": {
        "label": "Drilling and construction time", "unit": "years",
        "help": "Project lead time before operation. Pythermogis assigns well and plant CAPEX at the start of the economic lifetime rather than distributing well CAPEX over this period.",
    },
    "load_hours": {
        "label": "Annual full-load hours", "unit": "h/year",
        "help": "Equivalent operating hours used with geothermal power to calculate yearly produced energy.",
    },
    "electricity_purchase_price": {
        "label": "Purchased electricity price", "unit": "€ct/kWh",
        "help": "Electricity price applied to ESP and other parasitic electricity consumption.",
    },
    "tax_rate": {
        "label": "Tax rate", "unit": "%",
        "help": "Tax assumption used for deductions and tax-adjusted energy/income in the discounted cash-flow model.",
    },
    "interest_loan": {
        "label": "Loan interest rate", "unit": "%/year",
        "help": "Interest rate used to calculate annual annuity payments on the debt-financed share of CAPEX.",
    },
    "inflation": {
        "label": "OPEX inflation", "unit": "%/year",
        "help": "Annual escalation applied to operating expenditure from the second operating year onward.",
    },
    "equity_return": {
        "label": "Required equity return / discount rate", "unit": "%/year",
        "help": "Required return used to discount yearly income and tax-adjusted produced energy to present value.",
    },
    "debt_equity": {
        "label": "Debt-financed CAPEX share", "unit": "%",
        "help": "Percentage of initial CAPEX financed by debt; the remainder is equity financed.",
    },
    "utc_cutoff": {
        "label": "Commercial UTC cutoff", "unit": "€ct/kWh",
        "help": "Reference heat price used to calculate NPV from the difference between the cutoff and modelled Unit Technical Cost (UTC).",
    },
    "temperature_gradient": {
        "label": "Geothermal temperature gradient", "unit": "°C/km",
        "help": "Temperature increase per kilometre of depth used with surface temperature to calculate the reservoir-temperature grid when no temperature map is supplied.",
    },
    "surface_temperature": {
        "label": "Surface temperature", "unit": "°C",
        "help": "Temperature intercept at zero depth used with the geothermal gradient to calculate reservoir temperature.",
    },
}

RESULT_METADATA: dict[str, dict[str, str]] = {
    "power": {"label": "Net geothermal power", "unit": "MW", "calculation": "Converted geothermal output after applying the conversion scenario and parasitic losses. The basic energy relation is E = η·Q·C·ΔT."},
    "heat_pump_power": {"label": "Heat output including heat pump", "unit": "MW", "calculation": "Total useful heat including the heat-pump contribution when that conversion option is active."},
    "capex": {"label": "Total capital expenditure", "unit": "million €", "calculation": "Sum of doublet well cost, optional stimulation cost, and fixed plus capacity-dependent plant CAPEX, including configured contingency."},
    "opex": {"label": "First-year operating expenditure", "unit": "million €/year", "calculation": "Fixed, capacity-dependent, energy-dependent, CAPEX-related, and purchased-electricity operating costs for the first operating year."},
    "utc": {"label": "Unit Technical Cost / LCOE", "unit": "€ct/kWh", "calculation": "Ratio of total discounted cost to discounted tax-adjusted energy produced over the economic lifetime."},
    "npv": {"label": "Net present value", "unit": "million €", "calculation": "Calculated relative to the commercial UTC cutoff from discounted tax-adjusted heat production and the margin (UTC cutoff − UTC)."},
    "hprod": {"label": "Heat-production KPI", "unit": "API: TJ/year; theory KPI table: discounted MWh", "calculation": "Heat production derived from geothermal power and annual load hours. The public result-class documentation calls this annual heat production in TJ/year, while the theory KPI page describes Hprod as lifetime-discounted MWh; this viewer exposes that documentation inconsistency rather than silently choosing one interpretation."},
    "cop": {"label": "System coefficient of performance", "unit": "dimensionless", "calculation": "Ratio of useful geothermal output to consumed pumping/conversion electricity."},
    "cophp": {"label": "Heat-pump coefficient of performance", "unit": "dimensionless", "calculation": "Useful heat delivered by the heat pump divided by heat-pump electricity consumption."},
    "pres": {"label": "Required pump pressure", "unit": "bar", "calculation": "Pressure required to balance reservoir hydraulic resistance, wellbore friction, and thermosyphon effects at the calculated flow."},
    "flow_rate": {"label": "Production flow rate", "unit": "m³/h", "calculation": "Achievable doublet flow from the coupled pressure balance, constrained by pump pressure and the configured maximum flow."},
    "welld": {"label": "Producer–injector distance", "unit": "m", "calculation": "Optimized reservoir-level spacing, or the fixed configured spacing when optimization is disabled. Optimization limits thermal breakthrough over the technical lifetime."},
    "inj_temp": {"label": "Injection temperature", "unit": "°C", "calculation": "Temperature of the cooled fluid returned to the injection well after surface energy conversion."},
    "prd_temp": {"label": "Surface production temperature", "unit": "°C", "calculation": "Produced-fluid temperature at surface after heat loss along the production well."},
    "transmissivity_with_ntg": {"label": "Net transmissivity", "unit": "D·m", "calculation": "Gross permeability × thickness, corrected by net-to-gross and converted from mD·m to D·m."},
    "thickness": {"label": "Reservoir thickness used", "unit": "m", "calculation": "Gross reservoir thickness supplied to the simulation; probabilistic runs contain the sampled percentile value."},
    "transmissivity": {"label": "Gross transmissivity", "unit": "mD·m", "calculation": "Permeability × gross reservoir thickness before net-to-gross correction."},
    "permeability": {"label": "Reservoir permeability used", "unit": "mD", "calculation": "Permeability supplied or sampled for the doublet calculation."},
    "temperature": {"label": "Reservoir temperature", "unit": "°C", "calculation": "Reservoir temperature supplied as a grid or calculated from depth, surface temperature, and geothermal gradient."},
    "pos": {"label": "Probability of success", "unit": "%", "calculation": "Probability that NPV is positive, interpolated across the simulated p-values at NPV = 0."},
}


def state(key: str, factory):
    if key not in st.session_state:
        st.session_state[key] = factory()
    return st.session_state[key]


def choose_dataset() -> xr.Dataset | None:
    bundled = available_netcdf_files()
    choices = ["Upload a NetCDF file"] + [str(path.relative_to(ROOT)) for path in bundled]
    source = st.radio("Dataset source", choices, horizontal=True)
    try:
        if source == "Upload a NetCDF file":
            upload = st.file_uploader("NetCDF geology/result file", type=["nc", "netcdf"])
            return load_dataset(upload) if upload else None
        return load_dataset(bundled[choices.index(source) - 1])
    except Exception as exc:
        st.error(f"Could not open the dataset: {exc}")
        return None


def field_mapping(dataset: xr.Dataset) -> dict[str, str]:
    names = list(dataset.data_vars)
    required = ["thickness", "porosity", "ntg", "depth"]
    optional = ["permeability", "transmissivity", "temperature", "mask"]
    mapping = {}
    for field in required + optional:
        default = names.index(field) + 1 if field in names else 0
        mapping[field] = st.selectbox(field.replace("_", " ").title(), ["—"] + names, index=default, key=f"map_{field}")
        if mapping[field] == "—":
            mapping[field] = ""
    return mapping


def setting_is_modified(field: str, value: object) -> bool:
    default = DEFAULT_SETTINGS[field]
    if isinstance(default, bool):
        return bool(value) != default
    return not np.isclose(float(value), float(default))


def setting_increment(field: str, default: object) -> float | int:
    """Return a practical increment instead of Streamlit's generic 0.01 step."""
    if isinstance(default, int) and not isinstance(default, bool):
        return 1
    metadata = SETTING_METADATA[field]
    unit = metadata["unit"].lower()
    if unit in {"fraction", "dimensionless"} or abs(float(default)) <= 1.0:
        return 0.1
    return 1.0


def settings_editor(
    settings: dict[str, object], fields: list[str], title: str, introduction: str,
    *, show_docs_link: bool = True,
) -> None:
    """Render staged settings that only update the model when the form is applied."""
    st.subheader(title)
    st.write(introduction)
    st.caption(
        "Edit as many values as needed without rerunning the page. Orange labels identify draft "
        "values that differ from the model defaults. Select Apply settings at the bottom to use "
        "the complete draft configuration."
    )
    for field in fields:
        st.session_state.setdefault(f"setting_draft_{field}", settings[field])

    draft_modified_count = sum(
        setting_is_modified(field, st.session_state[f"setting_draft_{field}"])
        for field in fields
    )
    pending_count = sum(
        st.session_state[f"setting_draft_{field}"] != settings[field]
        for field in fields
    )
    if pending_count:
        st.info(f"{pending_count} staged change{'s' if pending_count != 1 else ''} are not yet applied.")
    elif draft_modified_count:
        st.warning(f"{draft_modified_count} applied setting{'s' if draft_modified_count != 1 else ''} differ from the model defaults.")
    else:
        st.success("Model defaults active for this section.")

    form_key = "settings_form_" + "_".join(title.lower().split())
    reset_field: str | None = None
    with st.form(form_key):
        columns = st.columns(2, gap="large")
        for index, field in enumerate(fields):
            default = DEFAULT_SETTINGS[field]
            metadata = SETTING_METADATA[field]
            draft_value = st.session_state[f"setting_draft_{field}"]
            modified = setting_is_modified(field, draft_value)
            unit = metadata["unit"]
            label = f"{'🟠 ' if modified else ''}{metadata['label']} [{unit}]"
            widget_key = f"setting_draft_{field}"
            with columns[index % 2]:
                input_column, reset_column = st.columns([8.5, 1.5], vertical_alignment="bottom")
                with input_column:
                    if isinstance(default, bool):
                        st.checkbox(label, key=widget_key, help=metadata["help"])
                    elif isinstance(default, int):
                        st.number_input(label, step=1, key=widget_key, help=metadata["help"])
                    else:
                        st.number_input(
                            label, key=widget_key, help=metadata["help"],
                            step=float(setting_increment(field, default)),
                        )
                with reset_column:
                    if st.form_submit_button(
                        "↶", help=f"Reset draft to default: {default}",
                        disabled=not modified, width="stretch",
                        key=f"reset_draft_{form_key}_{field}",
                    ):
                        reset_field = field
                st.caption(metadata["help"])

        st.divider()
        apply_column, defaults_column = st.columns([3, 2])
        apply_clicked = apply_column.form_submit_button(
            "Apply settings", type="primary", width="stretch", key=f"apply_{form_key}",
        )
        reset_all_clicked = defaults_column.form_submit_button(
            "Reset draft to model defaults", width="stretch", key=f"reset_all_{form_key}",
        )

    if reset_field is not None:
        st.session_state[f"setting_draft_{reset_field}"] = DEFAULT_SETTINGS[reset_field]
        st.rerun()
    if reset_all_clicked:
        for field in fields:
            st.session_state[f"setting_draft_{field}"] = DEFAULT_SETTINGS[field]
        st.rerun()
    if apply_clicked:
        for field in fields:
            settings[field] = st.session_state[f"setting_draft_{field}"]
        st.success("Settings applied. This configuration will be used by the model.")

    if show_docs_link:
        st.markdown(f"[Open the Pythermogis theory documentation]({THEORY_URL})")


def is_depth_property(variable: str) -> bool:
    """Identify properties whose colour scale should run shallow-to-deep in reverse."""
    key = variable.lower().replace("_", " ")
    return any(token in key for token in ("depth", "top reservoir", "reservoir top", "burial"))


def boundary_for_grid(boundary, grid):
    """Return a boundary transformed to the grid CRS or the selected Danish fallback CRS."""
    if boundary is None:
        return None
    grid_crs = getattr(grid.rio, "crs", None)
    target_crs = grid_crs or st.session_state.get("boundary_grid_crs", "EPSG:23032")
    prepared = boundary.copy()
    if target_crs:
        if prepared.crs is None:
            prepared = prepared.set_crs(target_crs, allow_override=True)
        elif str(prepared.crs) != str(target_crs):
            prepared = prepared.to_crs(target_crs)
    return prepared


def plot_boundary_overlay(ax, grid, boundary) -> None:
    """Draw a boundary visibly without allowing it to change the raster map extent."""
    prepared = boundary_for_grid(boundary, grid)
    if prepared is None or prepared.empty:
        return
    x_limits, y_limits = ax.get_xlim(), ax.get_ylim()
    geometry_types = prepared.geom_type.fillna("")
    line_mask = geometry_types.isin(["LineString", "MultiLineString"])
    polygon_mask = geometry_types.isin(["Polygon", "MultiPolygon"])
    point_mask = geometry_types.isin(["Point", "MultiPoint"])
    style = {"color": "#ff3b30", "alpha": 0.95, "zorder": 20}
    if line_mask.any():
        prepared.loc[line_mask].plot(ax=ax, linewidth=1.0, **style)
    if polygon_mask.any():
        prepared.loc[polygon_mask].boundary.plot(ax=ax, linewidth=1.0, **style)
    if point_mask.any():
        prepared.loc[point_mask].plot(ax=ax, markersize=8, **style)
    ax.set_xlim(x_limits)
    ax.set_ylim(y_limits)


def show_result_map(dataset: xr.Dataset, boundary) -> None:
    variable = st.selectbox(
        "Result variable to inspect", list(dataset.data_vars), key="result_grid_variable",
        format_func=lambda name: RESULT_METADATA.get(name, {}).get("label", name.replace("_", " ").title()),
    )
    result_column, dataset_column = st.columns(2, gap="large")
    with result_column:
        show_grid_viewer(
            dataset,
            boundary,
            key_prefix="result_grid",
            title="Result map and statistics",
            variable=variable,
            compact=True,
        )
    with dataset_column:
        metadata = RESULT_METADATA.get(variable)
        st.markdown("#### What this result means")
        if metadata:
            st.markdown(f"**{metadata['label']}**")
            st.caption(f"NetCDF variable: `{variable}` · Unit: **{metadata['unit']}**")
            st.write(metadata["calculation"])
        else:
            unit = dataset[variable].attrs.get("units", "not documented in the dataset")
            long_name = dataset[variable].attrs.get("long_name", variable.replace("_", " ").title())
            st.markdown(f"**{long_name}**")
            st.caption(f"NetCDF variable: `{variable}` · Unit: **{unit}**")
            st.info("No Pythermogis calculation note is registered for this additional variable; dataset attributes are shown instead.")
        st.markdown(
            "The technical outputs come from the coupled reservoir/well pressure and energy "
            "balances. Economic outputs combine the resulting power and energy with CAPEX, "
            "OPEX, tax, financing, inflation, and discounting assumptions."
        )
        st.markdown(f"[Read the underlying calculation theory]({THEORY_URL})")
        st.divider()
        st.metric("Result variables", len(dataset.data_vars))
        st.caption(f"Dataset dimensions: {dict(dataset.sizes)}")


def show_grid_viewer(
    dataset: xr.Dataset,
    boundary,
    key_prefix: str = "input_grid",
    *,
    title: str = "2D grid viewer and histogram",
    variable: str | None = None,
    compact: bool = False,
    show_histogram: bool = True,
) -> None:
    """Inspect any loaded geology grid without having to run a simulation."""
    if compact:
        st.markdown(f"#### {title}")
    else:
        st.subheader(title)
    if variable is None:
        variable = st.selectbox("Grid to inspect", list(dataset.data_vars), key=f"{key_prefix}_variable")
    else:
        st.caption(f"Grid: `{variable}`")
    grid = dataset[variable]

    # A realization, percentile, or time dimension is normally the leading
    # dimension.  Slice every non-spatial dimension until a map can be shown.
    spatial_dims = {"x", "y", "longitude", "latitude", "lon", "lat"}
    for dim in list(grid.dims):
        if dim not in spatial_dims and grid.ndim > 2:
            index = st.slider(
                f"{dim} index",
                min_value=0,
                max_value=grid.sizes[dim] - 1,
                value=0,
                key=f"{key_prefix}_{variable}_{dim}",
            )
            grid = grid.isel({dim: index})

    def render_map() -> None:
        fig, ax = plt.subplots(figsize=(5.8, 3.7) if compact else (7, 4.5))
        if grid.ndim == 2:
            x_dim = "x" if "x" in grid.dims else grid.dims[-1]
            y_dim = "y" if "y" in grid.dims else grid.dims[0]
            grid.plot(
                ax=ax,
                x=x_dim,
                y=y_dim,
                cmap="viridis_r" if is_depth_property(variable) else "viridis",
            )
            if boundary is not None:
                try:
                    plot_boundary_overlay(ax, grid, boundary)
                except Exception as exc:
                    st.warning(f"Boundary could not be overlaid: {exc}")
        elif grid.ndim == 1:
            grid.plot(ax=ax)
        else:
            ax.text(0.5, 0.5, f"Scalar value: {grid.item():g}", ha="center", va="center")
            ax.set_axis_off()
        ax.set_title(variable)
        if grid.ndim == 2:
            ax.set_aspect("equal", adjustable="box")
            ax.tick_params(labelsize=5)
            ax.set_xlabel(ax.get_xlabel(), fontsize=6)
            ax.set_ylabel(ax.get_ylabel(), fontsize=6)
            if len(fig.axes) > 1:
                fig.axes[-1].tick_params(labelsize=5)
        st.pyplot(fig, clear_figure=True)

    def render_summary() -> None:
        values = grid.values
        finite = values[~np.isnan(values)]
        geometry = grid_geometry(xr.Dataset({"selected_grid": grid}))
        metric_columns = st.columns(3) if compact else None
        if geometry["dx"] is not None:
            if compact:
                metric_columns[0].metric("Cell size", f"{geometry['dx']:,.0f} × {geometry['dy']:,.0f} m")
            else:
                st.metric("Cell size X", f"{geometry['dx']:,.0f} m")
                st.metric("Cell size Y", f"{geometry['dy']:,.0f} m")
        if compact:
            metric_columns[1].metric("Grid cells", f"{geometry['cell_count']:,}")
            metric_columns[2].metric("Active / valid cells", f"{finite.size:,}")
        else:
            st.metric("Grid cells", f"{geometry['cell_count']:,}")
            st.metric("Active / valid cells", f"{finite.size:,}")
        if finite.size:
            if not compact:
                st.metric("Minimum", f"{finite.min():.4g}")
                st.metric("Maximum", f"{finite.max():.4g}")
                st.metric("Mean", f"{finite.mean():.4g}")
            if show_histogram:
                histogram, histogram_axis = plt.subplots(figsize=(5.8, 2.1) if compact else (3.6, 2.5))
                histogram_axis.hist(finite.ravel(), bins=40, color="#1f77b4", edgecolor="white")
                histogram_axis.set_title(f"Distribution — min {finite.min():.4g}, mean {finite.mean():.4g}, max {finite.max():.4g}", fontsize=7)
                histogram_axis.set_xlabel(variable, fontsize=6)
                histogram_axis.set_ylabel("Cells", fontsize=6)
                histogram_axis.tick_params(labelsize=5)
                st.pyplot(histogram, clear_figure=True)
        st.caption(f"Dimensions: {dict(grid.sizes)}")
        grid_crs = getattr(grid.rio, "crs", None)
        assumed_crs = st.session_state.get("boundary_grid_crs", "EPSG:23032")
        st.caption(f"CRS: {grid_crs or f'not stored; boundary overlay assumes {assumed_crs}'}")

    if compact:
        render_map()
        render_summary()
    else:
        left, right = st.columns([3, 1])
        with left:
            render_map()
        with right:
            render_summary()


def load_boundary_upload(project_name: str) -> None:
    """Persist and load a project boundary for all geology and result viewers."""
    boundary_folder = project_data_root(project_name) / "input_data" / "boundaries"
    boundary_folder.mkdir(parents=True, exist_ok=True)
    with st.expander("Boundary shapefile overlay", expanded=False):
        st.selectbox(
            "Grid CRS used when the grids do not store one",
            ["EPSG:23032", "EPSG:25832"],
            format_func=lambda value: {
                "EPSG:23032": "ED50 / UTM zone 32N (EPSG:23032)",
                "EPSG:25832": "ETRS89 / UTM zone 32N (EPSG:25832)",
            }[value],
            key="boundary_grid_crs",
            help="The Danish ZMAP files do not contain CRS metadata. Select the coordinate system represented by their x/y coordinates.",
        )
        shape_files = st.file_uploader(
            "Optional .shp bundle",
            type=["shp", "shx", "dbf", "prj", "cpg"],
            accept_multiple_files=True,
            key="boundary_shapefile_upload",
            help="Select the .shp, .shx, .dbf, and .prj files together. The boundary is shown on input and result maps.",
        )
        if shape_files:
            try:
                for item in shape_files:
                    (boundary_folder / item.name).write_bytes(item.getvalue())
            except Exception as exc:
                st.error(f"Could not save the shapefile bundle: {exc}")

        project_boundaries = sorted(
            (project_data_root(project_name) / "input_data").rglob("*.shp"),
            key=lambda path: path.name.lower(),
        )
        if project_boundaries:
            import geopandas as gpd

            preferred_text = st.session_state.get("boundary_source_path", "")
            preferred = next(
                (path for path in project_boundaries if str(path) == preferred_text),
                project_boundaries[0],
            )
            selected_boundary = st.selectbox(
                "Project boundary",
                project_boundaries,
                index=project_boundaries.index(preferred),
                format_func=lambda path: path.name,
                key="project_boundary_selector",
            )
            try:
                boundary = gpd.read_file(selected_boundary)
                st.session_state.boundary = boundary
                st.session_state.boundary_source_path = str(selected_boundary)
                bounds = boundary.total_bounds
                st.success(
                    f"Boundary active: {selected_boundary.name} — {len(boundary):,} feature(s), "
                    f"CRS {boundary.crs or 'not defined'}."
                )
                st.caption(
                    f"Bounds: x {bounds[0]:,.0f}–{bounds[2]:,.0f}; "
                    f"y {bounds[1]:,.0f}–{bounds[3]:,.0f}"
                )
            except Exception as exc:
                st.error(f"Could not read the shapefile bundle: {exc}")
        else:
            st.caption("No project boundary is stored yet. Upload the .shp, .shx, .dbf, and .prj files together.")


def typed_project_file_importer(
    project_name: str,
    subfolder_key: str,
    *,
    allowed_types: list[str],
    label: str,
    requirements_text: str | None = None,
) -> list[Path]:
    """Show files already present for a geology mode and allow more files to be copied in."""
    input_folder = project_data_root(project_name) / INPUT_SUBFOLDERS[subfolder_key]
    input_folder.mkdir(parents=True, exist_ok=True)
    st.caption(f"Active input folder: `{input_folder}`")
    existing_files = [
        path for path in project_files(project_name, INPUT_SUBFOLDERS[subfolder_key])
        if path.suffix.lower().lstrip(".") in allowed_types
    ]
    with st.expander("Add files to this geology input folder", expanded=False):
        if requirements_text:
            st.markdown(requirements_text)
        new_files = st.file_uploader(
            label,
            type=allowed_types,
            accept_multiple_files=True,
            key=f"typed_input_upload_{subfolder_key}",
            help="Use the file explorer to select one or more files. They are copied into this project's matching input folder.",
        )
        if new_files and st.button("Copy selected files into this project folder", key=f"save_typed_input_{subfolder_key}"):
            saved = []
            for upload in new_files:
                destination = input_folder / upload.name
                destination.write_bytes(upload.getvalue())
                saved.append(destination)
            st.success(f"Copied {len(saved)} file(s) to {input_folder}")
            st.rerun()
    if existing_files:
        st.caption(f"Found {len(existing_files)} compatible file(s) already in this folder.")
    else:
        st.warning("No compatible files found yet. Add files above to continue.")
    return existing_files


DEFAULT_FACIES_COLORS = [
    "#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd",
    "#8c564b", "#e377c2", "#7f7f7f", "#bcbd22", "#17becf",
]


def default_facies_color(position: int) -> str:
    return DEFAULT_FACIES_COLORS[position % len(DEFAULT_FACIES_COLORS)]


def read_facies_definition(path: Path | None) -> dict:
    if path is None or not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        st.warning(f"Could not read facies definition JSON: {exc}")
        return {}


MAX_AUTOMATIC_STATISTICS_BYTES = 250 * 1024 * 1024


@st.cache_data(show_spinner=False)
def cached_input_grid_statistics(
    path_text: str,
    modified_ns: int,
    size_bytes: int,
) -> dict[str, object]:
    """Calculate useful input-grid statistics once per file version."""
    del modified_ns  # Included in the cache key so edited files are recalculated.
    if size_bytes > MAX_AUTOMATIC_STATISTICS_BYTES:
        return {
            "status": f"Skipped: file is {size_bytes / 1024**2:,.0f} MB",
            "active_cells": None,
            "minimum": None,
            "mean": None,
            "maximum": None,
        }
    try:
        grid = load_grid_source(Path(path_text))
        values = np.asarray(grid.values, dtype=float).ravel()
        finite = values[np.isfinite(values)]
        if finite.size:
            sentinel = (finite <= -7_000.0) | np.isclose(finite, -999.0)
            finite = finite[~sentinel]
        if not finite.size:
            return {
                "status": "No valid numeric cells",
                "active_cells": 0,
                "minimum": None,
                "mean": None,
                "maximum": None,
            }
        return {
            "status": "OK",
            "active_cells": int(finite.size),
            "minimum": float(np.min(finite)),
            "mean": float(np.mean(finite)),
            "maximum": float(np.max(finite)),
        }
    except Exception as exc:
        return {
            "status": f"Could not inspect: {exc}",
            "active_cells": None,
            "minimum": None,
            "mean": None,
            "maximum": None,
        }


def input_grid_interpretation(field: str, path: Path, statistics: dict[str, object]) -> str:
    """Suggest likely porosity/permeability units from filenames and values."""
    minimum = statistics.get("minimum")
    mean = statistics.get("mean")
    maximum = statistics.get("maximum")
    if minimum is None or mean is None or maximum is None:
        return str(statistics.get("status", "Not inspected"))
    name = path.stem.lower()
    if field == "porosity":
        if minimum >= 0 and maximum <= 1.0:
            return "Likely fraction (0–1)"
        if minimum >= 0 and maximum <= 100.0:
            return "Likely percent (0–100)"
        return "Porosity range needs review"
    if field in {"permeability_mean", "permeability_sd", "permeability"}:
        explicitly_log = any(token in name for token in ("ln_perm", "lnperm", "log_perm", "logperm"))
        if explicitly_log:
            return "Filename indicates ln(permeability)"
        if minimum <= 0:
            return "Contains ≤0; cannot apply ln() directly"
        if maximum > 20 or mean > 15:
            return "Likely raw permeability in mD"
        return "Positive but unit is ambiguous; check source metadata"
    return ""


def format_grid_statistic(value: object) -> str:
    if value is None:
        return "—"
    return f"{float(value):.5g}"


def generate_standard_deviation_grid(
    mean_grid: xr.DataArray, mode: str, value: float,
) -> xr.DataArray:
    """Generate an SD grid from a constant or a percentage-based rule."""
    valid = np.isfinite(mean_grid)
    if mode == "Constant SD":
        generated = xr.where(valid, float(value), np.nan)
    elif mode == "Percentage of local mean":
        generated = xr.where(valid, np.abs(mean_grid) * float(value) / 100.0, np.nan)
    elif mode == "Percentage of spatial mean (constant)":
        spatial_mean = float(np.abs(mean_grid).mean(skipna=True))
        generated = xr.where(valid, spatial_mean * float(value) / 100.0, np.nan)
    else:
        raise ValueError(f"Unsupported standard-deviation generation mode: {mode}")
    return generated.astype(float)


def facies_definition_panel(project_name: str, subfolder_key: str, grdecls: list[Path]) -> dict:
    """Load and edit a compact project facies definition."""
    input_folder = project_data_root(project_name) / INPUT_SUBFOLDERS[subfolder_key]
    input_folder.mkdir(parents=True, exist_ok=True)
    json_files = sorted(input_folder.glob("*.json"), key=lambda p: p.name.lower())
    with st.expander("Facies definitions", expanded=False):
        uploaded = st.file_uploader(
            "Upload facies definition JSON",
            type=["json"],
            key=f"facies_definition_upload_{subfolder_key}",
            help="Load a GO-Forward facies_config.json. It is copied into this geology input folder.",
        )
        if uploaded is not None and st.button("Use uploaded definition", key=f"save_facies_definition_{subfolder_key}"):
            destination = input_folder / "facies_config.json"
            destination.write_bytes(uploaded.getvalue())
            st.success(f"Saved {destination.name}")
            st.rerun()

        selected_json: Path | None = None
        if json_files:
            preferred = next((path for path in json_files if path.name.lower() == "facies_config.json"), json_files[0])
            selected_json = st.selectbox(
                "Definition file",
                json_files,
                index=json_files.index(preferred),
                format_func=lambda p: p.name,
                key=f"facies_definition_select_{subfolder_key}",
            )
        else:
            selected_json = input_folder / "facies_config.json"
            st.caption("No definition file yet. Upload one, or define detected facies below.")

        payload = read_facies_definition(selected_json)
        names = {int(k): str(v) for k, v in payload.get("facies_names", {}).items()} if payload else {}
        colors = {int(k): str(v) for k, v in payload.get("facies_colors", {}).items()} if payload else {}
        metadata = {
            int(k): v for k, v in payload.get("facies_metadata", {}).items() if isinstance(v, dict)
        } if payload else {}
        codes = sorted(set(names) | set(colors) | set(metadata))
        if not codes and grdecls:
            try:
                properties = cached_grdecl_properties(str(grdecls[0]))
                facies_property = preferred_grdecl_property(properties, ("FACIES", "ROCKTYPE", "LITHO"), properties[0])
                sample = cached_grdecl_dataframe(str(grdecls[0]), facies_property, 250_000)
                codes = sorted(pd.to_numeric(sample[facies_property], errors="coerce").dropna().round().astype(int).unique())
                payload["facies_property"] = facies_property
            except Exception:
                codes = []

        if not codes:
            st.info("Select a GRDECL or upload a facies definition to edit names and colours.")
            return payload

        version = hashlib.sha1(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()[:10]
        edited_names: dict[int, str] = {}
        edited_colors: dict[int, str] = {}
        edited_metadata: dict[int, dict] = {}
        st.caption("Edit the geological name, display colour, and reservoir category. Save once; the viewer uses this definition automatically.")
        for position, code in enumerate(codes):
            item = metadata.get(code, {})
            current_category = str(item.get("category", "reservoir" if item.get("reservoir", item.get("is_reservoir", False)) else "non_reservoir"))
            columns = st.columns([0.55, 2.25, 0.9, 1.5])
            columns[0].write(f"**{code}**")
            edited_names[code] = columns[1].text_input(
                "Name", names.get(code, f"Facies {code}"), key=f"facies_{subfolder_key}_{version}_name_{code}", label_visibility="collapsed"
            )
            edited_colors[code] = columns[2].color_picker(
                "Colour", colors.get(code, default_facies_color(position)), key=f"facies_{subfolder_key}_{version}_color_{code}", label_visibility="collapsed"
            )
            edited_metadata[code] = dict(item)
            edited_metadata[code]["category"] = columns[3].selectbox(
                "Category", ["reservoir", "non_reservoir"],
                index=0 if current_category == "reservoir" else 1,
                key=f"facies_{subfolder_key}_{version}_category_{code}", label_visibility="collapsed",
            )
        if st.button("Save facies definitions", key=f"save_facies_edits_{subfolder_key}_{version}"):
            payload["facies_names"] = {str(code): edited_names[code] for code in codes}
            payload["facies_colors"] = {str(code): edited_colors[code] for code in codes}
            payload["facies_metadata"] = {str(code): edited_metadata[code] for code in codes}
            selected_json.parent.mkdir(parents=True, exist_ok=True)
            selected_json.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
            st.success("Facies definitions saved.")
            st.rerun()
        return payload


@st.cache_data(show_spinner=False)
def cached_grdecl_properties(path_text: str) -> list[str]:
    return grdecl_property_keywords(Path(path_text))


@st.cache_data(show_spinner=False)
def cached_grdecl_dimensions(path_text: str) -> tuple[int, int, int]:
    return grdecl_dimensions(Path(path_text))


@st.cache_data(show_spinner=False)
def cached_grdecl_dataframe(path_text: str, property_keyword: str, max_rows: int) -> pd.DataFrame:
    return grdecl_inspection_dataframe(Path(path_text), property_keyword, max_rows=max_rows)


def _facies_names_and_colors(payload: dict) -> tuple[dict[int, str], dict[int, str]]:
    names = {int(k): str(v) for k, v in payload.get("facies_names", {}).items()} if payload else {}
    colors = {int(k): str(v) for k, v in payload.get("facies_colors", {}).items()} if payload else {}
    return names, colors


def _is_discrete_property(property_name: str, series: pd.Series) -> bool:
    key = property_name.lower()
    if any(token in key for token in ("facies", "rocktype", "litho")):
        numeric = pd.to_numeric(series, errors="coerce").dropna()
        return not numeric.empty and np.allclose(numeric, np.round(numeric))
    return False


def _valid_grdecl_continuous_values(series: pd.Series) -> pd.Series:
    """Return numeric GRDECL values with common undefined sentinels masked."""
    values = pd.to_numeric(series, errors="coerce").astype(float)
    valid = np.isfinite(values) & (values > -7_000.0) & ~np.isclose(values, -999.0)
    return values.where(valid)


def _plot_grdecl_scatter(df: pd.DataFrame, property_name: str, payload: dict, *, mode: str, key: str) -> None:
    names, colors = _facies_names_and_colors(payload)
    work = df.copy()
    values = pd.to_numeric(work[property_name], errors="coerce")
    discrete = _is_discrete_property(property_name, work[property_name])
    if not discrete:
        values = _valid_grdecl_continuous_values(work[property_name])
        valid_rows = values.notna()
        work = work.loc[valid_rows].copy()
        values = values.loc[valid_rows]
        if work.empty:
            st.warning("This slice contains no valid property values after undefined GRDECL sentinels were removed.")
            return
    fig = go.Figure()
    reverse_colors = is_depth_property(property_name)

    if mode == "Map":
        x_field, y_field = "X", "Y"
        title = "K-layer map"
    elif mode == "Cross-section I":
        x_field, y_field = "J", "Z"
        title = "I-column cross-section"
    elif mode == "Cross-section J":
        x_field, y_field = "I", "Z"
        title = "J-row cross-section"
    else:
        if "perm" in property_name.lower():
            values = np.log10(values.clip(lower=1e-12))
        fig.add_trace(
            go.Scatter3d(
                x=work["X"],
                y=work["Y"],
                z=work["Z"],
                mode="markers",
                marker={
                    "size": 2, "color": values, "colorscale": "Viridis",
                    "reversescale": reverse_colors, "colorbar": {"title": property_name},
                },
                customdata=work[["I", "J", "K", "CellIndex", property_name]].to_numpy(),
                hovertemplate=(
                    f"<b>{property_name}: %{{customdata[4]}}</b><br>"
                    "I,J,K: %{customdata[0]}, %{customdata[1]}, %{customdata[2]}<br>"
                    "CellIndex: %{customdata[3]}<extra></extra>"
                ),
            )
        )
        fig.update_layout(height=460, margin=dict(l=10, r=10, t=35, b=10), scene={"aspectmode": "data"})
        st.plotly_chart(fig, use_container_width=True, key=key)
        return

    if discrete:
        cats = sorted(int(v) for v in values.dropna().round().unique())
        for pos, cat in enumerate(cats):
            mask = values.round().astype("Int64") == cat
            label = f"{cat} — {names[cat]}" if cat in names else f"Facies {cat}"
            fig.add_trace(
                go.Scattergl(
                    x=work.loc[mask, x_field],
                    y=work.loc[mask, y_field],
                    mode="markers",
                    name=label,
                    marker={"size": 4, "color": colors.get(cat, default_facies_color(pos))},
                    customdata=work.loc[mask, ["I", "J", "K", "CellIndex", property_name]].to_numpy(),
                    hovertemplate=(
                        f"<b>{label}</b><br>"
                        "I,J,K: %{customdata[0]}, %{customdata[1]}, %{customdata[2]}<br>"
                        "CellIndex: %{customdata[3]}<extra></extra>"
                    ),
                )
            )
    else:
        plot_values = values
        colorbar_title = property_name
        if "perm" in property_name.lower():
            plot_values = np.log10(values.clip(lower=1e-12))
            colorbar_title = f"{property_name} log10"
        fig.add_trace(
            go.Scattergl(
                x=work[x_field],
                y=work[y_field],
                mode="markers",
                marker={
                    "size": 4, "color": plot_values, "colorscale": "Viridis",
                    "reversescale": reverse_colors, "colorbar": {"title": colorbar_title},
                },
                customdata=work[["I", "J", "K", "CellIndex", property_name]].to_numpy(),
                hovertemplate=(
                    f"<b>{property_name}: %{{customdata[4]}}</b><br>"
                    "I,J,K: %{customdata[0]}, %{customdata[1]}, %{customdata[2]}<br>"
                    "CellIndex: %{customdata[3]}<extra></extra>"
                ),
            )
        )

    fig.update_layout(height=420, margin=dict(l=10, r=10, t=35, b=10), title=title)
    if mode == "Map":
        fig.update_yaxes(scaleanchor="x", scaleratio=1)
    else:
        fig.update_yaxes(autorange="reversed", title="Z")
    st.plotly_chart(fig, use_container_width=True, key=key)


def grdecl_inspection_panel(grdecls: list[Path], facies_payload: dict, *, key_prefix: str) -> None:
    """Inspect selected GRDECL properties before generating 2D Pythermogis maps."""
    if not grdecls:
        st.info("Select a GRDECL to inspect its layers and properties.")
        return
    st.subheader("Inspect GRDECL before conversion")
    selected_grdecl = st.selectbox(
        "GRDECL to inspect",
        grdecls,
        format_func=lambda p: p.name,
        key=f"{key_prefix}_inspect_grdecl",
    )
    try:
        nx, ny, nz = cached_grdecl_dimensions(str(selected_grdecl))
        properties = cached_grdecl_properties(str(selected_grdecl))
    except Exception as exc:
        st.error(f"Could not inspect GRDECL: {exc}")
        return
    st.caption(f"Grid dimensions: {nx} × {ny} × {nz} = {nx * ny * nz:,} cells")
    if not properties:
        st.warning("No cell-sized GRDECL properties were detected.")
        return

    preferred = next((name for name in ("Facies", "FACIES", "RockType", "ROCKTYPE") if name in properties), properties[0])
    c1, c2 = st.columns([2, 1])
    property_name = c1.selectbox(
        "Property to inspect",
        properties,
        index=properties.index(preferred),
        key=f"{key_prefix}_inspect_property",
        help="This list includes cell-sized GRDECL properties such as Facies, PORO/POROMEAN, and PERMX/PERMMEAN when present.",
    )
    max_rows = c2.selectbox(
        "Viewer sample limit",
        [25_000, 50_000, 100_000, 150_000, 250_000],
        index=2,
        format_func=lambda n: f"{n:,} cells",
        key=f"{key_prefix}_inspect_rows",
    )
    try:
        df = cached_grdecl_dataframe(str(selected_grdecl), property_name, int(max_rows))
    except Exception as exc:
        st.error(f"Could not load GRDECL property `{property_name}`: {exc}")
        return

    numeric = pd.to_numeric(df[property_name], errors="coerce")
    if _is_discrete_property(property_name, df[property_name]):
        counts = numeric.dropna().round().astype(int).value_counts().sort_index()
        st.caption(f"{len(counts)} facies code(s) occur in the displayed sample. Names and colours come from the saved facies definition.")
    else:
        stats = _valid_grdecl_continuous_values(df[property_name]).dropna()
        if not stats.empty:
            a, b, c = st.columns(3)
            a.metric("Min", f"{stats.min():.4g}")
            b.metric("Mean", f"{stats.mean():.4g}")
            c.metric("Max", f"{stats.max():.4g}")
            st.caption("Undefined GRDECL values such as -7777, -77777, and -999 are excluded from statistics and colour scaling.")

    view = st.radio("GRDECL viewer", ["Map", "Cross-section I", "Cross-section J", "3D", "Data table"], horizontal=True, key=f"{key_prefix}_view")
    plot_df = df
    if view == "Map":
        selected_k = st.slider("K layer", int(df["K"].min()), int(df["K"].max()), int(df["K"].median()), key=f"{key_prefix}_k")
        plot_df = df[df["K"] == selected_k]
    elif view == "Cross-section I":
        selected_i = st.slider("Grid column I", int(df["I"].min()), int(df["I"].max()), int(df["I"].median()), key=f"{key_prefix}_i")
        plot_df = df[df["I"] == selected_i]
    elif view == "Cross-section J":
        selected_j = st.slider("Grid row J", int(df["J"].min()), int(df["J"].max()), int(df["J"].median()), key=f"{key_prefix}_j")
        plot_df = df[df["J"] == selected_j]

    if view == "Data table":
        st.dataframe(df.head(2_000), use_container_width=True)
    elif plot_df.empty:
        st.warning("No sampled cells in this slice. Increase the viewer sample limit or choose another slice.")
    else:
        _plot_grdecl_scatter(plot_df, property_name, facies_payload, mode=view, key=f"{key_prefix}_{view}")



def preferred_grdecl_property(properties: list[str], tokens: tuple[str, ...], fallback: str) -> str:
    exact = {name.upper(): name for name in properties}
    for token in tokens:
        if token.upper() in exact:
            return exact[token.upper()]
    for name in properties:
        lower = name.lower()
        if any(token.lower() in lower for token in tokens):
            return name
    return fallback


def project_sidebar() -> str:
    """Create/select a dashboard project."""
    st.subheader("Project")
    existing = list_projects()
    if "best-fit" not in existing and (ROOT / "data" / "best-fit").exists():
        existing = ["best-fit"] + existing
    selected = st.selectbox(
        "Existing projects",
        existing or ["demo-project"],
        index=0,
        help="Projects live under data/<project>/input_data and data/<project>/output_data.",
    )
    new_project = st.text_input("Create new project", placeholder="e.g. Gassum Denmark")
    if st.button("Create / use project"):
        try:
            selected = safe_project_name(new_project or selected)
            ensure_project(selected)
            st.session_state.active_project = selected
            st.success(f"Using project: {selected}")
        except Exception as exc:
            st.error(f"Could not create project: {exc}")
    if "active_project" not in st.session_state:
        st.session_state.active_project = safe_project_name(selected)
        ensure_project(st.session_state.active_project)

    active = st.session_state.active_project
    st.caption(f"Input: `{project_input_dir(active)}`")
    st.caption(f"Output: `{project_output_dir(active)}`")

    input_count = sum(len(project_files(active, folder)) for folder in INPUT_SUBFOLDERS.values())
    output_count = sum(len(project_files(active, folder)) for folder in OUTPUT_SUBFOLDERS.values())
    st.caption(f"Typed project files: {input_count} input, {output_count} output")
    return active


def pos_map(results: xr.Dataset) -> xr.DataArray:
    """Calculate probability of positive NPV without requiring the Java runtime."""
    def calculate(npv, p_values):
        if np.all(np.diff(npv) > 0):
            return 100 - np.interp(0.0, npv, p_values)
        return np.interp(0.0, npv[::-1], p_values[::-1])

    return xr.apply_ufunc(
        calculate, results["npv"], results["p_value"],
        input_core_dims=[["p_value"], ["p_value"]], vectorize=True,
        output_dtypes=[float], dask="parallelized",
    ).rename("POS")


def show_location_analysis(results: xr.Dataset, boundary) -> None:
    if "npv" not in results or "p_value" not in results or "x" not in results.coords or "y" not in results.coords:
        return
    st.subheader("Location analysis")
    pos = results["pos"] if "pos" in results else pos_map(results)
    method = st.radio("Location source", ["XY coordinates", "Select point on POS map", "Address"], horizontal=True)
    x, y = float(pos.x.mean()), float(pos.y.mean())
    if method == "XY coordinates":
        col_x, col_y = st.columns(2)
        x = col_x.number_input("X coordinate (m)", value=x)
        y = col_y.number_input("Y coordinate (m)", value=y)
    elif method == "Select point on POS map":
        stride_x = max(1, pos.sizes["x"] // 250)
        stride_y = max(1, pos.sizes["y"] // 250)
        preview = pos.isel(x=slice(None, None, stride_x), y=slice(None, None, stride_y))
        click = st.plotly_chart(
            go.Figure(go.Heatmap(x=preview.x.values, y=preview.y.values, z=preview.values, colorscale="Viridis", colorbar={"title": "POS [%]"})),
            use_container_width=True, on_select="rerun", selection_mode="points", key="pos_location_picker",
        )
        selection = getattr(click, "selection", click.get("selection", {}) if isinstance(click, dict) else {})
        points = getattr(selection, "points", selection.get("points", []) if isinstance(selection, dict) else [])
        if points:
            x, y = float(points[0]["x"]), float(points[0]["y"])
            st.success(f"Selected: {x:.0f}, {y:.0f} m")
        else:
            st.caption("Click a cell in the POS map to select its location.")
    else:
        address = st.text_input("Address")
        if st.button("Find address") and address:
            try:
                from geopy.geocoders import Nominatim
                from pyproj import Transformer
                found = Nominatim(user_agent="go-forward-pythermogis").geocode(address)
                if found is None:
                    raise ValueError("Address not found.")
                crs = getattr(pos.rio, "crs", None) or "EPSG:23032"
                x, y = Transformer.from_crs("EPSG:4326", crs, always_xy=True).transform(found.longitude, found.latitude)
                st.session_state.address_location = (x, y)
            except Exception as exc:
                st.error(f"Could not resolve address: {exc}")
        if "address_location" not in st.session_state:
            st.caption("Enter an address and select Find address.")
            return
        x, y = st.session_state.address_location
        st.caption(f"Resolved location: {x:.0f}, {y:.0f} m")

    selected = results.sel(x=x, y=y, method="nearest")
    selected_x, selected_y = float(selected.x), float(selected.y)
    probability = float(pos.sel(x=x, y=y, method="nearest"))
    fig, axes = plt.subplots(ncols=2, figsize=(10, 4.5))
    selected["npv"].plot(y="p_value", ax=axes[0])
    axes[0].axvline(0.0, color="tab:orange", ls="--")
    axes[0].axhline(probability, color="tab:orange", ls="--", label=f"POS: {probability:.1f}%")
    axes[0].legend(fontsize=6)
    axes[0].set_title(f"NPV at [{selected_x:.0f}, {selected_y:.0f}]", fontsize=8)
    axes[0].tick_params(labelsize=6)
    axes[0].set_xlabel("NPV [million EUR]", fontsize=7)
    axes[0].set_ylabel("p-value [%]", fontsize=7)
    pos.plot(ax=axes[1])
    axes[1].scatter(selected_x, selected_y, marker="x", color="tab:red")
    if boundary is not None:
        try:
            plot_boundary_overlay(axes[1], pos, boundary)
        except Exception:
            pass
    axes[1].set_aspect("equal", adjustable="box")
    axes[1].tick_params(labelsize=5)
    plt.tight_layout()
    st.pyplot(fig, clear_figure=True)


header, logo = st.columns([5, 1])
with header:
    st.title("GO-Forward geothermal workflows")
    st.caption("Project-based Pythermogis workflow for 2D grids and GRDECL-derived maps.")
with logo:
    if LOGO_PATH.exists():
        st.image(LOGO_PATH, use_container_width=True)

with st.sidebar:
    active_project = project_sidebar()
    st.divider()
    st.write("Workspace layout")
    st.code(
        "dashboard/\n"
        "data/<project>/input_data/<geology-type>/\n"
        "data/<project>/output_data/<geology-type>/"
    )

workflow = "Pythermogis"

settings = state("settings", default_settings)
dataset = state("dataset", lambda: None)
boundary = state("boundary", lambda: None)
mapping = state("mapping", dict)
results = state("results", lambda: None)

tabs = st.tabs([
    "Geology input", "Well design", "Cost model", "Economic model",
    "Geothermal simulation", "Geothermal results",
])

with tabs[0]:
    st.subheader("Geology input")
    geology_source = st.radio(
        "Geology source",
        [
            "Current 2D grids — deterministic",
            "Current 2D grids — probabilistic",
            "Single GRDECL → deterministic 2D maps",
            "Multiple GRDECLs → probabilistic statistics",
        ],
    )
    source_folder_key = {
        "Current 2D grids — deterministic": "2d_best_fit",
        "Current 2D grids — probabilistic": "2d_probabilistic",
        "Single GRDECL → deterministic 2D maps": "grdecl_best_fit",
        "Multiple GRDECLs → probabilistic statistics": "grdecl_multi",
    }[geology_source]
    st.session_state.active_source_folder_key = source_folder_key
    source_state_key = f"{active_project}|{geology_source}"
    if st.session_state.get("geology_source_state_key") != source_state_key:
        st.session_state.geology_source_state_key = source_state_key
        st.session_state.raw_selected_dataset = None
        st.session_state.dataset = None
        st.session_state.mapping = {}
    stochastic = geology_source in {
        "Current 2D grids — probabilistic",
        "Multiple GRDECLs → probabilistic statistics",
    }
    st.info("Choose the geology source first. The dashboard then uses the matching typed project input folder.")
    if "GRDECL" in geology_source:
        available_input_files = typed_project_file_importer(
            active_project,
            source_folder_key,
            allowed_types=["grdecl", "grd", "inc"],
            label="Select GRDECL file(s) to copy into this project",
            requirements_text=(
                "**Required input:** one GRDECL for the deterministic workflow or multiple "
                "GRDECL realizations for probabilistic statistics. Include geometry and the "
                "reservoir facies/property arrays needed for conversion."
            ),
        )
        facies_payload = {}
    else:
        available_input_files = typed_project_file_importer(
            active_project,
            source_folder_key,
            allowed_types=["nc", "netcdf", "tif", "tiff", "zmap", "asc"],
            label="Select 2D grid file(s) to copy into this project",
            requirements_text=(
                "**Required grid properties:** depth (or top), thickness, net-to-gross (NTG), "
                "porosity, and permeability. A temperature grid is optional because temperature "
                "can instead be calculated from depth and a geothermal gradient."
                + (
                    "\n\n**Probabilistic additions:** standard-deviation grids for thickness "
                    "and permeability. If either is unavailable, it can be generated below from "
                    "a constant or a percentage of the mean grid."
                    if stochastic else ""
                )
            ),
        )
        facies_payload = {}
    load_boundary_upload(active_project)

    selected: xr.Dataset | None = None
    if "GRDECL" in geology_source:
        st.subheader("GRDECL to 2D map conversion")
        chosen_grdecls = st.multiselect(
            f"Select GRDECL file(s) from {INPUT_SUBFOLDERS[source_folder_key]}",
            available_input_files,
            format_func=lambda p: p.name,
            help="Use one file for a deterministic conversion or several files for mean/SD statistics.",
        )
        if geology_source.startswith("Single") and len(chosen_grdecls) > 1:
            st.warning("Single GRDECL mode uses only one file. Select one file, or switch to multiple-GRDECL mode.")
        if geology_source.startswith("Multiple") and len(chosen_grdecls) == 1:
            st.info("Multiple-GRDECL mode needs several realizations to calculate statistics.")
        definition_column, viewer_column = st.columns([0.36, 0.64], gap="large")
        with definition_column:
            facies_payload = facies_definition_panel(active_project, source_folder_key, chosen_grdecls)
        with viewer_column:
            grdecl_inspection_panel(
                chosen_grdecls,
                facies_payload,
                key_prefix=f"grdecl_inspect_{source_folder_key}",
            )

        st.subheader("GRDECL to 2D conversion settings")
        conversion_properties = []
        if chosen_grdecls:
            try:
                conversion_properties = cached_grdecl_properties(str(chosen_grdecls[0]))
            except Exception:
                conversion_properties = []
        property_set_version = hashlib.sha1("|".join(conversion_properties).encode("utf-8")).hexdigest()[:8]
        configured_facies_property = str(facies_payload.get("facies_property", ""))
        facies_default = preferred_grdecl_property(
            conversion_properties,
            tuple(value for value in (configured_facies_property, "FACIES", "ROCKTYPE", "LITHO") if value),
            conversion_properties[0] if conversion_properties else "FACIES",
        )
        first, second = st.columns(2)
        if conversion_properties:
            facies_key = first.selectbox(
                "Facies property used for the reservoir mask",
                conversion_properties,
                index=conversion_properties.index(facies_default) if facies_default in conversion_properties else 0,
                key=f"facies_key_{source_folder_key}_{property_set_version}",
            )
        else:
            facies_key = first.text_input("Facies property used for the reservoir mask", value=facies_default)
        depth_shift = second.number_input("Depth shift (m)", value=0.0)

        facies_names, _ = _facies_names_and_colors(facies_payload)
        facies_metadata = {
            int(code): item for code, item in facies_payload.get("facies_metadata", {}).items() if isinstance(item, dict)
        }
        facies_codes = sorted(set(facies_names) | set(facies_metadata))
        if not facies_codes and chosen_grdecls and facies_key in conversion_properties:
            try:
                facies_df = cached_grdecl_dataframe(str(chosen_grdecls[0]), facies_key, 250_000)
                facies_codes = sorted(pd.to_numeric(facies_df[facies_key], errors="coerce").dropna().round().astype(int).unique())
            except Exception:
                facies_codes = []
        default_reservoir_facies = [
            code for code in facies_codes
            if str(facies_metadata.get(code, {}).get("category", "")).lower() == "reservoir"
            or bool(facies_metadata.get(code, {}).get("reservoir", facies_metadata.get(code, {}).get("is_reservoir", False)))
        ]
        facies_definition_version = hashlib.sha1(
            json.dumps(facies_payload, sort_keys=True).encode("utf-8")
        ).hexdigest()[:8]
        reservoir_facies = st.multiselect(
            "Reservoir facies included in the 2D maps",
            facies_codes,
            default=default_reservoir_facies,
            format_func=lambda code: f"{code} — {facies_names.get(code, f'Facies {code}')}",
            key=f"reservoir_facies_{source_folder_key}_{property_set_version}_{facies_definition_version}",
            help="Thickness, depth, porosity and permeability are aggregated over all selected reservoir facies.",
        )

        st.caption("Choose explicitly whether each map uses a GRDECL property or one constant fallback value.")
        porosity_default = preferred_grdecl_property(
            conversion_properties,
            ("PORO50", "MPOR_TOTAL_P50", "IGPORO50", "PORO", "POROSITY"),
            conversion_properties[0] if conversion_properties else "",
        )
        permeability_default = preferred_grdecl_property(
            conversion_properties,
            ("PERM50", "PERMGEOM", "PERMX", "PERMEABILITY"),
            conversion_properties[0] if conversion_properties else "",
        )
        c4, c5 = st.columns(2)
        porosity_source_options = ["GRDECL property", "Constant fallback"] if conversion_properties else ["Constant fallback"]
        permeability_source_options = ["GRDECL property", "Constant fallback"] if conversion_properties else ["Constant fallback"]
        porosity_source = c4.radio(
            "Porosity source",
            porosity_source_options,
            horizontal=True,
            key=f"porosity_source_{source_folder_key}_{property_set_version}",
        )
        permeability_source = c5.radio(
            "Permeability source",
            permeability_source_options,
            horizontal=True,
            key=f"permeability_source_{source_folder_key}_{property_set_version}",
        )

        porosity_key = ""
        porosity_property_in_percent = False
        grdecl_porosity = 0.2
        if porosity_source == "GRDECL property":
            porosity_key = c4.selectbox(
                "Porosity property",
                conversion_properties,
                index=conversion_properties.index(porosity_default) if porosity_default in conversion_properties else 0,
                key=f"porosity_key_{source_folder_key}_{property_set_version}",
            )
            porosity_unit = c4.selectbox(
                "Porosity property unit",
                ["Percent (0–100) — convert to fraction", "Fraction (0–1)"],
                key=f"grdecl_porosity_unit_{source_folder_key}_{property_set_version}",
                help="Pythermogis requires a fraction. T>Map PORO properties are commonly stored as percent.",
            )
            porosity_property_in_percent = porosity_unit.startswith("Percent")
            c4.caption(f"Using `{porosity_key}` from every selected GRDECL.")
        else:
            grdecl_porosity = c4.number_input(
                "Constant porosity fallback (fraction)", value=0.2, min_value=0.0, max_value=1.0,
                key=f"porosity_fallback_{source_folder_key}_{property_set_version}",
            )

        permeability_key = ""
        grdecl_perm = 100.0
        if permeability_source == "GRDECL property":
            permeability_key = c5.selectbox(
                "Permeability property",
                conversion_properties,
                index=conversion_properties.index(permeability_default) if permeability_default in conversion_properties else 0,
                key=f"permeability_key_{source_folder_key}_{property_set_version}",
            )
            c5.caption(f"Using `{permeability_key}` from every selected GRDECL.")
        else:
            grdecl_perm = c5.number_input(
                "Constant permeability fallback (mD)", value=100.0, min_value=0.001,
                key=f"permeability_fallback_{source_folder_key}_{property_set_version}",
            )

        grdecl_ntg = st.number_input("Constant NTG", value=1.0, min_value=0.0, max_value=1.0)
        grdecl_ln_perm_sd = 0.01
        if stochastic and not permeability_key:
            grdecl_ln_perm_sd = c5.number_input("Fallback ln permeability SD", value=0.01, min_value=0.0)
        if st.button("Generate 2D Pythermogis maps from GRDECL", type="primary"):
            try:
                grdecls_to_convert = chosen_grdecls[:1] if geology_source.startswith("Single") else chosen_grdecls
                with st.spinner("Converting GRDECL realization(s) to 2D maps…"):
                    selected = convert_grdecl_to_dataset(
                        grdecls_to_convert,
                        facies_key=facies_key,
                        reservoir_facies=reservoir_facies,
                        porosity_key=porosity_key.strip(),
                        permeability_key=permeability_key.strip(),
                        porosity_property_in_percent=porosity_property_in_percent,
                        depth_shift=depth_shift,
                        porosity=grdecl_porosity,
                        ntg=grdecl_ntg,
                        permeability=grdecl_perm,
                        ln_permeability_sd=grdecl_ln_perm_sd,
                        output_dir=project_data_root(active_project) / OUTPUT_SUBFOLDERS[source_folder_key] / "generated_2d_maps",
                    )
                st.session_state.raw_selected_dataset = selected
                generated = selected.attrs.get("generated_maps", "")
                st.success(f"Generated {len(selected.data_vars)} maps from {len(grdecls_to_convert)} GRDECL file(s).")
                if generated:
                    st.caption("Generated ZMAP files:")
                    st.code(generated)
                notes = selected.attrs.get("conversion_notes", "")
                if notes:
                    st.warning("Some GRDECL properties used fallback values:")
                    st.code(notes)
            except Exception as exc:
                st.exception(exc)
        selected = st.session_state.get("raw_selected_dataset")
    else:
        run_type = "Probabilistic P10/P50/P90" if stochastic else "Deterministic best-fit"
        st.caption(f"Run type: {run_type}")
        property_fields = (
            ["depth", "thickness", "porosity", "ntg", "permeability"]
            if not stochastic
            else ["depth", "thickness_mean", "thickness_sd", "porosity", "ntg", "permeability_mean", "permeability_sd"]
        )
        uploads = {}
        detected_statistics: dict[str, dict[str, object]] = {}
        chosen_grid_files = st.multiselect(
            f"Select project input grid files from {INPUT_SUBFOLDERS[source_folder_key]}",
            available_input_files,
            default=available_input_files,
            format_func=lambda p: p.name,
            help="Multi-file selector: choose exactly which copied input files should be used.",
        )
        if chosen_grid_files:
            uploads = detect_grid_sources(chosen_grid_files, stochastic)
            detected_rows = []
            with st.spinner("Inspecting detected grid values…"):
                for field in property_fields:
                    source = uploads.get(field)
                    statistics: dict[str, object] = {
                        "status": "Not found", "active_cells": None,
                        "minimum": None, "mean": None, "maximum": None,
                    }
                    if isinstance(source, Path) and source.exists():
                        file_info = source.stat()
                        statistics = cached_input_grid_statistics(
                            str(source), file_info.st_mtime_ns, file_info.st_size
                        )
                    detected_statistics[field] = statistics
                    detected_rows.append(
                        {
                            "Property": field,
                            "Detected file": source.name if source else "Not found",
                            "Active cells": (
                                f"{int(statistics['active_cells']):,}"
                                if statistics.get("active_cells") is not None else "—"
                            ),
                            "Min": format_grid_statistic(statistics.get("minimum")),
                            "Mean": format_grid_statistic(statistics.get("mean")),
                            "Max": format_grid_statistic(statistics.get("maximum")),
                            "Interpretation": (
                                input_grid_interpretation(field, source, statistics)
                                if isinstance(source, Path) else "Not found"
                            ),
                        }
                    )
            st.dataframe(
                detected_rows,
                hide_index=True,
                use_container_width=True,
            )
            st.caption(
                "Statistics use valid numeric cells and exclude common undefined sentinels. "
                f"Automatic inspection is skipped for individual files larger than "
                f"{MAX_AUTOMATIC_STATISTICS_BYTES / 1024**2:,.0f} MB."
            )
            generatable_sd_fields = {"thickness_sd", "permeability_sd"} if stochastic else set()
            missing = [
                field for field in property_fields
                if uploads.get(field) is None and field not in generatable_sd_fields
            ]
            if missing:
                st.warning(
                    f"Could not auto-detect {', '.join(missing)}. "
                    "Check the selected files or rename them to include the matching key."
                )
            missing_sd = [field for field in generatable_sd_fields if uploads.get(field) is None]
            if missing_sd:
                st.info(
                    f"No file was detected for {', '.join(sorted(missing_sd))}. "
                    "You can generate these uncertainty grids below."
                )

        selected_signature = "|".join(
            f"{path.name}:{path.stat().st_mtime_ns}" for path in chosen_grid_files if path.exists()
        )
        controls_version = hashlib.sha1(selected_signature.encode("utf-8")).hexdigest()[:8]
        porosity_statistics = detected_statistics.get("porosity", {})
        porosity_maximum = porosity_statistics.get("maximum")
        porosity_is_probably_percent = (
            porosity_maximum is not None and float(porosity_maximum) > 1.0
        )
        porosity_form = st.radio(
            "Porosity values in the detected file",
            ["fraction", "percent"],
            index=1 if porosity_is_probably_percent else 0,
            horizontal=True,
            format_func=lambda choice: (
                "Already fraction (0–1) — use unchanged"
                if choice == "fraction"
                else "Percent (0–100) — divide by 100"
            ),
            key=f"porosity_representation_{source_folder_key}_{controls_version}",
            help="Pythermogis requires porosity as a fraction.",
        )
        porosity_unit = (
            "Percent (0–100) — convert to fraction"
            if porosity_form == "percent" else "Fraction (0–1)"
        )
        if porosity_maximum is not None:
            if porosity_is_probably_percent and porosity_form == "fraction":
                st.warning(
                    f"Detected porosity has maximum {float(porosity_maximum):.5g}, so it looks like percent. "
                    "Using it unchanged would pass values above 1.0 to Pythermogis."
                )
            elif not porosity_is_probably_percent and porosity_form == "percent":
                st.warning(
                    f"Detected porosity has maximum {float(porosity_maximum):.5g}, so it already looks like a fraction. "
                    "Dividing it by 100 may be incorrect."
                )

        permeability_form = "raw"
        if stochastic:
            permeability_mean_stats = detected_statistics.get("permeability_mean", {})
            permeability_sd_stats = detected_statistics.get("permeability_sd", {})
            mean_source = uploads.get("permeability_mean")
            sd_source = uploads.get("permeability_sd")
            mean_interpretation = (
                input_grid_interpretation("permeability_mean", mean_source, permeability_mean_stats)
                if isinstance(mean_source, Path) else ""
            )
            sd_interpretation = (
                input_grid_interpretation("permeability_sd", sd_source, permeability_sd_stats)
                if isinstance(sd_source, Path) else ""
            )
            likely_raw_permeability = "raw permeability" in mean_interpretation.lower() or "raw permeability" in sd_interpretation.lower()
            likely_log_permeability = "filename indicates ln" in mean_interpretation.lower() and "filename indicates ln" in sd_interpretation.lower()
            permeability_form = st.radio(
                "Permeability values in the two detected files",
                ["raw", "log"],
                index=1 if likely_log_permeability else 0,
                format_func=lambda choice: (
                    "Raw permeability mean + raw SD in mD — apply ln() to both grids"
                    if choice == "raw"
                    else "Already ln(permeability) mean + ln-permeability SD — keep values unchanged"
                ),
                key=f"permeability_representation_{source_folder_key}_{controls_version}",
                help="The Gassum workflow in example 06 applies np.log() independently to GASSUM_perm and GASSUM_perm_sd.",
            )
            if permeability_form == "raw":
                st.info(
                    "Conversion selected: the dashboard will calculate `np.log(permeability_mean)` and "
                    "`np.log(permeability_sd)`. The viewer will then show the transformed grids as "
                    "`ln_permeability_mean` and `ln_permeability_sd`, matching the Gassum notebook workflow."
                )
                if likely_log_permeability:
                    st.warning("Both filenames indicate ln-permeability. Applying ln() again would be a double transformation.")
            else:
                st.info(
                    "No numerical conversion selected: the dashboard will keep both grids unchanged and "
                    "label them `ln_permeability_mean` and `ln_permeability_sd`."
                )
                if likely_raw_permeability:
                    mean_value = permeability_mean_stats.get("mean")
                    st.warning(
                        "The detected values look like raw permeability in mD"
                        + (f" (mean {float(mean_value):.5g})" if mean_value is not None else "")
                        + ". Keeping them unchanged would relabel mD values as ln(permeability). "
                        "Select the raw-mD conversion unless the source metadata explicitly says these are already logarithmic."
                    )

        sd_configuration: dict[str, dict[str, object]] = {}
        if stochastic:
            st.markdown("#### Standard-deviation grid sources")
            st.write(
                "Use detected SD grids, or generate them from the corresponding mean grid. A "
                "percentage of the local mean preserves the same relative uncertainty at every "
                "cell. A percentage of the spatial mean produces one constant SD value and is "
                "therefore simply a convenient way to define a constant from the dataset."
            )
            sd_columns = st.columns(2, gap="large")
            for column, sd_field, mean_field, label, default_constant, default_percentage in [
                (sd_columns[0], "thickness_sd", "thickness_mean", "Thickness SD", 10.0, 10.0),
                (sd_columns[1], "permeability_sd", "permeability_mean", "Permeability SD", 25.0, 25.0),
            ]:
                detected_sd = uploads.get(sd_field) is not None
                source_options = (
                    ["Use detected SD grid", "Constant SD", "Percentage of local mean", "Percentage of spatial mean (constant)"]
                    if detected_sd
                    else ["Constant SD", "Percentage of local mean", "Percentage of spatial mean (constant)"]
                )
                default_index = 0 if detected_sd else 1
                with column:
                    mode = st.selectbox(
                        f"{label} source", source_options, index=default_index,
                        key=f"{sd_field}_generation_mode_{controls_version}",
                    )
                    value = 0.0
                    if mode == "Constant SD":
                        unit_note = "m" if sd_field == "thickness_sd" else (
                            "mD before ln conversion" if permeability_form == "raw" else "ln-permeability units"
                        )
                        value = st.number_input(
                            f"Constant {label} [{unit_note}]", min_value=0.000001,
                            value=default_constant, step=1.0,
                            key=f"{sd_field}_constant_{controls_version}",
                        )
                    elif mode != "Use detected SD grid":
                        value = st.number_input(
                            f"{label} as percentage", min_value=0.1, max_value=500.0,
                            value=default_percentage, step=1.0,
                            key=f"{sd_field}_percentage_{controls_version}",
                        )
                    sd_configuration[sd_field] = {
                        "mode": mode, "value": float(value), "mean_field": mean_field,
                    }
            st.caption(
                "Recommendation: use percentage of the local mean when uncertainty is expected "
                "to scale with local reservoir magnitude. Use a constant when an interpreted or "
                "measurement-derived absolute SD applies across the full map."
            )
            if permeability_form == "log" and sd_configuration["permeability_sd"]["mode"] not in {"Use detected SD grid", "Constant SD"}:
                st.warning(
                    "Percentage-based generation from an already logarithmic permeability mean is "
                    "a heuristic. A constant SD in ln-permeability units is usually easier to interpret."
                )

        temperature_source = st.radio("Temperature", ["Calculate from geothermal gradient", "Upload temperature grid"], horizontal=True)
        if temperature_source == "Upload temperature grid":
            uploads["temperature"] = st.file_uploader("Temperature grid", type=["nc", "netcdf", "tif", "tiff", "zmap", "asc"], key="grid_upload_temperature")
        else:
            settings_editor(
                settings, ["temperature_gradient", "surface_temperature"], "Temperature model",
                "When no temperature grid is supplied, reservoir temperature is calculated from reservoir depth using this linear geothermal-gradient model.",
                show_docs_link=False,
            )
        required = property_fields
        missing_required = [
            field for field in required
            if uploads.get(field) is None
            and not (
                stochastic
                and field in sd_configuration
                and sd_configuration[field]["mode"] != "Use detected SD grid"
            )
        ]
        if not missing_required:
            try:
                grids = {name: load_grid_source(upload) for name, upload in uploads.items() if upload is not None}
                if stochastic:
                    for sd_field, specification in sd_configuration.items():
                        if specification["mode"] == "Use detected SD grid":
                            continue
                        mean_field = str(specification["mean_field"])
                        grids[sd_field] = generate_standard_deviation_grid(
                            grids[mean_field], str(specification["mode"]), float(specification["value"]),
                        ).rename(sd_field)
                porosity_min = float(grids["porosity"].min(skipna=True))
                porosity_max = float(grids["porosity"].max(skipna=True))
                if porosity_unit.startswith("Percent"):
                    if porosity_min < 0 or porosity_max > 100:
                        raise ValueError("Porosity declared as percent must be within 0–100.")
                    grids["porosity"] = grids["porosity"] / 100.0
                elif porosity_min < 0 or porosity_max > 1:
                    raise ValueError(
                        f"Porosity values range from {porosity_min:.3g} to {porosity_max:.3g}. "
                        "They appear to be percentages; choose ‘Percent (0–100) — convert to fraction’."
                    )
                if stochastic:
                    if permeability_form == "raw":
                        if (grids["permeability_mean"] <= 0).any() or (grids["permeability_sd"] <= 0).any():
                            raise ValueError("Permeability mean and SD must be strictly positive before logarithmic conversion.")
                        grids["ln_permeability_mean"] = np.log(grids.pop("permeability_mean"))
                        grids["ln_permeability_sd"] = np.log(grids.pop("permeability_sd"))
                    else:
                        grids["ln_permeability_mean"] = grids.pop("permeability_mean")
                        grids["ln_permeability_sd"] = grids.pop("permeability_sd")
                selected = dataset_from_single_grids(grids)
                st.session_state.raw_selected_dataset = selected
                st.success(f"Loaded {len(grids)} grids; dimensions: {dict(selected.sizes)}")
            except Exception as exc:
                st.error(f"Could not load the best-fit grids: {exc}")
        else:
            st.caption(
                "Provide every required grid or configure generation for missing SD grids to "
                "enable the viewer and simulation. Missing: " + ", ".join(missing_required)
            )

    selected = st.session_state.get("raw_selected_dataset")
    if selected is not None:
        geometry = grid_geometry(selected)
        if geometry["dx"] is not None:
            st.subheader("Validate grid resolution")
            metric_columns = st.columns(3)
            metric_columns[0].metric("Recognised cell size", f"{geometry['dx']:,.0f} × {geometry['dy']:,.0f} m")
            metric_columns[1].metric("Current grid cells", f"{geometry['cell_count']:,}")
            minimum_cellsize = max(float(geometry["dx"]), float(geometry["dy"]))
            top_controls = st.columns([2, 2, 1.4], vertical_alignment="bottom")
            resampling_enabled = top_controls[0].checkbox(
                "Resample to a coarser resolution", value=False,
                help="Leave this off to validate and simulate with the original grid resolution.",
            )
            comparison_variable = top_controls[1].selectbox(
                "Grid to preview and validate", list(selected.data_vars),
                key="resolution_comparison_variable",
            )

            validation_dataset = selected
            validation_label = (
                f"Original grids — no resampling ({geometry['dx']:,.0f} × {geometry['dy']:,.0f} m; "
                f"{geometry['cell_count']:,} cells)"
            )

            if resampling_enabled:
                st.info(
                    "Resampling is enabled. Choose the final cell size and interpolation method "
                    "below. The viewer on the right and the single validation button automatically "
                    "switch to this resampled dataset."
                )
                sampling_scales = [
                    scale for scale in [400.0, 500.0, 1000.0, 2500.0, 5000.0, 10000.0]
                    if scale >= minimum_cellsize
                ]
                if not sampling_scales:
                    sampling_scales = [minimum_cellsize]
                control_columns = st.columns(2, vertical_alignment="bottom")
                selected_scale = control_columns[0].selectbox(
                    "Final sampling scale",
                    [f"{scale:,.0f} × {scale:,.0f} m" for scale in sampling_scales] + ["Custom"],
                    index=sampling_scales.index(5000.0) if 5000.0 in sampling_scales else len(sampling_scales) - 1,
                )
                target_cellsize = (
                    control_columns[0].number_input(
                        "Custom final cell size (m)", min_value=minimum_cellsize,
                        value=minimum_cellsize, step=100.0,
                    )
                    if selected_scale == "Custom"
                    else float(selected_scale.split(" ")[0].replace(",", ""))
                )
                interpolation = control_columns[1].radio(
                    "Resampling method", ["nearest", "linear"], horizontal=True
                )
                estimated_cells = int(geometry["cell_count"] * (minimum_cellsize / target_cellsize) ** 2)
                metric_columns[2].metric("Estimated final cells", f"~{estimated_cells:,}")
                with st.spinner("Creating resampled-grid preview"):
                    validation_dataset = resample_dataset(selected, target_cellsize, interpolation)
                preview_geometry = grid_geometry(validation_dataset)
                validation_label = (
                    f"Resampled grids — {preview_geometry['dx']:,.0f} × {preview_geometry['dy']:,.0f} m; "
                    f"{preview_geometry['cell_count']:,} cells; {interpolation} interpolation"
                )
            else:
                metric_columns[2].metric("Final grid cells", f"{geometry['cell_count']:,}")

            validation_button_label = (
                "Validate resampled grids" if resampling_enabled else "Validate original grids"
            )
            validate_clicked = top_controls[2].button(
                validation_button_label, type="primary", width="stretch",
            )

            original_column, resampled_column = st.columns(2, gap="large")
            with original_column:
                show_grid_viewer(
                    selected, st.session_state.boundary, key_prefix="resolution_original",
                    title="Original grids", variable=comparison_variable, compact=True,
                )
            with resampled_column:
                if resampling_enabled:
                    show_grid_viewer(
                        validation_dataset, st.session_state.boundary, key_prefix="resampled_comparison",
                        title="Resampled-grid preview", variable=comparison_variable, compact=True,
                    )
                else:
                    st.markdown("#### Resampled-grid preview")
                    st.info(
                        "Resampling is off. The validation button currently uses the original grid "
                        "without changing its values, coordinates, cell size, or cell count."
                    )

            st.caption(f"Validation candidate: {validation_label}")
            if validate_clicked:
                st.session_state.dataset = validation_dataset
                st.session_state.mapping = {name: name for name in validation_dataset.data_vars}
                st.session_state.run_type = "stochastic" if stochastic else "deterministic"
                final_geometry = grid_geometry(validation_dataset)
                choice = "resampled" if resampling_enabled else "original, not resampled"
                st.success(
                    f"Validated {choice} simulation grids: {final_geometry['x_cells']} × "
                    f"{final_geometry['y_cells']} = {final_geometry['cell_count']:,} cells at "
                    f"{final_geometry['dx']:,.0f} × {final_geometry['dy']:,.0f} m."
                )
        else:
            show_grid_viewer(selected, st.session_state.boundary, key_prefix="raw_grid")
            st.warning("The grids do not expose x/y coordinates, so their cell size cannot be recognised or resampled.")
with tabs[1]:
    settings_editor(
        settings,
        ["optimize_well_distance", "well_distance", "min_well_distance", "max_well_distance", "max_flow", "pump_efficiency", "pump_depth", "outer_diameter", "inner_diameter", "injector_skin", "producer_skin"],
        "Well design",
        "The doublet model solves a coupled mass, pressure, and energy balance through the reservoir, producer, surface system, and injector. These controls set the well geometry and operating constraints that influence achievable flow, pumping demand, and thermal breakthrough.",
    )

with tabs[2]:
    settings_editor(
        settings,
        ["well_cost_constant", "well_cost_depth", "well_cost_depth2", "well_cost_scaling", "capex_constant", "capex_variable", "capex_contingency", "opex_base", "opex_power", "opex_energy", "opex_per_capex"],
        "Cost model",
        "CAPEX combines the two depth-dependent wells with fixed and power-dependent surface-plant costs. Annual OPEX combines fixed, installed-power, produced-energy, CAPEX-related, and purchased-electricity terms. The labels below expose the role and unit of every coefficient.",
    )

with tabs[3]:
    settings_editor(
        settings,
        ["economic_lifetime", "drilling_time", "load_hours", "electricity_purchase_price", "tax_rate", "interest_loan", "inflation", "equity_return", "debt_equity", "utc_cutoff"],
        "Economic model",
        "The economic model converts CAPEX, annual OPEX, and produced energy into discounted cash flow. It calculates UTC/LCOE from discounted cost per discounted tax-adjusted energy and calculates NPV relative to the selected commercial UTC cutoff.",
    )

with tabs[4]:
    st.subheader("Geothermal simulation")
    st.write(
        "Choose the output filename before starting. A successful calculation is saved "
        "automatically in the active project's matching geology-output folder."
    )
    active_output_key = st.session_state.get("active_source_folder_key", "2d_best_fit")
    active_output_subfolder = OUTPUT_SUBFOLDERS.get(active_output_key, OUTPUT_SUBFOLDERS["2d_best_fit"])
    active_output_folder = project_data_root(active_project) / active_output_subfolder
    active_output_folder.mkdir(parents=True, exist_ok=True)

    raw_result_name = st.text_input(
        "Result filename", value="pythermogis_results.nc", key="simulation_result_filename",
        help="The .nc extension is added automatically. Folder components are removed so the result stays inside this project's output folder.",
    ).strip()
    safe_result_name = Path(raw_result_name).name if raw_result_name else ""
    if safe_result_name and not safe_result_name.lower().endswith(".nc"):
        safe_result_name = f"{safe_result_name}.nc"
    output_path = active_output_folder / safe_result_name if safe_result_name else None
    output_exists = bool(output_path and output_path.exists())
    overwrite_result = False
    collision_key = str(output_path) if output_path else ""
    if st.session_state.get("overwrite_result_collision_key") != collision_key:
        st.session_state.overwrite_result_collision_key = collision_key
        st.session_state.overwrite_simulation_result = False
    if not safe_result_name:
        st.error("Enter a result filename before running the simulation.")
    elif output_exists:
        st.warning(f"`{safe_result_name}` already exists in this project output folder.")
        overwrite_result = st.checkbox(
            "Overwrite the existing result", key="overwrite_simulation_result",
        )
        if not overwrite_result:
            st.info("Choose another filename above or explicitly enable overwrite before running.")
    else:
        st.success(f"New result will be saved automatically as `{safe_result_name}`.")
    st.caption(f"Output folder: `{active_output_folder}`")

    st.divider()
    if st.session_state.dataset is not None:
        validated_column, validation_column = st.columns(2, gap="large")
        with validated_column:
            show_grid_viewer(
                st.session_state.dataset, st.session_state.boundary,
                key_prefix="simulation_validated_input", title="Validated simulation grid",
                compact=True, show_histogram=False,
            )
        with validation_column:
            validated_geometry = grid_geometry(st.session_state.dataset)
            st.markdown("#### Simulation input status")
            st.success("Validated geology is available for simulation.")
            if validated_geometry["dx"] is not None:
                st.metric("Validated cell size", f"{validated_geometry['dx']:,.0f} × {validated_geometry['dy']:,.0f} m")
            st.metric("Validated grid cells", f"{validated_geometry['cell_count']:,}")
            st.caption(f"Variables: {', '.join(st.session_state.dataset.data_vars)}")
    else:
        st.info("No validated simulation grid is currently available. Validate one in the Geology input tab.")
    st.divider()

    filename_ready = bool(output_path and (not output_exists or overwrite_result))
    stochastic_run = bool(st.session_state.mapping.get("thickness_mean"))
    if stochastic_run:
        required = ["thickness_mean", "thickness_sd", "ln_permeability_mean", "ln_permeability_sd", "porosity", "ntg", "depth"]
        inputs_ready = st.session_state.dataset is not None and all(st.session_state.mapping.get(name) for name in required)
        if not inputs_ready:
            st.warning("Load and validate depth, thickness mean/SD, log-permeability mean/SD, porosity, and net-to-gross before running.")
        p_values = st.multiselect(
            "Requested percentiles", [1.0, 5.0, 10.0, 25.0, 50.0, 75.0, 90.0, 95.0, 99.0],
            default=[10.0, 50.0, 90.0],
        )
        st.caption("Percentiles are passed as 0–100 values, e.g. 10, 50, and 90.")
        detailed_progress = st.checkbox("Show detailed cell progress", value=True, key="stochastic_progress")
        rows_per_chunk = st.slider("Rows per progress update", 1, 50, 5, disabled=not detailed_progress, key="stochastic_chunk_rows")
        run_clicked = st.button(
            "Run probabilistic Pythermogis simulation and save", type="primary",
            disabled=not (inputs_ready and filename_ready and bool(p_values)),
        )
        if run_clicked:
            progress = st.status("Preparing probabilistic simulation", expanded=True)
            progress_bar = st.progress(0, text="Waiting to start calculation")
            try:
                def update_cells(done, total):
                    progress_bar.progress(done / total, text=f"Calculating {done:,}/{total:,} cells")
                st.session_state.results = simulate_dataset(
                    st.session_state.dataset, st.session_state.mapping, settings,
                    status=progress.write, p_values=p_values,
                    cell_progress=update_cells if detailed_progress else None,
                    rows_per_chunk=rows_per_chunk,
                )
                progress.write(f"Saving NetCDF result to {output_path}")
                st.session_state.results.to_netcdf(output_path, mode="w")
                st.session_state.current_result_path = output_path
                progress_bar.empty()
                progress.update(label="Simulation complete and result saved", state="complete", expanded=False)
                st.success(f"Simulation complete. Result saved automatically to `{output_path}`.")
            except Exception as exc:
                progress.update(label="Simulation or result saving failed", state="error", expanded=True)
                st.exception(exc)
    else:
        inputs_ready = (
            st.session_state.dataset is not None
            and all(st.session_state.mapping.get(name) for name in ["thickness", "porosity", "ntg", "depth"])
            and bool(st.session_state.mapping.get("permeability") or st.session_state.mapping.get("transmissivity"))
        )
        if not inputs_ready:
            st.warning("Load and validate thickness, porosity, net-to-gross, depth, and either permeability or transmissivity before running.")
        run_clicked = st.button(
            "Run Pythermogis simulation and save", type="primary",
            disabled=not (inputs_ready and filename_ready),
        )
        if run_clicked:
            cell_bar = st.progress(0, text="Waiting to start calculation")
            def update_cells(done, total):
                cell_bar.progress(done / total, text=f"Calculating {done:,}/{total:,} cells")
            progress = st.status("Preparing simulation…", expanded=True)
            try:
                with st.spinner("Starting the Java backend and running the doublet calculation…"):
                    st.session_state.results = simulate_dataset(
                        st.session_state.dataset, st.session_state.mapping, settings,
                        status=progress.write, cell_progress=update_cells, rows_per_chunk=5,
                    )
                progress.write(f"Saving NetCDF result to {output_path}")
                st.session_state.results.to_netcdf(output_path, mode="w")
                st.session_state.current_result_path = output_path
                progress.update(label="Simulation complete and result saved", state="complete", expanded=False)
                st.success(f"Simulation complete. Result saved automatically to `{output_path}`.")
            except Exception as exc:
                progress.update(label="Simulation or result saving failed", state="error", expanded=True)
                st.exception(exc)

with tabs[5]:
    st.subheader("Geothermal results")
    st.write("Open a saved project result or an external NetCDF result, then inspect each output with its unit and calculation explanation.")
    active_output_key = st.session_state.get("active_source_folder_key", "2d_best_fit")
    active_output_subfolder = OUTPUT_SUBFOLDERS.get(active_output_key, OUTPUT_SUBFOLDERS["2d_best_fit"])
    active_output_folder = project_data_root(active_project) / active_output_subfolder
    active_output_folder.mkdir(parents=True, exist_ok=True)
    existing_results = [
        path for path in project_files(active_project, active_output_subfolder)
        if path.suffix.lower() in {".nc", ".netcdf"}
    ]
    st.caption(f"Active output folder: `{active_output_folder}`")
    result_selector, result_action = st.columns([4, 1], vertical_alignment="bottom")
    selected_result = result_selector.selectbox(
        "Open project result", ["—"] + existing_results,
        format_func=lambda path: "—" if path == "—" else path.name,
    )
    if result_action.button("Open selected result", disabled=selected_result == "—", width="stretch"):
        try:
            previous_results = st.session_state.get("results")
            if previous_results is not None and hasattr(previous_results, "close"):
                previous_results.close()
            st.session_state.results = load_dataset(selected_result)
            st.session_state.current_result_path = selected_result
            st.success(f"Loaded project result: {selected_result.name}")
        except Exception as exc:
            st.error(f"Could not load project result: {exc}")

    result_file = st.file_uploader(
        "Or open an external NetCDF results file", type=["nc", "netcdf"], key="results_file",
    )
    if result_file is not None:
        upload_signature = (result_file.name, result_file.size)
        if st.session_state.get("loaded_result_upload_signature") != upload_signature:
            try:
                previous_results = st.session_state.get("results")
                if previous_results is not None and hasattr(previous_results, "close"):
                    previous_results.close()
                st.session_state.results = load_dataset(result_file)
                st.session_state.loaded_result_upload_signature = upload_signature
                st.session_state.current_result_path = None
                st.success(f"Loaded external result: {len(st.session_state.results.data_vars)} variables.")
            except Exception as exc:
                st.error(f"Could not load results file: {exc}")

    if st.session_state.results is None:
        st.info("No result is open. Select a project result above or upload a NetCDF file.")
    else:
        current_path = st.session_state.get("current_result_path")
        if current_path:
            st.success(f"Open result: `{current_path}`")
        download_name = Path(current_path).name if current_path else "pythermogis_results.nc"
        st.download_button(
            "Download open result as NetCDF", st.session_state.results.to_netcdf(),
            download_name, "application/x-netcdf",
        )
        show_result_map(st.session_state.results, st.session_state.boundary)
        show_location_analysis(st.session_state.results, st.session_state.boundary)
