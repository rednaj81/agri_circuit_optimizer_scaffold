from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

from decision_platform.data_io.loader import (
    BUNDLE_MANIFEST_FILENAME,
    MANIFEST_DOCUMENT_KEYS,
    MANIFEST_TABLE_KEYS,
    SCENARIO_BUNDLE_VERSION,
    ScenarioBundle,
    load_scenario_bundle,
)


TABLE_ATTRIBUTE_NAMES = {
    "nodes.csv": "nodes",
    "components.csv": "components",
    "candidate_links.csv": "candidate_links",
    "edge_component_rules.csv": "edge_component_rules",
    "route_requirements.csv": "route_requirements",
    "quality_rules.csv": "quality_rules",
    "weight_profiles.csv": "weight_profiles",
    "layout_constraints.csv": "layout_constraints",
}

DOCUMENT_ATTRIBUTE_NAMES = {
    "topology_rules.yaml": "topology_rules",
    "scenario_settings.yaml": "scenario_settings",
}

CANONICAL_TABLE_PATHS = {
    "nodes.csv": "nodes.csv",
    "components.csv": "component_catalog.csv",
    "candidate_links.csv": "candidate_links.csv",
    "edge_component_rules.csv": "edge_component_rules.csv",
    "route_requirements.csv": "route_requirements.csv",
    "quality_rules.csv": "quality_rules.csv",
    "weight_profiles.csv": "weight_profiles.csv",
    "layout_constraints.csv": "layout_constraints.csv",
}

CANONICAL_DOCUMENT_PATHS = {
    "topology_rules.yaml": "topology_rules.yaml",
    "scenario_settings.yaml": "scenario_settings.yaml",
}


def save_scenario_bundle(
    bundle: ScenarioBundle,
    output_dir: str | Path,
    *,
    include_legacy_components_alias: bool = False,
) -> dict[str, Path]:
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    exported: dict[str, Path] = {}
    for logical_name, relative_path in CANONICAL_TABLE_PATHS.items():
        frame = getattr(bundle, TABLE_ATTRIBUTE_NAMES[logical_name]).copy()
        destination = out_dir / relative_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        frame.to_csv(destination, index=False, lineterminator="\n")
        exported[logical_name] = destination

    if include_legacy_components_alias:
        legacy_components = out_dir / "components.csv"
        bundle.components.copy().to_csv(legacy_components, index=False, lineterminator="\n")
        exported["components_legacy_alias"] = legacy_components

    for logical_name, relative_path in CANONICAL_DOCUMENT_PATHS.items():
        payload = getattr(bundle, DOCUMENT_ATTRIBUTE_NAMES[logical_name])
        destination = out_dir / relative_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(
            yaml.safe_dump(payload, sort_keys=False, allow_unicode=True),
            encoding="utf-8",
        )
        exported[logical_name] = destination

    manifest_path = out_dir / BUNDLE_MANIFEST_FILENAME
    manifest_path.write_text(
        yaml.safe_dump(build_bundle_manifest(), sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )
    exported["bundle_manifest"] = manifest_path
    return exported


def build_bundle_manifest() -> dict[str, object]:
    return {
        "bundle_version": SCENARIO_BUNDLE_VERSION,
        "tables": {
            key: CANONICAL_TABLE_PATHS[filename]
            for key, filename in MANIFEST_TABLE_KEYS.items()
        },
        "documents": {
            key: CANONICAL_DOCUMENT_PATHS[filename]
            for key, filename in MANIFEST_DOCUMENT_KEYS.items()
        },
    }


def update_bundle_from_authoring_payload(
    bundle: ScenarioBundle,
    *,
    nodes_rows: list[dict[str, Any]] | None = None,
    components_rows: list[dict[str, Any]] | None = None,
    route_rows: list[dict[str, Any]] | None = None,
    scenario_settings_text: str | None = None,
) -> ScenarioBundle:
    scenario_settings = bundle.scenario_settings
    if scenario_settings_text is not None:
        parsed = yaml.safe_load(scenario_settings_text) if scenario_settings_text.strip() else {}
        if not isinstance(parsed, dict):
            raise ValueError("scenario_settings editor content must deserialize to a mapping.")
        scenario_settings = parsed
    return replace(
        bundle,
        nodes=_rows_to_frame(nodes_rows, bundle.nodes),
        components=_rows_to_frame(components_rows, bundle.components),
        route_requirements=_rows_to_frame(route_rows, bundle.route_requirements),
        scenario_settings=scenario_settings,
    )


def save_authored_scenario_bundle(
    source_scenario_dir: str | Path,
    output_dir: str | Path,
    *,
    nodes_rows: list[dict[str, Any]] | None = None,
    components_rows: list[dict[str, Any]] | None = None,
    route_rows: list[dict[str, Any]] | None = None,
    scenario_settings_text: str | None = None,
    include_legacy_components_alias: bool = False,
) -> tuple[ScenarioBundle, dict[str, Path]]:
    source_bundle = load_scenario_bundle(source_scenario_dir)
    edited_bundle = update_bundle_from_authoring_payload(
        source_bundle,
        nodes_rows=nodes_rows,
        components_rows=components_rows,
        route_rows=route_rows,
        scenario_settings_text=scenario_settings_text,
    )
    exported = save_scenario_bundle(
        edited_bundle,
        output_dir,
        include_legacy_components_alias=include_legacy_components_alias,
    )
    reloaded = load_scenario_bundle(output_dir)
    return reloaded, exported


def bundle_authoring_payload(bundle: ScenarioBundle) -> dict[str, Any]:
    return {
        "nodes_rows": bundle.nodes.to_dict("records"),
        "components_rows": bundle.components.to_dict("records"),
        "route_rows": bundle.route_requirements.to_dict("records"),
        "scenario_settings_text": yaml.safe_dump(bundle.scenario_settings, sort_keys=False, allow_unicode=True),
    }


def _rows_to_frame(rows: list[dict[str, Any]] | None, template: pd.DataFrame) -> pd.DataFrame:
    if rows is None:
        return template.copy()
    frame = pd.DataFrame(rows)
    if frame.empty:
        return pd.DataFrame(columns=template.columns)
    for column in template.columns:
        if column not in frame.columns:
            frame[column] = ""
    return frame.loc[:, template.columns].copy()
