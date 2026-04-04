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
    hydraulic_engine = scenario_settings.get("hydraulic_engine", {})
    primary_engine = str(hydraulic_engine.get("primary", "")).strip()
    fallback_engine = str(hydraulic_engine.get("fallback", "")).strip()
    if primary_engine not in {"watermodels_jl", "python_emulated_julia"}:
        raise ValueError("scenario_settings.yaml hydraulic_engine.primary must be 'watermodels_jl' or 'python_emulated_julia'.")
    if fallback_engine not in {"none", "python_emulated_julia"}:
        raise ValueError("scenario_settings.yaml hydraulic_engine.fallback must be 'none' or 'python_emulated_julia'.")


def _parse_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if text in {"1", "true", "yes", "y"}:
        return True
    if text in {"0", "false", "no", "n", ""}:
        return False
    raise ValueError(f"Invalid boolean value: {value}")
