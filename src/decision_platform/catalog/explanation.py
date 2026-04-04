from __future__ import annotations

from typing import Any

from decision_platform.ranking.scoring import RANKING_COLUMNS


DIMENSION_LABELS = {
    "install_cost": "custo",
    "quality_score_raw": "qualidade",
    "flow_out_score": "flow",
    "resilience_score": "resiliência",
    "cleaning_score": "limpeza",
    "operability_score": "operabilidade",
    "fallback_component_count": "fallback",
}


def build_selected_candidate_explanation(
    result: dict[str, Any],
    *,
    profile_id: str | None = None,
) -> dict[str, Any]:
    resolved_profile_id = profile_id or result.get("default_profile_id")
    ranked_records = list(result.get("ranked_profiles", {}).get(resolved_profile_id or "", []))
    if not ranked_records:
        return {}
    winner_record = ranked_records[0]
    runner_up_record = ranked_records[1] if len(ranked_records) > 1 else None
    winner_item = _lookup_catalog_item(result, str(winner_record["candidate_id"]))
    runner_up_item = _lookup_catalog_item(result, str(runner_up_record["candidate_id"])) if runner_up_record else None
    weights = result.get("weight_profiles_lookup", {}).get(resolved_profile_id or "", {})
    contribution_delta = _build_contribution_delta(winner_record, runner_up_record, weights)
    dimension_differences = _build_dimension_differences(winner_record, runner_up_record)
    technical_tie = _is_technical_tie(winner_record, runner_up_record, dimension_differences)
    key_factors = _build_key_factors(contribution_delta, dimension_differences, winner_item, runner_up_item)
    if technical_tie:
        key_factors = [
            {
                "dimension": "technical_tie",
                "label": "empate técnico",
                "contribution_delta": 0.0,
                "winner_value": winner_record.get("score_final"),
                "runner_up_value": runner_up_record.get("score_final") if runner_up_record else None,
                "summary": (
                    "vencedor e runner-up ficaram empatados nos scores e nas dimensões principais; "
                    "a escolha final permaneceu determinística pelo ordenamento do ranking exportado."
                ),
            }
        ]
    penalties = _build_penalties(contribution_delta, winner_item, runner_up_item)
    winner_rules = _collect_quality_rules(winner_item)
    critical_routes = _critical_routes(winner_item["metrics"].get("route_metrics", [])) if winner_item else []
    conclusion = _build_conclusion(
        winner_item,
        runner_up_item,
        key_factors,
        penalties,
        resolved_profile_id,
        technical_tie=technical_tie,
    )
    return {
        "candidate_id": winner_item["candidate_id"] if winner_item else None,
        "active_profile_id": resolved_profile_id,
        "decision_status": "technical_tie" if technical_tie else "winner_clear",
        "winner": _candidate_summary(winner_record, winner_item),
        "runner_up": _candidate_summary(runner_up_record, runner_up_item) if runner_up_record else None,
        "same_family_as_runner_up": bool(
            winner_item
            and runner_up_item
            and winner_item["topology_family"] == runner_up_item["topology_family"]
        ),
        "score_margin": {
            "winner": float(winner_record.get("score_final", 0.0)),
            "runner_up": float(runner_up_record.get("score_final", 0.0)) if runner_up_record else None,
            "delta": round(
                float(winner_record.get("score_final", 0.0)) - float(runner_up_record.get("score_final", 0.0)),
                6,
            )
            if runner_up_record
            else None,
        },
        "dimension_differences": dimension_differences,
        "decision_differences": _build_decision_differences(dimension_differences),
        "contribution_differences": contribution_delta,
        "key_factors": key_factors,
        "winner_penalties": penalties,
        "quality_rules_triggered": winner_rules,
        "critical_routes": critical_routes,
        "engineering_conclusion": conclusion,
        "winner_reason_summary": conclusion,
    }


def render_selected_candidate_explanation_markdown(explanation: dict[str, Any]) -> str:
    if not explanation:
        return "# Selected Candidate Explanation\n\nNo ranked candidate was available.\n"
    winner = explanation.get("winner") or {}
    runner_up = explanation.get("runner_up") or {}
    key_factors = explanation.get("key_factors", [])
    penalties = explanation.get("winner_penalties", [])
    critical_routes = explanation.get("critical_routes", [])
    lines = [
        "# Selected Candidate Explanation",
        "",
        f"- Winner: `{winner.get('candidate_id')}`",
        f"- Profile: `{explanation.get('active_profile_id')}`",
        f"- Runner-up: `{runner_up.get('candidate_id')}`",
        f"- Conclusion: {explanation.get('engineering_conclusion')}",
        "",
        "## Head-to-head",
        "",
        f"- Winner family: `{winner.get('topology_family')}`",
        f"- Runner-up family: `{runner_up.get('topology_family')}`",
        f"- Winner total cost: `{winner.get('total_cost')}`",
        f"- Runner-up total cost: `{runner_up.get('total_cost')}`",
        f"- Winner score: `{winner.get('score_final')}`",
        f"- Runner-up score: `{runner_up.get('score_final')}`",
        "",
        "## Key factors",
        "",
    ]
    for factor in key_factors:
        lines.append(f"- {factor['summary']}")
    lines.extend(["", "## Penalties", ""])
    if penalties:
        for penalty in penalties:
            lines.append(f"- {penalty}")
    else:
        lines.append("- No relevant penalty was identified for the winner.")
    lines.extend(["", "## Critical routes", ""])
    for route in critical_routes:
        lines.append(
            f"- `{route['route_id']}`: reason=`{route['reason']}`, slack=`{route['hydraulic_slack_lpm']}`, "
            f"bottleneck=`{route['bottleneck_component_id']}`, consequence=`{route['critical_consequence']}`"
        )
    return "\n".join(lines) + "\n"


def build_family_summary_records(result: dict[str, Any]) -> list[dict[str, Any]]:
    summary = result.get("summary", {})
    family_counts = summary.get("candidates_by_family", {})
    feasible_by_family = summary.get("feasible_by_family", {})
    infeasible_by_family = summary.get("infeasible_candidates_by_family", {})
    viability_rate = summary.get("viability_rate_by_family", {})
    cost_by_family = summary.get("feasible_cost_distribution_by_family", {})
    generated_by_family = summary.get("generation_report", {}).get("generated_by_family", {})
    returned_by_family = summary.get("generation_report", {}).get("returned_by_family", {})
    records = []
    for family in sorted(family_counts):
        cost_summary = cost_by_family.get(family, {})
        records.append(
            {
                "topology_family": family,
                "candidate_count": int(family_counts.get(family, 0)),
                "feasible_count": int(feasible_by_family.get(family, 0)),
                "infeasible_candidate_count": int(infeasible_by_family.get(family, 0)),
                "viability_rate": float(viability_rate.get(family, 0.0)),
                "generated_candidate_count": int(generated_by_family.get(family, 0)),
                "returned_candidate_count": int(returned_by_family.get(family, 0)),
                "feasible_cost_min": cost_summary.get("min"),
                "feasible_cost_median": cost_summary.get("median"),
                "feasible_cost_max": cost_summary.get("max"),
                "feasible_cost_p90": cost_summary.get("p90"),
                "feasible_cost_avg": cost_summary.get("avg"),
            }
        )
    return records


def build_infeasibility_summary(result: dict[str, Any]) -> dict[str, Any]:
    catalog = result.get("catalog", [])
    primary_reason_counts: dict[str, int] = {}
    by_family_and_reason: dict[str, dict[str, int]] = {}
    mandatory_failed_route_ids: dict[str, int] = {}
    category_counts: dict[str, int] = {}
    for item in catalog:
        metrics = item["metrics"]
        if bool(metrics.get("feasible")):
            continue
        family = str(item["topology_family"])
        reason = str(metrics.get("infeasibility_reason") or "unknown")
        primary_reason_counts[reason] = primary_reason_counts.get(reason, 0) + 1
        family_reasons = by_family_and_reason.setdefault(family, {})
        family_reasons[reason] = family_reasons.get(reason, 0) + 1
        for route_id in metrics.get("mandatory_failed_route_ids", []):
            mandatory_failed_route_ids[str(route_id)] = mandatory_failed_route_ids.get(str(route_id), 0) + 1
        for category, count in metrics.get("constraint_failure_categories", {}).items():
            category_counts[str(category)] = category_counts.get(str(category), 0) + int(count)
    return {
        "total_infeasible_candidates": int(sum(primary_reason_counts.values())),
        "primary_infeasibility_reason_counts": primary_reason_counts,
        "infeasibility_by_family_and_reason": by_family_and_reason,
        "mandatory_failed_route_ids_frequency": mandatory_failed_route_ids,
        "constraint_failure_category_counts": category_counts,
    }


def _candidate_summary(record: dict[str, Any] | None, item: dict[str, Any] | None) -> dict[str, Any] | None:
    if record is None or item is None:
        return None
    metrics = item["metrics"]
    return {
        "candidate_id": item["candidate_id"],
        "topology_family": item["topology_family"],
        "generation_source": item.get("generation_source"),
        "score_final": float(record.get("score_final", 0.0)),
        "rank": int(record.get("rank", 0)),
        "install_cost": float(metrics.get("install_cost", 0.0)),
        "fallback_cost": float(metrics.get("fallback_cost", 0.0)),
        "total_cost": round(float(metrics.get("install_cost", 0.0)) + float(metrics.get("fallback_cost", 0.0)), 3),
        "quality_score_raw": float(metrics.get("quality_score_raw", 0.0)),
        "flow_out_score": float(metrics.get("flow_out_score", 0.0)),
        "resilience_score": float(metrics.get("resilience_score", 0.0)),
        "operability_score": float(metrics.get("operability_score", 0.0)),
        "cleaning_score": float(metrics.get("cleaning_score", 0.0)),
        "fallback_component_count": int(metrics.get("fallback_component_count", 0)),
        "feasible": bool(metrics.get("feasible")),
        "infeasibility_reason": metrics.get("infeasibility_reason"),
    }


def _build_dimension_differences(
    winner_record: dict[str, Any],
    runner_up_record: dict[str, Any] | None,
) -> dict[str, dict[str, float | None]]:
    dimensions = {
        "total_cost": ("total_cost", True),
        "quality_score_raw": ("quality_score_raw", False),
        "resilience_score": ("resilience_score", False),
        "operability_score": ("operability_score", False),
        "cleaning_score": ("cleaning_score", False),
        "fallback_component_count": ("fallback_component_count", True),
    }
    winner_total_cost = float(winner_record.get("install_cost", 0.0)) + float(winner_record.get("fallback_cost", 0.0))
    runner_total_cost = (
        float(runner_up_record.get("install_cost", 0.0)) + float(runner_up_record.get("fallback_cost", 0.0))
        if runner_up_record
        else None
    )
    rows: dict[str, dict[str, float | None]] = {
        "total_cost": {
            "winner": round(winner_total_cost, 3),
            "runner_up": round(runner_total_cost, 3) if runner_total_cost is not None else None,
            "delta": round(winner_total_cost - runner_total_cost, 3) if runner_total_cost is not None else None,
        }
    }
    for field_name in ["quality_score_raw", "resilience_score", "operability_score", "cleaning_score", "fallback_component_count"]:
        winner_value = float(winner_record.get(field_name, 0.0))
        runner_value = float(runner_up_record.get(field_name, 0.0)) if runner_up_record else None
        rows[field_name] = {
            "winner": round(winner_value, 3),
            "runner_up": round(runner_value, 3) if runner_value is not None else None,
            "delta": round(winner_value - runner_value, 3) if runner_value is not None else None,
        }
    return rows


def _build_contribution_delta(
    winner_record: dict[str, Any],
    runner_up_record: dict[str, Any] | None,
    weights: dict[str, Any],
) -> list[dict[str, Any]]:
    if runner_up_record is None:
        return []
    total_weight = sum(float(weights.get(weight_key, 0.0)) for weight_key in RANKING_COLUMNS) or 1.0
    rows = []
    for weight_key, (metric_column, _) in RANKING_COLUMNS.items():
        normalized_key = f"{metric_column}_normalized"
        weight_ratio = float(weights.get(weight_key, 0.0)) / total_weight
        winner_contribution = float(winner_record.get(normalized_key, 0.0)) * weight_ratio
        runner_contribution = float(runner_up_record.get(normalized_key, 0.0)) * weight_ratio
        delta = winner_contribution - runner_contribution
        rows.append(
            {
                "dimension": metric_column,
                "label": DIMENSION_LABELS.get(metric_column, metric_column),
                "weight_ratio": round(weight_ratio, 6),
                "winner_contribution": round(winner_contribution, 6),
                "runner_up_contribution": round(runner_contribution, 6),
                "delta": round(delta, 6),
            }
        )
    return rows


def _build_decision_differences(
    dimension_differences: dict[str, dict[str, float | None]],
) -> dict[str, dict[str, float | None]]:
    return {
        "cost": dimension_differences.get("total_cost", {}),
        "quality": dimension_differences.get("quality_score_raw", {}),
        "resilience": dimension_differences.get("resilience_score", {}),
        "operability": dimension_differences.get("operability_score", {}),
        "cleaning": dimension_differences.get("cleaning_score", {}),
        "fallback": dimension_differences.get("fallback_component_count", {}),
    }


def _build_key_factors(
    contribution_delta: list[dict[str, Any]],
    dimension_differences: dict[str, dict[str, float | None]],
    winner_item: dict[str, Any] | None,
    runner_up_item: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    positive = sorted((row for row in contribution_delta if row["delta"] > 0), key=lambda row: row["delta"], reverse=True)
    rows = positive[:5]
    if not rows and winner_item is not None:
        rows = [row for row in contribution_delta if row["delta"] != 0][:3]
    factors = []
    for row in rows[:5]:
        dimension = str(row["dimension"])
        diff = dimension_differences.get(dimension, {})
        factors.append(
            {
                "dimension": dimension,
                "label": row["label"],
                "contribution_delta": row["delta"],
                "winner_value": diff.get("winner"),
                "runner_up_value": diff.get("runner_up"),
                "summary": (
                    f"{row['label']} favoreceu o vencedor em {row['delta']:.4f} de score ponderado "
                    f"({diff.get('winner')} vs {diff.get('runner_up')})."
                ),
            }
        )
    if winner_item and runner_up_item:
        winner_total = float(winner_item["metrics"].get("install_cost", 0.0)) + float(winner_item["metrics"].get("fallback_cost", 0.0))
        runner_total = float(runner_up_item["metrics"].get("install_cost", 0.0)) + float(runner_up_item["metrics"].get("fallback_cost", 0.0))
        if winner_total < runner_total and not any(factor["dimension"] == "install_cost" for factor in factors):
            factors.append(
                {
                    "dimension": "total_cost",
                    "label": "custo total",
                    "contribution_delta": None,
                    "winner_value": round(winner_total, 3),
                    "runner_up_value": round(runner_total, 3),
                    "summary": f"o vencedor manteve custo total menor ({winner_total:.3f} vs {runner_total:.3f}).",
                }
            )
    return factors[:5]


def _build_penalties(
    contribution_delta: list[dict[str, Any]],
    winner_item: dict[str, Any] | None,
    runner_up_item: dict[str, Any] | None,
) -> list[str]:
    if winner_item is None:
        return []
    penalties: list[str] = []
    winner_metrics = winner_item["metrics"]
    if int(winner_metrics.get("fallback_component_count", 0)) > 0:
        penalties.append(
            f"usa {int(winner_metrics.get('fallback_component_count', 0))} componentes de fallback "
            f"e adiciona {float(winner_metrics.get('fallback_cost', 0.0)):.3f} de custo de fallback"
        )
    failed_flags = [flag for flag in winner_metrics.get("quality_flags", []) if str(flag).endswith(":fail")]
    if failed_flags:
        penalties.append(f"aciona flags de qualidade desfavoráveis: {', '.join(sorted(set(failed_flags))[:5])}")
    negative = sorted((row for row in contribution_delta if row["delta"] < 0), key=lambda row: row["delta"])
    for row in negative[:3]:
        penalties.append(f"ficou atrás em {row['label']} por {-row['delta']:.4f} de score ponderado relativo")
    if runner_up_item is not None and winner_item["topology_family"] != runner_up_item["topology_family"]:
        penalties.append(
            f"ganhou contra uma família alternativa (`{runner_up_item['topology_family']}`), o que exige comparação cruzada de heurística"
        )
    return penalties[:5]


def _build_conclusion(
    winner_item: dict[str, Any] | None,
    runner_up_item: dict[str, Any] | None,
    key_factors: list[dict[str, Any]],
    penalties: list[str],
    profile_id: str | None,
    *,
    technical_tie: bool,
) -> str:
    if winner_item is None:
        return "Nenhum candidato ranqueado estava disponível."
    if technical_tie:
        runner_up_id = runner_up_item["candidate_id"] if runner_up_item else "sem runner-up"
        penalty = penalties[0] if penalties else "sem penalidade dominante"
        return (
            f"houve empate técnico com `{runner_up_id}` no perfil `{profile_id}`; a seleção oficial foi mantida "
            f"pelo ordenamento determinístico do ranking exportado. A principal ressalva é {penalty}."
        )
    factors = ", ".join(factor["label"] for factor in key_factors[:2]) if key_factors else "equilíbrio global de score"
    penalty = penalties[0] if penalties else "sem penalidade dominante"
    runner_up_id = runner_up_item["candidate_id"] if runner_up_item else "sem runner-up"
    return (
        f"venceu porque, no perfil `{profile_id}`, combinou melhor {factors} contra `{runner_up_id}`, "
        f"mantendo viabilidade nas rotas críticas; a principal ressalva é {penalty}."
    )


def _collect_quality_rules(candidate_item: dict[str, Any] | None) -> list[str]:
    if candidate_item is None:
        return []
    metrics = candidate_item["metrics"]
    triggered = set(str(rule) for rule in metrics.get("rules_triggered", []))
    for route in metrics.get("route_metrics", []):
        for rule in route.get("rules_triggered", []):
            triggered.add(str(rule))
    return sorted(triggered)


def _critical_routes(route_metrics: list[dict[str, Any]]) -> list[dict[str, Any]]:
    ranked = sorted(
        route_metrics,
        key=lambda route: (
            bool(route.get("feasible", True)),
            float(route.get("hydraulic_slack_lpm") or 0.0),
            -float(route.get("required_flow_lpm") or 0.0),
        ),
    )
    return [
        {
            "route_id": route.get("route_id"),
            "feasible": route.get("feasible"),
            "reason": route.get("reason"),
            "route_effective_q_max_lpm": route.get("route_effective_q_max_lpm"),
            "hydraulic_slack_lpm": route.get("hydraulic_slack_lpm"),
            "total_loss_lpm_equiv": route.get("total_loss_lpm_equiv"),
            "bottleneck_component_id": route.get("bottleneck_component_id"),
            "critical_consequence": route.get("critical_consequence"),
        }
        for route in ranked[:5]
    ]


def _lookup_catalog_item(result: dict[str, Any], candidate_id: str) -> dict[str, Any] | None:
    return next((candidate for candidate in result.get("catalog", []) if candidate["candidate_id"] == candidate_id), None)


def _is_technical_tie(
    winner_record: dict[str, Any],
    runner_up_record: dict[str, Any] | None,
    dimension_differences: dict[str, dict[str, float | None]],
) -> bool:
    if runner_up_record is None:
        return False
    if round(float(winner_record.get("score_final", 0.0)) - float(runner_up_record.get("score_final", 0.0)), 6) != 0.0:
        return False
    return all(round(float(values.get("delta") or 0.0), 6) == 0.0 for values in dimension_differences.values())
