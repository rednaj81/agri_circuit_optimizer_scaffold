from __future__ import annotations

import shutil
from pathlib import Path

import pandas as pd
import pytest
import yaml

from decision_platform.data_io.loader import BUNDLE_MANIFEST_FILENAME, load_scenario_bundle
from decision_platform.data_io.storage import save_scenario_bundle
from tests.decision_platform.scenario_utils import cleanup_scenario_copy, prepare_scenario_copy


pytestmark = [pytest.mark.fast]


def test_save_scenario_bundle_round_trip_is_lossless() -> None:
    bundle = load_scenario_bundle("data/decision_platform/maquete_v2")
    output_dir = Path("tests/_tmp/scenario_persistence_roundtrip")
    if output_dir.exists():
        shutil.rmtree(output_dir)
    try:
        exported = save_scenario_bundle(bundle, output_dir)
        reloaded = load_scenario_bundle(output_dir)

        assert exported["bundle_manifest"].name == BUNDLE_MANIFEST_FILENAME
        assert "components_legacy_alias" not in exported
        assert reloaded.bundle_version == bundle.bundle_version
        assert reloaded.resolved_files["components.csv"].name == "component_catalog.csv"
        pd.testing.assert_frame_equal(reloaded.nodes, bundle.nodes, check_dtype=False)
        pd.testing.assert_frame_equal(reloaded.components, bundle.components, check_dtype=False)
        pd.testing.assert_frame_equal(reloaded.candidate_links, bundle.candidate_links, check_dtype=False)
        pd.testing.assert_frame_equal(reloaded.edge_component_rules, bundle.edge_component_rules, check_dtype=False)
        pd.testing.assert_frame_equal(reloaded.route_requirements, bundle.route_requirements, check_dtype=False)
        pd.testing.assert_frame_equal(reloaded.quality_rules, bundle.quality_rules, check_dtype=False)
        pd.testing.assert_frame_equal(reloaded.weight_profiles, bundle.weight_profiles, check_dtype=False)
        pd.testing.assert_frame_equal(reloaded.layout_constraints, bundle.layout_constraints, check_dtype=False)
        assert reloaded.topology_rules == bundle.topology_rules
        assert reloaded.scenario_settings == bundle.scenario_settings
    finally:
        if output_dir.exists():
            shutil.rmtree(output_dir)


def test_manifest_prefers_component_catalog_over_legacy_alias() -> None:
    bundle = load_scenario_bundle("data/decision_platform/maquete_v2")
    output_dir = Path("tests/_tmp/scenario_persistence_manifest_precedence")
    if output_dir.exists():
        shutil.rmtree(output_dir)
    try:
        exported = save_scenario_bundle(bundle, output_dir, include_legacy_components_alias=True)

        legacy_alias = output_dir / "components.csv"
        assert exported["components_legacy_alias"] == legacy_alias
        legacy_alias.write_text(
            "component_id,category,cost,available_qty,is_fallback,hard_min_lpm,hard_max_lpm,confidence_min_lpm,confidence_max_lpm\n"
            "broken,pump,1,1,1,0,1,0,1\n",
            encoding="utf-8",
        )

        reloaded = load_scenario_bundle(output_dir)

        assert "broken" not in reloaded.components["component_id"].tolist()
        assert reloaded.resolved_files["components.csv"].name == "component_catalog.csv"
    finally:
        if output_dir.exists():
            shutil.rmtree(output_dir)


def test_loader_rejects_unsupported_bundle_version() -> None:
    scenario_dir = prepare_scenario_copy(
        "data/decision_platform/maquete_v2",
        "maquete_v2_invalid_bundle_version",
    )
    try:
        manifest_path = Path(scenario_dir) / BUNDLE_MANIFEST_FILENAME
        manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8")) or {}
        manifest["bundle_version"] = "decision_platform_scenario_bundle/v999"
        manifest_path.write_text(yaml.safe_dump(manifest, sort_keys=False), encoding="utf-8")

        with pytest.raises(ValueError, match="unsupported bundle_version"):
            load_scenario_bundle(scenario_dir)
    finally:
        cleanup_scenario_copy(scenario_dir)


def test_loader_rejects_manifest_with_missing_component_catalog() -> None:
    scenario_dir = prepare_scenario_copy(
        "data/decision_platform/maquete_v2",
        "maquete_v2_missing_component_catalog",
    )
    try:
        component_catalog = Path(scenario_dir) / "component_catalog.csv"
        component_catalog.unlink()

        with pytest.raises(FileNotFoundError, match="references missing files"):
            load_scenario_bundle(scenario_dir)
    finally:
        cleanup_scenario_copy(scenario_dir)


def test_loader_rejects_manifest_missing_required_entries() -> None:
    scenario_dir = prepare_scenario_copy(
        "data/decision_platform/maquete_v2",
        "maquete_v2_missing_manifest_entry",
    )
    try:
        manifest_path = Path(scenario_dir) / BUNDLE_MANIFEST_FILENAME
        manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8")) or {}
        del manifest["tables"]["components"]
        manifest_path.write_text(yaml.safe_dump(manifest, sort_keys=False), encoding="utf-8")

        with pytest.raises(ValueError, match="missing required entries"):
            load_scenario_bundle(scenario_dir)
    finally:
        cleanup_scenario_copy(scenario_dir)
