from __future__ import annotations

import random
from collections import Counter, defaultdict
from copy import deepcopy
from typing import Any

from decision_platform.data_io.loader import ScenarioBundle


def generate_candidate_topologies(bundle: ScenarioBundle) -> list[dict[str, Any]]:
    return generate_candidate_topology_bundle(bundle)["candidates"]


def generate_candidate_topology_bundle(bundle: ScenarioBundle) -> dict[str, Any]:
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
    report = _initialize_generation_report(
        families=families,
        population_size=population_size,
        generations=generations,
        keep_top_n_per_family=keep_top_n_per_family,
        random_seed=random_seed,
        enable_mutations=enable_mutations,
        enable_crossover=enable_crossover,
        allow_family_hopping=allow_family_hopping,
    )

    base_candidates = [_build_family_candidate(bundle, family, variant="base") for family in families]
    for candidate in base_candidates:
        _record_generated_candidate(report, candidate, generation_idx=0)
    candidate_pool = list(base_candidates)
    frontier = list(base_candidates)

    for generation_idx in range(1, generations + 1):
        next_frontier = []
        if enable_mutations:
            for candidate in frontier:
                mutations = _mutate_candidate(candidate, bundle, rng, generation_idx)
                next_frontier.extend(mutations)
                for mutation in mutations:
                    _record_generated_candidate(report, mutation, generation_idx=generation_idx)
        if enable_crossover and len(frontier) >= 2:
            crossovers = _crossover_candidates(frontier, bundle, rng, generation_idx, allow_family_hopping)
            next_frontier.extend(crossovers)
            for crossover in crossovers:
                _record_generated_candidate(report, crossover, generation_idx=generation_idx)
        if not next_frontier:
            report["generation_history"].append(
                {
                    "generation": generation_idx,
                    "raw_generated_count": 0,
                    "kept_count": 0,
                    "kept_by_family": {},
                    "discarded_by_reason": {},
                }
            )
            break
        pruned_frontier, frontier_stats = _prune_generation_frontier(next_frontier, keep_top_n_per_family)
        candidate_pool.extend(pruned_frontier)
        frontier = pruned_frontier
        report["generation_history"].append(
            {
                "generation": generation_idx,
                "raw_generated_count": len(next_frontier),
                "kept_count": len(pruned_frontier),
                "kept_by_family": frontier_stats["kept_by_family"],
                "discarded_by_reason": frontier_stats["discarded_by_reason"],
            }
        )
        _merge_counter(report["discarded_by_reason"], frontier_stats["discarded_by_reason"])

    deduped, dedupe_stats = _dedupe_candidates(candidate_pool)
    _merge_counter(report["discarded_by_reason"], dedupe_stats["discarded_by_reason"])

    per_family: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for candidate in deduped:
        per_family[candidate["topology_family"]].append(candidate)
    for family, family_candidates in per_family.items():
        selected, selection_stats = _select_diverse_candidates(family_candidates, keep_top_n_per_family)
        per_family[family] = selected
        _merge_counter(report["discarded_by_reason"], selection_stats["discarded_by_reason"])

    selected_pool_by_family = {family: list(candidates) for family, candidates in per_family.items()}
    round_robin, round_robin_stats = _round_robin_population(per_family, population_size)
    _merge_counter(report["discarded_by_reason"], round_robin_stats["discarded_by_reason"])

    finalized = _assign_unique_candidate_ids(round_robin)
    report["returned_candidate_count"] = len(finalized)
    report["returned_by_family"] = dict(Counter(candidate["topology_family"] for candidate in finalized))
    report["returned_by_source"] = dict(Counter(candidate["generation_source"] for candidate in finalized))
    report["distinct_structures_by_family"] = {
        family: len({tuple(sorted(candidate["installed_link_ids"])) for candidate in candidates})
        for family, candidates in selected_pool_by_family.items()
    }
    return {"candidates": finalized, "report": report}


def _initialize_generation_report(
    *,
    families: list[str],
    population_size: int,
    generations: int,
    keep_top_n_per_family: int,
    random_seed: int,
    enable_mutations: bool,
    enable_crossover: bool,
    allow_family_hopping: bool,
) -> dict[str, Any]:
    return {
        "settings": {
            "population_size": population_size,
            "generations": generations,
            "keep_top_n_per_family": keep_top_n_per_family,
            "random_seed": random_seed,
            "enable_mutations": enable_mutations,
            "enable_crossover": enable_crossover,
            "allow_family_hopping": allow_family_hopping,
        },
        "enabled_families": list(families),
        "generated_candidate_count": 0,
        "generated_by_family": {},
        "generated_by_source": {},
        "returned_candidate_count": 0,
        "returned_by_family": {},
        "returned_by_source": {},
        "distinct_structures_by_family": {},
        "discarded_by_reason": {},
        "generation_history": [],
    }


def _record_generated_candidate(report: dict[str, Any], candidate: dict[str, Any], *, generation_idx: int) -> None:
    report["generated_candidate_count"] += 1
    family = candidate["topology_family"]
    source = candidate["generation_source"]
    report["generated_by_family"][family] = report["generated_by_family"].get(family, 0) + 1
    report["generated_by_source"][source] = report["generated_by_source"].get(source, 0) + 1
    candidate.setdefault("metadata", {})
    candidate["metadata"]["generation"] = generation_idx


def _dedupe_candidates(candidates: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    deduped: dict[tuple[str, tuple[str, ...]], dict[str, Any]] = {}
    discarded = 0
    for candidate in candidates:
        key = (candidate["topology_family"], tuple(sorted(candidate["installed_link_ids"])))
        if key in deduped:
            discarded += 1
            current = deduped[key]
            current_score = _candidate_structural_score(current)
            new_score = _candidate_structural_score(candidate)
            if new_score > current_score:
                deduped[key] = candidate
            continue
        deduped[key] = candidate
    return list(deduped.values()), {"discarded_by_reason": {"duplicate_signature": discarded}}


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
        "generation_source": "base",
        "installed_link_ids": sorted(installed),
        "installed_links": installed,
        "metadata": {
            "family": family,
            "variant": variant,
            "generation": 0,
            "repaired": False,
            "repair_actions": [],
            "root_id": family,
            "origin_family": family,
            "lineage_label": "base",
        },
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
        removed_link_ids: list[str] = []
        added_link_ids: list[str] = []
        if mutable_ids:
            remove_count = min(len(mutable_ids), 1 + (mutation_idx % 2))
            removed_link_ids = sorted(rng.sample(mutable_ids, remove_count))
            for link_id in removed_link_ids:
                clone["installed_links"].pop(link_id, None)
        if addable_ids:
            add_count = min(len(addable_ids), 1 + ((generation_idx + mutation_idx) % 3))
            added_link_ids = sorted(rng.sample(addable_ids, add_count))
            for link_id in added_link_ids:
                clone["installed_links"][link_id] = _decorate_link(
                    {"link_id": link_id, **links[link_id]},
                    bundle,
                    candidate["topology_family"],
                    "mutated",
                )
        clone["installed_link_ids"] = sorted(clone["installed_links"])
        clone["metadata"] = {
            **clone.get("metadata", {}),
            "generation": generation_idx,
            "mutation_index": mutation_idx + 1,
            "repaired": False,
            "repair_actions": [],
            "root_id": clone.get("metadata", {}).get("root_id", clone["topology_family"]),
            "origin_family": candidate["topology_family"],
            "parent_id": candidate["candidate_id"],
            "removed_link_ids": removed_link_ids,
            "added_link_ids": added_link_ids,
            "lineage_label": f"mutation(g{generation_idx},-{len(removed_link_ids)},+{len(added_link_ids)})",
        }
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
        merged_family = "hybrid_free" if allow_family_hopping else left["topology_family"]
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
                    "parent_families": [left["topology_family"], right["topology_family"]],
                    "generation": generation_idx,
                    "repaired": False,
                    "repair_actions": [],
                    "root_id": merged_family,
                    "origin_family": left["topology_family"],
                    "lineage_label": f"crossover(g{generation_idx})",
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
    signature = _candidate_signature(candidate)
    family_bonus = {
        "star_manifolds": 1.0,
        "bus_with_pump_islands": 1.2,
        "loop_ring": 1.1,
        "hybrid_free": 1.3,
    }.get(candidate["topology_family"], 1.0)
    generation_source_bonus = {"base": 1.0, "mutation": 1.1, "crossover": 1.25}.get(candidate["generation_source"], 1.0)
    return (
        family_bonus,
        generation_source_bonus,
        len(signature["archetypes"]),
        optional_count,
        -link_count,
        -candidate.get("metadata", {}).get("generation", 0),
    )


def _prune_generation_frontier(
    candidates: list[dict[str, Any]],
    keep_top_n_per_family: int,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    deduped: dict[tuple[str, tuple[str, ...]], dict[str, Any]] = {}
    duplicate_count = 0
    for candidate in candidates:
        key = (candidate["topology_family"], tuple(sorted(candidate["installed_link_ids"])))
        if key in deduped:
            duplicate_count += 1
            if _candidate_structural_score(candidate) > _candidate_structural_score(deduped[key]):
                deduped[key] = candidate
            continue
        deduped[key] = candidate

    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for candidate in deduped.values():
        grouped[candidate["topology_family"]].append(candidate)
    pruned = []
    kept_by_family: dict[str, int] = {}
    family_cap_pruned = 0
    for family, family_candidates in grouped.items():
        selected, selection_stats = _select_diverse_candidates(
            family_candidates,
            max(1, min(keep_top_n_per_family, 6)),
        )
        kept_by_family[family] = len(selected)
        family_cap_pruned += selection_stats["discarded_by_reason"].get("family_cap_pruned", 0)
        pruned.extend(selected)

    return pruned, {
        "kept_by_family": kept_by_family,
        "discarded_by_reason": {
            "generation_duplicate_signature": duplicate_count,
            "family_cap_pruned": family_cap_pruned,
        },
    }


def _select_diverse_candidates(
    candidates: list[dict[str, Any]],
    limit: int,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    ranked = sorted(candidates, key=_candidate_structural_score, reverse=True)
    if len(ranked) <= limit:
        return ranked, {"discarded_by_reason": {"family_cap_pruned": 0}}

    selected: list[dict[str, Any]] = []
    remaining = list(ranked)
    while remaining and len(selected) < limit:
        if not selected:
            selected.append(remaining.pop(0))
            continue
        best_index = max(
            range(len(remaining)),
            key=lambda index: (
                _candidate_novelty_score(remaining[index], selected),
                _candidate_structural_score(remaining[index]),
            ),
        )
        selected.append(remaining.pop(best_index))
    return selected, {"discarded_by_reason": {"family_cap_pruned": max(0, len(ranked) - len(selected))}}


def _round_robin_population(
    per_family: dict[str, list[dict[str, Any]]],
    population_size: int,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    round_robin = []
    family_names = sorted(per_family)
    while len(round_robin) < population_size and any(per_family[family] for family in family_names):
        for family in family_names:
            if not per_family[family]:
                continue
            round_robin.append(per_family[family].pop(0))
            if len(round_robin) >= population_size:
                break
    remaining = sum(len(items) for items in per_family.values())
    return round_robin, {"discarded_by_reason": {"population_cap_pruned": max(0, remaining)}}


def _candidate_signature(candidate: dict[str, Any]) -> dict[str, Any]:
    installed_links = candidate["installed_links"].values()
    return {
        "link_ids": frozenset(candidate["installed_link_ids"]),
        "archetypes": tuple(sorted(link["archetype"] for link in installed_links)),
        "optional_categories": tuple(
            sorted(category for link in installed_links for category in link["selected_optional_categories"])
        ),
        "generation_source": candidate["generation_source"],
    }


def _candidate_novelty_score(candidate: dict[str, Any], selected: list[dict[str, Any]]) -> tuple[float, ...]:
    candidate_signature = _candidate_signature(candidate)
    link_distances = []
    optional_distances = []
    source_novelties = []
    for prior in selected:
        prior_signature = _candidate_signature(prior)
        union_links = candidate_signature["link_ids"] | prior_signature["link_ids"]
        link_distance = 0.0 if not union_links else len(candidate_signature["link_ids"] ^ prior_signature["link_ids"]) / len(union_links)
        link_distances.append(link_distance)
        union_optional = set(candidate_signature["optional_categories"]) | set(prior_signature["optional_categories"])
        optional_distance = 0.0 if not union_optional else len(set(candidate_signature["optional_categories"]) ^ set(prior_signature["optional_categories"])) / len(union_optional)
        optional_distances.append(optional_distance)
        source_novelties.append(float(candidate_signature["generation_source"] != prior_signature["generation_source"]))
    return (
        min(link_distances) if link_distances else 1.0,
        min(optional_distances) if optional_distances else 1.0,
        max(source_novelties) if source_novelties else 1.0,
        float(candidate.get("metadata", {}).get("generation", 0)),
    )


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


def _merge_counter(target: dict[str, int], updates: dict[str, int]) -> None:
    for key, value in updates.items():
        target[key] = target.get(key, 0) + int(value)


def _decode_family_hint(value: str) -> set[str]:
    raw = {item.strip() for item in str(value).replace('"', "").split(",") if item.strip()}
    mapping = {"star": "star_manifolds", "bus": "bus_with_pump_islands", "loop": "loop_ring", "hybrid": "hybrid_free"}
    return {mapping.get(item, item) for item in raw}


def _split_pipe(value: str) -> list[str]:
    return [item.strip() for item in str(value).split("|") if item.strip()]
