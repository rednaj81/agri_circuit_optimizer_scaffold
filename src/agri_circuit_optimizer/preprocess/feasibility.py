from __future__ import annotations

from typing import Any, Dict


def meter_compatibility(route: Dict[str, Any], meter: Dict[str, Any]) -> Dict[str, Any]:
    measurement_required = bool(route.get("measurement_required", False))
    meter_is_bypass = bool(meter.get("is_bypass", False))
    q_required = float(route.get("q_min_delivered_lpm", 0.0))
    dose_min = float(route.get("dose_min_l", 0.0))
    dose_error_max = float(route.get("dose_error_max_pct", 100.0))
    meter_q_min = float(meter.get("q_min_lpm", 0.0))
    meter_q_max = float(meter.get("q_max_lpm", 1e12))
    meter_dose_q_max = float(meter.get("meter_dose_q_max_lpm") or meter_q_max)
    effective_q_max = min(meter_q_max, meter_dose_q_max) if measurement_required else meter_q_max

    bypass_ok = not measurement_required or not meter_is_bypass
    q_range_ok = meter_q_min <= q_required <= effective_q_max

    if meter_is_bypass:
        dose_ok = not measurement_required
        error_ok = not measurement_required
    else:
        meter_batch_min = float(meter.get("meter_batch_min_l") or 0.0)
        meter_error = float(meter.get("meter_error_pct") or 0.0)
        dose_ok = meter_batch_min <= dose_min if measurement_required else True
        error_ok = meter_error <= dose_error_max if measurement_required else True

    compatible = bypass_ok and q_range_ok and dose_ok and error_ok
    return {
        "compatible": compatible,
        "meter_is_bypass": meter_is_bypass,
        "bypass_ok": bypass_ok,
        "q_range_ok": q_range_ok,
        "dose_ok": dose_ok,
        "error_ok": error_ok,
        "meter_q_min_lpm": meter_q_min,
        "meter_q_max_lpm": effective_q_max,
    }


def meter_can_serve_route(route: Dict[str, Any], meter: Dict[str, Any]) -> bool:
    return bool(meter_compatibility(route, meter)["compatible"])


def compute_route_min_flow(
    *,
    route: Dict[str, Any],
    source_option: Dict[str, Any],
    destination_option: Dict[str, Any],
    pump_option: Dict[str, Any],
    meter_option: Dict[str, Any],
    suction_option: Dict[str, Any],
    discharge_option: Dict[str, Any],
) -> float:
    return max(
        float(route.get("q_min_delivered_lpm", 0.0)),
        float(source_option.get("q_min_lpm", 0.0)),
        float(destination_option.get("q_min_lpm", 0.0)),
        float(pump_option.get("q_min_lpm", 0.0)),
        float(meter_option.get("q_min_lpm", 0.0)),
        float(suction_option.get("q_min_lpm", 0.0)),
        float(discharge_option.get("q_min_lpm", 0.0)),
    )


def summarize_route_hydraulics(
    *,
    route: Dict[str, Any],
    source_option: Dict[str, Any],
    destination_option: Dict[str, Any],
    pump_option: Dict[str, Any],
    meter_option: Dict[str, Any],
    suction_option: Dict[str, Any],
    discharge_option: Dict[str, Any],
    flow_delivered_lpm: float | None = None,
) -> Dict[str, Any]:
    meter_effective_q_max = float(meter_option.get("q_max_lpm", 0.0))
    if bool(route.get("measurement_required", False)):
        meter_effective_q_max = min(
            meter_effective_q_max,
            float(meter_option.get("meter_dose_q_max_lpm") or meter_effective_q_max),
        )
    stage_qmax = {
        "source_branch": float(source_option.get("q_max_lpm", 0.0)),
        "suction_trunk": float(suction_option.get("q_max_lpm", 0.0)),
        "pump": float(pump_option.get("q_max_lpm", 0.0)),
        "meter": meter_effective_q_max,
        "discharge_trunk": float(discharge_option.get("q_max_lpm", 0.0)),
        "destination_branch": float(destination_option.get("q_max_lpm", 0.0)),
    }
    stage_losses = {
        "source_branch": float(source_option.get("loss_lpm_equiv", 0.0)),
        "suction_trunk": float(suction_option.get("loss_lpm_equiv", 0.0)),
        "pump": float(pump_option.get("loss_lpm_equiv", 0.0)),
        "meter": float(meter_option.get("loss_lpm_equiv", 0.0)),
        "discharge_trunk": float(discharge_option.get("loss_lpm_equiv", 0.0)),
        "destination_branch": float(destination_option.get("loss_lpm_equiv", 0.0)),
    }
    total_loss = sum(stage_losses.values())
    effective_stage_capacity = {
        **stage_qmax,
        "pump_after_losses": max(0.0, stage_qmax["pump"] - total_loss),
    }
    required_flow = flow_delivered_lpm
    if required_flow is None:
        required_flow = compute_route_min_flow(
            route=route,
            source_option=source_option,
            destination_option=destination_option,
            pump_option=pump_option,
            meter_option=meter_option,
            suction_option=suction_option,
            discharge_option=discharge_option,
        )
    route_capacity = min(
        stage_qmax["source_branch"],
        stage_qmax["suction_trunk"],
        effective_stage_capacity["pump_after_losses"],
        stage_qmax["meter"],
        stage_qmax["discharge_trunk"],
        stage_qmax["destination_branch"],
    )
    hydraulic_slack = route_capacity - float(required_flow)
    bottleneck_label = min(
        effective_stage_capacity,
        key=lambda label: effective_stage_capacity[label],
    )
    bottleneck_capacity = effective_stage_capacity[bottleneck_label]
    return {
        "required_flow_lpm": float(required_flow),
        "total_loss_lpm_equiv": total_loss,
        "route_capacity_lpm": route_capacity,
        "hydraulic_slack_lpm": hydraulic_slack,
        "hydraulic_ok": hydraulic_slack >= -1e-9,
        "stage_losses_lpm_equiv": stage_losses,
        "effective_stage_capacity_lpm": effective_stage_capacity,
        "bottleneck_label": bottleneck_label,
        "bottleneck_capacity_lpm": bottleneck_capacity,
    }


def pump_can_serve_route(
    route: Dict[str, Any],
    pump: Dict[str, Any],
    *,
    total_loss_lpm_equiv: float = 0.0,
    required_flow_lpm: float | None = None,
) -> bool:
    q_required = (
        float(required_flow_lpm)
        if required_flow_lpm is not None
        else float(route.get("q_min_delivered_lpm", 0.0))
    )
    return max(0.0, float(pump.get("q_max_lpm", 0.0)) - total_loss_lpm_equiv) >= q_required
