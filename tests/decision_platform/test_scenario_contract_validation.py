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


def test_maquete_v2_route_contract_is_valid() -> None:
    bundle = load_scenario_bundle("data/decision_platform/maquete_v2")

    assert bundle.route_requirements["route_group"].isin(["core", "optional", "service"]).all()


def test_loader_rejects_route_entering_node_without_inbound_permission() -> None:
    scenario_dir = prepare_scenario_copy(
        "data/decision_platform/maquete_v2",
        "maquete_v2_route_enters_w",
    )
    try:
        update_scenario_table(
            scenario_dir,
            "route_requirements.csv",
            lambda frame: frame.assign(sink=frame["sink"].where(frame["route_id"] != "R004", "W")),
        )

        with pytest.raises(ValueError, match="allow_inbound=false"):
            load_scenario_bundle(scenario_dir)
    finally:
        cleanup_scenario_copy(scenario_dir)


def test_loader_rejects_route_leaving_node_without_outbound_permission() -> None:
    scenario_dir = prepare_scenario_copy(
        "data/decision_platform/maquete_v2",
        "maquete_v2_route_leaves_s",
    )
    try:
        update_scenario_table(
            scenario_dir,
            "route_requirements.csv",
            lambda frame: frame.assign(source=frame["source"].where(frame["route_id"] != "R004", "S")),
        )

        with pytest.raises(ValueError, match="allow_outbound=false"):
            load_scenario_bundle(scenario_dir)
    finally:
        cleanup_scenario_copy(scenario_dir)


def test_loader_rejects_dosing_route_without_measurement() -> None:
    scenario_dir = prepare_scenario_copy(
        "data/decision_platform/maquete_v2",
        "maquete_v2_dosing_without_measurement",
    )
    try:
        update_scenario_table(
            scenario_dir,
            "route_requirements.csv",
            lambda frame: frame.assign(
                measurement_required=frame["measurement_required"].where(frame["route_id"] != "R004", 0),
            ),
        )

        with pytest.raises(ValueError, match="without direct measurement"):
            load_scenario_bundle(scenario_dir)
    finally:
        cleanup_scenario_copy(scenario_dir)


def test_loader_rejects_duplicated_route_ids() -> None:
    scenario_dir = prepare_scenario_copy(
        "data/decision_platform/maquete_v2",
        "maquete_v2_duplicate_route_id",
    )
    try:
        def _duplicate_route_id(frame):
            updated = frame.copy()
            updated.loc[updated["route_id"] == "R005", "route_id"] = "R004"
            return updated

        update_scenario_table(scenario_dir, "route_requirements.csv", _duplicate_route_id)

        with pytest.raises(ValueError, match="duplicated route_id"):
            load_scenario_bundle(scenario_dir)
    finally:
        cleanup_scenario_copy(scenario_dir)


def test_loader_rejects_invalid_route_group() -> None:
    scenario_dir = prepare_scenario_copy(
        "data/decision_platform/maquete_v2",
        "maquete_v2_invalid_route_group",
    )
    try:
        update_scenario_table(
            scenario_dir,
            "route_requirements.csv",
            lambda frame: frame.assign(
                route_group=frame["route_group"].where(frame["route_id"] != "R018", "unsupported"),
            ),
        )

        with pytest.raises(ValueError, match="invalid route_group"):
            load_scenario_bundle(scenario_dir)
    finally:
        cleanup_scenario_copy(scenario_dir)


def test_loader_rejects_blank_link_id() -> None:
    scenario_dir = prepare_scenario_copy(
        "data/decision_platform/maquete_v2",
        "maquete_v2_blank_link_id",
    )
    try:
        update_scenario_table(
            scenario_dir,
            "candidate_links.csv",
            lambda frame: frame.assign(link_id=frame["link_id"].where(frame["link_id"] != "L001", "")),
        )

        with pytest.raises(ValueError, match="blank link_id"):
            load_scenario_bundle(scenario_dir)
    finally:
        cleanup_scenario_copy(scenario_dir)


def test_loader_rejects_duplicated_link_ids() -> None:
    scenario_dir = prepare_scenario_copy(
        "data/decision_platform/maquete_v2",
        "maquete_v2_duplicate_link_id",
    )
    try:
        def _duplicate_link_id(frame):
            updated = frame.copy()
            updated.loc[updated["link_id"] == "L002", "link_id"] = "L001"
            return updated

        update_scenario_table(scenario_dir, "candidate_links.csv", _duplicate_link_id)

        with pytest.raises(ValueError, match="duplicated link_id"):
            load_scenario_bundle(scenario_dir)
    finally:
        cleanup_scenario_copy(scenario_dir)


def test_loader_rejects_self_loop_candidate_link() -> None:
    scenario_dir = prepare_scenario_copy(
        "data/decision_platform/maquete_v2",
        "maquete_v2_self_loop_link",
    )
    try:
        update_scenario_table(
            scenario_dir,
            "candidate_links.csv",
            lambda frame: frame.assign(to_node=frame["to_node"].where(frame["link_id"] != "L013", "J1")),
        )

        with pytest.raises(ValueError, match="self-loop edges"):
            load_scenario_bundle(scenario_dir)
    finally:
        cleanup_scenario_copy(scenario_dir)


def test_loader_rejects_candidate_link_with_unknown_endpoint() -> None:
    scenario_dir = prepare_scenario_copy(
        "data/decision_platform/maquete_v2",
        "maquete_v2_unknown_link_endpoint",
    )
    try:
        update_scenario_table(
            scenario_dir,
            "candidate_links.csv",
            lambda frame: frame.assign(from_node=frame["from_node"].where(frame["link_id"] != "L013", "MISSING_NODE")),
        )

        with pytest.raises(ValueError, match="candidate_links.csv references unknown nodes"):
            load_scenario_bundle(scenario_dir)
    finally:
        cleanup_scenario_copy(scenario_dir)


def test_loader_rejects_candidate_link_with_missing_archetype_rule() -> None:
    scenario_dir = prepare_scenario_copy(
        "data/decision_platform/maquete_v2",
        "maquete_v2_missing_archetype_rule",
    )
    try:
        update_scenario_table(
            scenario_dir,
            "candidate_links.csv",
            lambda frame: frame.assign(archetype=frame["archetype"].where(frame["link_id"] != "L013", "unknown_rule")),
        )

        with pytest.raises(ValueError, match="without matching edge_component_rules"):
            load_scenario_bundle(scenario_dir)
    finally:
        cleanup_scenario_copy(scenario_dir)


def test_loader_rejects_route_requirement_with_unknown_endpoint() -> None:
    scenario_dir = prepare_scenario_copy(
        "data/decision_platform/maquete_v2",
        "maquete_v2_unknown_route_endpoint",
    )
    try:
        update_scenario_table(
            scenario_dir,
            "route_requirements.csv",
            lambda frame: frame.assign(source=frame["source"].where(frame["route_id"] != "R004", "MISSING_NODE")),
        )

        with pytest.raises(ValueError, match="route_requirements.csv references unknown nodes"):
            load_scenario_bundle(scenario_dir)
    finally:
        cleanup_scenario_copy(scenario_dir)


def test_loader_rejects_candidate_link_with_unknown_family_hint() -> None:
    scenario_dir = prepare_scenario_copy(
        "data/decision_platform/maquete_v2",
        "maquete_v2_unknown_family_hint",
    )
    try:
        update_scenario_table(
            scenario_dir,
            "candidate_links.csv",
            lambda frame: frame.assign(family_hint=frame["family_hint"].where(frame["link_id"] != "L013", "alien")),
        )

        with pytest.raises(ValueError, match="family_hint values outside"):
            load_scenario_bundle(scenario_dir)
    finally:
        cleanup_scenario_copy(scenario_dir)


def test_loader_rejects_candidate_link_with_disabled_family_hint() -> None:
    scenario_dir = prepare_scenario_copy(
        "data/decision_platform/maquete_v2",
        "maquete_v2_disabled_family_hint",
    )
    try:
        update_scenario_yaml(
            scenario_dir,
            "scenario_settings.yaml",
            lambda payload: {
                **payload,
                "enabled_families": ["star_manifolds"],
            },
        )

        with pytest.raises(ValueError, match="family_hint values outside"):
            load_scenario_bundle(scenario_dir)
    finally:
        cleanup_scenario_copy(scenario_dir)
