from __future__ import annotations

import random
from copy import deepcopy
from typing import Any

from decision_platform.data_io.loader import ScenarioBundle


def generate_candidate_topologies(bundle: ScenarioBundle) -> list[dict[str, Any]]:
    settings = bundle.scenario_settings.get("candidate_generation", {})
    population_size = min(int(settings.get("population_size", 24)), 20)
    random_seed = int(settings.get("random_seed", 42))
    enable_mutations = bool(settings.get("enable_mutations", True))
    enable_crossover = bool(settings.get("enable_crossover", True))
    rng = random.Random(random_seed)

    families = [
        family
        for family in bundle.scenario_settings.get("enabled_families", [])
        if bool(bundle.topology_rules.get("families", {}).get(family, {}).get("enabled", False))
    ]
    base_candidates = [_build_family_candidate(bundle, family, variant="base") for family in families]
    generated = list(base_candidates)
    if enable_mutations:
        for candidate in list(base_candidates):
            generated.extend(_mutate_candidate(candidate, bundle, rng))
    if enable_crossover and len(base_candidates) >= 2:
        generated.extend(_crossover_candidates(base_candidates, bundle, rng))

    deduped: dict[tuple[str, tuple[str, ...]], dict[str, Any]] = {}
    for candidate in generated:
        key = (candidate["topology_family"], tuple(sorted(candidate["installed_link_ids"])))
        deduped[key] = candidate
    ordered = sorted(
        deduped.values(),
        key=lambda item: (
            item["topology_family"],
            item["generation_source"],
            len(item["installed_link_ids"]),
            item["candidate_id"],
        ),
    )
    return ordered[:population_size]


def _build_family_candidate(bundle: ScenarioBundle, family: str, *, variant: str) -> dict[str, Any]:
    links = bundle.candidate_links.to_dict("records")
    family_links = [link for link in links if family in _decode_family_hint(link.get("family_hint", ""))]
    if family == "hybrid_free":
        family_links = links
    if family == "loop_ring":
        family_links = family_links + [
            link
            for link in links
            if "bus_with_pump_islands" in _decode_family_hint(link.get("family_hint", ""))
            and link not in family_links
        ]
    installed = {link["link_id"]: _decorate_link(link, bundle, family, variant) for link in family_links}
    return {
        "candidate_id": f"{family}__{variant}",
        "topology_family": family,
        "generation_source": f"family_{variant}",
        "installed_link_ids": sorted(installed),
        "installed_links": installed,
        "metadata": {"family": family, "variant": variant},
    }


def _mutate_candidate(candidate: dict[str, Any], bundle: ScenarioBundle, rng: random.Random) -> list[dict[str, Any]]:
    if candidate["topology_family"] == "star_manifolds":
        return []
    links = bundle.candidate_links.set_index("link_id").to_dict("index")
    optional_ids = [
        link_id
        for link_id, link in candidate["installed_links"].items()
        if link["archetype"] in {"upper_bypass_segment", "vertical_link", "loop_lower_chord", "loop_upper_chord"}
    ]
    suggestions = []
    for index in range(min(2, max(1, len(optional_ids)))):
        clone = deepcopy(candidate)
        clone["candidate_id"] = f"{candidate['candidate_id']}__mut{index + 1}"
        clone["generation_source"] = "mutation"
        if optional_ids:
            for link_id in rng.sample(optional_ids, min(len(optional_ids), 1 + index)):
                clone["installed_links"].pop(link_id, None)
        if candidate["topology_family"] == "hybrid_free":
            addable = [
                link_id
                for link_id in links
                if link_id not in clone["installed_links"]
                and links[link_id]["archetype"] in {"vertical_link", "upper_bypass_segment", "loop_lower_chord"}
            ]
            for link_id in rng.sample(addable, min(2, len(addable))):
                clone["installed_links"][link_id] = _decorate_link(
                    {"link_id": link_id, **links[link_id]},
                    bundle,
                    candidate["topology_family"],
                    "mutated",
                )
        clone["installed_link_ids"] = sorted(clone["installed_links"])
        suggestions.append(clone)
    return suggestions


def _crossover_candidates(base_candidates: list[dict[str, Any]], bundle: ScenarioBundle, rng: random.Random) -> list[dict[str, Any]]:
    results = []
    links = bundle.candidate_links.set_index("link_id").to_dict("index")
    for left, right in zip(base_candidates, base_candidates[1:]):
        merged_ids = sorted(set(left["installed_link_ids"]) | set(right["installed_link_ids"]))
        merged_family = "hybrid_free" if {left["topology_family"], right["topology_family"]} == {"star_manifolds", "bus_with_pump_islands"} else right["topology_family"]
        selected_ids = sorted(rng.sample(merged_ids, min(len(merged_ids), 14)))
        installed = {
            link_id: _decorate_link({"link_id": link_id, **links[link_id]}, bundle, merged_family, "crossover")
            for link_id in selected_ids
        }
        results.append(
            {
                "candidate_id": f"{left['topology_family']}__x__{right['topology_family']}",
                "topology_family": merged_family,
                "generation_source": "crossover",
                "installed_link_ids": sorted(installed),
                "installed_links": installed,
                "metadata": {"parents": [left["candidate_id"], right["candidate_id"]]},
            }
        )
    return results


def _decorate_link(link: dict[str, Any], bundle: ScenarioBundle, family: str, variant: str) -> dict[str, Any]:
    rules = bundle.edge_component_rules.set_index("archetype").to_dict("index")
    rule = rules[link["archetype"]]
    required_categories = _split_pipe(rule["required_categories"])
    optional_categories = _split_pipe(rule["optional_categories"])
    selected_optional: list[str] = []
    if family == "star_manifolds" and link["archetype"] == "star_trunk":
        selected_optional = ["pump", "meter", "connector"]
    elif family == "bus_with_pump_islands" and link["archetype"] == "pump_island_segment":
        selected_optional = ["pump", "meter"]
    elif family == "loop_ring" and link["archetype"] in {"pump_island_segment", "loop_lower_chord"}:
        selected_optional = ["pump", "meter", "connector"]
    elif family == "hybrid_free":
        if link["archetype"] in {"pump_island_segment", "star_trunk", "loop_lower_chord"}:
            selected_optional = ["pump", "meter", "connector"]
        elif link["archetype"] in {"vertical_link", "upper_bypass_segment"}:
            selected_optional = ["valve"]
    if variant in {"mutated", "crossover"} and "connector" not in selected_optional and "connector" in optional_categories:
        selected_optional.append("connector")
    return {
        **link,
        "required_categories": required_categories,
        "optional_categories": optional_categories,
        "selected_optional_categories": selected_optional,
        "max_series_pumps": int(rule["max_series_pumps"]),
        "max_reading_meters": int(rule["max_reading_meters"]),
    }


def _decode_family_hint(value: str) -> set[str]:
    raw = {item.strip() for item in str(value).replace('"', "").split(",") if item.strip()}
    mapping = {"star": "star_manifolds", "bus": "bus_with_pump_islands", "loop": "loop_ring", "hybrid": "hybrid_free"}
    return {mapping.get(item, item) for item in raw}


def _split_pipe(value: str) -> list[str]:
    return [item.strip() for item in str(value).split("|") if item.strip()]
