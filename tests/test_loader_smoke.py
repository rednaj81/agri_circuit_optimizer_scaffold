from agri_circuit_optimizer.io.load_data import load_scenario, scenario_summary


def test_loader_smoke():
    data = load_scenario("data/scenario/example")
    summary = scenario_summary(data)
    assert summary["nodes"] >= 1
    assert summary["routes"] >= 1
    assert summary["components"] >= 1
