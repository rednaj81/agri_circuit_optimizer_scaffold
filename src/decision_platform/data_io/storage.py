from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import shutil
from typing import Any
from uuid import uuid4

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
CANONICAL_STORAGE_MAPPING = {
    "bundle_manifest": BUNDLE_MANIFEST_FILENAME,
    "component_catalog": CANONICAL_TABLE_PATHS["components.csv"],
}


def save_scenario_bundle(
    bundle: ScenarioBundle,
    output_dir: str | Path,
    *,
    include_legacy_components_alias: bool = False,
) -> dict[str, Path]:
    out_dir = Path(output_dir)
    out_dir.parent.mkdir(parents=True, exist_ok=True)
    staging_dir = out_dir.with_name(f"staging_{out_dir.name}_{uuid4().hex}")
    staging_dir.mkdir(parents=True, exist_ok=False)

    try:
        exported_relative_paths = _write_bundle_directory(
            bundle,
            staging_dir,
            include_legacy_components_alias=include_legacy_components_alias,
        )
        load_scenario_bundle(staging_dir)
        return _publish_staged_bundle(
            staging_dir,
            out_dir,
            exported_relative_paths,
        )
    except Exception:
        shutil.rmtree(staging_dir, ignore_errors=True)
        raise


def _write_bundle_directory(
    bundle: ScenarioBundle,
    output_dir: Path,
    *,
    include_legacy_components_alias: bool = False,
) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)

    exported: dict[str, Path] = {}
    for logical_name, relative_path in CANONICAL_TABLE_PATHS.items():
        frame = getattr(bundle, TABLE_ATTRIBUTE_NAMES[logical_name]).copy()
        destination = output_dir / relative_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        frame.to_csv(destination, index=False, lineterminator="\n")
        exported[logical_name] = Path(relative_path)

    if include_legacy_components_alias:
        legacy_components = output_dir / "components.csv"
        bundle.components.copy().to_csv(legacy_components, index=False, lineterminator="\n")
        exported["components_legacy_alias"] = Path("components.csv")

    for logical_name, relative_path in CANONICAL_DOCUMENT_PATHS.items():
        payload = getattr(bundle, DOCUMENT_ATTRIBUTE_NAMES[logical_name])
        destination = output_dir / relative_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(
            yaml.safe_dump(payload, sort_keys=False, allow_unicode=True),
            encoding="utf-8",
        )
        exported[logical_name] = Path(relative_path)

    manifest_path = output_dir / BUNDLE_MANIFEST_FILENAME
    manifest_path.write_text(
        yaml.safe_dump(build_bundle_manifest(), sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )
    exported["bundle_manifest"] = Path(BUNDLE_MANIFEST_FILENAME)
    return exported


def _publish_staged_bundle(
    staging_dir: Path,
    output_dir: Path,
    exported_relative_paths: dict[str, Path],
) -> dict[str, Path]:
    backup_dir = output_dir.with_name(f"backup_{output_dir.name}_{uuid4().hex}")
    if output_dir.exists():
        output_dir.replace(backup_dir)
    try:
        staging_dir.replace(output_dir)
    except Exception:
        if backup_dir.exists() and not output_dir.exists():
            backup_dir.replace(output_dir)
        raise
    else:
        if backup_dir.exists():
            shutil.rmtree(backup_dir, ignore_errors=True)
    return {
        logical_name: output_dir / relative_path
        for logical_name, relative_path in exported_relative_paths.items()
    }


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
    candidate_links_rows: list[dict[str, Any]] | None = None,
    edge_component_rules_rows: list[dict[str, Any]] | None = None,
    route_rows: list[dict[str, Any]] | None = None,
    layout_constraints_rows: list[dict[str, Any]] | None = None,
    topology_rules_text: str | None = None,
    scenario_settings_text: str | None = None,
) -> ScenarioBundle:
    topology_rules = bundle.topology_rules
    if topology_rules_text is not None:
        parsed = yaml.safe_load(topology_rules_text) if topology_rules_text.strip() else {}
        if not isinstance(parsed, dict):
            raise ValueError("topology_rules editor content must deserialize to a mapping.")
        topology_rules = parsed
    scenario_settings = bundle.scenario_settings
    if scenario_settings_text is not None:
        parsed = yaml.safe_load(scenario_settings_text) if scenario_settings_text.strip() else {}
        if not isinstance(parsed, dict):
            raise ValueError("scenario_settings editor content must deserialize to a mapping.")
        scenario_settings = parsed
    scenario_settings = _normalize_canonical_storage_mapping(scenario_settings)
    return replace(
        bundle,
        nodes=_rows_to_frame(nodes_rows, bundle.nodes),
        components=_rows_to_frame(components_rows, bundle.components),
        candidate_links=_rows_to_frame(candidate_links_rows, bundle.candidate_links),
        edge_component_rules=_rows_to_frame(edge_component_rules_rows, bundle.edge_component_rules),
        route_requirements=_rows_to_frame(route_rows, bundle.route_requirements),
        layout_constraints=_rows_to_frame(layout_constraints_rows, bundle.layout_constraints),
        topology_rules=topology_rules,
        scenario_settings=scenario_settings,
    )


def save_authored_scenario_bundle(
    source_scenario_dir: str | Path,
    output_dir: str | Path,
    *,
    nodes_rows: list[dict[str, Any]] | None = None,
    components_rows: list[dict[str, Any]] | None = None,
    candidate_links_rows: list[dict[str, Any]] | None = None,
    edge_component_rules_rows: list[dict[str, Any]] | None = None,
    route_rows: list[dict[str, Any]] | None = None,
    layout_constraints_rows: list[dict[str, Any]] | None = None,
    topology_rules_text: str | None = None,
    scenario_settings_text: str | None = None,
    include_legacy_components_alias: bool = False,
) -> tuple[ScenarioBundle, dict[str, Path]]:
    source_bundle = load_scenario_bundle(source_scenario_dir)
    edited_bundle = update_bundle_from_authoring_payload(
        source_bundle,
        nodes_rows=nodes_rows,
        components_rows=components_rows,
        candidate_links_rows=candidate_links_rows,
        edge_component_rules_rows=edge_component_rules_rows,
        route_rows=route_rows,
        layout_constraints_rows=layout_constraints_rows,
        topology_rules_text=topology_rules_text,
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
        "candidate_links_rows": bundle.candidate_links.to_dict("records"),
        "edge_component_rules_rows": bundle.edge_component_rules.to_dict("records"),
        "route_rows": bundle.route_requirements.to_dict("records"),
        "layout_constraints_rows": bundle.layout_constraints.to_dict("records"),
        "topology_rules_text": yaml.safe_dump(bundle.topology_rules, sort_keys=False, allow_unicode=True),
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


def _normalize_canonical_storage_mapping(scenario_settings: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(scenario_settings)
    storage = normalized.get("storage")
    if storage is None:
        normalized["storage"] = dict(CANONICAL_STORAGE_MAPPING)
        return normalized
    if not isinstance(storage, dict):
        raise ValueError("scenario_settings.yaml storage must be a mapping when present.")
    bundle_manifest = str(storage.get("bundle_manifest", "")).strip()
    component_catalog = str(storage.get("component_catalog", "")).strip()
    if bundle_manifest != CANONICAL_STORAGE_MAPPING["bundle_manifest"]:
        raise ValueError(
            "scenario_settings.yaml storage.bundle_manifest must match the canonical bundle manifest filename."
        )
    if component_catalog != CANONICAL_STORAGE_MAPPING["component_catalog"]:
        raise ValueError(
            "scenario_settings.yaml storage.component_catalog must match the canonical component catalog filename."
        )
    normalized["storage"] = {
        **storage,
        **CANONICAL_STORAGE_MAPPING,
    }
    return normalized
