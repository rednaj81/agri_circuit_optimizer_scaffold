from __future__ import annotations

import json
from statistics import median
from typing import Any


FAILURE_REASON_TO_CATEGORY = {
    "no_path": "connectivity",
    "no_pump_available": "components",
    "measurement_required_without_compatible_meter": "measurement",
    "idle_pumps_not_allowed": "family_rules",
    "idle_meters_not_allowed": "family_rules",
    "insufficient_effective_capacity": "hydraulics",
    "hydraulic_or_meter_infeasible": "hydraulics",
}

FAILURE_CATEGORY_PRIORITY = {
    "fallback_not_allowed": 0,
    "connectivity": 1,
    "components": 2,
    "measurement": 3,
    "family_rules": 4,
    "hydraulics": 5,
    "unknown": 6,
}


def classify_failure_reason(reason: str | None) -> str:
    normalized = str(reason or "").strip()
    if not normalized:
        return "unknown"
    if normalized.startswith("quality_rule:"):
        return "quality_gate"
    return FAILURE_REASON_TO_CATEGORY.get(normalized, "unknown")


def build_constraint_failures(metrics: dict[str, Any]) -> list[dict[str, Any]]:
    failures: list[dict[str, Any]] = []
    for route in metrics.get("route_metrics", []):
        if bool(route.get("feasible", True)):
            continue
        reason = str(route.get("failure_reason") or route.get("reason") or "unknown")
        failures.append(
            {
                "scope": "route",
                "route_id": route.get("route_id"),
                "mandatory": bool(route.get("mandatory", False)),
                "route_group": route.get("route_group"),
                "source": route.get("source"),
                "sink": route.get("sink"),
                "reason": reason,
                "category": classify_failure_reason(reason),
                "affects_viability": bool(route.get("mandatory", False)),
            }
        )

    if metrics.get("engine_requested") == "watermodels_jl" and metrics.get("engine_used") != "watermodels_jl":
        failures.append(
            {
                "scope": "engine",
                "route_id": None,
                "mandatory": True,
                "route_group": None,
                "source": None,
                "sink": None,
                "reason": "fallback_not_allowed" if metrics.get("engine_warning") is None else "python_engine_fallback",
                "category": "fallback_not_allowed",
                "affects_viability": False,
            }
        )
    return failures


def summarize_constraint_failures(metrics: dict[str, Any]) -> dict[str, Any]:
    failures = build_constraint_failures(metrics)
    categories: dict[str, int] = {}
    reasons: dict[str, int] = {}
    mandatory_route_ids: list[str] = []
    for failure in failures:
        category = str(failure["category"])
        reason = str(failure["reason"])
        categories[category] = categories.get(category, 0) + 1
        reasons[reason] = reasons.get(reason, 0) + 1
        if failure["affects_viability"] and failure["route_id"]:
            mandatory_route_ids.append(str(failure["route_id"]))

    primary_infeasibility_reason = None
    if not bool(metrics.get("feasible", False)):
        primary_infeasibility_reason = _pick_primary_failure_reason(failures)

    return {
        "constraint_failures": failures,
        "constraint_failure_count": len(failures),
        "constraint_failure_categories": categories,
        "constraint_failure_reasons": reasons,
        "mandatory_failed_route_ids": sorted(set(mandatory_route_ids)),
        "infeasibility_reason": primary_infeasibility_reason,
    }


def viable_cost_distribution(values: list[float]) -> dict[str, float | None]:
    if not values:
        return {
            "min": None,
            "median": None,
            "max": None,
            "p90": None,
            "avg": None,
        }
    ordered = sorted(float(value) for value in values)
    p90_index = min(len(ordered) - 1, max(0, round((len(ordered) - 1) * 0.9)))
    return {
        "min": round(ordered[0], 3),
        "median": round(float(median(ordered)), 3),
        "max": round(ordered[-1], 3),
        "p90": round(ordered[p90_index], 3),
        "avg": round(sum(ordered) / len(ordered), 3),
    }


def serialize_constraint_failures(failures: list[dict[str, Any]]) -> str:
    return json.dumps(failures, ensure_ascii=False)


def _pick_primary_failure_reason(failures: list[dict[str, Any]]) -> str | None:
    affecting = [failure for failure in failures if failure.get("affects_viability")]
    candidates = affecting or failures
    if not candidates:
        return None
    ranked = sorted(
        candidates,
        key=lambda failure: (
            FAILURE_CATEGORY_PRIORITY.get(str(failure.get("category")), 99),
            str(failure.get("reason")),
            str(failure.get("route_id") or ""),
        ),
    )
    return str(ranked[0]["category"])
