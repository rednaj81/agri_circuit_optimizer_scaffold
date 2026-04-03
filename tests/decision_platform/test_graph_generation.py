from __future__ import annotations

from decision_platform.data_io.loader import load_scenario_bundle
from decision_platform.graph_generation.generator import generate_candidate_topologies


def test_generator_creates_multiple_families_and_mutations() -> None:
    bundle = load_scenario_bundle("data/decision_platform/maquete_v2")
    candidates = generate_candidate_topologies(bundle)

    families = {candidate["topology_family"] for candidate in candidates}
    generation_sources = {candidate["generation_source"] for candidate in candidates}

    assert {"star_manifolds", "bus_with_pump_islands", "loop_ring", "hybrid_free"} <= families
    assert "mutation" in generation_sources
    assert "crossover" in generation_sources
    assert len(candidates) <= 20
