from __future__ import annotations

import pytest

from decision_platform.data_io.loader import load_scenario_bundle


pytestmark = [pytest.mark.fast]


def test_maquete_v2_loader_reads_full_contract() -> None:
    bundle = load_scenario_bundle("data/decision_platform/maquete_v2")

    assert bundle.scenario_settings["scenario_id"] == "maquete_v2"
    assert bundle.bundle_version == "decision_platform_scenario_bundle/v1"
    assert bundle.bundle_manifest_path is not None
    assert bundle.resolved_files["components.csv"].name == "component_catalog.csv"
    assert set(bundle.topology_rules["families"]) >= {
        "star_manifolds",
        "bus_with_pump_islands",
        "loop_ring",
        "hybrid_free",
    }
    assert bundle.components.loc[bundle.components["category"] == "pump", "is_fallback"].any()
    assert bundle.components.loc[bundle.components["category"] == "meter", "is_fallback"].any()
    assert bundle.route_requirements["route_group"].isin(["core", "optional", "service"]).all()
