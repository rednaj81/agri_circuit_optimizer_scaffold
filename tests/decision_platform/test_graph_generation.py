from __future__ import annotations

from decision_platform.data_io.loader import load_scenario_bundle
from decision_platform.graph_generation.generator import generate_candidate_topologies, generate_candidate_topology_bundle


def test_generator_creates_multiple_families_and_mutations() -> None:
    bundle = load_scenario_bundle("data/decision_platform/maquete_v2")
    candidates = generate_candidate_topologies(bundle)

    families = {candidate["topology_family"] for candidate in candidates}
    generation_sources = {candidate["generation_source"] for candidate in candidates}

    assert {"star_manifolds", "bus_with_pump_islands", "loop_ring", "hybrid_free"} <= families
    assert "mutation" in generation_sources
    assert "crossover" in generation_sources
    assert len(candidates) > 20
    assert len(candidates) <= int(bundle.scenario_settings["candidate_generation"]["population_size"])
    assert any(candidate["metadata"]["lineage_label"].startswith("mutation(") for candidate in candidates if candidate["generation_source"] == "mutation")
    assert all("origin_family" in candidate["metadata"] for candidate in candidates)


def test_generator_report_exposes_discard_and_return_counts() -> None:
    bundle = load_scenario_bundle("data/decision_platform/maquete_v2")
    generated = generate_candidate_topology_bundle(bundle)

    report = generated["report"]
    assert report["generated_candidate_count"] >= report["returned_candidate_count"] >= 1
    assert report["generated_by_family"]
    assert report["returned_by_family"]
    assert "duplicate_signature" in report["discarded_by_reason"]
    assert "population_cap_pruned" in report["discarded_by_reason"]
