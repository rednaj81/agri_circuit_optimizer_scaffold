from __future__ import annotations

from decision_platform.catalog.quality_rules import apply_quality_rules
from decision_platform.data_io.loader import load_scenario_bundle
from decision_platform.graph_generation.generator import generate_candidate_topologies
from decision_platform.graph_repair.repair import normalize_candidate
from decision_platform.julia_bridge.python_engine import emulate_watermodels_cli
from decision_platform.scenario_engine.installer import build_candidate_payload
from tests.decision_platform.scenario_utils import cleanup_scenario_copy, prepare_scenario_copy


def test_quality_rules_drive_breakdown_and_flags() -> None:
    scenario_dir = prepare_scenario_copy(
        "data/decision_platform/maquete_v2",
        "maquete_v2_quality_rules",
        scenario_overrides={"hydraulic_engine": {"primary": "python_emulated_julia", "fallback": "none"}},
    )
    try:
        bundle = load_scenario_bundle(scenario_dir)
        candidate = generate_candidate_topologies(bundle)[0]
        payload = build_candidate_payload(normalize_candidate(candidate, bundle), bundle)
        metrics = apply_quality_rules(emulate_watermodels_cli(payload, bundle), bundle)
        assert "quality_score_breakdown" in metrics
        assert "quality_flags" in metrics
        assert "rules_triggered" in metrics
        assert any(route["quality_score_breakdown"] for route in metrics["route_metrics"] if route["feasible"])
    finally:
        cleanup_scenario_copy(scenario_dir)


def test_installer_logs_component_selection_and_prefers_non_fallback_assets() -> None:
    bundle = load_scenario_bundle("data/decision_platform/maquete_v2")
    candidate = generate_candidate_topologies(bundle)[0]
    payload = build_candidate_payload(normalize_candidate(candidate, bundle), bundle)

    assert payload["selection_log"]
    pump_choices = [entry for entry in payload["selection_log"] if entry["category"] == "pump"]
    meter_choices = [entry for entry in payload["selection_log"] if entry["category"] == "meter"]
    assert pump_choices
    assert meter_choices
    assert all("fallback" not in entry["selected_component_id"] for entry in pump_choices)
    assert all("fallback" not in entry["selected_component_id"] for entry in meter_choices)
