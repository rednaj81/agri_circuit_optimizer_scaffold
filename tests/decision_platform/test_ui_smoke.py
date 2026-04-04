from __future__ import annotations

import shutil
from pathlib import Path

import pytest
import yaml

from decision_platform.api.run_pipeline import OfficialRuntimeConfigError
from decision_platform.data_io.loader import load_scenario_bundle
from decision_platform.ui_dash._compat import DASH_AVAILABLE
from decision_platform.ui_dash.app import (
    build_app,
    build_candidate_detail,
    build_comparison_records,
    build_official_candidate_summary,
    build_catalog_view_state,
    filter_catalog_records,
    rerank_catalog,
    save_and_reopen_local_bundle,
)
from tests.decision_platform.scenario_utils import cleanup_scenario_copy, diagnostic_runtime_test_mode, prepare_scenario_copy

pytestmark = [pytest.mark.requires_dash, pytest.mark.ui]


def test_dash_app_builds_layout_and_callbacks_even_when_fail_closed() -> None:
    with diagnostic_runtime_test_mode():
        app = build_app("data/decision_platform/maquete_v2")

    assert hasattr(app, "layout")
    assert app.layout is not None
    callback_count = len(getattr(app, "callbacks", [])) or len(getattr(app, "callback_map", {}))
    assert callback_count >= 4


def test_real_dash_stack_is_available() -> None:
    assert DASH_AVAILABLE is True


def test_dash_app_exposes_authoring_save_reopen_controls() -> None:
    with diagnostic_runtime_test_mode():
        app = build_app("data/decision_platform/maquete_v2")

    layout_repr = repr(app.layout)
    assert "save-reopen-bundle-button" in layout_repr
    assert "candidate-links-grid" in layout_repr
    assert "edge-component-rules-grid" in layout_repr
    assert "layout-constraints-grid" in layout_repr
    assert "topology-rules-editor" in layout_repr
    assert "scenario-settings-editor" in layout_repr
    assert "bundle-output-dir-input" in layout_repr


@pytest.mark.slow
def test_dash_app_uses_pipeline_result_when_fallback_is_allowed(maquete_v2_fallback_runtime: dict[str, object]) -> None:
    scenario_dir = maquete_v2_fallback_runtime["scenario_dir"]
    result = maquete_v2_fallback_runtime["result"]
    with diagnostic_runtime_test_mode():
        app = build_app(scenario_dir)
    assert hasattr(app, "layout")
    assert app.layout is not None
    detail = build_candidate_detail(result, result["selected_candidate_id"])
    assert "breakdown" in detail
    assert detail["summary"]["candidate_id"] == result["selected_candidate_id"]
    assert detail["route_rows"]


@pytest.mark.slow
def test_ui_view_state_uses_official_selected_candidate_instead_of_catalog_first(
    maquete_v2_fallback_runtime: dict[str, object],
) -> None:
    result = maquete_v2_fallback_runtime["result"]
    manipulated = {**result, "catalog": list(reversed(result["catalog"]))}
    view_state = build_catalog_view_state(
        manipulated,
        profile_id=manipulated["default_profile_id"],
    )
    detail = build_candidate_detail(result, view_state["selected_candidate_id"])
    assert view_state["selected_candidate_id"] == result["selected_candidate_id"]
    assert view_state["selected_candidate_id"] != manipulated["catalog"][0]["candidate_id"]
    assert detail["cytoscape_elements"] == result["selected_candidate"]["render"]["cytoscape_elements"]
    assert detail["summary"]["generation_source"] == result["selected_candidate"]["generation_source"]


@pytest.mark.slow
def test_ui_save_reopen_flow_persists_bundle_and_refreshes_pipeline() -> None:
    scenario_dir = prepare_scenario_copy(
        "data/decision_platform/maquete_v2",
        "maquete_v2_ui_save_reopen_source",
        scenario_overrides={"hydraulic_engine": {"fallback": "python_emulated_julia"}},
    )
    output_dir = Path("tests/_tmp/maquete_v2_ui_save_reopen_saved")
    if output_dir.exists():
        shutil.rmtree(output_dir)
    try:
        bundle = load_scenario_bundle(scenario_dir)
        nodes_rows = bundle.nodes.to_dict("records")
        components_rows = bundle.components.to_dict("records")
        candidate_links_rows = bundle.candidate_links.to_dict("records")
        edge_component_rules_rows = bundle.edge_component_rules.to_dict("records")
        route_rows = bundle.route_requirements.to_dict("records")
        layout_constraints_rows = bundle.layout_constraints.to_dict("records")
        nodes_rows[0]["label"] = "W salvo na UI"
        components_rows[0]["cost"] = 321.0
        candidate_links_rows[0]["notes"] = "Tap salvo na UI"
        edge_component_rules_rows[0]["max_series_pumps"] = 1
        route_rows[0]["weight"] = 55.0
        layout_constraints_rows[0]["value"] = 1.5
        topology_rules = {
            **bundle.topology_rules,
            "families": {
                **bundle.topology_rules["families"],
                "hybrid_free": {
                    **bundle.topology_rules["families"]["hybrid_free"],
                    "max_active_pumps_per_route": 3,
                },
            },
        }
        scenario_settings = bundle.scenario_settings | {
            "ui": {
                **bundle.scenario_settings.get("ui", {}),
                "default_layout_mode": "save_reopen_ui",
            }
        }

        with diagnostic_runtime_test_mode():
            saved = save_and_reopen_local_bundle(
                current_scenario_dir=scenario_dir,
                output_dir=output_dir,
                nodes_rows=nodes_rows,
                components_rows=components_rows,
                candidate_links_rows=candidate_links_rows,
                edge_component_rules_rows=edge_component_rules_rows,
                route_rows=route_rows,
                layout_constraints_rows=layout_constraints_rows,
                topology_rules_text=yaml.safe_dump(topology_rules, sort_keys=False, allow_unicode=True),
                scenario_settings_text=yaml.safe_dump(scenario_settings, sort_keys=False, allow_unicode=True),
            )

        assert saved["scenario_dir"] == str(output_dir)
        assert saved["bundle"].nodes.iloc[0]["label"] == "W salvo na UI"
        assert float(saved["bundle"].components.iloc[0]["cost"]) == 321.0
        assert saved["bundle"].candidate_links.iloc[0]["notes"] == "Tap salvo na UI"
        assert int(saved["bundle"].edge_component_rules.iloc[0]["max_series_pumps"]) == 1
        assert float(saved["bundle"].route_requirements.iloc[0]["weight"]) == 55.0
        assert float(saved["bundle"].layout_constraints.iloc[0]["value"]) == 1.5
        assert saved["bundle"].topology_rules["families"]["hybrid_free"]["max_active_pumps_per_route"] == 3
        assert saved["bundle"].scenario_settings["ui"]["default_layout_mode"] == "save_reopen_ui"
        assert saved["result"] is not None
        assert saved["result"]["scenario_bundle_version"] == saved["bundle"].bundle_version
        assert saved["result"]["scenario_bundle_files"]["components.csv"] == "component_catalog.csv"
        assert saved["pipeline_error"] is None
    finally:
        if output_dir.exists():
            shutil.rmtree(output_dir)
        cleanup_scenario_copy(scenario_dir)


@pytest.mark.fast
def test_ui_save_reopen_rejects_legacy_source_without_manifest() -> None:
    scenario_dir = prepare_scenario_copy(
        "data/decision_platform/maquete_v2",
        "maquete_v2_ui_save_reopen_legacy_source",
    )
    output_dir = Path("tests/_tmp/maquete_v2_ui_save_reopen_legacy_saved")
    if output_dir.exists():
        shutil.rmtree(output_dir)
    try:
        bundle = load_scenario_bundle(scenario_dir)
        (Path(scenario_dir) / "scenario_bundle.yaml").unlink()

        with pytest.raises(OfficialRuntimeConfigError, match="Decision Platform UI save/reopen requires a canonical scenario bundle"):
            save_and_reopen_local_bundle(
                current_scenario_dir=scenario_dir,
                output_dir=output_dir,
                nodes_rows=bundle.nodes.to_dict("records"),
                components_rows=bundle.components.to_dict("records"),
                candidate_links_rows=bundle.candidate_links.to_dict("records"),
                edge_component_rules_rows=bundle.edge_component_rules.to_dict("records"),
                route_rows=bundle.route_requirements.to_dict("records"),
                layout_constraints_rows=bundle.layout_constraints.to_dict("records"),
                topology_rules_text=yaml.safe_dump(bundle.topology_rules, sort_keys=False, allow_unicode=True),
                scenario_settings_text=yaml.safe_dump(
                    bundle.scenario_settings,
                    sort_keys=False,
                    allow_unicode=True,
                ),
            )

        assert not output_dir.exists()
    finally:
        if output_dir.exists():
            shutil.rmtree(output_dir)
        cleanup_scenario_copy(scenario_dir)


@pytest.mark.slow
def test_catalog_filters_include_quality_resilience_flow_and_fallback(
    maquete_v2_fallback_runtime: dict[str, object],
) -> None:
    result = maquete_v2_fallback_runtime["result"]
    ranked = rerank_catalog(result, "balanced")
    filtered = filter_catalog_records(
        ranked,
        family="ALL",
        feasible_only=True,
        max_cost=1000,
        min_quality=50,
        min_flow=5,
        min_resilience=10,
        min_cleaning=0,
        min_operability=0,
        top_n_per_family=2,
        fallback_filter="WITH_FALLBACK",
    )
    assert filtered
    assert all(record["feasible"] for record in filtered)
    assert all(float(record["quality_score_raw"]) >= 50 for record in filtered)
    assert all(float(record["flow_out_score"]) >= 5 for record in filtered)
    assert all(float(record["resilience_score"]) >= 10 for record in filtered)
    assert all(int(record["fallback_component_count"]) > 0 for record in filtered)


@pytest.mark.slow
def test_catalog_filters_include_infeasibility_reason_and_family_summary(
    maquete_v2_fallback_runtime: dict[str, object],
) -> None:
    result = maquete_v2_fallback_runtime["result"]
    ranked = rerank_catalog(result, "balanced")
    target_reason = next(
        str(record["infeasibility_reason"])
        for record in ranked
        if record.get("infeasibility_reason") not in (None, "")
    )
    filtered = filter_catalog_records(
        ranked,
        infeasibility_reason=target_reason,
    )
    view_state = build_catalog_view_state(
        result,
        profile_id=result["default_profile_id"],
        infeasibility_reason=target_reason,
    )
    assert filtered
    assert all(str(record["infeasibility_reason"]) == target_reason for record in filtered)
    assert view_state["family_summary_records"]
    assert all("viability_rate" in row for row in view_state["family_summary_records"])


@pytest.mark.slow
def test_reranking_changes_visible_selected_candidate_when_weights_change(
    maquete_v2_fallback_runtime: dict[str, object],
) -> None:
    result = maquete_v2_fallback_runtime["result"]
    default_state = build_catalog_view_state(result, profile_id=result["default_profile_id"])
    reranked_state = build_catalog_view_state(
        result,
        profile_id=result["default_profile_id"],
        weight_overrides={
            "cost_weight": 1.0,
            "quality_weight": 0.0,
            "flow_weight": 0.0,
            "resilience_weight": 0.0,
            "cleaning_weight": 0.0,
            "operability_weight": 0.0,
        },
    )
    assert default_state["selected_candidate_id"] == result["selected_candidate_id"]
    assert reranked_state["selected_candidate_id"] == reranked_state["ranked_records"][0]["candidate_id"]


@pytest.mark.slow
def test_ui_summary_and_comparison_records_expose_decision_fields(maquete_v2_fallback_runtime: dict[str, object]) -> None:
    result = maquete_v2_fallback_runtime["result"]
    official = build_official_candidate_summary(
        result,
        profile_id=result["default_profile_id"],
        candidate_id=result["selected_candidate_id"],
    )
    comparison = build_comparison_records(
        result,
        [record["candidate_id"] for record in result["ranked_profiles"]["balanced"][:2]],
        profile_id=result["default_profile_id"],
        active_selected_id=result["selected_candidate_id"],
    )
    assert official["candidate_id"] == result["selected_candidate_id"]
    assert "critical_routes" in official
    assert "winner_reason_summary" in official
    assert official["runner_up_candidate_id"] == result["ranked_profiles"]["balanced"][1]["candidate_id"]
    assert comparison
    assert any(row["comparison_role"] in {"official,selected", "official"} for row in comparison)
    assert all("score_final" in row for row in comparison)
