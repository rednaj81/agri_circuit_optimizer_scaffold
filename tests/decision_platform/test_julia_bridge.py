from __future__ import annotations

import pytest

from decision_platform.data_io.loader import load_scenario_bundle
from decision_platform.graph_generation.generator import generate_candidate_topologies
from decision_platform.graph_repair.repair import normalize_candidate
from decision_platform.julia_bridge import bridge
from decision_platform.julia_bridge.bridge import JuliaBridgeError, evaluate_candidate_via_bridge
from decision_platform.scenario_engine.installer import build_candidate_payload
from tests.decision_platform.scenario_utils import cleanup_scenario_copy, prepare_scenario_copy


@pytest.mark.fast
def test_bridge_fails_closed_when_fallback_is_none(monkeypatch) -> None:
    monkeypatch.delenv(bridge.DISABLE_REAL_JULIA_PROBE_ENV, raising=False)
    bridge.clear_runtime_probe_caches()
    bundle = load_scenario_bundle("data/decision_platform/maquete_v2")
    candidate = generate_candidate_topologies(bundle)[0]
    payload = build_candidate_payload(normalize_candidate(candidate, bundle), bundle)
    monkeypatch.setattr(bridge, "julia_available", lambda: False)
    monkeypatch.setattr(bridge, "watermodels_available", lambda project_dir=None: False)

    try:
        evaluate_candidate_via_bridge(payload, bundle)
        raise AssertionError("Expected fail-closed JuliaBridgeError.")
    except JuliaBridgeError as exc:
        assert "Official runtime requires" in str(exc)


@pytest.mark.fast
def test_bridge_falls_back_when_python_emulation_is_allowed(monkeypatch) -> None:
    monkeypatch.delenv(bridge.DISABLE_REAL_JULIA_PROBE_ENV, raising=False)
    bridge.clear_runtime_probe_caches()
    scenario_dir = prepare_scenario_copy(
        "data/decision_platform/maquete_v2",
        "maquete_v2_bridge_fallback",
        scenario_overrides={"hydraulic_engine": {"fallback": "python_emulated_julia"}},
    )
    try:
        bundle = load_scenario_bundle(scenario_dir)
        candidate = generate_candidate_topologies(bundle)[0]
        payload = build_candidate_payload(normalize_candidate(candidate, bundle), bundle)
        monkeypatch.setattr(bridge, "julia_available", lambda: False)
        monkeypatch.setattr(bridge, "watermodels_available", lambda project_dir=None: False)
        metrics = evaluate_candidate_via_bridge(payload, bundle)
        assert metrics["engine_requested"] == "watermodels_jl"
        assert metrics["engine_used"] == "python_emulated_julia"
        assert metrics["engine_mode"] == "fallback_emulated"
        assert "Diagnostic-only fallback" in str(metrics["engine_warning"])
        assert metrics["real_julia_probe_disabled"] is False
    finally:
        cleanup_scenario_copy(scenario_dir)


@pytest.mark.fast
def test_bridge_allows_explicit_python_primary_for_diagnostic_paths(monkeypatch) -> None:
    monkeypatch.delenv(bridge.DISABLE_REAL_JULIA_PROBE_ENV, raising=False)
    bridge.clear_runtime_probe_caches()
    scenario_dir = prepare_scenario_copy(
        "data/decision_platform/maquete_v2",
        "maquete_v2_bridge_python_primary",
        scenario_overrides={"hydraulic_engine": {"primary": "python_emulated_julia", "fallback": "none"}},
    )
    try:
        bundle = load_scenario_bundle(scenario_dir)
        candidate = generate_candidate_topologies(bundle)[0]
        payload = build_candidate_payload(normalize_candidate(candidate, bundle), bundle)
        monkeypatch.setattr(bridge, "julia_available", lambda: False)
        monkeypatch.setattr(bridge, "watermodels_available", lambda project_dir=None: False)
        metrics = evaluate_candidate_via_bridge(payload, bundle)
        assert metrics["engine_requested"] == "python_emulated_julia"
        assert metrics["engine_used"] == "python_emulated_julia"
        assert metrics["engine_mode"] == "python_fallback_primary"
        assert metrics["engine_warning"] is None
        assert metrics["real_julia_probe_disabled"] is False
    finally:
        cleanup_scenario_copy(scenario_dir)


@pytest.mark.fast
def test_bridge_can_disable_real_julia_probe_for_diagnostic_test_mode(monkeypatch) -> None:
    monkeypatch.setenv(bridge.DISABLE_REAL_JULIA_PROBE_ENV, "1")
    bridge.clear_runtime_probe_caches()

    try:
        assert bridge.find_julia_executable() is None
        assert bridge.julia_available() is False
        assert bridge.watermodels_available() is False
    finally:
        monkeypatch.delenv(bridge.DISABLE_REAL_JULIA_PROBE_ENV, raising=False)
        bridge.clear_runtime_probe_caches()


@pytest.mark.fast
def test_bridge_marks_override_when_diagnostic_probe_is_disabled(monkeypatch) -> None:
    scenario_dir = prepare_scenario_copy(
        "data/decision_platform/maquete_v2",
        "maquete_v2_bridge_probe_override",
        scenario_overrides={"hydraulic_engine": {"fallback": "python_emulated_julia"}},
    )
    try:
        bundle = load_scenario_bundle(scenario_dir)
        candidate = generate_candidate_topologies(bundle)[0]
        payload = build_candidate_payload(normalize_candidate(candidate, bundle), bundle)
        monkeypatch.setenv(bridge.DISABLE_REAL_JULIA_PROBE_ENV, "1")
        bridge.clear_runtime_probe_caches()
        metrics = evaluate_candidate_via_bridge(payload, bundle)
        assert metrics["engine_used"] == "python_emulated_julia"
        assert metrics["real_julia_probe_disabled"] is True
        assert metrics["real_julia_probe_disable_env"] == bridge.DISABLE_REAL_JULIA_PROBE_ENV
        assert "not valid for the official Julia-only gate" in str(metrics["engine_warning"])
    finally:
        monkeypatch.delenv(bridge.DISABLE_REAL_JULIA_PROBE_ENV, raising=False)
        bridge.clear_runtime_probe_caches()
        cleanup_scenario_copy(scenario_dir)


@pytest.mark.fast
def test_bridge_rejects_override_without_diagnostic_fallback(monkeypatch) -> None:
    bundle = load_scenario_bundle("data/decision_platform/maquete_v2")
    candidate = generate_candidate_topologies(bundle)[0]
    payload = build_candidate_payload(normalize_candidate(candidate, bundle), bundle)
    monkeypatch.setenv(bridge.DISABLE_REAL_JULIA_PROBE_ENV, "1")
    bridge.clear_runtime_probe_caches()

    try:
        with pytest.raises(JuliaBridgeError) as exc:
            evaluate_candidate_via_bridge(payload, bundle)
        assert bridge.DISABLE_REAL_JULIA_PROBE_ENV in str(exc.value)
        assert "not valid for the official Julia-only gate" in str(exc.value)
    finally:
        monkeypatch.delenv(bridge.DISABLE_REAL_JULIA_PROBE_ENV, raising=False)
        bridge.clear_runtime_probe_caches()


@pytest.mark.fast
def test_bridge_uses_real_julia_when_available(monkeypatch) -> None:
    monkeypatch.delenv(bridge.DISABLE_REAL_JULIA_PROBE_ENV, raising=False)
    bridge.clear_runtime_probe_caches()
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


@pytest.mark.requires_julia
@pytest.mark.slow
def test_bridge_detects_real_julia_runtime_when_available() -> None:
    assert bridge.find_julia_executable()
    assert bridge.julia_available() is True
    assert bridge.watermodels_available() is True
