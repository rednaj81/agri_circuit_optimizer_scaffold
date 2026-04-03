from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd
import yaml


@dataclass(frozen=True)
class ScenarioBundle:
    base_dir: Path
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

DEFAULT_SCENARIO_FILES = (
    "nodes.csv",
    "components.csv",
    "candidate_links.csv",
    "edge_component_rules.csv",
    "route_requirements.csv",
    "quality_rules.csv",
    "weight_profiles.csv",
    "layout_constraints.csv",
    "topology_rules.yaml",
    "scenario_settings.yaml",
)


def load_scenario_bundle(base_dir: str | Path) -> ScenarioBundle:
    base = Path(base_dir)
    missing = [name for name in DEFAULT_SCENARIO_FILES if not (base / name).exists()]
    if missing:
        raise FileNotFoundError(f"Missing decision platform scenario files: {missing}")

    tables = {
        filename: _read_table(base / filename, filename)
        for filename in REQUIRED_TABLES
    }

    with open(base / "topology_rules.yaml", "r", encoding="utf-8") as fh:
        topology_rules = yaml.safe_load(fh) or {}
    with open(base / "scenario_settings.yaml", "r", encoding="utf-8") as fh:
        scenario_settings = yaml.safe_load(fh) or {}

    _validate_bundle(tables, topology_rules, scenario_settings)

    return ScenarioBundle(
        base_dir=base,
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
    profiles = tables["weight_profiles.csv"]

    node_ids = set(nodes["node_id"].tolist())
    link_endpoints = set(links["from_node"].tolist()) | set(links["to_node"].tolist())
    route_endpoints = set(routes["source"].tolist()) | set(routes["sink"].tolist())
    if sorted(link_endpoints - node_ids):
        raise ValueError(f"candidate_links.csv references unknown nodes: {sorted(link_endpoints - node_ids)}")
    if sorted(route_endpoints - node_ids):
        raise ValueError(f"route_requirements.csv references unknown nodes: {sorted(route_endpoints - node_ids)}")
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


def _parse_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if text in {"1", "true", "yes", "y"}:
        return True
    if text in {"0", "false", "no", "n", ""}:
        return False
    raise ValueError(f"Invalid boolean value: {value}")
