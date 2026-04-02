from __future__ import annotations

import pytest

from agri_circuit_optimizer.io.load_data import load_scenario
from agri_circuit_optimizer.preprocess.build_options import build_stage_options
from agri_circuit_optimizer.preprocess.feasibility import summarize_route_selectivity
from agri_circuit_optimizer.solve.run_case import solve_case
from scenario_utils import copy_example_scenario, keep_routes, read_csv, write_csv


def test_one_sided_nodes_only_expose_their_existing_branch_side() -> None:
    options = build_stage_options(load_scenario("data/scenario/maquete_core"))

    assert "W" in options["source_options"]
    assert "W" not in options["destination_options"]
    assert "IR" not in options["source_options"]
    assert "IR" in options["destination_options"]
    assert "S" not in options["source_options"]
    assert "S" in options["destination_options"]


def test_valid_route_reports_exactly_one_open_branch_per_side() -> None:
    scenario_dir = copy_example_scenario()
    keep_routes(scenario_dir, ["R001", "R007", "R015"])

    solution = solve_case(scenario_dir)

    assert all(route["selective_route_realizable"] is True for route in solution["routes"])
    assert all(route["extra_open_branch_conflict"] is False for route in solution["routes"])
    assert all(route["open_suction_branch_count"] == 1 for route in solution["routes"])
    assert all(route["open_discharge_branch_count"] == 1 for route in solution["routes"])


def test_passive_extra_destination_branch_invalidates_selective_star_route() -> None:
    scenario_dir = copy_example_scenario()
    keep_routes(scenario_dir, ["R001", "R015"])

    destination_templates = read_csv(scenario_dir, "destination_branch_templates")
    destination_templates["require_valve"] = 0
    write_csv(scenario_dir, "destination_branch_templates", destination_templates)

    data = load_scenario(scenario_dir)
    options = build_stage_options(data)
    active_source_nodes = sorted(set(data["routes"]["source"]))
    active_sink_nodes = sorted(set(data["routes"]["sink"]))
    route = data["routes"].loc[data["routes"]["route_id"] == "R001"].to_dict("records")[0]
    selectivity = summarize_route_selectivity(
        route=route,
        source_selection={
            node_id: options["source_options"][node_id][0] for node_id in active_source_nodes
        },
        destination_selection={
            node_id: options["destination_options"][node_id][0] for node_id in active_sink_nodes
        },
    )

    assert selectivity["selective_route_realizable"] is False
    assert selectivity["extra_open_branch_conflict"] is True
    assert selectivity["open_discharge_branch_count"] == 2
    assert selectivity["conflicting_sink_nodes"] == ["IR"]

    with pytest.raises(RuntimeError, match="Fallback enumeration could not find a feasible solution"):
        solve_case(scenario_dir)


def test_bidirectional_node_requires_independent_isolation_on_both_sides() -> None:
    scenario_dir = copy_example_scenario()
    keep_routes(scenario_dir, ["R007", "R011", "R015"])

    destination_templates = read_csv(scenario_dir, "destination_branch_templates")
    destination_templates["require_valve"] = 0
    write_csv(scenario_dir, "destination_branch_templates", destination_templates)

    with pytest.raises(RuntimeError, match="Fallback enumeration could not find a feasible solution"):
        solve_case(scenario_dir)
