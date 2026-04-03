from __future__ import annotations

import random
from copy import deepcopy
from typing import Any

from decision_platform.data_io.loader import ScenarioBundle


def generate_candidate_topologies(bundle: ScenarioBundle) -> list[dict[str, Any]]:
    settings = bundle.scenario_settings.get("candidate_generation", {})
    population_size = max(1, int(settings.get("population_size", 24)))
    generations = max(1, int(settings.get("generations", 8)))
    keep_top_n_per_family = max(1, int(settings.get("keep_top_n_per_family", 8)))
    random_seed = int(settings.get("random_seed", 42))
    enable_mutations = bool(settings.get("enable_mutations", True))
    enable_crossover = bool(settings.get("enable_crossover", True))
    allow_family_hopping = bool(settings.get("allow_family_hopping", True))
    rng = random.Random(random_seed)

    families = [
        family
        for family in bundle.scenario_settings.get("enabled_families", [])
        if bool(bundle.topology_rules.get("families", {}).get(family, {}).get("enabled", False))
    ]
    base_candidates = [_build_family_candidate(bundle, family, variant="base") for family in families]
    candidate_pool = list(base_candidates)
    frontier = list(base_candidates)

    for generation_idx in range(1, generations + 1):
        next_frontier = []
        if enable_mutations:
            for candidate in frontier:
                next_frontier.extend(_mutate_candidate(candidate, bundle, rng, generation_idx))
        if enable_crossover and len(frontier) >= 2:
            next_frontier.extend(
                _crossover_candidates(frontier, bundle, rng, generation_idx, allow_family_hopping)
            )
        if not next_frontier:
            break
        pruned_frontier = _prune_generation_frontier(next_frontier, keep_top_n_per_family)
        candidate_pool.extend(pruned_frontier)
        frontier = pruned_frontier

    deduped: dict[tuple[str, tuple[str, ...]], dict[str, Any]] = {}
    for candidate in candidate_pool:
        key = (candidate["topology_family"], tuple(sorted(candidate["installed_link_ids"])))
        deduped[key] = candidate

    per_family: dict[str, list[dict[str, Any]]] = {}
    for candidate in deduped.values():
        per_family.setdefault(candidate["topology_family"], []).append(candidate)
    for family in per_family:
        per_family[family] = sorted(
            per_family[family],
            key=_candidate_structural_score,
            reverse=True,
        )[:keep_top_n_per_family]

    round_robin = []
    family_names = sorted(per_family)
    while len(round_robin) < population_size and any(per_family[family] for family in family_names):
        for family in family_names:
            if not per_family[family]:
                continue
            round_robin.append(per_family[family].pop(0))
            if len(round_robin) >= population_size:
                break
    return _assign_unique_candidate_ids(round_robin)


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
        "metadata": {"family": family, "variant": variant, "generation": 0, "repaired": False, "root_id": f"{family}"},
    }


def _mutate_candidate(
    candidate: dict[str, Any],
    bundle: ScenarioBundle,
    rng: random.Random,
    generation_idx: int,
) -> list[dict[str, Any]]:
    links = bundle.candidate_links.set_index("link_id").to_dict("index")
    mutable_ids = [
        link_id
        for link_id, link in candidate["installed_links"].items()
        if link["archetype"] in {"upper_bypass_segment", "vertical_link", "loop_lower_chord", "loop_upper_chord", "bus_segment"}
    ]
    addable_ids = [
        link_id
        for link_id, link in links.items()
        if link_id not in candidate["installed_links"]
        and candidate["topology_family"] in _decode_family_hint(link.get("family_hint", ""))
    ]
    mutation_count = min(3, max(1, len(mutable_ids) // 2 + 1))
    results = []
    for mutation_idx in range(mutation_count):
        clone = deepcopy(candidate)
        clone["candidate_id"] = f"{candidate['topology_family']}__g{generation_idx}m{mutation_idx + 1}_{mutation_idx + 1}"
        clone["generation_source"] = "mutation"
        clone["metadata"] = {
            **clone.get("metadata", {}),
            "generation": generation_idx,
            "mutation_index": mutation_idx + 1,
            "repaired": False,
            "root_id": clone.get("metadata", {}).get("root_id", clone["topology_family"]),
        }
        if mutable_ids:
            remove_count = min(len(mutable_ids), 1 + (mutation_idx % 2))
            for link_id in rng.sample(mutable_ids, remove_count):
                clone["installed_links"].pop(link_id, None)
        if addable_ids:
            add_count = min(len(addable_ids), 1 + ((generation_idx + mutation_idx) % 3))
            for link_id in rng.sample(addable_ids, add_count):
                clone["installed_links"][link_id] = _decorate_link(
                    {"link_id": link_id, **links[link_id]},
                    bundle,
                    candidate["topology_family"],
                    "mutated",
                )
        clone["installed_link_ids"] = sorted(clone["installed_links"])
        results.append(clone)
    return results


def _crossover_candidates(
    frontier: list[dict[str, Any]],
    bundle: ScenarioBundle,
    rng: random.Random,
    generation_idx: int,
    allow_family_hopping: bool,
) -> list[dict[str, Any]]:
    results = []
    links = bundle.candidate_links.set_index("link_id").to_dict("index")
    for left, right in zip(frontier, frontier[1:]):
        merged_ids = sorted(set(left["installed_link_ids"]) | set(right["installed_link_ids"]))
        if not merged_ids:
            continue
        if allow_family_hopping:
            merged_family = "hybrid_free"
        else:
            merged_family = left["topology_family"]
        keep_count = min(len(merged_ids), max(6, int(len(merged_ids) * 0.75)))
        selected_ids = sorted(rng.sample(merged_ids, keep_count))
        installed = {
            link_id: _decorate_link({"link_id": link_id, **links[link_id]}, bundle, merged_family, "crossover")
            for link_id in selected_ids
        }
        results.append(
            {
                "candidate_id": f"{merged_family}__xg{generation_idx}_{len(results) + 1}",
                "topology_family": merged_family,
                "generation_source": "crossover",
                "installed_link_ids": sorted(installed),
                "installed_links": installed,
                "metadata": {
                    "parents": [left["candidate_id"], right["candidate_id"]],
                    "generation": generation_idx,
                    "repaired": False,
                    "root_id": merged_family,
                },
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
        selected_optional = ["pump", "meter", "connector"]
    elif family == "loop_ring" and link["archetype"] in {"pump_island_segment", "loop_lower_chord"}:
        selected_optional = ["pump", "meter", "connector"]
    elif family == "hybrid_free":
        if link["archetype"] in {"pump_island_segment", "star_trunk", "loop_lower_chord"}:
            selected_optional = ["pump", "meter", "connector"]
        elif link["archetype"] in {"vertical_link", "upper_bypass_segment", "loop_upper_chord"}:
            selected_optional = ["valve", "connector"]
    if variant in {"mutated", "crossover"}:
        for optional_category in ["connector", "valve"]:
            if optional_category in optional_categories and optional_category not in selected_optional:
                selected_optional.append(optional_category)
    return {
        **link,
        "required_categories": required_categories,
        "optional_categories": optional_categories,
        "selected_optional_categories": selected_optional,
        "max_series_pumps": int(rule["max_series_pumps"]),
        "max_reading_meters": int(rule["max_reading_meters"]),
    }


def _candidate_structural_score(candidate: dict[str, Any]) -> tuple[float, ...]:
    link_count = len(candidate["installed_link_ids"])
    optional_count = sum(len(link["selected_optional_categories"]) for link in candidate["installed_links"].values())
    family_bonus = {
        "star_manifolds": 1.0,
        "bus_with_pump_islands": 1.2,
        "loop_ring": 1.1,
        "hybrid_free": 1.3,
    }.get(candidate["topology_family"], 1.0)
    return (
        family_bonus,
        1.5 if candidate["generation_source"] == "crossover" else 1.0,
        optional_count,
        -link_count,
        -candidate.get("metadata", {}).get("generation", 0),
    )


def _prune_generation_frontier(candidates: list[dict[str, Any]], keep_top_n_per_family: int) -> list[dict[str, Any]]:
    deduped: dict[tuple[str, tuple[str, ...]], dict[str, Any]] = {}
    for candidate in candidates:
        key = (candidate["topology_family"], tuple(sorted(candidate["installed_link_ids"])))
        deduped[key] = candidate
    per_family: dict[str, list[dict[str, Any]]] = {}
    for candidate in deduped.values():
        per_family.setdefault(candidate["topology_family"], []).append(candidate)
    pruned = []
    for family, family_candidates in per_family.items():
        ranked = sorted(family_candidates, key=_candidate_structural_score, reverse=True)
        crossovers = [candidate for candidate in ranked if candidate["generation_source"] == "crossover"][:1]
        non_crossovers = [candidate for candidate in ranked if candidate["generation_source"] != "crossover"][
            : max(1, min(keep_top_n_per_family, 6) - len(crossovers))
        ]
        pruned.extend(crossovers + non_crossovers)
    return pruned


def _assign_unique_candidate_ids(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: dict[str, int] = {}
    finalized = []
    for candidate in candidates:
        clone = deepcopy(candidate)
        base_id = candidate["candidate_id"]
        seen[base_id] = seen.get(base_id, 0) + 1
        if seen[base_id] > 1:
            clone["candidate_id"] = f"{base_id}_{seen[base_id]}"
        finalized.append(clone)
    return finalized


def _decode_family_hint(value: str) -> set[str]:
    raw = {item.strip() for item in str(value).replace('"', "").split(",") if item.strip()}
    mapping = {"star": "star_manifolds", "bus": "bus_with_pump_islands", "loop": "loop_ring", "hybrid": "hybrid_free"}
    return {mapping.get(item, item) for item in raw}


def _split_pipe(value: str) -> list[str]:
    return [item.strip() for item in str(value).split("|") if item.strip()]
