from __future__ import annotations

import pytest

from decision_platform.data_io.loader import load_scenario_bundle
from tests.decision_platform.scenario_utils import (
    cleanup_scenario_copy,
    prepare_scenario_copy,
    update_scenario_table,
)


pytestmark = [pytest.mark.fast]


def test_maquete_v2_component_catalog_contract_is_valid() -> None:
    bundle = load_scenario_bundle("data/decision_platform/maquete_v2")

    assert bundle.components["component_id"].is_unique
    assert bundle.components.loc[bundle.components["category"] == "meter", "active_for_reading"].all()


def test_loader_rejects_duplicate_component_ids() -> None:
    scenario_dir = prepare_scenario_copy(
        "data/decision_platform/maquete_v2",
        "maquete_v2_duplicate_component_id",
    )
    try:
        def _duplicate_component_id(frame):
            updated = frame.copy()
            updated.loc[updated["component_id"] == "meter_mid_g1", "component_id"] = "meter_small_g1"
            return updated

        update_scenario_table(scenario_dir, "component_catalog.csv", _duplicate_component_id)

        with pytest.raises(ValueError, match="duplicated component_id"):
            load_scenario_bundle(scenario_dir)
    finally:
        cleanup_scenario_copy(scenario_dir)


def test_loader_rejects_unknown_component_category() -> None:
    scenario_dir = prepare_scenario_copy(
        "data/decision_platform/maquete_v2",
        "maquete_v2_unknown_component_category",
    )
    try:
        update_scenario_table(
            scenario_dir,
            "component_catalog.csv",
            lambda frame: frame.assign(
                category=frame["category"].where(frame["component_id"] != "tee_g1", "mystery_part"),
            ),
        )

        with pytest.raises(ValueError, match="unsupported categories"):
            load_scenario_bundle(scenario_dir)
    finally:
        cleanup_scenario_copy(scenario_dir)


def test_loader_rejects_unreadable_meter() -> None:
    scenario_dir = prepare_scenario_copy(
        "data/decision_platform/maquete_v2",
        "maquete_v2_unreadable_meter",
    )
    try:
        update_scenario_table(
            scenario_dir,
            "component_catalog.csv",
            lambda frame: frame.assign(
                active_for_reading=frame["active_for_reading"].where(frame["component_id"] != "meter_mid_g1", 0),
            ),
        )

        with pytest.raises(ValueError, match="active_for_reading=false"):
            load_scenario_bundle(scenario_dir)
    finally:
        cleanup_scenario_copy(scenario_dir)


def test_loader_rejects_invalid_component_inventory_or_cost() -> None:
    scenario_dir = prepare_scenario_copy(
        "data/decision_platform/maquete_v2",
        "maquete_v2_invalid_component_inventory",
    )
    try:
        update_scenario_table(
            scenario_dir,
            "component_catalog.csv",
            lambda frame: frame.assign(
                available_qty=frame["available_qty"].where(frame["component_id"] != "pump_main_300", 0),
            ),
        )

        with pytest.raises(ValueError, match="invalid available_qty"):
            load_scenario_bundle(scenario_dir)
    finally:
        cleanup_scenario_copy(scenario_dir)


def test_loader_rejects_edge_rule_with_unknown_category() -> None:
    scenario_dir = prepare_scenario_copy(
        "data/decision_platform/maquete_v2",
        "maquete_v2_edge_rule_unknown_category",
    )
    try:
        update_scenario_table(
            scenario_dir,
            "edge_component_rules.csv",
            lambda frame: frame.assign(
                allowed_categories=frame["allowed_categories"].where(
                    frame["rule_id"] != "R06",
                    "hose|pump|meter|connector|mystery_part",
                ),
            ),
        )

        with pytest.raises(ValueError, match="unsupported categories"):
            load_scenario_bundle(scenario_dir)
    finally:
        cleanup_scenario_copy(scenario_dir)


def test_loader_rejects_edge_rule_with_required_outside_allowed() -> None:
    scenario_dir = prepare_scenario_copy(
        "data/decision_platform/maquete_v2",
        "maquete_v2_edge_rule_required_outside_allowed",
    )
    try:
        update_scenario_table(
            scenario_dir,
            "edge_component_rules.csv",
            lambda frame: frame.assign(
                required_categories=frame["required_categories"].where(frame["rule_id"] != "R06", "hose|meter"),
                allowed_categories=frame["allowed_categories"].where(frame["rule_id"] != "R06", "hose|pump|connector"),
            ),
        )

        with pytest.raises(ValueError, match="required_categories outside allowed_categories"):
            load_scenario_bundle(scenario_dir)
    finally:
        cleanup_scenario_copy(scenario_dir)


def test_loader_rejects_edge_rule_with_optional_outside_allowed() -> None:
    scenario_dir = prepare_scenario_copy(
        "data/decision_platform/maquete_v2",
        "maquete_v2_edge_rule_optional_outside_allowed",
    )
    try:
        update_scenario_table(
            scenario_dir,
            "edge_component_rules.csv",
            lambda frame: frame.assign(
                optional_categories=frame["optional_categories"].where(frame["rule_id"] != "R06", "meter|check_valve"),
                allowed_categories=frame["allowed_categories"].where(frame["rule_id"] != "R06", "hose|pump|connector"),
            ),
        )

        with pytest.raises(ValueError, match="optional_categories outside allowed_categories"):
            load_scenario_bundle(scenario_dir)
    finally:
        cleanup_scenario_copy(scenario_dir)
