from __future__ import annotations

import pytest

from decision_platform.data_io.loader import load_scenario_bundle
from tests.decision_platform.scenario_utils import (
    cleanup_scenario_copy,
    prepare_scenario_copy,
    update_scenario_table,
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
