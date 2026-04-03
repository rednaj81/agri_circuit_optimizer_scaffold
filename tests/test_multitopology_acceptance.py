from __future__ import annotations

from pathlib import Path

import pandas as pd
import yaml

from agri_circuit_optimizer.io.load_data import load_scenario
from agri_circuit_optimizer.solve.run_case import solve_case
from agri_circuit_optimizer.solve.topology_engine import compare_family_solutions
from scenario_utils import copy_maquete_bus_scenario, keep_routes, read_csv, write_csv


def _read_topology_rules(path: Path) -> dict:
    return yaml.safe_load((path / "topology_rules.yaml").read_text(encoding="utf-8"))


def _write_topology_rules(path: Path, rules: dict) -> None:
    (path / "topology_rules.yaml").write_text(
        yaml.safe_dump(rules, sort_keys=False),
        encoding="utf-8",
    )


def test_multitopology_loader_reads_edges_and_rules() -> None:
    data = load_scenario("data/scenario/maquete_bus_manual")

    assert data["settings"]["topology_family"] == "bus_with_pump_islands"
    assert data["edges"] is not None
    assert len(data["edges"]) == 17
    assert data["topology_rules"]["allow_idle_pumps_on_path"] is True
    assert data["topology_rules"]["allow_idle_meters_on_path"] is True

    route_r013 = data["routes"].loc[data["routes"]["route_id"] == "R013"].iloc[0]
    assert route_r013["route_group"] == "service"


def test_manual_bus_reports_active_paths_and_single_reading_meter() -> None:
    solution = solve_case("data/scenario/maquete_bus_manual")

    assert solution["summary"]["topology_family"] == "bus_with_pump_islands"
    assert solution["summary"]["solver_status"] == "infeasible"
    assert solution["summary"]["service_routes_served"] == 1
    assert solution["summary"]["solenoid_total"] == 9

    route_r008 = next(route for route in solution["routes"] if route["route_id"] == "R008")
    route_r001 = next(route for route in solution["routes"] if route["route_id"] == "R001")
    route_r004 = next(route for route in solution["routes"] if route["route_id"] == "R004")

    assert route_r008["served"] is True
    assert route_r008["selected_meter_id"] == "meter_small_g1"
    assert route_r008["selective_route_realizable"] is True
    assert route_r008["active_path_edge_ids"]
    assert route_r001["served"] is True
    assert route_r001["selected_meter_id"] is None
    assert route_r004["served"] is False
    assert route_r004["failure_reason"] == "meter_selection"


def test_fixed_topology_respects_conflict_groups_in_path_selection() -> None:
    scenario_dir = copy_maquete_bus_scenario()
    keep_routes(scenario_dir, ["R009", "R013"])

    edges = read_csv(scenario_dir, "edges")
    edges = edges[
        edges["edge_id"].isin(["E_TAP_I", "E_TAP_IR", "E_TAP_P1", "E_BUS_12", "E_BUS_23"])
    ].copy()
    edges["group_id"] = edges["group_id"].astype("string")
    edges.loc[edges["edge_id"].isin(["E_BUS_12", "E_BUS_23"]), "group_id"] = "ALT_PATH"
    edges.loc[edges["edge_id"] == "E_BUS_12", "component_ids"] = "hose_g1_1m"
    shortcut = pd.DataFrame(
        [
            {
                "edge_id": "E_BUS_13_SHORT",
                "from_node": "B1",
                "to_node": "B3",
                "topology_family": "bus_with_pump_islands",
                "edge_kind": "pump_island",
                "length_m": 1.0,
                "direction_mode": "forward_only",
                "group_id": "ALT_PATH",
                "can_be_active": 1,
                "counts_towards_hose_total": 1,
                "counts_towards_connector_total": 0,
                "must_be_closed_if_unused": 0,
                "default_installed": 1,
                "component_ids": "hose_g1_1m|pump_suction_base_g1|meter_small_g1",
                "branch_role": "",
                "notes": "shortcut with single conflict edge",
            }
        ]
    )
    edges = pd.concat([edges, shortcut], ignore_index=True)
    write_csv(scenario_dir, "edges", edges)

    solution = solve_case(scenario_dir)
    route_r009 = next(route for route in solution["routes"] if route["route_id"] == "R009")

    assert route_r009["served"] is True
    assert route_r009["active_path_edge_ids"] == ["E_TAP_I", "E_BUS_13_SHORT", "E_TAP_P1"]


def test_idle_pumps_on_path_can_be_disabled_by_family_rule() -> None:
    scenario_dir = copy_maquete_bus_scenario()
    keep_routes(scenario_dir, ["R001", "R013"])

    rules = _read_topology_rules(scenario_dir)
    rules["allow_idle_pumps_on_path"] = False
    _write_topology_rules(scenario_dir, rules)

    solution = solve_case(scenario_dir)
    route_r001 = next(route for route in solution["routes"] if route["route_id"] == "R001")

    assert route_r001["served"] is False
    assert route_r001["failure_reason"] == "pump_selection"
    assert solution["summary"]["solver_status"] == "infeasible"


def test_service_route_can_fail_without_invalidating_core_routes() -> None:
    scenario_dir = copy_maquete_bus_scenario()
    keep_routes(scenario_dir, ["R002", "R013"])

    service_edges = read_csv(scenario_dir, "edges")
    service_edges = service_edges[service_edges["edge_id"] != "E_TAP_IR"].copy()
    write_csv(scenario_dir, "edges", service_edges)

    solution = solve_case(scenario_dir)
    route_r002 = next(route for route in solution["routes"] if route["route_id"] == "R002")
    route_r013 = next(route for route in solution["routes"] if route["route_id"] == "R013")

    assert route_r002["served"] is True
    assert route_r013["served"] is False
    assert solution["summary"]["core_routes_served"] == 1
    assert solution["summary"]["service_routes_served"] == 0
    assert solution["summary"]["solver_status"] == "ok"


def test_multitopology_family_comparison_shows_bus_vs_star_tradeoff() -> None:
    star_solution = solve_case("data/scenario/maquete_core")
    bus_solution = solve_case("data/scenario/maquete_bus_manual")

    comparison = compare_family_solutions(
        {
            star_solution["summary"]["topology_family"]: star_solution,
            bus_solution["summary"]["topology_family"]: bus_solution,
        }
    )

    star = comparison["families"]["star_manifolds"]
    bus = comparison["families"]["bus_with_pump_islands"]

    assert star["solenoid_total"] > bus["solenoid_total"]
    assert star["routes_served"] > bus["routes_served"]
    assert bus["total_material_cost"] < star["total_material_cost"]
