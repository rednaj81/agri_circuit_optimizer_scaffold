from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from agri_circuit_optimizer.config import REQUIRED_SCENARIO_FILES
from agri_circuit_optimizer.io.schemas import (
    REQUIRED_SETTINGS_KEYS,
    SCENARIO_TABLE_SCHEMAS,
    ScenarioPaths,
)


BOOLEAN_TRUE_VALUES = {"1", "true", "t", "yes", "y"}
BOOLEAN_FALSE_VALUES = {"0", "false", "f", "no", "n"}


class ScenarioValidationError(ValueError):
    """Raised when scenario files violate the documented contract."""


def build_scenario_paths(base_dir: str | Path) -> ScenarioPaths:
    base = Path(base_dir)
    return ScenarioPaths(
        base_dir=base,
        nodes_csv=base / "nodes.csv",
        routes_csv=base / "routes.csv",
        components_csv=base / "components.csv",
        source_branch_templates_csv=base / "source_branch_templates.csv",
        destination_branch_templates_csv=base / "destination_branch_templates.csv",
        trunk_templates_csv=base / "trunk_templates.csv",
        settings_yaml=base / "settings.yaml",
    )


def validate_scenario_files(base_dir: str | Path) -> None:
    base = Path(base_dir)
    missing = [name for name in REQUIRED_SCENARIO_FILES if not (base / name).exists()]
    if missing:
        raise FileNotFoundError(f"Missing scenario files: {missing}")


def _normalize_bool(value: Any, column: str, table_name: str) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        raise ScenarioValidationError(f"Null value found in boolean column '{column}' of '{table_name}'.")
    text = str(value).strip().lower()
    if text in BOOLEAN_TRUE_VALUES:
        return True
    if text in BOOLEAN_FALSE_VALUES:
        return False
    raise ScenarioValidationError(
        f"Invalid boolean value '{value}' in column '{column}' of '{table_name}'."
    )


def _ensure_required_columns(frame: Any, table_name: str) -> None:
    schema = SCENARIO_TABLE_SCHEMAS[table_name]
    missing_columns = [column for column in schema.required_columns if column not in frame.columns]
    if missing_columns:
        raise ScenarioValidationError(
            f"Table '{table_name}' is missing required columns: {missing_columns}."
        )


def _coerce_table_types(frame: Any, table_name: str) -> Any:
    import pandas as pd

    schema = SCENARIO_TABLE_SCHEMAS[table_name]
    coerced = frame.copy()
    _ensure_required_columns(coerced, table_name)

    for column in schema.string_columns:
        coerced[column] = coerced[column].fillna("").astype(str).str.strip()
        if (coerced[column] == "").any():
            raise ScenarioValidationError(
                f"Table '{table_name}' contains blank values in required text column '{column}'."
            )

    for column in schema.boolean_columns:
        coerced[column] = coerced[column].map(lambda value: _normalize_bool(value, column, table_name))

    for column in schema.integer_columns:
        numeric = pd.to_numeric(coerced[column], errors="coerce")
        if numeric.isna().any():
            raise ScenarioValidationError(
                f"Table '{table_name}' contains non-integer values in column '{column}'."
            )
        coerced[column] = numeric.astype(int)

    for column in schema.float_columns:
        numeric = pd.to_numeric(coerced[column], errors="coerce")
        if numeric.isna().any():
            raise ScenarioValidationError(
                f"Table '{table_name}' contains non-numeric values in column '{column}'."
            )
        coerced[column] = numeric.astype(float)

    for column in schema.nullable_float_columns:
        coerced[column] = pd.to_numeric(coerced[column], errors="coerce")

    return coerced


def _validate_unique_ids(frame: Any, table_name: str, id_column: str) -> None:
    duplicated = frame[frame[id_column].duplicated()][id_column].tolist()
    if duplicated:
        raise ScenarioValidationError(
            f"Table '{table_name}' contains duplicated identifiers in '{id_column}': {duplicated}."
        )


def _validate_settings(settings: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(settings, dict):
        raise ScenarioValidationError("settings.yaml must define a mapping of configuration keys.")

    missing_keys = [key for key in REQUIRED_SETTINGS_KEYS if key not in settings]
    if missing_keys:
        raise ScenarioValidationError(f"settings.yaml is missing required keys: {missing_keys}.")

    normalized = dict(settings)
    normalized["u_max_slots"] = int(normalized["u_max_slots"])
    normalized["v_max_slots"] = int(normalized["v_max_slots"])
    normalized["optional_route_reward"] = float(normalized["optional_route_reward"])
    normalized["robustness_weight"] = float(normalized["robustness_weight"])
    normalized["cleaning_cost_liters_per_operation"] = float(
        normalized["cleaning_cost_liters_per_operation"]
    )
    normalized["default_solver"] = str(normalized["default_solver"]).strip()
    normalized["allowed_system_diameter_classes"] = [
        str(value).strip()
        for value in normalized.get("allowed_system_diameter_classes", [])
        if str(value).strip()
    ]

    if normalized["u_max_slots"] <= 0 or normalized["v_max_slots"] <= 0:
        raise ScenarioValidationError("settings.yaml slots must be positive integers.")
    if not normalized["default_solver"]:
        raise ScenarioValidationError("settings.yaml key 'default_solver' must not be blank.")

    return normalized


def _validate_nodes_routes_components(data: Dict[str, Any]) -> None:
    nodes = data["nodes"]
    routes = data["routes"]
    components = data["components"]
    source_templates = data["source_branch_templates"]
    destination_templates = data["destination_branch_templates"]
    trunk_templates = data["trunk_templates"]

    _validate_unique_ids(nodes, "nodes", "node_id")
    _validate_unique_ids(routes, "routes", "route_id")
    _validate_unique_ids(components, "components", "component_id")
    _validate_unique_ids(source_templates, "source_branch_templates", "template_id")
    _validate_unique_ids(destination_templates, "destination_branch_templates", "template_id")
    _validate_unique_ids(trunk_templates, "trunk_templates", "template_id")

    node_ids = set(nodes["node_id"].tolist())
    unknown_sources = sorted(set(routes["source"]) - node_ids)
    unknown_sinks = sorted(set(routes["sink"]) - node_ids)
    if unknown_sources or unknown_sinks:
        raise ScenarioValidationError(
            "routes.csv references unknown nodes: "
            f"sources={unknown_sources or '[]'}, sinks={unknown_sinks or '[]'}."
        )

    if (routes["sink"] == "W").any():
        bad_routes = routes.loc[routes["sink"] == "W", "route_id"].tolist()
        raise ScenarioValidationError(f"Routes entering 'W' are forbidden: {bad_routes}.")

    if (routes["source"] == "S").any():
        bad_routes = routes.loc[routes["source"] == "S", "route_id"].tolist()
        raise ScenarioValidationError(f"Routes leaving 'S' are forbidden: {bad_routes}.")

    if not ((routes["source"] == "I") & (routes["sink"] == "IR")).any():
        raise ScenarioValidationError("Recirculation route 'I -> IR' must exist in routes.csv.")

    negative_qmin = routes.loc[routes["q_min_delivered_lpm"] < 0, "route_id"].tolist()
    if negative_qmin:
        raise ScenarioValidationError(
            f"Routes must have non-negative q_min_delivered_lpm: {negative_qmin}."
        )

    invalid_component_qty = components.loc[components["available_qty"] < 0, "component_id"].tolist()
    if invalid_component_qty:
        raise ScenarioValidationError(
            f"Components must have non-negative available_qty: {invalid_component_qty}."
        )

    invalid_qmax = components.loc[
        components["q_max_lpm"] < components["q_min_lpm"], "component_id"
    ].tolist()
    if invalid_qmax:
        raise ScenarioValidationError(
            f"Components with q_max_lpm < q_min_lpm are invalid: {invalid_qmax}."
        )

    if not (components["category"] == "pump").any():
        raise ScenarioValidationError("components.csv must contain at least one pump.")
    if not (components["category"] == "meter").any():
        raise ScenarioValidationError("components.csv must contain at least one meter or bypass.")


def _load_and_validate_csv(path: Path, table_name: str) -> Any:
    import pandas as pd

    try:
        frame = pd.read_csv(path)
    except Exception as exc:  # pragma: no cover - delegated to pandas internals
        raise ScenarioValidationError(f"Failed to read '{path.name}': {exc}") from exc
    return _coerce_table_types(frame, table_name)


def load_scenario(base_dir: str | Path) -> Dict[str, Any]:
    """Load scenario files with contract validation and normalized dtypes."""
    validate_scenario_files(base_dir)
    paths = build_scenario_paths(base_dir)

    import yaml

    with open(paths.settings_yaml, "r", encoding="utf-8") as fh:
        settings = _validate_settings(yaml.safe_load(fh))

    data = {
        "paths": paths,
        "nodes": _load_and_validate_csv(paths.nodes_csv, "nodes"),
        "routes": _load_and_validate_csv(paths.routes_csv, "routes"),
        "components": _load_and_validate_csv(paths.components_csv, "components"),
        "source_branch_templates": _load_and_validate_csv(
            paths.source_branch_templates_csv, "source_branch_templates"
        ),
        "destination_branch_templates": _load_and_validate_csv(
            paths.destination_branch_templates_csv, "destination_branch_templates"
        ),
        "trunk_templates": _load_and_validate_csv(paths.trunk_templates_csv, "trunk_templates"),
        "settings": settings,
    }
    _validate_nodes_routes_components(data)
    return data


def scenario_summary(data: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "nodes": len(data["nodes"]),
        "routes": len(data["routes"]),
        "components": len(data["components"]),
        "source_branch_templates": len(data["source_branch_templates"]),
        "destination_branch_templates": len(data["destination_branch_templates"]),
        "trunk_templates": len(data["trunk_templates"]),
        "mandatory_routes": int(data["routes"]["mandatory"].sum()),
        "solver": data["settings"].get("default_solver", "unknown"),
    }
