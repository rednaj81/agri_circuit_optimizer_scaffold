from __future__ import annotations

from agri_circuit_optimizer.io.load_data import load_scenario, scenario_summary


def test_loader_accepts_maquete_core_with_optional_geometry_columns() -> None:
    data = load_scenario("data/scenario/maquete_core")
    nodes = data["nodes"]
    routes = data["routes"]
    settings = data["settings"]

    assert "P4" in nodes["node_id"].tolist()
    assert {"x_m", "y_m", "footprint_w_m", "footprint_d_m"} <= set(nodes.columns)
    assert ((routes["source"] == "I") & (routes["sink"] == "IR")).any()
    assert not (routes["sink"] == "W").any()
    assert not (routes["source"] == "S").any()
    assert settings["hydraulic_loss_mode"] == "bottleneck_plus_length"
    assert settings["hose_total_available_m"] == 20.0
    assert settings["maquette_trunks_consume_connectors"] is False


def test_maquete_core_summary_counts_are_consistent() -> None:
    summary = scenario_summary(load_scenario("data/scenario/maquete_core"))

    assert summary["nodes"] == 9
    assert summary["routes"] == 23
    assert summary["mandatory_routes"] == 14
    assert summary["components"] == 14
