from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd
import yaml


@dataclass(frozen=True)
class ScenarioBundle:
    base_dir: Path
    bundle_version: str
    bundle_manifest_path: Path | None
    resolved_files: dict[str, Path]
    nodes: pd.DataFrame
    components: pd.DataFrame
    candidate_links: pd.DataFrame
    edge_component_rules: pd.DataFrame
    route_requirements: pd.DataFrame
    quality_rules: pd.DataFrame
    weight_profiles: pd.DataFrame
    layout_constraints: pd.DataFrame
    topology_rules: dict[str, Any]
    scenario_settings: dict[str, Any]


BUNDLE_MANIFEST_FILENAME = "scenario_bundle.yaml"
SCENARIO_BUNDLE_VERSION = "decision_platform_scenario_bundle/v1"

MANIFEST_TABLE_KEYS = {
    "nodes": "nodes.csv",
    "components": "components.csv",
    "candidate_links": "candidate_links.csv",
    "edge_component_rules": "edge_component_rules.csv",
    "route_requirements": "route_requirements.csv",
    "quality_rules": "quality_rules.csv",
    "weight_profiles": "weight_profiles.csv",
    "layout_constraints": "layout_constraints.csv",
}

MANIFEST_DOCUMENT_KEYS = {
    "topology_rules": "topology_rules.yaml",
    "scenario_settings": "scenario_settings.yaml",
}

DEFAULT_SCENARIO_FILE_ALIASES = {
    "nodes.csv": ("nodes.csv",),
    "components.csv": ("component_catalog.csv", "components.csv"),
    "candidate_links.csv": ("candidate_links.csv",),
    "edge_component_rules.csv": ("edge_component_rules.csv",),
    "route_requirements.csv": ("route_requirements.csv",),
    "quality_rules.csv": ("quality_rules.csv",),
    "weight_profiles.csv": ("weight_profiles.csv",),
    "layout_constraints.csv": ("layout_constraints.csv",),
    "topology_rules.yaml": ("topology_rules.yaml",),
    "scenario_settings.yaml": ("scenario_settings.yaml",),
}


REQUIRED_TABLES = {
    "nodes.csv": (
        "node_id",
        "node_type",
        "label",
        "x_m",
        "y_m",
        "allow_inbound",
        "allow_outbound",
    ),
    "components.csv": (
        "component_id",
        "category",
        "cost",
        "available_qty",
        "is_fallback",
        "hard_min_lpm",
        "hard_max_lpm",
        "confidence_min_lpm",
        "confidence_max_lpm",
    ),
    "candidate_links.csv": (
        "link_id",
        "from_node",
        "to_node",
        "archetype",
        "length_m",
        "bidirectional",
        "family_hint",
    ),
    "edge_component_rules.csv": (
        "rule_id",
        "archetype",
        "allowed_categories",
        "required_categories",
        "optional_categories",
        "max_series_pumps",
        "max_reading_meters",
    ),
    "route_requirements.csv": (
        "route_id",
        "source",
        "sink",
        "mandatory",
        "route_group",
        "q_min_delivered_lpm",
        "measurement_required",
        "weight",
    ),
    "quality_rules.csv": (
        "rule_id",
        "metric_scope",
        "metric_name",
        "operator",
        "threshold",
        "score_delta_if_true",
        "score_delta_if_false",
        "hard_filter",
    ),
    "weight_profiles.csv": (
        "profile_id",
        "cost_weight",
        "quality_weight",
        "flow_weight",
        "resilience_weight",
        "cleaning_weight",
        "operability_weight",
    ),
    "layout_constraints.csv": ("rule_id", "scope", "key", "value", "unit"),
}

BOOLEAN_COLUMNS = {
    "nodes.csv": ("allow_inbound", "allow_outbound", "requires_mixing_service", "is_candidate_hub"),
    "components.csv": ("is_fallback", "can_be_in_series", "active_for_reading"),
    "candidate_links.csv": ("bidirectional",),
    "route_requirements.csv": (
        "mandatory",
        "measurement_required",
        "cleaning_required",
        "allow_series_pumps",
    ),
    "quality_rules.csv": ("hard_filter",),
}

NUMERIC_COLUMNS = {
    "nodes.csv": ("x_m", "y_m"),
    "components.csv": (
        "nominal_diameter_mm",
        "cost",
        "available_qty",
        "quality_base_score",
        "hard_min_lpm",
        "hard_max_lpm",
        "confidence_min_lpm",
        "confidence_max_lpm",
        "forward_loss_pct_when_on",
        "reverse_loss_pct_when_off",
        "cleaning_hold_up_l",
    ),
    "candidate_links.csv": ("length_m", "install_cost_override"),
    "edge_component_rules.csv": ("max_series_pumps", "max_reading_meters"),
    "route_requirements.csv": (
        "q_min_delivered_lpm",
        "dose_min_l",
        "dose_error_max_pct",
        "weight",
    ),
    "quality_rules.csv": ("threshold", "score_delta_if_true", "score_delta_if_false"),
    "weight_profiles.csv": (
        "cost_weight",
        "quality_weight",
        "flow_weight",
        "resilience_weight",
        "cleaning_weight",
        "operability_weight",
    ),
    "layout_constraints.csv": ("value",),
}

ALLOWED_ROUTE_GROUPS = {"core", "optional", "service"}
SUPPORTED_COMPONENT_CATEGORIES = {
    "check_valve",
    "connector",
    "hose",
    "meter",
    "pump",
    "valve",
}
ALLOWED_FALLBACK_COMPONENT_CATEGORIES = {"meter", "pump", "valve"}


def load_scenario_bundle(base_dir: str | Path) -> ScenarioBundle:
    base = Path(base_dir)
    bundle_version, manifest_path, resolved_files = _resolve_scenario_files(base)

    tables = {
        filename: _read_table(resolved_files[filename], filename)
        for filename in REQUIRED_TABLES
    }

    with open(resolved_files["topology_rules.yaml"], "r", encoding="utf-8") as fh:
        topology_rules = yaml.safe_load(fh) or {}
    with open(resolved_files["scenario_settings.yaml"], "r", encoding="utf-8") as fh:
        scenario_settings = yaml.safe_load(fh) or {}

    _validate_bundle(tables, topology_rules, scenario_settings)

    return ScenarioBundle(
        base_dir=base,
        bundle_version=bundle_version,
        bundle_manifest_path=manifest_path,
        resolved_files=resolved_files,
        nodes=tables["nodes.csv"],
        components=tables["components.csv"],
        candidate_links=tables["candidate_links.csv"],
        edge_component_rules=tables["edge_component_rules.csv"],
        route_requirements=tables["route_requirements.csv"],
        quality_rules=tables["quality_rules.csv"],
        weight_profiles=tables["weight_profiles.csv"],
        layout_constraints=tables["layout_constraints.csv"],
        topology_rules=topology_rules,
        scenario_settings=scenario_settings,
    )


def _resolve_scenario_files(base_dir: Path) -> tuple[str, Path | None, dict[str, Path]]:
    manifest_path = base_dir / BUNDLE_MANIFEST_FILENAME
    if manifest_path.exists():
        manifest = _load_bundle_manifest(manifest_path)
        resolved = _resolve_manifest_files(base_dir, manifest)
        return SCENARIO_BUNDLE_VERSION, manifest_path, resolved
    return "legacy_directory_layout", None, _resolve_legacy_files(base_dir)


def _load_bundle_manifest(path: Path) -> dict[str, Any]:
    with open(path, "r", encoding="utf-8") as fh:
        manifest = yaml.safe_load(fh) or {}
    if not isinstance(manifest, dict):
        raise ValueError(f"Scenario bundle manifest '{path.name}' must be a mapping.")
    bundle_version = str(manifest.get("bundle_version", "")).strip()
    if bundle_version != SCENARIO_BUNDLE_VERSION:
        raise ValueError(
            f"Scenario bundle manifest '{path.name}' uses unsupported bundle_version "
            f"'{bundle_version or '<missing>'}'. Expected '{SCENARIO_BUNDLE_VERSION}'."
        )
    return manifest


def _resolve_manifest_files(base_dir: Path, manifest: dict[str, Any]) -> dict[str, Path]:
    tables = manifest.get("tables")
    documents = manifest.get("documents")
    if not isinstance(tables, dict):
        raise ValueError(f"Scenario bundle manifest '{BUNDLE_MANIFEST_FILENAME}' must define a 'tables' mapping.")
    if not isinstance(documents, dict):
        raise ValueError(f"Scenario bundle manifest '{BUNDLE_MANIFEST_FILENAME}' must define a 'documents' mapping.")
    resolved: dict[str, Path] = {}
    missing_entries: list[str] = []
    missing_files: list[str] = []
    for key, filename in MANIFEST_TABLE_KEYS.items():
        relative_path = str(tables.get(key, "")).strip()
        if not relative_path:
            missing_entries.append(f"tables.{key}")
            continue
        path = base_dir / relative_path
        if not path.exists():
            missing_files.append(relative_path)
        resolved[filename] = path
    for key, filename in MANIFEST_DOCUMENT_KEYS.items():
        relative_path = str(documents.get(key, "")).strip()
        if not relative_path:
            missing_entries.append(f"documents.{key}")
            continue
        path = base_dir / relative_path
        if not path.exists():
            missing_files.append(relative_path)
        resolved[filename] = path
    if missing_entries:
        raise ValueError(
            f"Scenario bundle manifest '{BUNDLE_MANIFEST_FILENAME}' is missing required entries: {missing_entries}"
        )
    if missing_files:
        raise FileNotFoundError(
            f"Scenario bundle manifest '{BUNDLE_MANIFEST_FILENAME}' references missing files: {missing_files}"
        )
    return resolved


def _resolve_legacy_files(base_dir: Path) -> dict[str, Path]:
    resolved: dict[str, Path] = {}
    missing: list[str] = []
    for filename, aliases in DEFAULT_SCENARIO_FILE_ALIASES.items():
        for candidate_name in aliases:
            candidate_path = base_dir / candidate_name
            if candidate_path.exists():
                resolved[filename] = candidate_path
                break
        else:
            missing.append(filename)
    if missing:
        raise FileNotFoundError(f"Missing decision platform scenario files: {missing}")
    return resolved


def _read_table(path: Path, filename: str) -> pd.DataFrame:
    frame = pd.read_csv(path)
    required = REQUIRED_TABLES[filename]
    missing = [column for column in required if column not in frame.columns]
    if missing:
        raise ValueError(f"Table '{filename}' missing required columns: {missing}")
    for column in frame.columns:
        if frame[column].dtype == object:
            frame[column] = frame[column].fillna("").astype(str).str.strip()
    for column in BOOLEAN_COLUMNS.get(filename, ()):
        frame[column] = frame[column].map(_parse_bool)
    for column in NUMERIC_COLUMNS.get(filename, ()):
        frame[column] = pd.to_numeric(frame[column], errors="raise")
    return frame


def _validate_bundle(
    tables: dict[str, pd.DataFrame],
    topology_rules: dict[str, Any],
    scenario_settings: dict[str, Any],
) -> None:
    nodes = tables["nodes.csv"]
    links = tables["candidate_links.csv"]
    routes = tables["route_requirements.csv"]
    components = tables["components.csv"]
    edge_rules = tables["edge_component_rules.csv"]
    profiles = tables["weight_profiles.csv"]
    node_directions = nodes.set_index("node_id")[["allow_inbound", "allow_outbound"]]

    node_ids = set(nodes["node_id"].tolist())
    link_endpoints = set(links["from_node"].tolist()) | set(links["to_node"].tolist())
    route_endpoints = set(routes["source"].tolist()) | set(routes["sink"].tolist())
    if sorted(link_endpoints - node_ids):
        raise ValueError(f"candidate_links.csv references unknown nodes: {sorted(link_endpoints - node_ids)}")
    if sorted(route_endpoints - node_ids):
        raise ValueError(f"route_requirements.csv references unknown nodes: {sorted(route_endpoints - node_ids)}")
    invalid_route_ids = sorted({route_id for route_id in routes["route_id"].tolist() if not str(route_id).strip()})
    if invalid_route_ids:
        raise ValueError("route_requirements.csv contains blank route_id values.")
    duplicate_route_ids = sorted(routes.loc[routes["route_id"].duplicated(keep=False), "route_id"].unique().tolist())
    if duplicate_route_ids:
        raise ValueError(f"route_requirements.csv contains duplicated route_id values: {duplicate_route_ids}")
    invalid_route_groups = sorted(
        {
            str(route_group).strip()
            for route_group in routes["route_group"].tolist()
            if str(route_group).strip() not in ALLOWED_ROUTE_GROUPS
        }
    )
    if invalid_route_groups:
        raise ValueError(f"route_requirements.csv contains invalid route_group values: {invalid_route_groups}")
    sink_direction_violations = routes.loc[
        routes["sink"].map(lambda node_id: not bool(node_directions.at[node_id, "allow_inbound"])),
        ["route_id", "sink"],
    ]
    if not sink_direction_violations.empty:
        violations = sink_direction_violations.to_dict("records")
        raise ValueError(
            "route_requirements.csv contains routes entering nodes with allow_inbound=false: "
            f"{violations}"
        )
    source_direction_violations = routes.loc[
        routes["source"].map(lambda node_id: not bool(node_directions.at[node_id, "allow_outbound"])),
        ["route_id", "source"],
    ]
    if not source_direction_violations.empty:
        violations = source_direction_violations.to_dict("records")
        raise ValueError(
            "route_requirements.csv contains routes leaving nodes with allow_outbound=false: "
            f"{violations}"
        )
    dosing_without_measurement = routes.loc[
        (~routes["measurement_required"])
        & ((routes["dose_min_l"] > 0) | (routes["dose_error_max_pct"] > 0)),
        ["route_id", "dose_min_l", "dose_error_max_pct"],
    ]
    if not dosing_without_measurement.empty:
        violations = dosing_without_measurement.to_dict("records")
        raise ValueError(
            "route_requirements.csv contains dosing routes without direct measurement: "
            f"{violations}"
        )
    _validate_component_catalog(components)
    _validate_edge_component_rules(edge_rules, components)
    if not (
        components.loc[components["category"] == "pump", "is_fallback"].any()
        and components.loc[components["category"] == "meter", "is_fallback"].any()
    ):
        raise ValueError("Scenario must include fallback pump and fallback meter.")
    if any(components["hard_max_lpm"] < components["hard_min_lpm"]):
        raise ValueError("components.csv contains hard range with max < min.")
    if any(components["confidence_max_lpm"] < components["confidence_min_lpm"]):
        raise ValueError("components.csv contains confidence range with max < min.")
    enabled_families = scenario_settings.get("enabled_families", [])
    known_families = set((topology_rules.get("families") or {}).keys())
    if not enabled_families:
        raise ValueError("scenario_settings.yaml must list enabled_families.")
    unknown_families = sorted(set(enabled_families) - known_families)
    if unknown_families:
        raise ValueError(f"enabled_families not declared in topology_rules.yaml: {unknown_families}")
    weight_sum = profiles[
        [
            "cost_weight",
            "quality_weight",
            "flow_weight",
            "resilience_weight",
            "cleaning_weight",
            "operability_weight",
        ]
    ].sum(axis=1)
    if (weight_sum <= 0).any():
        raise ValueError("weight_profiles.csv must define positive aggregate weights.")
    hydraulic_engine = scenario_settings.get("hydraulic_engine", {})
    primary_engine = str(hydraulic_engine.get("primary", "")).strip()
    fallback_engine = str(hydraulic_engine.get("fallback", "")).strip()
    if primary_engine not in {"watermodels_jl", "python_emulated_julia"}:
        raise ValueError("scenario_settings.yaml hydraulic_engine.primary must be 'watermodels_jl' or 'python_emulated_julia'.")
    if fallback_engine not in {"none", "python_emulated_julia"}:
        raise ValueError("scenario_settings.yaml hydraulic_engine.fallback must be 'none' or 'python_emulated_julia'.")


def _validate_component_catalog(components: pd.DataFrame) -> None:
    duplicate_component_ids = sorted(
        components.loc[components["component_id"].duplicated(keep=False), "component_id"].unique().tolist()
    )
    if duplicate_component_ids:
        raise ValueError(f"components.csv contains duplicated component_id values: {duplicate_component_ids}")
    invalid_component_ids = sorted(
        {component_id for component_id in components["component_id"].tolist() if not str(component_id).strip()}
    )
    if invalid_component_ids:
        raise ValueError("components.csv contains blank component_id values.")
    unknown_categories = sorted(set(components["category"].tolist()) - SUPPORTED_COMPONENT_CATEGORIES)
    if unknown_categories:
        raise ValueError(f"components.csv contains unsupported categories: {unknown_categories}")
    invalid_cost_components = components.loc[components["cost"] < 0, ["component_id", "cost"]]
    if not invalid_cost_components.empty:
        raise ValueError(
            "components.csv contains negative cost values: "
            f"{invalid_cost_components.to_dict('records')}"
        )
    invalid_qty_components = components.loc[
        (components["available_qty"] <= 0)
        | (~components["available_qty"].map(lambda value: float(value).is_integer())),
        ["component_id", "available_qty"],
    ]
    if not invalid_qty_components.empty:
        raise ValueError(
            "components.csv contains invalid available_qty values: "
            f"{invalid_qty_components.to_dict('records')}"
        )
    invalid_fallback_categories = components.loc[
        components["is_fallback"] & ~components["category"].isin(ALLOWED_FALLBACK_COMPONENT_CATEGORIES),
        ["component_id", "category"],
    ]
    if not invalid_fallback_categories.empty:
        raise ValueError(
            "components.csv contains fallback components with unsupported categories: "
            f"{invalid_fallback_categories.to_dict('records')}"
        )
    invalid_reading_components = components.loc[
        components["active_for_reading"] & (components["category"] != "meter"),
        ["component_id", "category"],
    ]
    if not invalid_reading_components.empty:
        raise ValueError(
            "components.csv contains non-meter components flagged for active reading: "
            f"{invalid_reading_components.to_dict('records')}"
        )
    unreadable_meters = components.loc[
        (components["category"] == "meter") & (~components["active_for_reading"]),
        ["component_id"],
    ]
    if not unreadable_meters.empty:
        raise ValueError(
            "components.csv contains meter components with active_for_reading=false: "
            f"{unreadable_meters.to_dict('records')}"
        )
    meter_range_violations = components.loc[
        (components["category"] == "meter")
        & (
            (components["hard_max_lpm"] <= 0)
            | (components["confidence_max_lpm"] <= 0)
            | (components["confidence_min_lpm"] < components["hard_min_lpm"])
            | (components["confidence_max_lpm"] > components["hard_max_lpm"])
        ),
        [
            "component_id",
            "hard_min_lpm",
            "hard_max_lpm",
            "confidence_min_lpm",
            "confidence_max_lpm",
        ],
    ]
    if not meter_range_violations.empty:
        raise ValueError(
            "components.csv contains meter components with incoherent reading ranges: "
            f"{meter_range_violations.to_dict('records')}"
        )


def _validate_edge_component_rules(edge_rules: pd.DataFrame, components: pd.DataFrame) -> None:
    known_catalog_categories = set(components["category"].tolist())
    duplicate_rule_ids = sorted(
        edge_rules.loc[edge_rules["rule_id"].duplicated(keep=False), "rule_id"].unique().tolist()
    )
    if duplicate_rule_ids:
        raise ValueError(f"edge_component_rules.csv contains duplicated rule_id values: {duplicate_rule_ids}")
    for rule in edge_rules.to_dict("records"):
        allowed = set(_split_pipe(rule["allowed_categories"]))
        required = set(_split_pipe(rule["required_categories"]))
        optional = set(_split_pipe(rule["optional_categories"]))
        if not allowed:
            raise ValueError(
                "edge_component_rules.csv contains rules with empty allowed_categories: "
                f"{rule['rule_id']}"
            )
        if not required:
            raise ValueError(
                "edge_component_rules.csv contains rules with empty required_categories: "
                f"{rule['rule_id']}"
            )
        unsupported = sorted((allowed | required | optional) - SUPPORTED_COMPONENT_CATEGORIES)
        if unsupported:
            raise ValueError(
                "edge_component_rules.csv contains unsupported categories: "
                f"rule_id={rule['rule_id']} categories={unsupported}"
            )
        missing_from_catalog = sorted((allowed | required | optional) - known_catalog_categories)
        if missing_from_catalog:
            raise ValueError(
                "edge_component_rules.csv references categories absent from component catalog: "
                f"rule_id={rule['rule_id']} categories={missing_from_catalog}"
            )
        missing_required = sorted(required - allowed)
        if missing_required:
            raise ValueError(
                "edge_component_rules.csv has required_categories outside allowed_categories: "
                f"rule_id={rule['rule_id']} categories={missing_required}"
            )
        missing_optional = sorted(optional - allowed)
        if missing_optional:
            raise ValueError(
                "edge_component_rules.csv has optional_categories outside allowed_categories: "
                f"rule_id={rule['rule_id']} categories={missing_optional}"
            )
        overlapping = sorted(required & optional)
        if overlapping:
            raise ValueError(
                "edge_component_rules.csv has categories marked as both required and optional: "
                f"rule_id={rule['rule_id']} categories={overlapping}"
            )


def _split_pipe(value: Any) -> list[str]:
    return [item.strip() for item in str(value).split("|") if item.strip()]


def _parse_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if text in {"1", "true", "yes", "y"}:
        return True
    if text in {"0", "false", "no", "n", ""}:
        return False
    raise ValueError(f"Invalid boolean value: {value}")
