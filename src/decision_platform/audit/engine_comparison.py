from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from pathlib import Path
from typing import Any

from decision_platform.catalog.explanation import build_selected_candidate_explanation
from decision_platform.catalog.pipeline import build_solution_catalog
from decision_platform.data_io.loader import ScenarioBundle


ENGINE_KEYS = [
    "feasible",
    "install_cost",
    "fallback_cost",
    "quality_score_raw",
    "flow_out_score",
    "resilience_score",
    "cleaning_score",
    "operability_score",
    "maintenance_score",
    "alternate_path_count_critical",
    "fallback_component_count",
]

ROUTE_KEYS = [
    "feasible",
    "reason",
    "failure_reason",
    "delivered_flow_lpm",
    "route_effective_q_max_lpm",
    "hydraulic_slack_lpm",
    "total_loss_lpm_equiv",
    "bottleneck_component_id",
    "critical_consequence",
]

ENGINE_DIFF_VARIANT = {
    "enabled_families": ["hybrid_free"],
    "candidate_generation": {
        "population_size": 80,
        "generations": 30,
        "keep_top_n_per_family": 20,
        "random_seed": 42,
        "enable_mutations": True,
        "enable_crossover": True,
        "allow_family_hopping": False,
    },
    "ranking": {
        "default_profile": "balanced",
        "keep_only_feasible": True,
    },
}


def audit_julia_engine_implementation() -> dict[str, Any]:
    decision_engine_path = Path(__file__).resolve().parents[3] / "julia" / "src" / "DecisionEngine.jl"
    text = decision_engine_path.read_text(encoding="utf-8")
    watermodels_calls = [
        line.strip()
        for line in text.splitlines()
        if "WaterModels." in line or "run_" in line and "WaterModels" in line
    ]
    uses_jump_smoke_model = "Model(HiGHS.Optimizer)" in text and "@objective(model, Max, x)" in text
    return {
        "decision_engine_path": str(decision_engine_path),
        "watermodels_imported": "using WaterModels" in text,
        "jump_imported": "using JuMP" in text,
        "highs_imported": "using HiGHS" in text,
        "watermodels_solver_calls_found": watermodels_calls,
        "uses_jump_smoke_model": uses_jump_smoke_model,
        "what_uses_watermodels_in_practice": [
            "O runtime Julia sobe um processo real com ambiente `julia/Project.toml` e valida disponibilidade de WaterModels/JuMP/HiGHS antes da avaliação.",
            "O arquivo `DecisionEngine.jl` importa `WaterModels`, mas não chama APIs de formulação ou solve da biblioteca para calcular a rede hidráulica.",
            "A decisão por rota hoje é calculada por lógica própria em Julia: enumeração de caminhos, seleção de bomba/medidor, perdas lineares equivalentes e gargalo por capacidade mínima.",
        ],
        "simplifications_still_present": [
            "Não há modelo de rede hidráulica WaterModels resolvendo balanço/acoplamento global.",
            "As perdas são agregadas por componente em percentuais lineares equivalentes.",
            "A capacidade efetiva por rota é o mínimo entre capacidades corrigidas por perda ao longo do caminho.",
            "Fallbacks de bomba/medidor continuam sendo injetados pela lógica do payload, não por otimização da rede.",
            "A resiliência continua derivada de contagem heurística de caminhos alternativos.",
        ],
        "metrics_emitted_by_julia_engine": [
            "feasible",
            "mandatory_unserved",
            "install_cost",
            "fallback_cost",
            "quality_score_raw",
            "flow_out_score",
            "resilience_score",
            "cleaning_score",
            "operability_score",
            "maintenance_score",
            "alternate_path_count_critical",
            "fallback_component_count",
            "bom_summary",
            "route_metrics",
        ],
        "metrics_post_processed_in_python_after_engine": [
            "quality_score_raw pode ser ajustado por `quality_rules.csv`",
            "feasible pode ser endurecido por hard filters de qualidade, se existirem",
            "ranking final depende de normalização global em `ranking/scoring.py`",
        ],
    }


def build_engine_comparison_suite(bundle: ScenarioBundle, *, julia_result: dict[str, Any] | None = None) -> dict[str, Any]:
    base_julia_result = julia_result or build_solution_catalog(bundle)
    base_python_result = build_solution_catalog(_clone_bundle_with_engine(bundle, primary="python_emulated_julia", fallback="none"))
    variant_bundle = _clone_bundle_with_overrides(bundle, ENGINE_DIFF_VARIANT)
    variant_julia_result = build_solution_catalog(variant_bundle)
    variant_python_result = build_solution_catalog(_clone_bundle_with_engine(variant_bundle, primary="python_emulated_julia", fallback="none"))
    scenario_comparisons = {
        "maquete_v2": _build_engine_comparison("maquete_v2", base_julia_result, base_python_result),
        "hybrid_free_focus_variant": _build_engine_comparison(
            "hybrid_free_focus_variant",
            variant_julia_result,
            variant_python_result,
        ),
    }
    return {
        "implementation_audit": audit_julia_engine_implementation(),
        "scenario_comparisons": scenario_comparisons,
        "candidate_rows": _build_candidate_rows_for_suite(
            {
                "maquete_v2": {
                    "julia": base_julia_result,
                    "python": base_python_result,
                },
                "hybrid_free_focus_variant": {
                    "julia": variant_julia_result,
                    "python": variant_python_result,
                },
            }
        ),
    }


def _build_engine_comparison(
    label: str,
    julia_result: dict[str, Any],
    python_result: dict[str, Any],
) -> dict[str, Any]:
    profiles = sorted(julia_result.get("ranked_profiles", {}))
    candidate_differences = _candidate_differences(julia_result, python_result)
    default_profile_id = str(julia_result.get("default_profile_id") or profiles[0] if profiles else "")
    julia_explanation = build_selected_candidate_explanation(julia_result, profile_id=default_profile_id)
    python_explanation = build_selected_candidate_explanation(python_result, profile_id=default_profile_id)
    same_winner = julia_result.get("selected_candidate_id") == python_result.get("selected_candidate_id")
    ranking_difference_observed = _ranking_difference_observed(julia_result, python_result, profiles)
    route_metric_difference_observed = any(item["route_difference_count"] > 0 for item in candidate_differences)
    return {
        "label": label,
        "default_profile_id": default_profile_id,
        "candidate_count": {
            "julia": len(julia_result["catalog"]),
            "python": len(python_result["catalog"]),
        },
        "feasible_count": {
            "julia": sum(1 for item in julia_result["catalog"] if bool(item["metrics"]["feasible"])),
            "python": sum(1 for item in python_result["catalog"] if bool(item["metrics"]["feasible"])),
        },
        "selected_candidate": {
            "julia": julia_result.get("selected_candidate_id"),
            "python": python_result.get("selected_candidate_id"),
            "same": same_winner,
        },
        "same_winner": same_winner,
        "top_candidate_by_profile": {
            profile: {
                "julia": _top_record(julia_result, profile),
                "python": _top_record(python_result, profile),
                "same_top_candidate": _top_record(julia_result, profile).get("candidate_id") == _top_record(python_result, profile).get("candidate_id"),
            }
            for profile in profiles
        },
        "selected_candidate_breakdown": {
            "julia": _selected_breakdown(julia_result),
            "python": _selected_breakdown(python_result),
        },
        "winner_vs_runner_up": {
            "julia": julia_explanation,
            "python": python_explanation,
        },
        "changed_candidate_count": len(candidate_differences),
        "changed_route_count": sum(item["route_difference_count"] for item in candidate_differences),
        "changed_candidates": candidate_differences[:20],
        "ranking_difference_observed": ranking_difference_observed,
        "decision_difference_observed": bool(candidate_differences) or not same_winner,
        "route_metric_difference_observed": route_metric_difference_observed,
        "text_summary": _build_text_summary(
            default_profile_id,
            julia_explanation,
            python_explanation,
            same_winner=same_winner,
            ranking_difference_observed=ranking_difference_observed,
            route_metric_difference_observed=route_metric_difference_observed,
        ),
    }


def _clone_bundle_with_engine(bundle: ScenarioBundle, *, primary: str, fallback: str) -> ScenarioBundle:
    cloned = _clone_bundle_with_overrides(bundle, {})
    cloned.scenario_settings.setdefault("hydraulic_engine", {})
    cloned.scenario_settings["hydraulic_engine"]["primary"] = primary
    cloned.scenario_settings["hydraulic_engine"]["fallback"] = fallback
    return cloned


def _clone_bundle_with_overrides(bundle: ScenarioBundle, overrides: dict[str, Any]) -> ScenarioBundle:
    settings = deepcopy(bundle.scenario_settings)
    _deep_update(settings, overrides)
    return replace(bundle, scenario_settings=settings)


def _deep_update(target: dict[str, Any], updates: dict[str, Any]) -> None:
    for key, value in updates.items():
        if isinstance(value, dict) and isinstance(target.get(key), dict):
            _deep_update(target[key], value)
            continue
        target[key] = deepcopy(value)


def _top_record(result: dict[str, Any], profile: str) -> dict[str, Any]:
    records = result.get("ranked_profiles", {}).get(profile, [])
    if not records:
        return {}
    record = records[0]
    return {
        "candidate_id": record.get("candidate_id"),
        "topology_family": record.get("topology_family"),
        "generation_source": record.get("generation_source"),
        "score_final": record.get("score_final"),
        "install_cost": record.get("install_cost"),
        "fallback_cost": record.get("fallback_cost"),
        "total_cost": round(float(record.get("install_cost", 0.0)) + float(record.get("fallback_cost", 0.0)), 3),
        "quality_score_raw": record.get("quality_score_raw"),
        "flow_out_score": record.get("flow_out_score"),
        "resilience_score": record.get("resilience_score"),
        "fallback_component_count": record.get("fallback_component_count"),
        "feasible": record.get("feasible"),
    }


def _selected_breakdown(result: dict[str, Any]) -> dict[str, Any]:
    selected = result.get("selected_candidate")
    if not selected:
        return {}
    metrics = selected["metrics"]
    return {
        "candidate_id": selected["candidate_id"],
        "topology_family": selected["topology_family"],
        "generation_source": selected.get("generation_source"),
        "score_breakdown": {
            key: metrics.get(key)
            for key in ENGINE_KEYS
        },
        "route_metrics": [
            {
                "route_id": route.get("route_id"),
                **{key: route.get(key) for key in ROUTE_KEYS},
            }
            for route in metrics.get("route_metrics", [])
        ],
    }


def _candidate_differences(julia_result: dict[str, Any], python_result: dict[str, Any]) -> list[dict[str, Any]]:
    python_by_id = {item["candidate_id"]: item for item in python_result["catalog"]}
    differences = []
    for julia_item in julia_result["catalog"]:
        candidate_id = julia_item["candidate_id"]
        python_item = python_by_id[candidate_id]
        metric_diff = {
            key: {"julia": julia_item["metrics"].get(key), "python": python_item["metrics"].get(key)}
            for key in ENGINE_KEYS
            if julia_item["metrics"].get(key) != python_item["metrics"].get(key)
        }
        route_diffs = []
        for julia_route, python_route in zip(julia_item["metrics"].get("route_metrics", []), python_item["metrics"].get("route_metrics", [])):
            diff = {
                key: {"julia": julia_route.get(key), "python": python_route.get(key)}
                for key in ROUTE_KEYS
                if julia_route.get(key) != python_route.get(key)
            }
            if diff:
                route_diffs.append({"route_id": julia_route.get("route_id"), "difference": diff})
        if metric_diff or route_diffs:
            differences.append(
                {
                    "candidate_id": candidate_id,
                    "topology_family": julia_item["topology_family"],
                    "metric_differences": metric_diff,
                    "route_difference_count": len(route_diffs),
                    "route_differences": route_diffs[:10],
                }
            )
    return differences


def _ranking_difference_observed(
    julia_result: dict[str, Any],
    python_result: dict[str, Any],
    profiles: list[str],
) -> bool:
    for profile in profiles:
        julia_ranking = [record["candidate_id"] for record in julia_result.get("ranked_profiles", {}).get(profile, [])]
        python_ranking = [record["candidate_id"] for record in python_result.get("ranked_profiles", {}).get(profile, [])]
        if julia_ranking != python_ranking:
            return True
    return False


def _build_text_summary(
    profile_id: str,
    julia_explanation: dict[str, Any],
    python_explanation: dict[str, Any],
    *,
    same_winner: bool,
    ranking_difference_observed: bool,
    route_metric_difference_observed: bool,
) -> dict[str, Any]:
    julia_winner = (julia_explanation.get("winner") or {}).get("candidate_id")
    python_winner = (python_explanation.get("winner") or {}).get("candidate_id")
    if same_winner:
        conclusion = (
            f"Mesma decisão no perfil `{profile_id}`: Julia e Python escolheram `{julia_winner}`. "
            f"Ranking_diff={ranking_difference_observed}; route_diff={route_metric_difference_observed}."
        )
    else:
        conclusion = (
            f"Decisão diferente no perfil `{profile_id}`: Julia escolheu `{julia_winner}` e Python escolheu "
            f"`{python_winner}`. Ranking_diff={ranking_difference_observed}; route_diff={route_metric_difference_observed}."
        )
    return {
        "julia_reason": julia_explanation.get("engineering_conclusion"),
        "python_reason": python_explanation.get("engineering_conclusion"),
        "summary": conclusion,
    }


def _build_candidate_rows_for_suite(
    scenario_results: dict[str, dict[str, dict[str, Any]]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for scenario_label, engines in scenario_results.items():
        for engine_name, result in engines.items():
            default_profile_id = str(result.get("default_profile_id") or "")
            explanations_by_profile = {
                profile_id: build_selected_candidate_explanation(result, profile_id=profile_id)
                for profile_id in result.get("ranked_profiles", {})
            }
            for profile_id, ranked_records in result.get("ranked_profiles", {}).items():
                explanation = explanations_by_profile.get(profile_id, {})
                runner_up_id = ((explanation.get("runner_up") or {}).get("candidate_id"))
                winner_id = ((explanation.get("winner") or {}).get("candidate_id"))
                for record in ranked_records:
                    rows.append(
                        {
                            "scenario": scenario_label,
                            "engine": engine_name,
                            "profile_id": profile_id,
                            "is_default_profile": profile_id == default_profile_id,
                            "candidate_id": record.get("candidate_id"),
                            "rank": int(record.get("rank", 0)),
                            "topology_family": record.get("topology_family"),
                            "feasible": bool(record.get("feasible")),
                            "infeasibility_reason": record.get("infeasibility_reason"),
                            "score_final": record.get("score_final"),
                            "install_cost": record.get("install_cost"),
                            "fallback_cost": record.get("fallback_cost"),
                            "total_cost": round(
                                float(record.get("install_cost", 0.0)) + float(record.get("fallback_cost", 0.0)),
                                3,
                            ),
                            "quality_score_raw": record.get("quality_score_raw"),
                            "flow_out_score": record.get("flow_out_score"),
                            "resilience_score": record.get("resilience_score"),
                            "cleaning_score": record.get("cleaning_score"),
                            "operability_score": record.get("operability_score"),
                            "fallback_component_count": record.get("fallback_component_count"),
                            "is_winner": record.get("candidate_id") == winner_id,
                            "is_runner_up": record.get("candidate_id") == runner_up_id,
                        }
                    )
    return rows
