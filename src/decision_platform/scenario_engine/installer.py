from __future__ import annotations

from collections import defaultdict
from math import ceil
from typing import Any

from decision_platform.data_io.loader import ScenarioBundle


def build_candidate_payload(candidate: dict[str, Any], bundle: ScenarioBundle) -> dict[str, Any]:
    component_groups = _index_components(bundle)
    demand_profile = _build_demand_profile(bundle)
    installed_links = {}
    usage_counter: defaultdict[str, int] = defaultdict(int)
    module_m = float(
        bundle.layout_constraints.loc[
            bundle.layout_constraints["key"] == "hose_module_m", "value"
        ].iloc[0]
    )
    selection_log = []
    for link_id in candidate["installed_link_ids"]:
        link = candidate["installed_links"][link_id]
        installed_components = []
        link_selection_log = []
        for category in link["required_categories"] + link["selected_optional_categories"]:
            chosen_components, chosen_log = _allocate_components_for_category(
                category=category,
                link=link,
                component_groups=component_groups,
                usage_counter=usage_counter,
                module_m=module_m,
                demand_profile=demand_profile,
            )
            installed_components.extend(chosen_components)
            if chosen_log:
                link_selection_log.extend(chosen_log)
        installed_links[link_id] = {
            **link,
            "installed_components": installed_components,
            "selection_log": link_selection_log,
        }
        selection_log.extend(link_selection_log)
    family_rules = bundle.topology_rules["families"][candidate["topology_family"]]
    fallback_components = {
        category: next(
            (component for component in component_groups.get(category, []) if bool(component["is_fallback"])),
            None,
        )
        for category in ["pump", "meter", "valve"]
    }
    return {
        "candidate_id": candidate["candidate_id"],
        "topology_family": candidate["topology_family"],
        "family_rules": family_rules,
        "installed_links": installed_links,
        "route_requirements": bundle.route_requirements.to_dict("records"),
        "global_preferences": bundle.topology_rules.get("global_preferences", {}),
        "fallback_components": fallback_components,
        "selection_log": selection_log,
    }


def _build_demand_profile(bundle: ScenarioBundle) -> dict[str, float]:
    routes = bundle.route_requirements
    measurement_routes = routes.loc[routes["measurement_required"]]
    return {
        "route_count": float(len(routes)),
        "max_flow": float(routes["q_min_delivered_lpm"].max()),
        "median_flow": float(routes["q_min_delivered_lpm"].median()),
        "measurement_max_flow": float(measurement_routes["q_min_delivered_lpm"].max()) if not measurement_routes.empty else 0.0,
        "measurement_min_flow": float(measurement_routes["q_min_delivered_lpm"].min()) if not measurement_routes.empty else 0.0,
        "measurement_avg_flow": float(measurement_routes["q_min_delivered_lpm"].mean()) if not measurement_routes.empty else 0.0,
    }


def _index_components(bundle: ScenarioBundle) -> dict[str, list[dict[str, Any]]]:
    groups: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
    for component in bundle.components.to_dict("records"):
        groups[component["category"]].append(component)
    for category in groups:
        groups[category] = sorted(
            groups[category],
            key=lambda item: (
                bool(item["is_fallback"]),
                float(item["cost"]),
                -float(item["quality_base_score"]),
                float(item["forward_loss_pct_when_on"]),
                float(item["cleaning_hold_up_l"]),
            ),
        )
    return dict(groups)


def _allocate_components_for_category(
    *,
    category: str,
    link: dict[str, Any],
    component_groups: dict[str, list[dict[str, Any]]],
    usage_counter: defaultdict[str, int],
    module_m: float,
    demand_profile: dict[str, float],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    if category == "hose":
        hose_component = component_groups["hose"][0]
        hose_count = max(1, int(ceil(float(link["length_m"]) / max(module_m, 1e-6))))
        return (
            [_copy_component(hose_component) for _ in range(hose_count)],
            [
                {
                    "link_id": link["link_id"],
                    "category": "hose",
                    "selected_component_id": hose_component["component_id"],
                    "reason": f"length={link['length_m']}m -> modules={hose_count}",
                }
            ],
        )

    candidates = component_groups.get(category, [])
    if not candidates:
        return [], []
    if category == "connector" and link["archetype"] not in {
        "tank_tap",
        "service_tap",
        "star_tap",
        "supply_tap",
        "outlet_tap",
    }:
        return [], []

    limit = 1
    if category == "pump":
        limit = max(1, int(link.get("max_series_pumps", 1)))
    if category == "meter":
        limit = max(1, int(link.get("max_reading_meters", 1)))

    selected = []
    selection_log = []
    available_candidates = [
        component
        for component in candidates
        if usage_counter[component["component_id"]] < int(component["available_qty"])
    ]
    if not available_candidates:
        available_candidates = [component for component in candidates if bool(component["is_fallback"])] or candidates[-1:]
    ranked_candidates = sorted(
        available_candidates,
        key=lambda item: _component_score(item, category, demand_profile),
        reverse=True,
    )

    for position in range(limit):
        if not ranked_candidates:
            break
        component = ranked_candidates[0] if position == 0 else _pick_additional_component(
            ranked_candidates,
            category,
            selected,
            demand_profile,
        )
        if component is None:
            break
        selected.append(_copy_component(component))
        usage_counter[component["component_id"]] += 1
        selection_log.append(
            {
                "link_id": link["link_id"],
                "category": category,
                "selected_component_id": component["component_id"],
                "reason": _component_reason(component, category, demand_profile),
            }
        )
        ranked_candidates = [
            item
            for item in ranked_candidates
            if usage_counter[item["component_id"]] < int(item["available_qty"])
        ]
        if category in {"meter", "connector", "valve", "check_valve"}:
            break
    return selected, selection_log


def _pick_additional_component(
    candidates: list[dict[str, Any]],
    category: str,
    selected: list[dict[str, Any]],
    demand_profile: dict[str, float],
) -> dict[str, Any] | None:
    if category != "pump":
        return None
    current_capacity = sum(float(component["hard_max_lpm"]) for component in selected)
    if current_capacity >= demand_profile["max_flow"]:
        return None
    for component in candidates:
        if component["component_id"] in {item["component_id"] for item in selected} and not bool(component["can_be_in_series"]):
            continue
        return component
    return None


def _component_score(component: dict[str, Any], category: str, demand_profile: dict[str, float]) -> tuple[float, ...]:
    fallback_penalty = -1000.0 if bool(component["is_fallback"]) else 0.0
    cost_penalty = -float(component["cost"])
    quality_bonus = float(component["quality_base_score"])
    cleaning_bonus = -float(component["cleaning_hold_up_l"]) * 10.0
    loss_bonus = -float(component["forward_loss_pct_when_on"])
    if category == "pump":
        coverage = min(float(component["hard_max_lpm"]), demand_profile["max_flow"])
        confidence = min(float(component["confidence_max_lpm"]), demand_profile["max_flow"])
        return (
            fallback_penalty,
            coverage,
            confidence,
            quality_bonus,
            loss_bonus,
            cleaning_bonus,
            cost_penalty,
        )
    if category == "meter":
        hard_fit = float(component["hard_min_lpm"]) <= demand_profile["measurement_avg_flow"] <= float(component["hard_max_lpm"])
        conf_fit = float(component["confidence_min_lpm"]) <= demand_profile["measurement_avg_flow"] <= float(component["confidence_max_lpm"])
        range_width = -(float(component["hard_max_lpm"]) - float(component["hard_min_lpm"]))
        return (
            fallback_penalty,
            100.0 if hard_fit else 0.0,
            100.0 if conf_fit else 0.0,
            quality_bonus,
            range_width,
            cleaning_bonus,
            cost_penalty,
        )
    return (
        fallback_penalty,
        quality_bonus,
        cleaning_bonus,
        loss_bonus,
        cost_penalty,
    )


def _component_reason(component: dict[str, Any], category: str, demand_profile: dict[str, float]) -> str:
    if category == "pump":
        return (
            f"pump hard_max={component['hard_max_lpm']} confidence_max={component['confidence_max_lpm']} "
            f"target_max_flow={demand_profile['max_flow']}"
        )
    if category == "meter":
        return (
            f"meter hard=[{component['hard_min_lpm']},{component['hard_max_lpm']}] "
            f"confidence=[{component['confidence_min_lpm']},{component['confidence_max_lpm']}] "
            f"target_avg_measurement_flow={round(demand_profile['measurement_avg_flow'], 3)}"
        )
    return f"selected by category ranking cost={component['cost']} quality={component['quality_base_score']}"


def _copy_component(component: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in component.items()}
