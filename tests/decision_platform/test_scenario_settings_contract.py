from __future__ import annotations

import pytest

from decision_platform.data_io.loader import load_scenario_bundle
from tests.decision_platform.scenario_utils import (
    cleanup_scenario_copy,
    prepare_scenario_copy,
    update_scenario_table,
    update_scenario_yaml,
)


pytestmark = [pytest.mark.fast]


def test_maquete_v2_settings_topology_layout_contract_is_valid() -> None:
    bundle = load_scenario_bundle("data/decision_platform/maquete_v2")

    assert bundle.scenario_settings["scenario_id"] == "maquete_v2"
    assert bundle.scenario_settings["ranking"]["default_profile"] == "balanced"
    assert "families" in bundle.topology_rules
    assert bundle.layout_constraints["rule_id"].is_unique


def test_loader_rejects_missing_scenario_id() -> None:
    scenario_dir = prepare_scenario_copy(
        "data/decision_platform/maquete_v2",
        "maquete_v2_missing_scenario_id",
    )
    try:
        update_scenario_yaml(
            scenario_dir,
            "scenario_settings.yaml",
            lambda payload: {key: value for key, value in payload.items() if key != "scenario_id"},
        )

        with pytest.raises(ValueError, match="non-empty scenario_id"):
            load_scenario_bundle(scenario_dir)
    finally:
        cleanup_scenario_copy(scenario_dir)


def test_loader_rejects_duplicate_enabled_families() -> None:
    scenario_dir = prepare_scenario_copy(
        "data/decision_platform/maquete_v2",
        "maquete_v2_duplicate_enabled_families",
    )
    try:
        update_scenario_yaml(
            scenario_dir,
            "scenario_settings.yaml",
            lambda payload: {
                **payload,
                "enabled_families": [
                    "star_manifolds",
                    "star_manifolds",
                    "loop_ring",
                ],
            },
        )

        with pytest.raises(ValueError, match="duplicate values"):
            load_scenario_bundle(scenario_dir)
    finally:
        cleanup_scenario_copy(scenario_dir)


def test_loader_rejects_missing_default_profile() -> None:
    scenario_dir = prepare_scenario_copy(
        "data/decision_platform/maquete_v2",
        "maquete_v2_missing_default_profile",
    )
    try:
        update_scenario_yaml(
            scenario_dir,
            "scenario_settings.yaml",
            lambda payload: {
                **payload,
                "ranking": {
                    **payload["ranking"],
                    "default_profile": "missing_profile",
                },
            },
        )

        with pytest.raises(ValueError, match="must reference an existing weight_profiles"):
            load_scenario_bundle(scenario_dir)
    finally:
        cleanup_scenario_copy(scenario_dir)


def test_loader_rejects_noncanonical_storage_mapping() -> None:
    scenario_dir = prepare_scenario_copy(
        "data/decision_platform/maquete_v2",
        "maquete_v2_invalid_storage_mapping",
    )
    try:
        update_scenario_yaml(
            scenario_dir,
            "scenario_settings.yaml",
            lambda payload: {
                **payload,
                "storage": {
                    **payload["storage"],
                    "component_catalog": "components.csv",
                },
            },
        )

        with pytest.raises(ValueError, match="canonical component catalog filename"):
            load_scenario_bundle(scenario_dir)
    finally:
        cleanup_scenario_copy(scenario_dir)


def test_loader_accepts_missing_storage_mapping_for_authoring_input() -> None:
    scenario_dir = prepare_scenario_copy(
        "data/decision_platform/maquete_v2",
        "maquete_v2_missing_storage_mapping",
    )
    try:
        update_scenario_yaml(
            scenario_dir,
            "scenario_settings.yaml",
            lambda payload: {key: value for key, value in payload.items() if key != "storage"},
        )

        bundle = load_scenario_bundle(scenario_dir)

        assert "storage" not in bundle.scenario_settings
    finally:
        cleanup_scenario_copy(scenario_dir)


def test_loader_rejects_topology_rule_with_non_boolean_flag() -> None:
    scenario_dir = prepare_scenario_copy(
        "data/decision_platform/maquete_v2",
        "maquete_v2_topology_non_boolean_flag",
    )
    try:
        update_scenario_yaml(
            scenario_dir,
            "topology_rules.yaml",
            lambda payload: {
                **payload,
                "families": {
                    **payload["families"],
                    "star_manifolds": {
                        **payload["families"]["star_manifolds"],
                        "allow_cycles": "false",
                    },
                },
            },
        )

        with pytest.raises(ValueError, match="must be boolean"):
            load_scenario_bundle(scenario_dir)
    finally:
        cleanup_scenario_copy(scenario_dir)


def test_loader_rejects_topology_rule_with_non_positive_route_limit() -> None:
    scenario_dir = prepare_scenario_copy(
        "data/decision_platform/maquete_v2",
        "maquete_v2_topology_invalid_route_limit",
    )
    try:
        update_scenario_yaml(
            scenario_dir,
            "topology_rules.yaml",
            lambda payload: {
                **payload,
                "families": {
                    **payload["families"],
                    "hybrid_free": {
                        **payload["families"]["hybrid_free"],
                        "max_active_pumps_per_route": 0,
                    },
                },
            },
        )

        with pytest.raises(ValueError, match="positive integer"):
            load_scenario_bundle(scenario_dir)
    finally:
        cleanup_scenario_copy(scenario_dir)


def test_loader_rejects_layout_with_duplicate_rule_id() -> None:
    scenario_dir = prepare_scenario_copy(
        "data/decision_platform/maquete_v2",
        "maquete_v2_layout_duplicate_rule_id",
    )
    try:
        def _duplicate_rule_id(frame):
            updated = frame.copy()
            updated.loc[updated["rule_id"] == "L08", "rule_id"] = "L07"
            return updated

        update_scenario_table(scenario_dir, "layout_constraints.csv", _duplicate_rule_id)

        with pytest.raises(ValueError, match="duplicated rule_id"):
            load_scenario_bundle(scenario_dir)
    finally:
        cleanup_scenario_copy(scenario_dir)


def test_loader_rejects_layout_missing_required_global_key() -> None:
    scenario_dir = prepare_scenario_copy(
        "data/decision_platform/maquete_v2",
        "maquete_v2_layout_missing_required_key",
    )
    try:
        update_scenario_table(
            scenario_dir,
            "layout_constraints.csv",
            lambda frame: frame.loc[frame["key"] != "hose_module_m"].reset_index(drop=True),
        )

        with pytest.raises(ValueError, match="missing required global keys"):
            load_scenario_bundle(scenario_dir)
    finally:
        cleanup_scenario_copy(scenario_dir)


def test_loader_rejects_layout_with_invalid_hose_module() -> None:
    scenario_dir = prepare_scenario_copy(
        "data/decision_platform/maquete_v2",
        "maquete_v2_layout_invalid_hose_module",
    )
    try:
        update_scenario_table(
            scenario_dir,
            "layout_constraints.csv",
            lambda frame: frame.assign(value=frame["value"].where(frame["key"] != "hose_module_m", 0)),
        )

        with pytest.raises(ValueError, match="hose_module_m"):
            load_scenario_bundle(scenario_dir)
    finally:
        cleanup_scenario_copy(scenario_dir)
