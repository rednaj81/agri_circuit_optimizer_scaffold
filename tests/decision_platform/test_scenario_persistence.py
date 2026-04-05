from __future__ import annotations

import shutil
from pathlib import Path

import pandas as pd
import pytest
import yaml

from decision_platform.api.run_pipeline import run_decision_pipeline
from decision_platform.data_io.loader import BUNDLE_MANIFEST_FILENAME, load_scenario_bundle
from decision_platform.data_io.storage import save_authored_scenario_bundle, save_scenario_bundle
from tests.decision_platform.scenario_utils import (
    cleanup_scenario_copy,
    diagnostic_runtime_test_mode,
    prepare_isolated_tmp_dir,
    prepare_scenario_copy,
)


pytestmark = [pytest.mark.fast]


def test_save_scenario_bundle_round_trip_is_lossless() -> None:
    bundle = load_scenario_bundle("data/decision_platform/maquete_v2")
    output_dir = prepare_isolated_tmp_dir("scenario_persistence_roundtrip")
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
    output_dir = prepare_isolated_tmp_dir("scenario_persistence_manifest_precedence")
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


def test_save_authored_bundle_persists_authoring_changes() -> None:
    source_bundle = load_scenario_bundle("data/decision_platform/maquete_v2")
    output_dir = prepare_isolated_tmp_dir("scenario_persistence_authored")
    try:
        nodes_rows = source_bundle.nodes.to_dict("records")
        components_rows = source_bundle.components.to_dict("records")
        candidate_links_rows = source_bundle.candidate_links.to_dict("records")
        edge_component_rules_rows = source_bundle.edge_component_rules.to_dict("records")
        route_rows = source_bundle.route_requirements.to_dict("records")
        layout_constraints_rows = source_bundle.layout_constraints.to_dict("records")

        nodes_rows[0]["label"] = "W editado"
        components_rows[0]["cost"] = 123.0
        candidate_links_rows[0]["notes"] = "Tap P1 editado"
        edge_component_rules_rows[0]["max_series_pumps"] = 1
        route_rows[0]["weight"] = 77.0
        layout_constraints_rows[0]["value"] = 1.5

        topology_rules = dict(source_bundle.topology_rules)
        topology_rules["families"] = dict(topology_rules["families"])
        topology_rules["families"]["hybrid_free"] = dict(topology_rules["families"]["hybrid_free"])
        topology_rules["families"]["hybrid_free"]["max_active_pumps_per_route"] = 3
        scenario_settings = dict(source_bundle.scenario_settings)
        scenario_settings["ui"] = dict(scenario_settings.get("ui", {}))
        scenario_settings["ui"]["default_layout_mode"] = "edited_layout"

        reloaded, exported = save_authored_scenario_bundle(
            "data/decision_platform/maquete_v2",
            output_dir,
            nodes_rows=nodes_rows,
            components_rows=components_rows,
            candidate_links_rows=candidate_links_rows,
            edge_component_rules_rows=edge_component_rules_rows,
            route_rows=route_rows,
            layout_constraints_rows=layout_constraints_rows,
            topology_rules_text=yaml.safe_dump(topology_rules, sort_keys=False, allow_unicode=True),
            scenario_settings_text=yaml.safe_dump(scenario_settings, sort_keys=False, allow_unicode=True),
        )

        assert exported["bundle_manifest"].name == BUNDLE_MANIFEST_FILENAME
        assert reloaded.nodes.iloc[0]["label"] == "W editado"
        assert float(reloaded.components.iloc[0]["cost"]) == 123.0
        assert reloaded.candidate_links.iloc[0]["notes"] == "Tap P1 editado"
        assert int(reloaded.edge_component_rules.iloc[0]["max_series_pumps"]) == 1
        assert float(reloaded.route_requirements.iloc[0]["weight"]) == 77.0
        assert float(reloaded.layout_constraints.iloc[0]["value"]) == 1.5
        assert reloaded.topology_rules["families"]["hybrid_free"]["max_active_pumps_per_route"] == 3
        assert reloaded.scenario_settings["ui"]["default_layout_mode"] == "edited_layout"
        assert reloaded.scenario_settings["storage"]["bundle_manifest"] == BUNDLE_MANIFEST_FILENAME
        assert reloaded.scenario_settings["storage"]["component_catalog"] == "component_catalog.csv"
    finally:
        if output_dir.exists():
            shutil.rmtree(output_dir)


def test_save_authored_bundle_repopulates_missing_storage_mapping() -> None:
    source_bundle = load_scenario_bundle("data/decision_platform/maquete_v2")
    output_dir = prepare_isolated_tmp_dir("scenario_persistence_missing_storage_mapping")
    try:
        scenario_settings = {
            key: value
            for key, value in source_bundle.scenario_settings.items()
            if key != "storage"
        }

        reloaded, exported = save_authored_scenario_bundle(
            "data/decision_platform/maquete_v2",
            output_dir,
            scenario_settings_text=yaml.safe_dump(scenario_settings, sort_keys=False, allow_unicode=True),
        )

        assert exported["bundle_manifest"].name == BUNDLE_MANIFEST_FILENAME
        assert reloaded.scenario_settings["storage"]["bundle_manifest"] == BUNDLE_MANIFEST_FILENAME
        assert reloaded.scenario_settings["storage"]["component_catalog"] == "component_catalog.csv"
        assert reloaded.resolved_files["components.csv"].name == "component_catalog.csv"
    finally:
        if output_dir.exists():
            shutil.rmtree(output_dir)


@pytest.mark.slow
def test_saved_bundle_runs_with_canonical_execution_provenance() -> None:
    scenario_dir = prepare_scenario_copy(
        "data/decision_platform/maquete_v2",
        "maquete_v2_persistence_run_provenance",
        scenario_overrides={"hydraulic_engine": {"fallback": "python_emulated_julia"}},
    )
    output_dir = prepare_isolated_tmp_dir("scenario_persistence_run_provenance")
    try:
        reloaded, _ = save_authored_scenario_bundle(
            scenario_dir,
            output_dir,
            topology_rules_text=yaml.safe_dump(
                load_scenario_bundle(scenario_dir).topology_rules,
                sort_keys=False,
                allow_unicode=True,
            ),
            scenario_settings_text=yaml.safe_dump(
                load_scenario_bundle(scenario_dir).scenario_settings,
                sort_keys=False,
                allow_unicode=True,
            ),
        )
        with diagnostic_runtime_test_mode():
            result = run_decision_pipeline(
                output_dir,
                allow_diagnostic_python_emulation=True,
            )

        assert reloaded.bundle_manifest_path is not None
        assert result["scenario_bundle_root"] == str(output_dir.resolve())
        assert result["scenario_provenance"]["requested_dir_matches_bundle_root"] is True
        assert result["runtime"]["scenario_provenance"]["scenario_root"] == str(output_dir.resolve())
        assert result["runtime"]["scenario_provenance"]["bundle_manifest"].endswith("scenario_bundle.yaml")
        assert result["runtime"]["scenario_provenance"]["bundle_files"]["components.csv"] == "component_catalog.csv"
    finally:
        if output_dir.exists():
            shutil.rmtree(output_dir)
        cleanup_scenario_copy(scenario_dir)


def test_save_authored_bundle_fails_closed_for_invalid_route_contract() -> None:
    source_bundle = load_scenario_bundle("data/decision_platform/maquete_v2")
    output_dir = prepare_isolated_tmp_dir("scenario_persistence_invalid_route")
    try:
        route_rows = source_bundle.route_requirements.to_dict("records")
        route_rows[0]["measurement_required"] = False
        route_rows[0]["dose_min_l"] = 1.0
        route_rows[0]["dose_error_max_pct"] = 2.0

        with pytest.raises(ValueError, match="dosing routes without direct measurement"):
            save_authored_scenario_bundle(
                "data/decision_platform/maquete_v2",
                output_dir,
                route_rows=route_rows,
                topology_rules_text=yaml.safe_dump(
                    source_bundle.topology_rules,
                    sort_keys=False,
                    allow_unicode=True,
                ),
                scenario_settings_text=yaml.safe_dump(
                    source_bundle.scenario_settings,
                    sort_keys=False,
                    allow_unicode=True,
                ),
            )
    finally:
        if output_dir.exists():
            shutil.rmtree(output_dir)


def test_save_authored_bundle_fails_closed_for_divergent_storage_mapping_without_publishing_bundle() -> None:
    source_bundle = load_scenario_bundle("data/decision_platform/maquete_v2")
    output_dir = prepare_isolated_tmp_dir("scenario_persistence_invalid_storage_mapping")
    try:
        scenario_settings = {
            **source_bundle.scenario_settings,
            "storage": {
                **source_bundle.scenario_settings["storage"],
                "component_catalog": "components.csv",
            },
        }

        with pytest.raises(ValueError, match="canonical component catalog filename"):
            save_authored_scenario_bundle(
                "data/decision_platform/maquete_v2",
                output_dir,
                scenario_settings_text=yaml.safe_dump(scenario_settings, sort_keys=False, allow_unicode=True),
            )

        assert not (output_dir / BUNDLE_MANIFEST_FILENAME).exists()
        assert not (output_dir / "component_catalog.csv").exists()
    finally:
        if output_dir.exists():
            shutil.rmtree(output_dir)


def test_save_authored_bundle_preserves_existing_valid_output_on_invalid_rewrite() -> None:
    source_bundle = load_scenario_bundle("data/decision_platform/maquete_v2")
    output_dir = prepare_isolated_tmp_dir("scenario_persistence_preserve_existing_on_failure")
    try:
        initial_reloaded, _ = save_authored_scenario_bundle(
            "data/decision_platform/maquete_v2",
            output_dir,
        )
        initial_manifest = (output_dir / BUNDLE_MANIFEST_FILENAME).read_text(encoding="utf-8")
        initial_component_catalog = (output_dir / "component_catalog.csv").read_text(encoding="utf-8")

        scenario_settings = {
            **source_bundle.scenario_settings,
            "storage": {
                **source_bundle.scenario_settings["storage"],
                "bundle_manifest": "bundle.yaml",
            },
        }

        with pytest.raises(ValueError, match="canonical bundle manifest filename"):
            save_authored_scenario_bundle(
                "data/decision_platform/maquete_v2",
                output_dir,
                scenario_settings_text=yaml.safe_dump(scenario_settings, sort_keys=False, allow_unicode=True),
            )

        reloaded_after_failure = load_scenario_bundle(output_dir)
        assert reloaded_after_failure.scenario_settings["storage"] == initial_reloaded.scenario_settings["storage"]
        assert (output_dir / BUNDLE_MANIFEST_FILENAME).read_text(encoding="utf-8") == initial_manifest
        assert (output_dir / "component_catalog.csv").read_text(encoding="utf-8") == initial_component_catalog
    finally:
        if output_dir.exists():
            shutil.rmtree(output_dir)


def test_save_authored_bundle_fails_closed_for_invalid_node_contract() -> None:
    source_bundle = load_scenario_bundle("data/decision_platform/maquete_v2")
    output_dir = prepare_isolated_tmp_dir("scenario_persistence_invalid_node")
    try:
        nodes_rows = source_bundle.nodes.to_dict("records")
        nodes_rows[0]["node_id"] = nodes_rows[1]["node_id"]

        with pytest.raises(ValueError, match="duplicated node_id"):
            save_authored_scenario_bundle(
                "data/decision_platform/maquete_v2",
                output_dir,
                nodes_rows=nodes_rows,
                topology_rules_text=yaml.safe_dump(
                    source_bundle.topology_rules,
                    sort_keys=False,
                    allow_unicode=True,
                ),
                scenario_settings_text=yaml.safe_dump(
                    source_bundle.scenario_settings,
                    sort_keys=False,
                    allow_unicode=True,
                ),
            )
    finally:
        if output_dir.exists():
            shutil.rmtree(output_dir)


def test_save_authored_bundle_fails_closed_for_invalid_node_direction_contract() -> None:
    source_bundle = load_scenario_bundle("data/decision_platform/maquete_v2")
    output_dir = prepare_isolated_tmp_dir("scenario_persistence_invalid_node_direction")
    try:
        nodes_rows = source_bundle.nodes.to_dict("records")
        for row in nodes_rows:
            if row["node_id"] == "W":
                row["allow_outbound"] = False
                break

        with pytest.raises(ValueError, match="allow_outbound=false"):
            save_authored_scenario_bundle(
                "data/decision_platform/maquete_v2",
                output_dir,
                nodes_rows=nodes_rows,
                topology_rules_text=yaml.safe_dump(
                    source_bundle.topology_rules,
                    sort_keys=False,
                    allow_unicode=True,
                ),
                scenario_settings_text=yaml.safe_dump(
                    source_bundle.scenario_settings,
                    sort_keys=False,
                    allow_unicode=True,
                ),
            )
    finally:
        if output_dir.exists():
            shutil.rmtree(output_dir)


def test_save_authored_bundle_fails_closed_for_node_rename_with_broken_references() -> None:
    source_bundle = load_scenario_bundle("data/decision_platform/maquete_v2")
    output_dir = prepare_isolated_tmp_dir("scenario_persistence_invalid_node_rename_references")
    try:
        nodes_rows = source_bundle.nodes.to_dict("records")
        for row in nodes_rows:
            if row["node_id"] == "P1":
                row["node_id"] = "P1_RENAMED"
                break

        with pytest.raises(ValueError, match="references unknown nodes"):
            save_authored_scenario_bundle(
                "data/decision_platform/maquete_v2",
                output_dir,
                nodes_rows=nodes_rows,
                candidate_links_rows=source_bundle.candidate_links.to_dict("records"),
                route_rows=source_bundle.route_requirements.to_dict("records"),
                topology_rules_text=yaml.safe_dump(
                    source_bundle.topology_rules,
                    sort_keys=False,
                    allow_unicode=True,
                ),
                scenario_settings_text=yaml.safe_dump(
                    source_bundle.scenario_settings,
                    sort_keys=False,
                    allow_unicode=True,
                ),
            )
    finally:
        if output_dir.exists():
            shutil.rmtree(output_dir)


def test_save_authored_bundle_supports_explicit_legacy_source_layout() -> None:
    scenario_dir = prepare_scenario_copy(
        "data/decision_platform/maquete_v2",
        "maquete_v2_explicit_legacy_source",
    )
    output_dir = prepare_isolated_tmp_dir("scenario_persistence_legacy_source_saved")
    try:
        (Path(scenario_dir) / BUNDLE_MANIFEST_FILENAME).unlink()
        legacy_bundle = load_scenario_bundle(scenario_dir)

        reloaded, exported = save_authored_scenario_bundle(
            scenario_dir,
            output_dir,
            nodes_rows=legacy_bundle.nodes.to_dict("records"),
            components_rows=legacy_bundle.components.to_dict("records"),
            candidate_links_rows=legacy_bundle.candidate_links.to_dict("records"),
            edge_component_rules_rows=legacy_bundle.edge_component_rules.to_dict("records"),
            route_rows=legacy_bundle.route_requirements.to_dict("records"),
            layout_constraints_rows=legacy_bundle.layout_constraints.to_dict("records"),
            topology_rules_text=yaml.safe_dump(legacy_bundle.topology_rules, sort_keys=False, allow_unicode=True),
            scenario_settings_text=yaml.safe_dump(
                legacy_bundle.scenario_settings,
                sort_keys=False,
                allow_unicode=True,
            ),
        )

        assert legacy_bundle.bundle_version == "legacy_directory_layout"
        assert legacy_bundle.bundle_manifest_path is None
        assert exported["bundle_manifest"].name == BUNDLE_MANIFEST_FILENAME
        assert reloaded.bundle_version != "legacy_directory_layout"
        assert reloaded.bundle_manifest_path is not None
        assert reloaded.resolved_files["components.csv"].name == "component_catalog.csv"
    finally:
        if output_dir.exists():
            shutil.rmtree(output_dir)
        cleanup_scenario_copy(scenario_dir)


def test_save_authored_bundle_fails_closed_for_invalid_topology_contract() -> None:
    source_bundle = load_scenario_bundle("data/decision_platform/maquete_v2")
    output_dir = prepare_isolated_tmp_dir("scenario_persistence_invalid_topology")
    try:
        candidate_links_rows = source_bundle.candidate_links.to_dict("records")
        candidate_links_rows[1]["link_id"] = candidate_links_rows[0]["link_id"]

        with pytest.raises(ValueError, match="duplicated link_id"):
            save_authored_scenario_bundle(
                "data/decision_platform/maquete_v2",
                output_dir,
                candidate_links_rows=candidate_links_rows,
                topology_rules_text=yaml.safe_dump(
                    source_bundle.topology_rules,
                    sort_keys=False,
                    allow_unicode=True,
                ),
                scenario_settings_text=yaml.safe_dump(
                    source_bundle.scenario_settings,
                    sort_keys=False,
                    allow_unicode=True,
                ),
            )
    finally:
        if output_dir.exists():
            shutil.rmtree(output_dir)
