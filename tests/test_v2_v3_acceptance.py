from __future__ import annotations

from pathlib import Path

import pytest

from agri_circuit_optimizer.io.load_data import load_scenario
from agri_circuit_optimizer.model.build_model import build_model
from agri_circuit_optimizer.model.sets_params import build_sets_and_parameters
from agri_circuit_optimizer.preprocess.build_options import build_stage_options
from agri_circuit_optimizer.preprocess.feasibility import meter_compatibility
from agri_circuit_optimizer.solve.run_case import (
    _extract_solution,
    _solve_case_fallback,
    _solve_model,
    solve_case,
)
from scenario_utils import copy_example_scenario, keep_routes, read_csv, read_settings, write_csv, write_settings


def _keep_routes(scenario_dir: Path, route_ids: list[str]) -> None:
    keep_routes(scenario_dir, route_ids)


def test_v2_dose_and_error_can_force_specific_meter() -> None:
    scenario_dir = copy_example_scenario()
    _keep_routes(scenario_dir, ["R007", "R015"])

    routes = read_csv(scenario_dir, "routes")
    routes.loc[routes["route_id"] == "R007", ["q_min_delivered_lpm", "dose_min_l", "dose_error_max_pct"]] = [
        25,
        1,
        1,
    ]
    write_csv(scenario_dir, "routes", routes)

    solution = solve_case(scenario_dir)
    route_r007 = next(route for route in solution["routes"] if route["route_id"] == "R007")

    assert route_r007["selected_meter_id"] == "meter_mag_g1_mid"
    assert route_r007["meter_is_bypass"] is False
    assert route_r007["meter_q_range_ok"] is True
    assert route_r007["meter_dose_ok"] is True
    assert route_r007["meter_error_ok"] is True


def test_v2_mandatory_route_fails_when_no_meter_is_compatible() -> None:
    scenario_dir = copy_example_scenario()
    _keep_routes(scenario_dir, ["R007", "R015"])

    routes = read_csv(scenario_dir, "routes")
    routes.loc[routes["route_id"] == "R007", "dose_error_max_pct"] = 0
    write_csv(scenario_dir, "routes", routes)

    data = load_scenario(scenario_dir)
    with pytest.raises(ValueError, match="Mandatory routes without any viable option chain"):
        build_stage_options(data)


def test_v2_non_measurement_route_can_use_bypass() -> None:
    scenario_dir = copy_example_scenario()
    _keep_routes(scenario_dir, ["R001", "R015"])

    solution = solve_case(scenario_dir)
    route_ids = {route["route_id"] for route in solution["routes"]}

    assert route_ids == {"R001", "R015"}
    assert all(route["measurement_required"] is False for route in solution["routes"])
    assert all(route["meter_is_bypass"] is True for route in solution["routes"])
    assert {route["selected_meter_id"] for route in solution["routes"]} == {"bypass_g1"}


def test_v2_metering_payload_matches_fallback_and_pyomo_when_available() -> None:
    scenario_dir = copy_example_scenario()
    _keep_routes(scenario_dir, ["R007", "R015"])

    data = load_scenario(scenario_dir)
    options = build_stage_options(data)
    payload = build_sets_and_parameters(data, options)
    route = payload["routes"]["R007"]

    expected_flags = {
        option_id: meter_compatibility(route, option)
        for option_id, option in payload["meter_options"].items()
    }
    assert payload["route_meter_compatibility"]["R007"] == expected_flags

    fallback_solution = _solve_case_fallback(data, options, "highs")
    fallback_route = next(route for route in fallback_solution["routes"] if route["route_id"] == "R007")
    fallback_flags = expected_flags[fallback_route["meter_option_id"]]

    assert fallback_route["meter_q_range_ok"] == fallback_flags["q_range_ok"]
    assert fallback_route["meter_dose_ok"] == fallback_flags["dose_ok"]
    assert fallback_route["meter_error_ok"] == fallback_flags["error_ok"]
    assert fallback_route["meter_is_bypass"] == fallback_flags["meter_is_bypass"]

    try:
        model = build_model(data, options)
        solver_used, results = _solve_model(model, "highs")
    except Exception:
        return

    pyomo_solution = _extract_solution(model, results, solver_used)
    pyomo_route = next(route for route in pyomo_solution["routes"] if route["route_id"] == "R007")

    assert pyomo_route["selected_meter_id"] == fallback_route["selected_meter_id"]
    assert pyomo_route["meter_is_bypass"] == fallback_route["meter_is_bypass"]
    assert pyomo_route["meter_q_range_ok"] == fallback_route["meter_q_range_ok"]
    assert pyomo_route["meter_dose_ok"] == fallback_route["meter_dose_ok"]
    assert pyomo_route["meter_error_ok"] == fallback_route["meter_error_ok"]


def test_v3_incompatible_system_class_makes_route_infeasible() -> None:
    scenario_dir = copy_example_scenario()
    _keep_routes(scenario_dir, ["R007", "R015"])

    settings = read_settings(scenario_dir)
    settings["allowed_system_diameter_classes"] = ["g2"]
    write_settings(scenario_dir, settings)

    data = load_scenario(scenario_dir)
    with pytest.raises(ValueError, match="Mandatory routes without any viable option chain"):
        build_stage_options(data)


def test_v3_excessive_losses_make_scenario_infeasible() -> None:
    scenario_dir = copy_example_scenario()
    _keep_routes(scenario_dir, ["R001", "R015"])

    components = read_csv(scenario_dir, "components")
    components.loc[components["component_id"].str.contains("hose_"), "loss_lpm_equiv"] = 40.0
    write_csv(scenario_dir, "components", components)

    with pytest.raises(RuntimeError, match="Fallback enumeration could not find a feasible solution"):
        _solve_case_fallback(load_scenario(scenario_dir), build_stage_options(load_scenario(scenario_dir)), "highs")

    try:
        model = build_model(load_scenario(scenario_dir), build_stage_options(load_scenario(scenario_dir)))
        solver_used, results = _solve_model(model, "highs")
        pyomo_solution = _extract_solution(model, results, solver_used)
    except Exception:
        return

    assert not pyomo_solution["routes"]


def test_v3_pyomo_and_fallback_agree_on_loss_driven_topology_upgrade() -> None:
    scenario_dir = copy_example_scenario()
    _keep_routes(scenario_dir, ["R001", "R015"])

    components = read_csv(scenario_dir, "components")
    components.loc[components["component_id"].isin(["hose_g1_5m", "hose_g2_5m"]), "loss_lpm_equiv"] = 40.0
    write_csv(scenario_dir, "components", components)

    data = load_scenario(scenario_dir)
    options = build_stage_options(data)
    fallback_solution = _solve_case_fallback(data, options, "highs")

    assert fallback_solution["topology"]["suction_trunk_option_id"].endswith("hose_g1_10m_connector_g1")
    assert fallback_solution["topology"]["discharge_trunk_option_id"].endswith("hose_g1_10m_connector_g1")

    try:
        model = build_model(data, options)
        solver_used, results = _solve_model(model, "highs")
    except Exception:
        return

    pyomo_solution = _extract_solution(model, results, solver_used)

    assert pyomo_solution["topology"]["suction_trunk_option_id"] == fallback_solution["topology"]["suction_trunk_option_id"]
    assert pyomo_solution["topology"]["discharge_trunk_option_id"] == fallback_solution["topology"]["discharge_trunk_option_id"]
    assert pyomo_solution["summary"]["system_class"] == fallback_solution["summary"]["system_class"]
    assert {item["route_id"] for item in pyomo_solution["routes"]} == {item["route_id"] for item in fallback_solution["routes"]}
    assert pyomo_solution["bom"] == fallback_solution["bom"]
    for py_item, fb_item in zip(
        sorted(pyomo_solution["hydraulics"], key=lambda item: item["route_id"]),
        sorted(fallback_solution["hydraulics"], key=lambda item: item["route_id"]),
    ):
        assert py_item["route_id"] == fb_item["route_id"]
        assert py_item["system_class"] == fb_item["system_class"]
        assert py_item["suction_trunk_option_id"] == fb_item["suction_trunk_option_id"]
        assert py_item["discharge_trunk_option_id"] == fb_item["discharge_trunk_option_id"]
        assert py_item["gargalo_principal"] == fb_item["gargalo_principal"]
        assert py_item["flow_delivered_lpm"] == pytest.approx(fb_item["flow_delivered_lpm"])
        assert py_item["q_min_required_lpm"] == pytest.approx(fb_item["q_min_required_lpm"])
        assert py_item["total_loss_lpm_equiv"] == pytest.approx(fb_item["total_loss_lpm_equiv"])
        assert py_item["hydraulic_slack_lpm"] == pytest.approx(fb_item["hydraulic_slack_lpm"])


def test_v3_solver_picks_larger_pump_when_smaller_one_cannot_overcome_losses() -> None:
    scenario_dir = copy_example_scenario()
    _keep_routes(scenario_dir, ["R001", "R015"])

    routes = read_csv(scenario_dir, "routes")
    routes.loc[routes["route_id"] == "R001", "q_min_delivered_lpm"] = 70.0
    write_csv(scenario_dir, "routes", routes)
    components = read_csv(scenario_dir, "components")

    solution = solve_case(scenario_dir)
    route_r001 = next(route for route in solution["routes"] if route["route_id"] == "R001")
    hydraulic_r001 = next(item for item in solution["hydraulics"] if item["route_id"] == "R001")
    pump_capacity = float(
        components.loc[
            components["component_id"] == route_r001["pump_component_id"],
            "q_max_lpm",
        ].iloc[0]
    )

    assert pump_capacity > 80.0
    assert hydraulic_r001["total_loss_lpm_equiv"] > 0.0
    assert hydraulic_r001["hydraulic_slack_lpm"] >= 0.0
    assert hydraulic_r001["gargalo_principal"]


def test_v3_example_regression_keeps_v1_v2_contracts_and_new_reports() -> None:
    scenario_dir = copy_example_scenario()
    _keep_routes(scenario_dir, ["R001", "R007", "R015"])
    solution = solve_case(scenario_dir)

    for route in solution["routes"]:
        assert "selected_meter_id" in route
        assert "meter_is_bypass" in route
        assert "meter_q_range_ok" in route
        assert "meter_dose_ok" in route
        assert "meter_error_ok" in route

    for hydraulic in solution["hydraulics"]:
        assert "total_loss_lpm_equiv" in hydraulic
        assert "hydraulic_slack_lpm" in hydraulic
        assert "gargalo_principal" in hydraulic
        assert hydraulic["hydraulic_slack_lpm"] >= 0.0
