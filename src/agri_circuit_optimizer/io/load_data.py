from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from agri_circuit_optimizer.config import REQUIRED_SCENARIO_FILES
from agri_circuit_optimizer.io.schemas import (
    REQUIRED_SETTINGS_KEYS,
    SCENARIO_TABLE_SCHEMAS,
    ScenarioPaths,
)

BRANCH_ROLE_BY_TEMPLATE_TABLE = {
    "source_branch_templates": "suction",
    "destination_branch_templates": "discharge",
}


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
        edges_csv=base / "edges.csv",
        topology_rules_yaml=base / "topology_rules.yaml",
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
        if column not in schema.allow_blank_string_columns and (coerced[column] == "").any():
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

    for column in schema.optional_string_columns:
        if column not in coerced.columns:
            continue
        coerced[column] = coerced[column].fillna("").astype(str).str.strip()

    for column in schema.optional_boolean_columns:
        if column not in coerced.columns:
            continue
        coerced[column] = coerced[column].map(
            lambda value: _normalize_bool(value, column, table_name) if pd.notna(value) else False
        )

    for column in schema.optional_integer_columns:
        if column not in coerced.columns:
            continue
        numeric = pd.to_numeric(coerced[column], errors="coerce")
        if numeric.isna().any():
            raise ScenarioValidationError(
                f"Table '{table_name}' contains non-integer values in optional column '{column}'."
            )
        coerced[column] = numeric.astype(int)

    for column in schema.optional_float_columns:
        if column not in coerced.columns:
            continue
        numeric = pd.to_numeric(coerced[column], errors="coerce")
        if numeric.isna().any():
            raise ScenarioValidationError(
                f"Table '{table_name}' contains non-numeric values in optional column '{column}'."
            )
        coerced[column] = numeric.astype(float)

    for column in schema.optional_nullable_float_columns:
        if column not in coerced.columns:
            continue
        coerced[column] = pd.to_numeric(coerced[column], errors="coerce")

    return coerced


def _validate_unique_ids(frame: Any, table_name: str, id_column: str) -> None:
    duplicated = frame[frame[id_column].duplicated()][id_column].tolist()
    if duplicated:
        raise ScenarioValidationError(
            f"Table '{table_name}' contains duplicated identifiers in '{id_column}': {duplicated}."
        )


def _split_encoded_values(raw_value: Any) -> list[str]:
    if raw_value is None:
        return []
    text = str(raw_value).strip()
    if not text:
        return []
    return [chunk.strip() for chunk in text.split("|") if chunk.strip()]


def _validate_topology_rules(
    topology_rules: Dict[str, Any] | None,
    *,
    topology_family: str,
) -> Dict[str, Any]:
    rules = dict(topology_rules or {})
    rules["topology_family"] = str(rules.get("topology_family", topology_family)).strip() or topology_family
    if rules["topology_family"] != topology_family:
        raise ScenarioValidationError(
            "topology_rules.yaml topology_family must match settings.yaml topology_family."
        )
    rules["max_active_pumps_per_route"] = int(rules.get("max_active_pumps_per_route", 1))
    rules["max_reading_meters_per_route"] = int(rules.get("max_reading_meters_per_route", 1))
    rules["allow_idle_pumps_on_path"] = _normalize_bool(
        rules.get("allow_idle_pumps_on_path", False),
        "allow_idle_pumps_on_path",
        "topology_rules",
    )
    rules["allow_idle_meters_on_path"] = _normalize_bool(
        rules.get("allow_idle_meters_on_path", False),
        "allow_idle_meters_on_path",
        "topology_rules",
    )
    rules["allow_passive_bypass_on_path"] = _normalize_bool(
        rules.get("allow_passive_bypass_on_path", True),
        "allow_passive_bypass_on_path",
        "topology_rules",
    )
    rules["enforce_simple_path"] = _normalize_bool(
        rules.get("enforce_simple_path", True),
        "enforce_simple_path",
        "topology_rules",
    )
    rules["allow_cycle_if_inactive"] = _normalize_bool(
        rules.get("allow_cycle_if_inactive", True),
        "allow_cycle_if_inactive",
        "topology_rules",
    )
    rules["treat_extra_open_branch_as_invalid"] = _normalize_bool(
        rules.get("treat_extra_open_branch_as_invalid", True),
        "treat_extra_open_branch_as_invalid",
        "topology_rules",
    )
    rules["core_routes_group"] = str(rules.get("core_routes_group", "core")).strip() or "core"
    rules["service_routes_group"] = str(rules.get("service_routes_group", "service")).strip() or "service"

    if rules["max_active_pumps_per_route"] <= 0:
        raise ScenarioValidationError("topology_rules.yaml max_active_pumps_per_route must be positive.")
    if rules["max_reading_meters_per_route"] <= 0:
        raise ScenarioValidationError(
            "topology_rules.yaml max_reading_meters_per_route must be positive."
        )
    return rules


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
    normalized["topology_family"] = str(
        normalized.get("topology_family", "star_manifolds")
    ).strip() or "star_manifolds"
    normalized["allowed_system_diameter_classes"] = [
        str(value).strip()
        for value in normalized.get("allowed_system_diameter_classes", [])
        if str(value).strip()
    ]
    normalized["hydraulic_loss_mode"] = str(
        normalized.get("hydraulic_loss_mode", "additive_lpm")
    ).strip() or "additive_lpm"
    normalized["hose_total_available_m"] = float(normalized.get("hose_total_available_m", 0.0))
    normalized["hose_module_m"] = float(normalized.get("hose_module_m", 1.0))
    normalized["bend_factor"] = float(normalized.get("bend_factor", 1.0))
    normalized["connection_margin_m"] = float(normalized.get("connection_margin_m", 0.0))
    normalized["minimum_branch_hose_m"] = float(normalized.get("minimum_branch_hose_m", 0.0))
    normalized["suction_manifold_x_m"] = (
        float(normalized["suction_manifold_x_m"])
        if normalized.get("suction_manifold_x_m") is not None
        else None
    )
    normalized["suction_manifold_y_m"] = (
        float(normalized["suction_manifold_y_m"])
        if normalized.get("suction_manifold_y_m") is not None
        else None
    )
    normalized["discharge_manifold_x_m"] = (
        float(normalized["discharge_manifold_x_m"])
        if normalized.get("discharge_manifold_x_m") is not None
        else None
    )
    normalized["discharge_manifold_y_m"] = (
        float(normalized["discharge_manifold_y_m"])
        if normalized.get("discharge_manifold_y_m") is not None
        else None
    )
    normalized["trunk_length_suction_m"] = float(normalized.get("trunk_length_suction_m", 0.0))
    normalized["trunk_length_discharge_m"] = float(normalized.get("trunk_length_discharge_m", 0.0))
    normalized["prefer_shorter_hose_weight"] = float(normalized.get("prefer_shorter_hose_weight", 0.0))
    normalized["count_external_hose_inside_total"] = _normalize_bool(
        normalized.get("count_external_hose_inside_total", False),
        "count_external_hose_inside_total",
        "settings",
    )
    normalized["allow_meter_extra"] = _normalize_bool(
        normalized.get("allow_meter_extra", True),
        "allow_meter_extra",
        "settings",
    )
    normalized["maquette_trunks_consume_connectors"] = _normalize_bool(
        normalized.get("maquette_trunks_consume_connectors", True),
        "maquette_trunks_consume_connectors",
        "settings",
    )
    normalized["min_length_factor"] = float(normalized.get("min_length_factor", 0.1))

    if normalized["u_max_slots"] <= 0 or normalized["v_max_slots"] <= 0:
        raise ScenarioValidationError("settings.yaml slots must be positive integers.")
    if not normalized["default_solver"]:
        raise ScenarioValidationError("settings.yaml key 'default_solver' must not be blank.")
    if normalized["topology_family"] not in {"star_manifolds", "bus_with_pump_islands"}:
        raise ScenarioValidationError(
            "settings.yaml key 'topology_family' must be one of "
            "['star_manifolds', 'bus_with_pump_islands']."
        )
    if normalized["hose_module_m"] <= 0:
        raise ScenarioValidationError("settings.yaml key 'hose_module_m' must be positive.")
    if normalized["bend_factor"] <= 0:
        raise ScenarioValidationError("settings.yaml key 'bend_factor' must be positive.")
    if normalized["min_length_factor"] <= 0 or normalized["min_length_factor"] > 1:
        raise ScenarioValidationError("settings.yaml key 'min_length_factor' must be in (0, 1].")

    return normalized


def _validate_nodes_routes_components(data: Dict[str, Any]) -> None:
    nodes = data["nodes"]
    routes = data["routes"]
    components = data["components"]
    source_templates = data["source_branch_templates"]
    destination_templates = data["destination_branch_templates"]
    trunk_templates = data["trunk_templates"]
    edges = data.get("edges")

    _validate_unique_ids(nodes, "nodes", "node_id")
    _validate_unique_ids(routes, "routes", "route_id")
    _validate_unique_ids(components, "components", "component_id")
    _validate_unique_ids(source_templates, "source_branch_templates", "template_id")
    _validate_unique_ids(destination_templates, "destination_branch_templates", "template_id")
    _validate_unique_ids(trunk_templates, "trunk_templates", "template_id")
    if edges is not None:
        _validate_unique_ids(edges, "edges", "edge_id")

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

    if "hose_length_m" in components.columns:
        invalid_hose_length = components.loc[
            components["hose_length_m"].notna() & (components["hose_length_m"] <= 0), "component_id"
        ].tolist()
        if invalid_hose_length:
            raise ScenarioValidationError(
                f"Components with non-positive hose_length_m are invalid: {invalid_hose_length}."
            )

    if "x_m" in nodes.columns or "y_m" in nodes.columns:
        x_series = nodes["x_m"] if "x_m" in nodes.columns else None
        y_series = nodes["y_m"] if "y_m" in nodes.columns else None
        if x_series is None or y_series is None:
            missing_coordinates = nodes["node_id"].tolist()
        else:
            missing_coordinates = nodes.loc[x_series.isna() | y_series.isna(), "node_id"].tolist()
        if missing_coordinates:
            raise ScenarioValidationError(
                f"Nodes with geometry must define both x_m and y_m: {missing_coordinates}."
            )

    valid_route_groups = {"", "core", "service"}
    if "route_group" in routes.columns:
        invalid_route_groups = sorted(
            {
                str(value).strip()
                for value in routes["route_group"].tolist()
                if str(value).strip() not in valid_route_groups
            }
        )
        if invalid_route_groups:
            raise ScenarioValidationError(
                f"routes.csv contains invalid route_group values: {invalid_route_groups}."
            )

    valid_node_roles = {"", "source_only", "sink_only", "bidirectional", "service", "isolated"}
    if "node_role" in nodes.columns:
        invalid_node_roles = sorted(
            {
                str(value).strip()
                for value in nodes["node_role"].tolist()
                if str(value).strip() not in valid_node_roles
            }
        )
        if invalid_node_roles:
            raise ScenarioValidationError(
                f"nodes.csv contains invalid node_role values: {invalid_node_roles}."
            )

    if edges is not None:
        settings_family = str(data["settings"].get("topology_family", "star_manifolds"))
        topology_family_values = (
            edges["topology_family"].tolist() if "topology_family" in edges.columns else []
        )
        edge_families = sorted(
            {
                str(value).strip()
                for value in topology_family_values
                if str(value).strip()
            }
        )
        if edge_families and edge_families != [settings_family]:
            raise ScenarioValidationError(
                f"edges.csv topology_family values {edge_families} do not match '{settings_family}'."
            )
        unknown_edge_from = sorted(set(edges["from_node"]) - node_ids)
        unknown_edge_to = sorted(set(edges["to_node"]) - node_ids)
        if unknown_edge_from or unknown_edge_to:
            raise ScenarioValidationError(
                "edges.csv references unknown nodes: "
                f"from={unknown_edge_from or '[]'}, to={unknown_edge_to or '[]'}."
            )
        valid_direction_modes = {"forward_only", "reverse_only", "bidirectional", "conditional"}
        invalid_direction_modes = sorted(
            {
                str(value).strip()
                for value in edges["direction_mode"].tolist()
                if str(value).strip() not in valid_direction_modes
            }
        )
        if invalid_direction_modes:
            raise ScenarioValidationError(
                f"edges.csv contains invalid direction_mode values: {invalid_direction_modes}."
            )
        component_ids = set(components["component_id"].tolist())
        edge_component_usage: dict[str, int] = {}
        for edge in edges.to_dict("records"):
            for component_id in _split_encoded_values(edge["component_ids"]):
                if component_id not in component_ids:
                    raise ScenarioValidationError(
                        f"edges.csv edge '{edge['edge_id']}' references unknown component '{component_id}'."
                    )
                if bool(edge.get("default_installed", False)):
                    edge_component_usage[component_id] = edge_component_usage.get(component_id, 0) + 1
        for component_id, qty in edge_component_usage.items():
            available_qty = int(
                components.loc[components["component_id"] == component_id, "available_qty"].iloc[0]
            )
            if qty > available_qty:
                raise ScenarioValidationError(
                    f"edges.csv installs component '{component_id}' {qty} times, exceeding "
                    f"available_qty={available_qty}."
                )


def _derive_node_operational_role(node: Any) -> str:
    is_source = bool(node["is_source"])
    is_sink = bool(node["is_sink"])
    if is_source and is_sink:
        return "bidirectional"
    if is_source:
        return "source_only"
    if is_sink:
        return "sink_only"
    return "isolated"


def _annotate_operational_semantics(data: Dict[str, Any]) -> Dict[str, Any]:
    normalized = dict(data)
    nodes = normalized["nodes"].copy()
    nodes["operational_role"] = nodes.apply(_derive_node_operational_role, axis=1)
    if "node_role" in nodes.columns:
        nodes["node_role"] = nodes["node_role"].replace("", None).fillna(nodes["operational_role"])
    else:
        nodes["node_role"] = nodes["operational_role"]
    normalized["nodes"] = nodes

    routes = normalized["routes"].copy()
    if "route_group" not in routes.columns:
        routes["route_group"] = "core"
    else:
        routes["route_group"] = routes["route_group"].replace("", "core").fillna("core")
    normalized["routes"] = routes

    for table_name, branch_role in BRANCH_ROLE_BY_TEMPLATE_TABLE.items():
        frame = normalized[table_name].copy()
        if "branch_role" not in frame.columns:
            frame["branch_role"] = branch_role
        else:
            frame["branch_role"] = frame["branch_role"].replace("", branch_role).fillna(branch_role)
            invalid_templates = frame.loc[frame["branch_role"] != branch_role, "template_id"].tolist()
            if invalid_templates:
                raise ScenarioValidationError(
                    f"Table '{table_name}' has invalid branch_role values for templates "
                    f"{invalid_templates}. Expected '{branch_role}'."
                )
        normalized[table_name] = frame

    if normalized.get("edges") is not None:
        edges = normalized["edges"].copy()
        if "topology_family" not in edges.columns:
            edges["topology_family"] = normalized["settings"]["topology_family"]
        else:
            edges["topology_family"] = edges["topology_family"].replace(
                "", normalized["settings"]["topology_family"]
            ).fillna(normalized["settings"]["topology_family"])
        if "branch_role" not in edges.columns:
            edges["branch_role"] = ""
        normalized["edges"] = edges

    return normalized


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

    topology_rules = None
    if paths.topology_rules_yaml.exists() or settings["topology_family"] != "star_manifolds":
        if not paths.topology_rules_yaml.exists():
            raise ScenarioValidationError(
                "topology_rules.yaml is required when topology_family is not 'star_manifolds'."
            )
        with open(paths.topology_rules_yaml, "r", encoding="utf-8") as fh:
            topology_rules = _validate_topology_rules(
                yaml.safe_load(fh),
                topology_family=settings["topology_family"],
            )

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
        "topology_rules": topology_rules,
    }
    if paths.edges_csv.exists():
        data["edges"] = _load_and_validate_csv(paths.edges_csv, "edges")
    else:
        data["edges"] = None
    _validate_nodes_routes_components(data)
    return _annotate_operational_semantics(data)


def scenario_summary(data: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "nodes": len(data["nodes"]),
        "routes": len(data["routes"]),
        "components": len(data["components"]),
        "source_branch_templates": len(data["source_branch_templates"]),
        "destination_branch_templates": len(data["destination_branch_templates"]),
        "trunk_templates": len(data["trunk_templates"]),
        "edges": 0 if data.get("edges") is None else len(data["edges"]),
        "mandatory_routes": int(data["routes"]["mandatory"].sum()),
        "solver": data["settings"].get("default_solver", "unknown"),
        "topology_family": data["settings"].get("topology_family", "star_manifolds"),
    }
