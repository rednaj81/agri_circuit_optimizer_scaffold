from __future__ import annotations

import argparse
import json
from math import isnan
from itertools import combinations_with_replacement
from pathlib import Path
from typing import Any, Dict

from agri_circuit_optimizer.io.load_data import load_scenario, scenario_summary
from agri_circuit_optimizer.model.build_model import build_model
from agri_circuit_optimizer.postprocess.reports import (
    build_bom_report,
    build_hydraulic_report,
    build_route_report,
)
from agri_circuit_optimizer.preprocess.build_options import build_stage_options
from agri_circuit_optimizer.preprocess.feasibility import (
    compute_route_min_flow,
    summarize_route_selectivity,
    summarize_route_hydraulics,
)
from agri_circuit_optimizer.solve.topology_engine import (
    dry_run_fixed_topology,
    is_fixed_topology_mode,
    solve_fixed_topology_case,
)

EXTRA_USAGE_EPSILON = 1e-3


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run or dry-run a scenario.")
    parser.add_argument("--scenario", required=True, help="Path to scenario directory")
    parser.add_argument("--solver", default=None, help="Solver name override")
    parser.add_argument("--dry-run", action="store_true", help="Only validate and summarize")
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Optional directory to persist summary and reports as JSON files",
    )
    return parser.parse_args()


def solve_case(
    scenario_dir: str | Path,
    *,
    solver_name: str | None = None,
    output_dir: str | Path | None = None,
) -> Dict[str, Any]:
    scenario_path = Path(scenario_dir)
    data = load_scenario(scenario_path)
    if is_fixed_topology_mode(data):
        solution = solve_fixed_topology_case(
            data,
            solver_name=solver_name or data["settings"]["default_solver"],
        )
        if output_dir is not None:
            write_reports(solution, output_dir)
        return solution

    options = build_stage_options(data)

    try:
        import pyomo.environ as pyo

        model = build_model(data, options)
        solver_used, results = _solve_model(model, solver_name or data["settings"]["default_solver"])
        solution = _extract_solution(model, results, solver_used)
        solution["summary"]["objective_value"] = float(pyo.value(model.total_objective))
    except Exception as exc:
        solution = _solve_case_fallback(data, options, solver_name or data["settings"]["default_solver"])
        solution["summary"]["solver_fallback_reason"] = str(exc)

    solution["summary"].update(_inventory_summary(solution.get("bom", [])))

    if output_dir is not None:
        write_reports(solution, output_dir)

    return solution


def write_reports(solution: Dict[str, Any], output_dir: str | Path) -> None:
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    report_payloads = {
        "summary.json": solution["summary"],
        "bom.json": build_bom_report(solution),
        "routes.json": build_route_report(solution),
        "hydraulics.json": build_hydraulic_report(solution),
    }
    if "topology" in solution:
        report_payloads["topology.json"] = solution["topology"]
    if "comparison" in solution and solution["comparison"]:
        report_payloads["comparison.json"] = solution["comparison"]
    for filename, payload in report_payloads.items():
        (out_dir / filename).write_text(
            json.dumps(payload, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )


def _solve_model(model: Any, solver_name: str) -> tuple[str, Any]:
    import pyomo.environ as pyo

    candidates = []
    for candidate in [solver_name, "highs", "appsi_highs"]:
        if candidate and candidate not in candidates:
            candidates.append(candidate)

    for candidate in candidates:
        solver = pyo.SolverFactory(candidate)
        if solver is None:
            continue
        try:
            if not solver.available(False):
                continue
        except Exception:
            continue

        results = solver.solve(model, tee=False)
        termination = str(results.solver.termination_condition).lower()
        if "optimal" in termination or "feasible" in termination:
            return candidate, results
        raise RuntimeError(f"Solver '{candidate}' failed with termination '{termination}'.")

    raise RuntimeError(
        f"No available solver found among candidates: {candidates}. Install HiGHS/highspy first."
    )


def _extract_solution(model: Any, results: Any, solver_name: str) -> Dict[str, Any]:
    import pyomo.environ as pyo

    payload = model._payload
    selected_source_options = {
        node_id: next(
            option_id
            for option_id in payload["source_option_ids_by_node"][node_id]
            if pyo.value(model.source_option_selected[node_id, option_id]) > 0.5
        )
        for node_id in payload["source_nodes"]
        if pyo.value(model.source_node_active[node_id]) > 0.5
    }
    selected_destination_options = {
        node_id: next(
            option_id
            for option_id in payload["destination_option_ids_by_node"][node_id]
            if pyo.value(model.destination_option_selected[node_id, option_id]) > 0.5
        )
        for node_id in payload["sink_nodes"]
        if pyo.value(model.sink_node_active[node_id]) > 0.5
    }
    selected_pump_slots = {
        slot: next(
            option_id
            for option_id in payload["pump_option_ids"]
            if pyo.value(model.pump_option_selected[slot, option_id]) > 0.5
        )
        for slot in payload["pump_slots"]
        if sum(
            pyo.value(model.pump_option_selected[slot, option_id])
            for option_id in payload["pump_option_ids"]
        )
        > 0.5
    }
    selected_meter_slots = {
        slot: next(
            option_id
            for option_id in payload["meter_option_ids"]
            if pyo.value(model.meter_option_selected[slot, option_id]) > 0.5
        )
        for slot in payload["meter_slots"]
        if sum(
            pyo.value(model.meter_option_selected[slot, option_id])
            for option_id in payload["meter_option_ids"]
        )
        > 0.5
    }
    selected_suction_trunk = next(
        option_id
        for option_id in payload["suction_trunk_option_ids"]
        if pyo.value(model.suction_trunk_selected[option_id]) > 0.5
    )
    selected_discharge_trunk = next(
        option_id
        for option_id in payload["discharge_trunk_option_ids"]
        if pyo.value(model.discharge_trunk_selected[option_id]) > 0.5
    )

    assignment: Dict[str, Dict[str, Any]] = {}
    selectivity_by_route = {
        route_id: summarize_route_selectivity(
            route=payload["routes"][route_id],
            source_selection={
                node_id: payload["source_options"][option_id]
                for node_id, option_id in selected_source_options.items()
            },
            destination_selection={
                node_id: payload["destination_options"][option_id]
                for node_id, option_id in selected_destination_options.items()
            },
        )
        for route_id in payload["route_ids"]
        if pyo.value(model.route_active[route_id]) > 0.5
    }
    for route_id in payload["route_ids"]:
        if pyo.value(model.route_active[route_id]) <= 0.5:
            continue
        route = payload["routes"][route_id]
        source_option = payload["source_options"][selected_source_options[route["source"]]]
        destination_option = payload["destination_options"][
            selected_destination_options[route["sink"]]
        ]
        pump_slot, pump_option_id = next(
            (slot, option_id)
            for slot in payload["pump_slots"]
            for option_id in payload["pump_option_ids"]
            if pyo.value(model.route_uses_pump_option[route_id, slot, option_id]) > 0.5
        )
        meter_slot, meter_option_id = next(
            (slot, option_id)
            for slot in payload["meter_slots"]
            for option_id in payload["meter_option_ids"]
            if pyo.value(model.route_uses_meter_option[route_id, slot, option_id]) > 0.5
        )
        pump_option = payload["pump_options"][pump_option_id]
        meter_option = payload["meter_options"][meter_option_id]
        suction_option = payload["suction_trunk_options"][selected_suction_trunk]
        discharge_option = payload["discharge_trunk_options"][selected_discharge_trunk]
        flow = float(pyo.value(model.flow_delivered_lpm[route_id]))
        meter_flags = payload["route_meter_compatibility"][route_id][meter_option_id]
        hydraulics = summarize_route_hydraulics(
            route=route,
            source_option=source_option,
            destination_option=destination_option,
            pump_option=pump_option,
            meter_option=meter_option,
            suction_option=suction_option,
            discharge_option=discharge_option,
            flow_delivered_lpm=flow,
        )
        assignment[route_id] = {
            "route": route,
            "source_option": source_option,
            "destination_option": destination_option,
            "pump_slot": pump_slot,
            "pump_option": pump_option,
            "meter_slot": meter_slot,
            "meter_option": meter_option,
            "flow_delivered_lpm": flow,
            "meter_flags": meter_flags,
            "hydraulics": hydraulics,
            "selectivity": selectivity_by_route[route_id],
        }

    bom = _build_bom(
        payload,
        selected_source_options,
        selected_destination_options,
        selected_pump_slots,
        selected_meter_slots,
        selected_suction_trunk,
        selected_discharge_trunk,
    )
    routes_report, hydraulics_report = _build_reports_from_assignment(
        assignment=assignment,
        system_class=_summarize_system_class(
            payload,
            selected_source_options=selected_source_options,
            selected_destination_options=selected_destination_options,
            selected_pump_slots=selected_pump_slots,
            selected_meter_slots=selected_meter_slots,
            selected_suction_trunk=selected_suction_trunk,
            selected_discharge_trunk=selected_discharge_trunk,
        ),
        suction_option_id=selected_suction_trunk,
        discharge_option_id=selected_discharge_trunk,
    )

    return {
        "summary": {
            "solver": solver_name,
            "solver_status": str(results.solver.status),
            "termination_condition": str(results.solver.termination_condition),
            "topology_family": "star_manifolds",
            "system_class": _summarize_system_class(
                payload,
                selected_source_options=selected_source_options,
                selected_destination_options=selected_destination_options,
                selected_pump_slots=selected_pump_slots,
                selected_meter_slots=selected_meter_slots,
                selected_suction_trunk=selected_suction_trunk,
                selected_discharge_trunk=selected_discharge_trunk,
            ),
            "routes_served": len(routes_report),
            "mandatory_routes_served": sum(1 for route in routes_report if route["mandatory"]),
            "total_material_cost": round(sum(item["total_cost"] for item in bom), 3),
        },
        "bom": bom,
        "routes": routes_report,
        "hydraulics": hydraulics_report,
        "topology": {
            "source_options": selected_source_options,
            "destination_options": selected_destination_options,
            "pump_slots": selected_pump_slots,
            "meter_slots": selected_meter_slots,
            "suction_trunk_option_id": selected_suction_trunk,
            "discharge_trunk_option_id": selected_discharge_trunk,
        },
    }


def _solve_case_fallback(data: Dict[str, Any], options: Dict[str, Any], solver_name: str) -> Dict[str, Any]:
    settings = data["settings"]
    routes = data["routes"].to_dict("records")
    components = data["components"].to_dict("records")
    mandatory_routes = [route for route in routes if route["mandatory"]]
    optional_routes = [route for route in routes if not route["mandatory"]]
    fallback_payload = {
        "source_options": {
            option["option_id"]: option
            for options_by_node in options["source_options"].values()
            for option in options_by_node
        },
        "destination_options": {
            option["option_id"]: option
            for options_by_node in options["destination_options"].values()
            for option in options_by_node
        },
        "pump_options": {
            option["option_id"]: option for option in options["pump_slot_options"]
        },
        "meter_options": {
            option["option_id"]: option for option in options["meter_slot_options"]
        },
        "suction_trunk_options": {
            option["option_id"]: option for option in options["suction_trunk_options"]
        },
        "discharge_trunk_options": {
            option["option_id"]: option for option in options["discharge_trunk_options"]
        },
    }

    best_solution: Dict[str, Any] | None = None
    best_objective: float | None = None
    optional_subsets = [[]]
    if optional_routes:
        optional_subsets = [
            [optional_routes[index] for index in range(len(optional_routes)) if mask & (1 << index)]
            for mask in range(1 << len(optional_routes))
        ]

    for system_class in options["system_classes"]:
        for optional_subset in optional_subsets:
            active_routes = mandatory_routes + optional_subset
            if any(
                system_class not in options["route_class_feasibility"][route["route_id"]]
                for route in active_routes
            ):
                continue

            branch_topologies = _enumerate_branch_topologies(
                active_routes=active_routes,
                source_options=options["source_options"],
                destination_options=options["destination_options"],
                suction_trunk_options=options["suction_trunk_options"],
                discharge_trunk_options=options["discharge_trunk_options"],
                components=components,
                system_class=system_class,
            )
            if not branch_topologies:
                continue

            for branch_topology in branch_topologies:
                topology_selectivity = {
                    route["route_id"]: summarize_route_selectivity(
                        route=route,
                        source_selection=branch_topology["source_selection"],
                        destination_selection=branch_topology["destination_selection"],
                    )
                    for route in active_routes
                }
                if not all(
                    item["selective_route_realizable"] for item in topology_selectivity.values()
                ):
                    continue
                for selected_pumps in _enumerate_slot_combinations(
                    slot_options=options["pump_slot_options"],
                    max_slots=int(settings["u_max_slots"]),
                    system_class=system_class,
                ):
                    for selected_meters in _enumerate_slot_combinations(
                        slot_options=options["meter_slot_options"],
                        max_slots=int(settings["v_max_slots"]),
                        system_class=system_class,
                    ):
                        assignment = _assign_routes(
                            active_routes=active_routes,
                            source_selection=branch_topology["source_selection"],
                            destination_selection=branch_topology["destination_selection"],
                            selected_pumps=selected_pumps,
                            selected_meters=selected_meters,
                            suction_option=branch_topology["suction_option"],
                            discharge_option=branch_topology["discharge_option"],
                            selectivity_by_route=topology_selectivity,
                        )
                        if assignment is None:
                            continue

                        bom = _build_bom_from_fallback(
                            components=components,
                            source_selection=branch_topology["source_selection"],
                            destination_selection=branch_topology["destination_selection"],
                            selected_pumps=selected_pumps,
                            selected_meters=selected_meters,
                            suction_option=branch_topology["suction_option"],
                            discharge_option=branch_topology["discharge_option"],
                        )
                        if bom is None:
                            continue

                        hydraulic_bonus = float(settings["robustness_weight"]) * sum(
                            item["hydraulics"]["hydraulic_slack_lpm"] for item in assignment.values()
                        )
                        material_cost = sum(item["total_cost"] for item in bom)
                        extra_usage_penalty = EXTRA_USAGE_EPSILON * sum(
                            int(item["qty"]) for item in bom if bool(item.get("is_extra", False))
                        )
                        cleaning_penalty = float(settings["cleaning_cost_liters_per_operation"]) * len(active_routes)
                        optional_reward = float(settings["optional_route_reward"]) * sum(
                            float(route["weight"]) for route in optional_subset
                        )
                        objective_value = (
                            material_cost
                            + extra_usage_penalty
                            + cleaning_penalty
                            - optional_reward
                            - hydraulic_bonus
                        )

                        if best_objective is None or objective_value < best_objective:
                            topology_source_options = {
                                node_id: option["option_id"]
                                for node_id, option in branch_topology["source_selection"].items()
                            }
                            topology_destination_options = {
                                node_id: option["option_id"]
                                for node_id, option in branch_topology["destination_selection"].items()
                            }
                            topology_pump_slots = {
                                slot: option["option_id"] for slot, option in selected_pumps.items()
                            }
                            topology_meter_slots = {
                                slot: option["option_id"] for slot, option in selected_meters.items()
                            }
                            topology_system_class = _summarize_system_class(
                                fallback_payload,
                                selected_source_options=topology_source_options,
                                selected_destination_options=topology_destination_options,
                                selected_pump_slots=topology_pump_slots,
                                selected_meter_slots=topology_meter_slots,
                                selected_suction_trunk=branch_topology["suction_option"]["option_id"],
                                selected_discharge_trunk=branch_topology["discharge_option"]["option_id"],
                            )
                            routes_report, hydraulics_report = _build_reports_from_assignment(
                                assignment=assignment,
                                system_class=topology_system_class,
                                suction_option_id=branch_topology["suction_option"]["option_id"],
                                discharge_option_id=branch_topology["discharge_option"]["option_id"],
                            )
                            best_objective = objective_value
                            best_solution = {
                                "summary": {
                                    "solver": solver_name,
                                    "solver_status": "fallback",
                                    "termination_condition": "enumerated",
                                    "topology_family": "star_manifolds",
                                    "system_class": topology_system_class,
                                    "routes_served": len(routes_report),
                                    "mandatory_routes_served": len(mandatory_routes),
                                    "total_material_cost": round(material_cost, 3),
                                    "objective_value": round(objective_value, 3),
                                },
                                "bom": bom,
                                "routes": routes_report,
                                "hydraulics": hydraulics_report,
                                "topology": {
                                    "source_options": topology_source_options,
                                    "destination_options": topology_destination_options,
                                    "pump_slots": topology_pump_slots,
                                    "meter_slots": topology_meter_slots,
                                    "suction_trunk_option_id": branch_topology["suction_option"]["option_id"],
                                    "discharge_trunk_option_id": branch_topology["discharge_option"]["option_id"],
                                },
                            }

    if best_solution is None:
        raise RuntimeError("Fallback enumeration could not find a feasible solution.")
    return best_solution


def _enumerate_branch_topologies(
    *,
    active_routes: list[Dict[str, Any]],
    source_options: Dict[str, list[Dict[str, Any]]],
    destination_options: Dict[str, list[Dict[str, Any]]],
    suction_trunk_options: list[Dict[str, Any]],
    discharge_trunk_options: list[Dict[str, Any]],
    components: list[Dict[str, Any]],
    system_class: str,
) -> list[Dict[str, Any]]:
    component_availability = {
        component["component_id"]: int(component["available_qty"]) for component in components
    }
    source_node_ids = sorted({route["source"] for route in active_routes})
    sink_node_ids = sorted({route["sink"] for route in active_routes})
    source_candidates = {
        node_id: sorted(
            list(source_options[node_id]),
            key=lambda option: (option["cost"], option["loss_lpm_equiv"]),
        )
        for node_id in source_node_ids
    }
    destination_candidates = {
        node_id: sorted(
            list(destination_options[node_id]),
            key=lambda option: (option["cost"], option["loss_lpm_equiv"]),
        )
        for node_id in sink_node_ids
    }
    if any(not options for options in source_candidates.values()) or any(
        not options for options in destination_candidates.values()
    ):
        return None

    suction_candidates = [
        option for option in suction_trunk_options if option["sys_diameter_class"] == system_class
    ]
    discharge_candidates = [
        option for option in discharge_trunk_options if option["sys_diameter_class"] == system_class
    ]
    topologies: list[Dict[str, Any]] = []

    for suction_option in sorted(suction_candidates, key=lambda option: option["cost"]):
        for discharge_option in sorted(discharge_candidates, key=lambda option: option["cost"]):
            remaining = dict(component_availability)
            if not _reserve_option(remaining, suction_option) or not _reserve_option(
                remaining, discharge_option
            ):
                continue
            branch_selections = _enumerate_branch_selections(
                source_candidates=source_candidates,
                destination_candidates=destination_candidates,
                remaining_components=remaining,
            )
            if not branch_selections:
                continue
            for branch_selection in branch_selections:
                topology_cost = (
                    suction_option["cost"]
                    + discharge_option["cost"]
                    + branch_selection["total_cost"]
                )
                topologies.append(
                    {
                    "source_selection": branch_selection["source_selection"],
                    "destination_selection": branch_selection["destination_selection"],
                    "suction_option": suction_option,
                    "discharge_option": discharge_option,
                    "system_class": system_class,
                    "topology_cost": topology_cost,
                }
                )

    return sorted(
        topologies,
        key=lambda topology: (
            topology["topology_cost"],
            topology["suction_option"]["loss_lpm_equiv"] + topology["discharge_option"]["loss_lpm_equiv"],
        ),
    )


def _enumerate_branch_selections(
    *,
    source_candidates: Dict[str, list[Dict[str, Any]]],
    destination_candidates: Dict[str, list[Dict[str, Any]]],
    remaining_components: Dict[str, int],
) -> list[Dict[str, Any]]:
    node_specs = [
        ("source", node_id, source_candidates[node_id]) for node_id in sorted(source_candidates)
    ] + [
        ("destination", node_id, destination_candidates[node_id])
        for node_id in sorted(destination_candidates)
    ]
    branch_selections: list[Dict[str, Any]] = []

    def search(
        index: int,
        current_remaining: Dict[str, int],
        current_cost: float,
        current_source: Dict[str, Dict[str, Any]],
        current_destination: Dict[str, Dict[str, Any]],
    ) -> None:
        if index == len(node_specs):
            branch_selections.append(
                {
                "source_selection": dict(current_source),
                "destination_selection": dict(current_destination),
                "total_cost": current_cost,
                }
            )
            return

        kind, node_id, option_list = node_specs[index]
        for option in option_list:
            next_remaining = dict(current_remaining)
            if not _reserve_option(next_remaining, option):
                continue
            if kind == "source":
                current_source[node_id] = option
                search(
                    index + 1,
                    next_remaining,
                    current_cost + option["cost"],
                    current_source,
                    current_destination,
                )
                current_source.pop(node_id, None)
            else:
                current_destination[node_id] = option
                search(
                    index + 1,
                    next_remaining,
                    current_cost + option["cost"],
                    current_source,
                    current_destination,
                )
                current_destination.pop(node_id, None)

    search(0, dict(remaining_components), 0.0, {}, {})
    return sorted(
        branch_selections,
        key=lambda selection: (
            selection["total_cost"],
            sum(
                option["loss_lpm_equiv"]
                for option in selection["source_selection"].values()
            )
            + sum(
                option["loss_lpm_equiv"]
                for option in selection["destination_selection"].values()
            ),
        ),
    )


def _enumerate_slot_combinations(
    *,
    slot_options: list[Dict[str, Any]],
    max_slots: int,
    system_class: str,
) -> list[Dict[int, Dict[str, Any]]]:
    candidates = [option for option in slot_options if option["sys_diameter_class"] == system_class]
    combinations: list[Dict[int, Dict[str, Any]]] = []
    for slot_count in range(1, max_slots + 1):
        for combo in combinations_with_replacement(candidates, slot_count):
            combinations.append({index + 1: option for index, option in enumerate(combo)})
    return sorted(
        combinations,
        key=lambda combo: (sum(option["cost"] for option in combo.values()), len(combo)),
    )


def _assign_routes(
    *,
    active_routes: list[Dict[str, Any]],
    source_selection: Dict[str, Dict[str, Any]],
    destination_selection: Dict[str, Dict[str, Any]],
    selected_pumps: Dict[int, Dict[str, Any]],
    selected_meters: Dict[int, Dict[str, Any]],
    suction_option: Dict[str, Any],
    discharge_option: Dict[str, Any],
    selectivity_by_route: Dict[str, Dict[str, Any]],
) -> Dict[str, Dict[str, Any]] | None:
    assignment: Dict[str, Dict[str, Any]] = {}
    for route in active_routes:
        matched = None
        source_option = source_selection[route["source"]]
        destination_option = destination_selection[route["sink"]]
        selectivity = selectivity_by_route[route["route_id"]]
        if not bool(selectivity["selective_route_realizable"]):
            return None
        for pump_slot, pump_option in selected_pumps.items():
            for meter_slot, meter_option in selected_meters.items():
                meter_flags = _build_meter_flags(route, meter_option)
                if not meter_flags["compatible"]:
                    continue
                flow = compute_route_min_flow(
                    route=route,
                    source_option=source_option,
                    destination_option=destination_option,
                    pump_option=pump_option,
                    meter_option=meter_option,
                    suction_option=suction_option,
                    discharge_option=discharge_option,
                )
                hydraulics = summarize_route_hydraulics(
                    route=route,
                    source_option=source_option,
                    destination_option=destination_option,
                    pump_option=pump_option,
                    meter_option=meter_option,
                    suction_option=suction_option,
                    discharge_option=discharge_option,
                    flow_delivered_lpm=flow,
                )
                if not hydraulics["hydraulic_ok"]:
                    continue
                matched = {
                    "route": route,
                    "source_option": source_option,
                    "destination_option": destination_option,
                    "pump_slot": pump_slot,
                    "pump_option": pump_option,
                    "meter_slot": meter_slot,
                    "meter_option": meter_option,
                    "flow_delivered_lpm": flow,
                    "meter_flags": meter_flags,
                    "hydraulics": hydraulics,
                    "selectivity": selectivity,
                }
                break
            if matched is not None:
                break
        if matched is None:
            return None
        assignment[route["route_id"]] = matched
    return assignment


def _build_meter_flags(route: Dict[str, Any], meter_option: Dict[str, Any]) -> Dict[str, Any]:
    from agri_circuit_optimizer.preprocess.feasibility import meter_compatibility

    return meter_compatibility(route, meter_option)


def _build_bom_from_fallback(
    *,
    components: list[Dict[str, Any]],
    source_selection: Dict[str, Dict[str, Any]],
    destination_selection: Dict[str, Dict[str, Any]],
    selected_pumps: Dict[int, Dict[str, Any]],
    selected_meters: Dict[int, Dict[str, Any]],
    suction_option: Dict[str, Any],
    discharge_option: Dict[str, Any],
) -> list[Dict[str, Any]] | None:
    component_index = {component["component_id"]: component for component in components}
    component_qty: Dict[str, int] = {}
    role_qty: Dict[str, Dict[str, int]] = {}

    def accumulate(option: Dict[str, Any], role: str) -> None:
        for component_id, qty in option["component_counts"].items():
            component_qty[component_id] = component_qty.get(component_id, 0) + int(qty)
            role_qty.setdefault(component_id, {"suction": 0, "discharge": 0, "other": 0})[role] += int(qty)

    for option in source_selection.values():
        accumulate(option, "suction")
    for option in destination_selection.values():
        accumulate(option, "discharge")
    for option in selected_pumps.values():
        accumulate(option, "other")
    for option in selected_meters.values():
        accumulate(option, "other")
    accumulate(suction_option, "other")
    accumulate(discharge_option, "other")

    for component_id, qty in component_qty.items():
        if qty > int(component_index[component_id]["available_qty"]):
            return None

    bom = []
    for component_id, qty in sorted(component_qty.items()):
        unit_cost = float(component_index[component_id]["cost"])
        bom.append(
            {
                "component_id": component_id,
                "category": component_index[component_id]["category"],
                "qty": qty,
                "unit_cost": unit_cost,
                "total_cost": round(qty * unit_cost, 3),
                "is_extra": bool(component_index[component_id].get("is_extra", False)),
                "extra_penalty_group": component_index[component_id].get("extra_penalty_group", ""),
                "hose_length_m": _float_or_default(component_index[component_id].get("hose_length_m")),
                "qty_suction": int(role_qty.get(component_id, {}).get("suction", 0)),
                "qty_discharge": int(role_qty.get(component_id, {}).get("discharge", 0)),
                "qty_other": int(role_qty.get(component_id, {}).get("other", 0)),
            }
        )
    return bom


def _summarize_system_class(
    payload: Dict[str, Any],
    *,
    selected_source_options: Dict[str, str],
    selected_destination_options: Dict[str, str],
    selected_pump_slots: Dict[int, str],
    selected_meter_slots: Dict[int, str],
    selected_suction_trunk: str,
    selected_discharge_trunk: str,
) -> str:
    selected_classes = {
        payload["source_options"][option_id]["sys_diameter_class"]
        for option_id in selected_source_options.values()
    }
    selected_classes.update(
        payload["destination_options"][option_id]["sys_diameter_class"]
        for option_id in selected_destination_options.values()
    )
    selected_classes.update(
        payload["pump_options"][option_id]["sys_diameter_class"]
        for option_id in selected_pump_slots.values()
    )
    selected_classes.update(
        payload["meter_options"][option_id]["sys_diameter_class"]
        for option_id in selected_meter_slots.values()
    )
    selected_classes.add(payload["suction_trunk_options"][selected_suction_trunk]["sys_diameter_class"])
    selected_classes.add(
        payload["discharge_trunk_options"][selected_discharge_trunk]["sys_diameter_class"]
    )
    if len(selected_classes) == 1:
        return next(iter(selected_classes))
    return "mixed"


def _build_reports_from_assignment(
    *,
    assignment: Dict[str, Dict[str, Any]],
    system_class: str,
    suction_option_id: str,
    discharge_option_id: str,
) -> tuple[list[Dict[str, Any]], list[Dict[str, Any]]]:
    routes_report: list[Dict[str, Any]] = []
    hydraulics_report: list[Dict[str, Any]] = []

    for route_id in sorted(assignment):
        item = assignment[route_id]
        route = item["route"]
        pump_option = item["pump_option"]
        meter_option = item["meter_option"]
        meter_flags = item["meter_flags"]
        hydraulics = item["hydraulics"]
        selectivity = item["selectivity"]
        flow = float(item["flow_delivered_lpm"])

        routes_report.append(
            {
                "route_id": route_id,
                "source": route["source"],
                "sink": route["sink"],
                "mandatory": bool(route["mandatory"]),
                "measurement_required": bool(route["measurement_required"]),
                "flow_delivered_lpm": flow,
                "q_min_required_lpm": float(route["q_min_delivered_lpm"]),
                "pump_slot": item["pump_slot"],
                "pump_option_id": pump_option["option_id"],
                "pump_component_id": pump_option["metadata"]["component_id"],
                "meter_slot": item["meter_slot"],
                "meter_option_id": meter_option["option_id"],
                "selected_meter_id": meter_option["metadata"]["component_id"],
                "meter_component_id": meter_option["metadata"]["component_id"],
                "meter_is_bypass": bool(meter_option.get("is_bypass", False)),
                "meter_q_range_ok": bool(meter_flags["q_range_ok"]),
                "meter_dose_ok": bool(meter_flags["dose_ok"]),
                "meter_error_ok": bool(meter_flags["error_ok"]),
                "source_option_id": item["source_option"]["option_id"],
                "destination_option_id": item["destination_option"]["option_id"],
                "source_branch_selected": selectivity["source_branch_selected"],
                "discharge_branch_selected": selectivity["discharge_branch_selected"],
                "selective_route_realizable": bool(selectivity["selective_route_realizable"]),
                "extra_open_branch_conflict": bool(selectivity["extra_open_branch_conflict"]),
                "open_suction_branch_count": int(selectivity["open_suction_branch_count"]),
                "open_discharge_branch_count": int(selectivity["open_discharge_branch_count"]),
                "conflicting_source_nodes": list(selectivity["conflicting_source_nodes"]),
                "conflicting_sink_nodes": list(selectivity["conflicting_sink_nodes"]),
                "source_branch_hose_m": float(hydraulics["source_branch_hose_m"]),
                "destination_branch_hose_m": float(hydraulics["destination_branch_hose_m"]),
                "route_effective_q_max_lpm": float(hydraulics["route_effective_q_max_lpm"]),
                "hydraulic_mode": hydraulics["hydraulic_mode"],
            }
        )
        hydraulics_report.append(
            {
                "route_id": route_id,
                "system_class": system_class,
                "suction_trunk_option_id": suction_option_id,
                "discharge_trunk_option_id": discharge_option_id,
                "flow_delivered_lpm": flow,
                "q_min_required_lpm": float(route["q_min_delivered_lpm"]),
                "total_loss_lpm_equiv": float(hydraulics["total_loss_lpm_equiv"]),
                "route_effective_q_max_lpm": float(hydraulics["route_effective_q_max_lpm"]),
                "hydraulic_slack_lpm": float(hydraulics["hydraulic_slack_lpm"]),
                "gargalo_principal": hydraulics["bottleneck_label"],
                "bottleneck_component_id": hydraulics["bottleneck_component_id"],
                "route_hose_total_m": float(hydraulics["route_hose_total_m"]),
                "hydraulic_mode": hydraulics["hydraulic_mode"],
            }
        )

    return routes_report, hydraulics_report


def _reserve_option(remaining_components: Dict[str, int], option: Dict[str, Any]) -> bool:
    for component_id, qty in option["component_counts"].items():
        if remaining_components.get(component_id, 0) < qty:
            return False
    for component_id, qty in option["component_counts"].items():
        remaining_components[component_id] -= qty
    return True


def _build_bom(
    payload: Dict[str, Any],
    selected_source_options: Dict[str, str],
    selected_destination_options: Dict[str, str],
    selected_pump_slots: Dict[int, str],
    selected_meter_slots: Dict[int, str],
    selected_suction_trunk: str,
    selected_discharge_trunk: str,
) -> list[Dict[str, Any]]:
    component_qty: Dict[str, int] = {}
    role_qty: Dict[str, Dict[str, int]] = {}

    def accumulate(option: Dict[str, Any], role: str) -> None:
        for component_id, qty in option["component_counts"].items():
            component_qty[component_id] = component_qty.get(component_id, 0) + int(qty)
            role_qty.setdefault(component_id, {"suction": 0, "discharge": 0, "other": 0})[role] += int(qty)

    for option_id in selected_source_options.values():
        accumulate(payload["source_options"][option_id], "suction")
    for option_id in selected_destination_options.values():
        accumulate(payload["destination_options"][option_id], "discharge")
    for option_id in selected_pump_slots.values():
        accumulate(payload["pump_options"][option_id], "other")
    for option_id in selected_meter_slots.values():
        accumulate(payload["meter_options"][option_id], "other")
    accumulate(payload["suction_trunk_options"][selected_suction_trunk], "other")
    accumulate(payload["discharge_trunk_options"][selected_discharge_trunk], "other")

    bom = []
    for component_id, qty in sorted(component_qty.items()):
        unit_cost = float(payload["components"][component_id]["cost"])
        bom.append(
            {
                "component_id": component_id,
                "category": payload["components"][component_id]["category"],
                "qty": qty,
                "unit_cost": unit_cost,
                "total_cost": round(qty * unit_cost, 3),
                "is_extra": bool(payload["components"][component_id].get("is_extra", False)),
                "extra_penalty_group": payload["components"][component_id].get("extra_penalty_group", ""),
                "hose_length_m": _float_or_default(payload["components"][component_id].get("hose_length_m")),
                "qty_suction": int(role_qty.get(component_id, {}).get("suction", 0)),
                "qty_discharge": int(role_qty.get(component_id, {}).get("discharge", 0)),
                "qty_other": int(role_qty.get(component_id, {}).get("other", 0)),
            }
        )
    return bom


def _inventory_summary(bom: list[Dict[str, Any]]) -> Dict[str, Any]:
    hose_total_used_m = sum(
        float(item.get("hose_length_m", 0.0)) * int(item["qty"])
        for item in bom
        if item.get("category") == "hose"
    )
    tee_total_used = sum(
        int(item["qty"])
        for item in bom
        if item.get("category") == "connector"
    )
    solenoid_suction_total = sum(
        int(item.get("qty_suction", 0))
        for item in bom
        if item.get("category") == "valve"
    )
    solenoid_discharge_total = sum(
        int(item.get("qty_discharge", 0))
        for item in bom
        if item.get("category") == "valve"
    )
    solenoid_total = sum(
        int(item["qty"])
        for item in bom
        if item.get("category") == "valve"
    )
    base_usage: Dict[str, int] = {}
    extra_usage: Dict[str, int] = {}
    for item in bom:
        target = extra_usage if item.get("is_extra", False) else base_usage
        target[item["component_id"]] = int(item["qty"])
    return {
        "hose_total_used_m": round(hose_total_used_m, 3),
        "tee_total_used": tee_total_used,
        "solenoid_suction_total": solenoid_suction_total,
        "solenoid_discharge_total": solenoid_discharge_total,
        "solenoid_total": solenoid_total,
        "base_vs_extra_usage": {
            "base": base_usage,
            "extra": extra_usage,
        },
    }


def _float_or_default(value: Any, default: float = 0.0) -> float:
    if value is None:
        return float(default)
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return float(default)
    if isnan(numeric):
        return float(default)
    return numeric


def main() -> None:
    args = parse_args()
    scenario_dir = Path(args.scenario)

    data = load_scenario(scenario_dir)
    summary = scenario_summary(data)
    print(json.dumps(summary, indent=2, ensure_ascii=False))

    if args.dry_run:
        if is_fixed_topology_mode(data):
            dry_run_summary = {
                **summary,
                **dry_run_fixed_topology(data),
            }
        else:
            options = build_stage_options(data)
            dry_run_summary = {
                **summary,
                "system_classes": options["system_classes"],
                "mandatory_routes_with_viable_classes": sum(
                    1
                    for route_id in data["routes"].loc[data["routes"]["mandatory"], "route_id"].tolist()
                    if options["route_class_feasibility"][route_id]
                ),
            }
        print(json.dumps(dry_run_summary, indent=2, ensure_ascii=False))
        print("Dry-run completed: scenario loaded, validated and preprocessed.")
        return

    solution = solve_case(scenario_dir, solver_name=args.solver, output_dir=args.output_dir)
    print(json.dumps(solution["summary"], indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
