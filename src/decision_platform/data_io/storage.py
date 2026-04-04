from __future__ import annotations

from pathlib import Path

import yaml

from decision_platform.data_io.loader import (
    BUNDLE_MANIFEST_FILENAME,
    MANIFEST_DOCUMENT_KEYS,
    MANIFEST_TABLE_KEYS,
    SCENARIO_BUNDLE_VERSION,
    ScenarioBundle,
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
