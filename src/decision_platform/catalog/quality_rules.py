from __future__ import annotations

from typing import Any

import pandas as pd

from decision_platform.data_io.loader import ScenarioBundle


def apply_quality_rules(metrics: dict[str, Any], bundle: ScenarioBundle) -> dict[str, Any]:
    enriched = dict(metrics)
    route_metrics = [dict(route) for route in metrics.get("route_metrics", [])]
    rules = bundle.quality_rules.to_dict("records")

    route_score_total = 0.0
    route_count = max(len(route_metrics), 1)
    for route in route_metrics:
        base_quality = float(route.get("quality_score_base", route.get("quality_score", 0.0)))
        route_breakdown = []
        route_flags = []
        route_rules_triggered = []
        route_delta = 0.0
        route_feasible = bool(route.get("feasible", False))
        for rule in rules:
            if rule["metric_scope"] != "route":
                continue
            passed, delta = _evaluate_rule(rule, route)
            if passed is None:
                continue
            route_delta += delta
            route_breakdown.append(
                {
                    "rule_id": rule["rule_id"],
                    "metric_name": rule["metric_name"],
                    "passed": passed,
                    "delta": delta,
                    "description": rule.get("description", ""),
                }
            )
            if delta != 0 or bool(rule["hard_filter"]):
                route_rules_triggered.append(rule["rule_id"])
            route_flags.append(f"{rule['rule_id']}:{'pass' if passed else 'fail'}")
            if bool(rule["hard_filter"]) and not passed:
                route_feasible = False
                route["reason"] = f"quality_rule:{rule['rule_id']}"
        route["feasible"] = route_feasible
        route["quality_score_delta"] = round(route_delta, 3)
        route["quality_score"] = round(base_quality + route_delta, 3)
        route["quality_score_breakdown"] = route_breakdown
        route["quality_flags"] = route_flags
        route["rules_triggered"] = route_rules_triggered
        route_score_total += route["quality_score"]

    solution_breakdown = []
    solution_flags = []
    solution_rules_triggered = []
    solution_delta = 0.0
    solution_feasible = bool(enriched.get("feasible", False))
    solution_context = dict(enriched)
    solution_context["route_metrics"] = route_metrics
    for rule in rules:
        if rule["metric_scope"] != "solution":
            continue
        passed, delta = _evaluate_rule(rule, solution_context)
        if passed is None:
            continue
        solution_delta += delta
        solution_breakdown.append(
            {
                "rule_id": rule["rule_id"],
                "metric_name": rule["metric_name"],
                "passed": passed,
                "delta": delta,
                "description": rule.get("description", ""),
            }
        )
        if delta != 0 or bool(rule["hard_filter"]):
            solution_rules_triggered.append(rule["rule_id"])
        solution_flags.append(f"{rule['rule_id']}:{'pass' if passed else 'fail'}")
        if bool(rule["hard_filter"]) and not passed:
            solution_feasible = False

    enriched["route_metrics"] = route_metrics
    enriched["feasible"] = solution_feasible and not enriched.get("mandatory_unserved")
    enriched["quality_score_raw"] = round(route_score_total / route_count + solution_delta, 3)
    enriched["quality_score_breakdown"] = solution_breakdown
    enriched["quality_flags"] = solution_flags
    enriched["rules_triggered"] = solution_rules_triggered
    return enriched


def _evaluate_rule(rule: dict[str, Any], context: dict[str, Any]) -> tuple[bool | None, float]:
    metric_name = str(rule["metric_name"])
    if metric_name not in context:
        return None, 0.0
    value = context.get(metric_name)
    threshold = rule.get("threshold", 0)
    passed = _compare(value, rule["operator"], threshold)
    delta = float(rule["score_delta_if_true"] if passed else rule["score_delta_if_false"])
    return passed, delta


def _compare(value: Any, operator: str, threshold: Any) -> bool:
    normalized_value = _normalize_value(value)
    normalized_threshold = _normalize_value(threshold)
    if operator == "<=":
        return normalized_value <= normalized_threshold
    if operator == ">=":
        return normalized_value >= normalized_threshold
    if operator == "==":
        return normalized_value == normalized_threshold
    if operator == "!=":
        return normalized_value != normalized_threshold
    if operator == "<":
        return normalized_value < normalized_threshold
    if operator == ">":
        return normalized_value > normalized_threshold
    raise ValueError(f"Unsupported rule operator: {operator}")


def _normalize_value(value: Any) -> float | str:
    if isinstance(value, bool):
        return 1.0 if value else 0.0
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, pd.Series):
        return float(value.iloc[0])
    text = str(value).strip()
    try:
        return float(text)
    except ValueError:
        return text
