from __future__ import annotations

from functools import lru_cache

import pytest

from agri_circuit_optimizer.io.load_data import load_scenario
from agri_circuit_optimizer.model.build_model import build_model
from agri_circuit_optimizer.preprocess.build_options import build_stage_options
from agri_circuit_optimizer.solve.run_case import (
    _extract_solution,
    _solve_case_fallback,
    _solve_model,
    solve_case,
)
from scenario_utils import (
    copy_maquete_scenario,
    read_csv,
    read_settings,
    write_csv,
    write_settings,
)


def _keep_routes(scenario_dir, route_ids: list[str]) -> None:
    routes = read_csv(scenario_dir, "routes")
    write_csv(scenario_dir, "routes", routes[routes["route_id"].isin(route_ids)].copy())


@lru_cache(maxsize=1)
def _solve_maquete_core() -> dict:
    return solve_case("data/scenario/maquete_core")


def test_maquete_options_compute_branch_lengths_and_keep_p4_participating() -> None:
    data = load_scenario("data/scenario/maquete_core")
    options = build_stage_options(data)

    assert "P4" in options["source_options"]
    assert "P4" in options["destination_options"]
    assert options["route_class_feasibility"]["R013"] == ["g1"]

    p4_source = options["source_options"]["P4"][0]
    p4_destination = options["destination_options"]["P4"][0]

    assert p4_source["hose_length_m"] >= 1.0
    assert p4_source["hose_modules_used"] == int(p4_source["hose_modules_used"])
    assert p4_source["component_counts"]["hose_g1_1m"] == p4_source["hose_modules_used"]
    assert p4_destination["hose_length_m"] >= 1.0
    assert p4_destination["component_counts"]["hose_g1_1m"] == p4_destination["hose_modules_used"]


def test_maquete_trunks_do_not_consume_tees_in_bottleneck_mode() -> None:
    options = build_stage_options(load_scenario("data/scenario/maquete_core"))

    for trunk_option in options["suction_trunk_options"] + options["discharge_trunk_options"]:
        assert trunk_option["metadata"]["consume_connector"] is False
        assert "connector" not in trunk_option["category_profile"]
        assert not any(component_id.startswith("tee_") for component_id in trunk_option["component_counts"])
        assert trunk_option["component_counts"]["hose_g1_1m"] == trunk_option["hose_modules_used"]


def test_maquete_core_solves_end_to_end_with_expected_inventory_and_metering() -> None:
    solution = _solve_maquete_core()

    assert solution["summary"]["solver_status"] == "ok"
    assert solution["summary"]["system_class"] == "g1"
    assert solution["summary"]["mandatory_routes_served"] == 14
    assert solution["summary"]["routes_served"] == 23
    assert solution["summary"]["hose_total_used_m"] == pytest.approx(17.0)
    assert solution["summary"]["tee_total_used"] == 15
    assert solution["summary"]["base_vs_extra_usage"]["extra"] == {"tee_extra_g1": 5}

    route_ids = {route["route_id"] for route in solution["routes"]}
    assert "R013" in route_ids
    assert all(
        route["flow_delivered_lpm"] >= route["q_min_required_lpm"]
        for route in solution["routes"]
    )
    assert all(
        not route["meter_is_bypass"]
        for route in solution["routes"]
        if route["measurement_required"]
    )
    assert all(
        route["hydraulic_mode"] == "bottleneck_plus_length"
        for route in solution["routes"]
    )
    assert all(
        hydraulic["hydraulic_mode"] == "bottleneck_plus_length"
        for hydraulic in solution["hydraulics"]
    )

    bom_ids = {item["component_id"] for item in solution["bom"]}
    assert "pump_extra_g1" not in bom_ids
    assert "valve_extra_g1" not in bom_ids


def test_maquete_small_slice_keeps_pyomo_and_fallback_consistent() -> None:
    scenario_dir = copy_maquete_scenario()
    _keep_routes(scenario_dir, ["R004", "R013"])

    data = load_scenario(scenario_dir)
    options = build_stage_options(data)
    fallback_solution = _solve_case_fallback(data, options, "highs")

    model = build_model(data, options)
    solver_used, results = _solve_model(model, "highs")
    pyomo_solution = _extract_solution(model, results, solver_used)

    assert pyomo_solution["summary"]["system_class"] == fallback_solution["summary"]["system_class"]
    assert pyomo_solution["bom"] == fallback_solution["bom"]
    assert {route["route_id"] for route in pyomo_solution["routes"]} == {"R004", "R013"}
    assert pyomo_solution["routes"] == fallback_solution["routes"]
    assert pyomo_solution["hydraulics"] == fallback_solution["hydraulics"]


def test_maquete_more_distance_increases_hose_and_reduces_hydraulic_slack() -> None:
    scenario_dir = copy_maquete_scenario()
    _keep_routes(scenario_dir, ["R004", "R013"])

    baseline = solve_case(scenario_dir)

    settings = read_settings(scenario_dir)
    settings["suction_manifold_x_m"] = -0.8
    settings["discharge_manifold_x_m"] = 1.6
    write_settings(scenario_dir, settings)

    stretched = solve_case(scenario_dir)

    assert stretched["summary"]["hose_total_used_m"] > baseline["summary"]["hose_total_used_m"]
    assert sum(item["hydraulic_slack_lpm"] for item in stretched["hydraulics"]) < sum(
        item["hydraulic_slack_lpm"] for item in baseline["hydraulics"]
    )


def test_maquete_low_tee_capacity_becomes_reported_bottleneck() -> None:
    scenario_dir = copy_maquete_scenario()
    _keep_routes(scenario_dir, ["R001", "R013"])

    components = read_csv(scenario_dir, "components")
    components.loc[components["component_id"].str.contains("tee_"), "q_max_lpm"] = 35.0
    write_csv(scenario_dir, "components", components)

    solution = solve_case(scenario_dir)

    for hydraulic in solution["hydraulics"]:
        assert hydraulic["gargalo_principal"] == "source_branch"
        assert hydraulic["bottleneck_component_id"] == "tee_base_g1"
        assert hydraulic["route_effective_q_max_lpm"] == pytest.approx(34.3)


def test_maquete_small_meter_can_be_rejected_in_favor_of_mid_meter() -> None:
    scenario_dir = copy_maquete_scenario()
    _keep_routes(scenario_dir, ["R004", "R013"])

    routes = read_csv(scenario_dir, "routes")
    routes.loc[routes["route_id"] == "R004", ["q_min_delivered_lpm", "dose_error_max_pct"]] = [45.0, 1.5]
    write_csv(scenario_dir, "routes", routes)

    solution = solve_case(scenario_dir)
    route_r004 = next(route for route in solution["routes"] if route["route_id"] == "R004")

    assert route_r004["selected_meter_id"] == "meter_mid_g1"
    assert route_r004["meter_is_bypass"] is False
    assert route_r004["meter_q_range_ok"] is True
    assert route_r004["meter_dose_ok"] is True
    assert route_r004["meter_error_ok"] is True
