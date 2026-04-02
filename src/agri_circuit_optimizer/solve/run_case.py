from __future__ import annotations

import argparse
import json
from itertools import combinations_with_replacement, product
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
    scenario_dir: str | Path, *, solver_name: str | None = None, output_dir: str | Path | None = None
) -> Dict[str, Any]:
    scenario_path = Path(scenario_dir)
    data = load_scenario(scenario_path)
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
    system_class = next(
        system_class
        for system_class in payload["system_classes"]
        if pyo.value(model.system_class_selected[system_class]) > 0.5
    )
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
        if sum(pyo.value(model.pump_option_selected[slot, option_id]) for option_id in payload["pump_option_ids"])
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

    routes = []
    hydraulics = []
    active_route_ids = [
        route_id for route_id in payload["route_ids"] if pyo.value(model.route_active[route_id]) > 0.5
    ]
    for route_id in active_route_ids:
        route = payload["routes"][route_id]
        source_option_id = selected_source_options[route["source"]]
        destination_option_id = selected_destination_options[route["sink"]]
        pump_slot = next(
            slot
            for slot in payload["pump_slots"]
            if pyo.value(model.route_uses_pump_slot[route_id, slot]) > 0.5
        )
        meter_slot = next(
            slot
            for slot in payload["meter_slots"]
            if pyo.value(model.route_uses_meter_slot[route_id, slot]) > 0.5
        )
        pump_option_id = selected_pump_slots[pump_slot]
        meter_option_id = selected_meter_slots[meter_slot]
        flow = float(pyo.value(model.flow_delivered_lpm[route_id]))

        source_option = payload["source_options"][source_option_id]
        destination_option = payload["destination_options"][destination_option_id]
        pump_option = payload["pump_options"][pump_option_id]
        meter_option = payload["meter_options"][meter_option_id]
        suction_option = payload["suction_trunk_options"][selected_suction_trunk]
        discharge_option = payload["discharge_trunk_options"][selected_discharge_trunk]

        route_loss = (
            source_option["loss_lpm_equiv"]
            + suction_option["loss_lpm_equiv"]
            + pump_option["loss_lpm_equiv"]
            + meter_option["loss_lpm_equiv"]
            + discharge_option["loss_lpm_equiv"]
            + destination_option["loss_lpm_equiv"]
        )
        hydraulic_slack = pump_option["q_max_lpm"] - flow

        routes.append(
            {
                "route_id": route_id,
                "source": route["source"],
                "sink": route["sink"],
                "mandatory": bool(route["mandatory"]),
                "measurement_required": bool(route["measurement_required"]),
                "flow_delivered_lpm": flow,
                "q_min_required_lpm": float(route["q_min_delivered_lpm"]),
                "pump_slot": pump_slot,
                "pump_option_id": pump_option_id,
                "pump_component_id": pump_option["metadata"]["component_id"],
                "meter_slot": meter_slot,
                "meter_option_id": meter_option_id,
                "meter_component_id": meter_option["metadata"]["component_id"],
                "meter_is_bypass": bool(meter_option.get("is_bypass", False)),
                "source_option_id": source_option_id,
                "destination_option_id": destination_option_id,
            }
        )
        hydraulics.append(
            {
                "route_id": route_id,
                "system_class": system_class,
                "suction_trunk_option_id": selected_suction_trunk,
                "discharge_trunk_option_id": selected_discharge_trunk,
                "flow_delivered_lpm": flow,
                "q_min_required_lpm": float(route["q_min_delivered_lpm"]),
                "loss_lpm_equiv": route_loss,
                "hydraulic_slack_lpm": hydraulic_slack,
            }
        )

    bom = _build_bom(payload, selected_source_options, selected_destination_options, selected_pump_slots, selected_meter_slots, selected_suction_trunk, selected_discharge_trunk)

    return {
        "summary": {
            "solver": solver_name,
            "solver_status": str(results.solver.status),
            "termination_condition": str(results.solver.termination_condition),
            "system_class": system_class,
            "routes_served": len(active_route_ids),
            "mandatory_routes_served": sum(1 for route in routes if route["mandatory"]),
            "total_material_cost": round(sum(item["total_cost"] for item in bom), 3),
        },
        "bom": bom,
        "routes": routes,
        "hydraulics": hydraulics,
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
    mandatory_routes = [route for route in routes if route["mandatory"]]
    optional_routes = [route for route in routes if not route["mandatory"]]

    best_solution: Dict[str, Any] | None = None
    best_objective: float | None = None

    optional_subsets = [[]]
    if optional_routes:
        optional_subsets = [
            [optional_routes[index] for index in range(len(optional_routes)) if mask & (1 << index)]
            for mask in range(1 << len(optional_routes))
        ]

    for optional_subset in optional_subsets:
        active_routes = mandatory_routes + optional_subset
        if not active_routes:
            continue

        branch_topology = _select_branch_topology(
            active_routes=active_routes,
            source_options=options["source_options"],
            destination_options=options["destination_options"],
            suction_trunk_options=options["suction_trunk_options"],
            discharge_trunk_options=options["discharge_trunk_options"],
            components=data["components"].to_dict("records"),
        )
        if branch_topology is None:
            continue

        source_selection = branch_topology["source_selection"]
        destination_selection = branch_topology["destination_selection"]
        suction_option = branch_topology["suction_option"]
        discharge_option = branch_topology["discharge_option"]

        for selected_pumps in _enumerate_slot_combinations(
            slot_options=options["pump_slot_options"],
            max_slots=int(settings["u_max_slots"]),
        ):
            for selected_meters in _enumerate_slot_combinations(
                slot_options=options["meter_slot_options"],
                max_slots=int(settings["v_max_slots"]),
            ):
                    assignment = _assign_routes(
                        active_routes=active_routes,
                        source_selection=source_selection,
                        destination_selection=destination_selection,
                        selected_pumps=selected_pumps,
                        selected_meters=selected_meters,
                        suction_option=suction_option,
                        discharge_option=discharge_option,
                    )
                    if assignment is None:
                        continue

                    bom = _build_bom_from_fallback(
                        components=data["components"].to_dict("records"),
                        source_selection=source_selection,
                        destination_selection=destination_selection,
                        selected_pumps=selected_pumps,
                        selected_meters=selected_meters,
                        suction_option=suction_option,
                        discharge_option=discharge_option,
                    )
                    if bom is None:
                        continue

                    material_cost = sum(item["total_cost"] for item in bom)
                    cleaning_penalty = float(settings["cleaning_cost_liters_per_operation"]) * len(active_routes)
                    optional_reward = float(settings["optional_route_reward"]) * sum(
                        float(route["weight"]) for route in optional_subset
                    )
                    objective_value = material_cost + cleaning_penalty - optional_reward

                    if best_objective is None or objective_value < best_objective:
                        routes_report, hydraulics_report = _build_route_and_hydraulic_reports_from_assignment(
                            assignment=assignment,
                            system_class=branch_topology["system_class"],
                            suction_option=suction_option,
                            discharge_option=discharge_option,
                        )
                        best_objective = objective_value
                        best_solution = {
                            "summary": {
                                "solver": solver_name,
                                "solver_status": "fallback",
                                "termination_condition": "enumerated",
                                "system_class": branch_topology["system_class"],
                                "routes_served": len(active_routes),
                                "mandatory_routes_served": len(mandatory_routes),
                                "total_material_cost": round(material_cost, 3),
                                "objective_value": round(objective_value, 3),
                            },
                            "bom": bom,
                            "routes": routes_report,
                            "hydraulics": hydraulics_report,
                            "topology": {
                                "source_options": {
                                    node_id: option["option_id"] for node_id, option in source_selection.items()
                                },
                                "destination_options": {
                                    node_id: option["option_id"] for node_id, option in destination_selection.items()
                                },
                                "pump_slots": {
                                    slot: option["option_id"] for slot, option in selected_pumps.items()
                                },
                                "meter_slots": {
                                    slot: option["option_id"] for slot, option in selected_meters.items()
                                },
                                "suction_trunk_option_id": suction_option["option_id"],
                                "discharge_trunk_option_id": discharge_option["option_id"],
                            },
                        }

    if best_solution is None:
        raise RuntimeError("Fallback enumeration could not find a feasible V1 solution.")
    return best_solution


def _select_cheapest_by_class(option_list: list[Dict[str, Any]], system_class: str) -> Dict[str, Any] | None:
    candidates = [option for option in option_list if option["sys_diameter_class"] == system_class]
    if not candidates:
        return None
    return min(candidates, key=lambda option: (option["cost"], option["loss_lpm_equiv"]))


def _select_branch_options_for_routes(
    *,
    routes: list[Dict[str, Any]],
    options_by_node: Dict[str, list[Dict[str, Any]]],
    system_class: str | None,
    node_key: str,
) -> Dict[str, Dict[str, Any]] | None:
    selection: Dict[str, Dict[str, Any]] = {}
    for route in routes:
        node_id = route[node_key]
        if node_id in selection:
            continue
        candidates = [
            option
            for option in options_by_node[node_id]
            if system_class is None or option["sys_diameter_class"] == system_class
        ]
        if not candidates:
            return None
        selection[node_id] = min(candidates, key=lambda option: (option["cost"], option["loss_lpm_equiv"]))
    return selection


def _enumerate_slot_combinations(
    *,
    slot_options: list[Dict[str, Any]],
    max_slots: int,
    system_class: str | None = None,
) -> list[Dict[int, Dict[str, Any]]]:
    candidates = [
        option
        for option in slot_options
        if system_class is None or option["sys_diameter_class"] == system_class
    ]
    combinations: list[Dict[int, Dict[str, Any]]] = []
    for slot_count in range(1, max_slots + 1):
        for combo in combinations_with_replacement(candidates, slot_count):
            combinations.append({index + 1: option for index, option in enumerate(combo)})
    return sorted(
        combinations,
        key=lambda combo: (sum(option["cost"] for option in combo.values()), len(combo)),
    )


def _select_branch_topology(
    *,
    active_routes: list[Dict[str, Any]],
    source_options: Dict[str, list[Dict[str, Any]]],
    destination_options: Dict[str, list[Dict[str, Any]]],
    suction_trunk_options: list[Dict[str, Any]],
    discharge_trunk_options: list[Dict[str, Any]],
    components: list[Dict[str, Any]],
) -> Dict[str, Any] | None:
    best_topology: Dict[str, Any] | None = None
    best_cost: float | None = None

    source_node_ids = sorted({route["source"] for route in active_routes})
    sink_node_ids = sorted({route["sink"] for route in active_routes})
    source_option_lists = [source_options[node_id] for node_id in source_node_ids]
    destination_option_lists = [destination_options[node_id] for node_id in sink_node_ids]

    for selected_source_options in product(*source_option_lists):
        source_selection = dict(zip(source_node_ids, selected_source_options))
        for selected_destination_options in product(*destination_option_lists):
            destination_selection = dict(zip(sink_node_ids, selected_destination_options))
            for suction_option in suction_trunk_options:
                for discharge_option in discharge_trunk_options:
                    bom = _build_bom_from_fallback(
                        components=components,
                        source_selection=source_selection,
                        destination_selection=destination_selection,
                        selected_pumps={},
                        selected_meters={},
                        suction_option=suction_option,
                        discharge_option=discharge_option,
                    )
                    if bom is None:
                        continue
                    topology_cost = sum(item["total_cost"] for item in bom)
                    if best_cost is None or topology_cost < best_cost:
                        selected_classes = {
                            option["sys_diameter_class"] for option in source_selection.values()
                        } | {
                            option["sys_diameter_class"] for option in destination_selection.values()
                        } | {suction_option["sys_diameter_class"], discharge_option["sys_diameter_class"]}
                        best_cost = topology_cost
                        best_topology = {
                            "source_selection": source_selection,
                            "destination_selection": destination_selection,
                            "suction_option": suction_option,
                            "discharge_option": discharge_option,
                            "system_class": selected_classes.pop() if len(selected_classes) == 1 else "mixed",
                        }
    return best_topology


def _assign_routes(
    *,
    active_routes: list[Dict[str, Any]],
    source_selection: Dict[str, Dict[str, Any]],
    destination_selection: Dict[str, Dict[str, Any]],
    selected_pumps: Dict[int, Dict[str, Any]],
    selected_meters: Dict[int, Dict[str, Any]],
    suction_option: Dict[str, Any],
    discharge_option: Dict[str, Any],
) -> Dict[str, Dict[str, Any]] | None:
    assignment: Dict[str, Dict[str, Any]] = {}
    for route in active_routes:
        matched = None
        for pump_slot, pump_option in selected_pumps.items():
            for meter_slot, meter_option in selected_meters.items():
                flow = _compute_route_flow(
                    route=route,
                    source_option=source_selection[route["source"]],
                    destination_option=destination_selection[route["sink"]],
                    pump_option=pump_option,
                    meter_option=meter_option,
                    suction_option=suction_option,
                    discharge_option=discharge_option,
                )
                if flow is None:
                    continue
                matched = {
                    "route": route,
                    "source_option": source_selection[route["source"]],
                    "destination_option": destination_selection[route["sink"]],
                    "pump_slot": pump_slot,
                    "pump_option": pump_option,
                    "meter_slot": meter_slot,
                    "meter_option": meter_option,
                    "flow_delivered_lpm": flow,
                }
                break
            if matched is not None:
                break
        if matched is None:
            return None
        assignment[route["route_id"]] = matched
    return assignment


def _compute_route_flow(
    *,
    route: Dict[str, Any],
    source_option: Dict[str, Any],
    destination_option: Dict[str, Any],
    pump_option: Dict[str, Any],
    meter_option: Dict[str, Any],
    suction_option: Dict[str, Any],
    discharge_option: Dict[str, Any],
) -> float | None:
    if route["measurement_required"] and meter_option.get("is_bypass", False):
        return None

    flow = max(
        float(route["q_min_delivered_lpm"]),
        float(source_option["q_min_lpm"]),
        float(destination_option["q_min_lpm"]),
        float(pump_option["q_min_lpm"]),
        float(meter_option["q_min_lpm"]),
        float(suction_option["q_min_lpm"]),
        float(discharge_option["q_min_lpm"]),
    )
    max_flow = min(
        float(source_option["q_max_lpm"]),
        float(destination_option["q_max_lpm"]),
        float(pump_option["q_max_lpm"]),
        float(meter_option["q_max_lpm"]),
        float(suction_option["q_max_lpm"]),
        float(discharge_option["q_max_lpm"]),
    )
    if flow > max_flow:
        return None
    return flow


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

    def accumulate(option: Dict[str, Any]) -> None:
        for component_id, qty in option["component_counts"].items():
            component_qty[component_id] = component_qty.get(component_id, 0) + int(qty)

    for option in source_selection.values():
        accumulate(option)
    for option in destination_selection.values():
        accumulate(option)
    for option in selected_pumps.values():
        accumulate(option)
    for option in selected_meters.values():
        accumulate(option)
    accumulate(suction_option)
    accumulate(discharge_option)

    for component_id, qty in component_qty.items():
        if qty > int(component_index[component_id]["available_qty"]):
            return None

    bom = []
    for component_id, qty in sorted(component_qty.items()):
        unit_cost = float(component_index[component_id]["cost"])
        bom.append(
            {
                "component_id": component_id,
                "qty": qty,
                "unit_cost": unit_cost,
                "total_cost": round(qty * unit_cost, 3),
            }
        )
    return bom


def _build_route_and_hydraulic_reports_from_assignment(
    *,
    assignment: Dict[str, Dict[str, Any]],
    system_class: str,
    suction_option: Dict[str, Any],
    discharge_option: Dict[str, Any],
) -> tuple[list[Dict[str, Any]], list[Dict[str, Any]]]:
    routes_report: list[Dict[str, Any]] = []
    hydraulics_report: list[Dict[str, Any]] = []

    for route_id in sorted(assignment):
        item = assignment[route_id]
        route = item["route"]
        flow = float(item["flow_delivered_lpm"])
        pump_option = item["pump_option"]
        meter_option = item["meter_option"]
        route_loss = (
            item["source_option"]["loss_lpm_equiv"]
            + suction_option["loss_lpm_equiv"]
            + pump_option["loss_lpm_equiv"]
            + meter_option["loss_lpm_equiv"]
            + discharge_option["loss_lpm_equiv"]
            + item["destination_option"]["loss_lpm_equiv"]
        )

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
                "meter_component_id": meter_option["metadata"]["component_id"],
                "meter_is_bypass": bool(meter_option.get("is_bypass", False)),
                "source_option_id": item["source_option"]["option_id"],
                "destination_option_id": item["destination_option"]["option_id"],
            }
        )
        hydraulics_report.append(
            {
                "route_id": route_id,
                "system_class": system_class,
                "suction_trunk_option_id": suction_option["option_id"],
                "discharge_trunk_option_id": discharge_option["option_id"],
                "flow_delivered_lpm": flow,
                "q_min_required_lpm": float(route["q_min_delivered_lpm"]),
                "loss_lpm_equiv": route_loss,
                "hydraulic_slack_lpm": float(pump_option["q_max_lpm"]) - flow,
            }
        )

    return routes_report, hydraulics_report


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

    def accumulate(option: Dict[str, Any]) -> None:
        for component_id, qty in option["component_counts"].items():
            component_qty[component_id] = component_qty.get(component_id, 0) + int(qty)

    for option_id in selected_source_options.values():
        accumulate(payload["source_options"][option_id])
    for option_id in selected_destination_options.values():
        accumulate(payload["destination_options"][option_id])
    for option_id in selected_pump_slots.values():
        accumulate(payload["pump_options"][option_id])
    for option_id in selected_meter_slots.values():
        accumulate(payload["meter_options"][option_id])
    accumulate(payload["suction_trunk_options"][selected_suction_trunk])
    accumulate(payload["discharge_trunk_options"][selected_discharge_trunk])

    bom = []
    for component_id, qty in sorted(component_qty.items()):
        unit_cost = float(payload["components"][component_id]["cost"])
        bom.append(
            {
                "component_id": component_id,
                "qty": qty,
                "unit_cost": unit_cost,
                "total_cost": round(qty * unit_cost, 3),
            }
        )
    return bom


def main() -> None:
    args = parse_args()
    scenario_dir = Path(args.scenario)

    data = load_scenario(scenario_dir)
    summary = scenario_summary(data)
    print(json.dumps(summary, indent=2, ensure_ascii=False))

    if args.dry_run:
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
