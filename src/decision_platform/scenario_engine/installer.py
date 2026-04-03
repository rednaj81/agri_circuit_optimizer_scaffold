from __future__ import annotations

from collections import defaultdict
from math import ceil
from typing import Any

from decision_platform.data_io.loader import ScenarioBundle


def build_candidate_payload(candidate: dict[str, Any], bundle: ScenarioBundle) -> dict[str, Any]:
    component_groups = _index_components(bundle)
    installed_links = {}
    usage_counter: defaultdict[str, int] = defaultdict(int)
    module_m = float(
        bundle.layout_constraints.loc[
            bundle.layout_constraints["key"] == "hose_module_m", "value"
        ].iloc[0]
    )
    for link_id in candidate["installed_link_ids"]:
        link = candidate["installed_links"][link_id]
        installed_components = []
        for category in link["required_categories"] + link["selected_optional_categories"]:
            installed_components.extend(
                _allocate_components_for_category(
                    category=category,
                    link=link,
                    component_groups=component_groups,
                    usage_counter=usage_counter,
                    module_m=module_m,
                )
            )
        installed_links[link_id] = {**link, "installed_components": installed_components}
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
) -> list[dict[str, Any]]:
    if category == "hose":
        hose_component = component_groups["hose"][0]
        hose_count = max(1, int(ceil(float(link["length_m"]) / max(module_m, 1e-6))))
        return [_copy_component(hose_component) for _ in range(hose_count)]

    candidates = component_groups.get(category, [])
    if not candidates:
        return []
    if category == "connector" and link["archetype"] not in {
        "tank_tap",
        "service_tap",
        "star_tap",
        "supply_tap",
        "outlet_tap",
    }:
        return []

    limit = 1
    if category == "pump":
        limit = min(1, int(link.get("max_series_pumps", 1))) or 1
    if category == "meter":
        limit = min(1, int(link.get("max_reading_meters", 1))) or 1

    selected = []
    for _ in range(limit):
        component = _pick_component(candidates, usage_counter)
        selected.append(_copy_component(component))
        usage_counter[component["component_id"]] += 1
    return selected


def _pick_component(candidates: list[dict[str, Any]], usage_counter: defaultdict[str, int]) -> dict[str, Any]:
    for component in candidates:
        if usage_counter[component["component_id"]] < int(component["available_qty"]):
            return component
    fallback_candidates = [component for component in candidates if bool(component["is_fallback"])]
    return fallback_candidates[0] if fallback_candidates else candidates[-1]


def _copy_component(component: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in component.items()}
