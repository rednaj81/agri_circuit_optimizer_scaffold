from __future__ import annotations

from decision_platform.data_io.loader import load_scenario_bundle
from decision_platform.graph_generation.generator import generate_candidate_topologies
from decision_platform.graph_repair.repair import normalize_candidate
from decision_platform.julia_bridge.bridge import evaluate_candidate_via_bridge, julia_available
from decision_platform.scenario_engine.installer import build_candidate_payload


def test_bridge_returns_metrics_even_without_local_julia() -> None:
    bundle = load_scenario_bundle("data/decision_platform/maquete_v2")
    candidate = generate_candidate_topologies(bundle)[0]
    payload = build_candidate_payload(normalize_candidate(candidate, bundle), bundle)
    metrics = evaluate_candidate_via_bridge(payload, bundle)

    assert "engine" in metrics
    assert "route_metrics" in metrics
    assert isinstance(julia_available(), bool)
    if not julia_available():
        assert metrics["engine"] == "python_emulated_julia"
