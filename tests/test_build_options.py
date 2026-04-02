from agri_circuit_optimizer.io.load_data import load_scenario
from agri_circuit_optimizer.preprocess.build_options import build_stage_options


def test_build_stage_options_creates_v1_option_sets():
    data = load_scenario("data/scenario/example")
    options = build_stage_options(data)

    assert sorted(options["system_classes"]) == ["g1", "g2"]
    assert set(options["source_options"]["W"][0]["component_counts"]) >= {
        "hose_g1_5m",
        "connector_g1",
    }
    assert len(options["pump_slot_options"]) >= 2
    assert len(options["meter_slot_options"]) >= 2
    assert len(options["suction_trunk_options"]) == 2
    assert len(options["discharge_trunk_options"]) == 2


def test_build_stage_options_keeps_mandatory_routes_viable():
    data = load_scenario("data/scenario/example")
    options = build_stage_options(data)
    mandatory_routes = data["routes"].loc[data["routes"]["mandatory"], "route_id"].tolist()

    assert mandatory_routes
    for route_id in mandatory_routes:
        assert options["route_class_feasibility"][route_id]


def test_branch_generation_prunes_dominated_hose_variants():
    data = load_scenario("data/scenario/example")
    options = build_stage_options(data)

    water_option_ids = [option["option_id"] for option in options["source_options"]["W"]]
    assert not any("10m" in option_id for option_id in water_option_ids)
