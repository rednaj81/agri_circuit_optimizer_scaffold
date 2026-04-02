from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

from agri_circuit_optimizer.io.load_data import load_scenario
from agri_circuit_optimizer.solve.run_case import solve_case
from scenario_utils import copy_example_scenario, keep_routes


def test_v1_example_solves_end_to_end_and_respects_frozen_rules():
    scenario_dir = copy_example_scenario()
    keep_routes(scenario_dir, ["R001", "R007", "R015"])

    data = load_scenario(scenario_dir)
    solution = solve_case(scenario_dir)
    routes_by_id = {route["route_id"]: route for route in solution["routes"]}
    mandatory_routes = data["routes"].loc[data["routes"]["mandatory"], "route_id"].tolist()

    assert solution["summary"]["routes_served"] >= len(mandatory_routes)
    assert solution["summary"]["mandatory_routes_served"] == len(mandatory_routes)
    assert solution["summary"]["system_class"] in {"g1", "g2", "mixed"}

    for route_id in mandatory_routes:
        assert route_id in routes_by_id
        assert routes_by_id[route_id]["flow_delivered_lpm"] >= routes_by_id[route_id]["q_min_required_lpm"]
        assert routes_by_id[route_id]["sink"] != "W"
        assert routes_by_id[route_id]["source"] != "S"

    assert routes_by_id["R015"]["source"] == "I"
    assert routes_by_id["R015"]["sink"] == "IR"

    measurement_routes = [route for route in solution["routes"] if route["measurement_required"]]
    assert measurement_routes
    assert all(not route["meter_is_bypass"] for route in measurement_routes)
    assert all(route["selective_route_realizable"] for route in solution["routes"])
    assert all(route["open_suction_branch_count"] == 1 for route in solution["routes"])
    assert all(route["open_discharge_branch_count"] == 1 for route in solution["routes"])


def test_v1_reports_are_written_to_output_dir():
    scenario_dir = copy_example_scenario()
    keep_routes(scenario_dir, ["R001", "R007", "R015"])
    output_dir = Path("tests/_tmp") / f"reports-{uuid4().hex}"
    solution = solve_case(scenario_dir, output_dir=output_dir)

    assert (output_dir / "summary.json").exists()
    assert (output_dir / "bom.json").exists()
    assert (output_dir / "routes.json").exists()
    assert (output_dir / "hydraulics.json").exists()

    written_summary = json.loads((output_dir / "summary.json").read_text(encoding="utf-8"))
    assert written_summary["system_class"] == solution["summary"]["system_class"]
