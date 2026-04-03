from __future__ import annotations

from decision_platform.data_io.loader import load_scenario_bundle
from decision_platform.graph_generation.generator import generate_candidate_topologies
from decision_platform.graph_repair.repair import normalize_candidate
from decision_platform.julia_bridge import bridge
from decision_platform.julia_bridge.bridge import JuliaBridgeError, evaluate_candidate_via_bridge
from decision_platform.scenario_engine.installer import build_candidate_payload
from tests.decision_platform.scenario_utils import cleanup_scenario_copy, prepare_scenario_copy


def test_bridge_fails_closed_when_fallback_is_none(monkeypatch) -> None:
    bundle = load_scenario_bundle("data/decision_platform/maquete_v2")
    candidate = generate_candidate_topologies(bundle)[0]
    payload = build_candidate_payload(normalize_candidate(candidate, bundle), bundle)
    monkeypatch.setattr(bridge, "julia_available", lambda: False)
    monkeypatch.setattr(bridge, "watermodels_available", lambda project_dir=None: False)

    try:
        evaluate_candidate_via_bridge(payload, bundle)
        raise AssertionError("Expected fail-closed JuliaBridgeError.")
    except JuliaBridgeError as exc:
        assert "fallback 'none'" in str(exc)


def test_bridge_falls_back_when_python_emulation_is_allowed() -> None:
    scenario_dir = prepare_scenario_copy(
        "data/decision_platform/maquete_v2",
        "maquete_v2_bridge_fallback",
        scenario_overrides={"hydraulic_engine": {"fallback": "python_emulated_julia"}},
    )
    try:
        bundle = load_scenario_bundle(scenario_dir)
        candidate = generate_candidate_topologies(bundle)[0]
        payload = build_candidate_payload(normalize_candidate(candidate, bundle), bundle)
        metrics = evaluate_candidate_via_bridge(payload, bundle)
        assert metrics["engine_requested"] == "watermodels_jl"
        assert metrics["engine_used"] == "python_emulated_julia"
        assert metrics["engine_mode"] == "fallback_emulated"
    finally:
        cleanup_scenario_copy(scenario_dir)


def test_bridge_uses_real_julia_when_available(monkeypatch) -> None:
    scenario_dir = prepare_scenario_copy(
        "data/decision_platform/maquete_v2",
        "maquete_v2_bridge_real_mock",
        scenario_overrides={"hydraulic_engine": {"fallback": "none"}},
    )
    try:
        bundle = load_scenario_bundle(scenario_dir)
        candidate = generate_candidate_topologies(bundle)[0]
        payload = build_candidate_payload(normalize_candidate(candidate, bundle), bundle)
        monkeypatch.setattr(bridge, "julia_available", lambda: True)
        monkeypatch.setattr(bridge, "watermodels_available", lambda project_dir=None: True)
        monkeypatch.setattr(
            bridge,
            "_call_real_julia",
            lambda payload: {
                "engine": "julia_cli",
                "feasible": True,
                "mandatory_unserved": [],
                "install_cost": 1.0,
                "fallback_cost": 0.0,
                "quality_score_raw": 10.0,
                "flow_out_score": 20.0,
                "resilience_score": 30.0,
                "cleaning_score": 40.0,
                "operability_score": 50.0,
                "maintenance_score": 60.0,
                "alternate_path_count_critical": 0,
                "fallback_component_count": 0,
                "bom_summary": {"components": [], "total_components": 0},
                "route_metrics": [],
            },
        )
        metrics = evaluate_candidate_via_bridge(payload, bundle)
        assert metrics["engine_used"] == "watermodels_jl"
        assert metrics["engine_mode"] == "real_julia"
        assert metrics["julia_available"] is True
        assert metrics["watermodels_available"] is True
    finally:
        cleanup_scenario_copy(scenario_dir)


def test_bridge_detects_real_julia_runtime_when_available() -> None:
    assert bridge.find_julia_executable()
    assert bridge.julia_available() is True
    assert bridge.watermodels_available() is True
