from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest
import yaml

from decision_platform.api.run_pipeline import OfficialRuntimeConfigError, run_decision_pipeline
from decision_platform.data_io.loader import load_scenario_bundle
from decision_platform.ui_dash.app import save_and_reopen_local_bundle
from tests.decision_platform.scenario_utils import (
    cleanup_scenario_copy,
    diagnostic_runtime_test_mode,
    prepare_maquete_v2_acceptance_scenario,
)


@pytest.mark.slow
def test_phase1_exit_canonical_bundle_flow_is_versionable_and_traceable() -> None:
    scenario_dir = prepare_maquete_v2_acceptance_scenario(
        "maquete_v2_phase1_exit_source",
        scenario_overrides={"hydraulic_engine": {"fallback": "python_emulated_julia"}},
    )
    save_dir = Path("tests/_tmp/maquete_v2_phase1_exit_saved")
    export_dir = Path("tests/_tmp/maquete_v2_phase1_exit_export")
    for path in (save_dir, export_dir):
        if path.exists():
            shutil.rmtree(path)
    try:
        source_bundle = load_scenario_bundle(scenario_dir)
        assert source_bundle.bundle_manifest_path is not None
        assert source_bundle.resolved_files["components.csv"].name == "component_catalog.csv"

        nodes_rows = source_bundle.nodes.to_dict("records")
        components_rows = source_bundle.components.to_dict("records")
        candidate_links_rows = source_bundle.candidate_links.to_dict("records")
        edge_component_rules_rows = source_bundle.edge_component_rules.to_dict("records")
        route_rows = source_bundle.route_requirements.to_dict("records")
        layout_constraints_rows = source_bundle.layout_constraints.to_dict("records")

        nodes_rows[0]["label"] = "W phase1 exit"
        components_rows[0]["cost"] = 222.0
        candidate_links_rows[0]["notes"] = "phase1_exit_trace"
        edge_component_rules_rows[0]["max_series_pumps"] = 1
        route_rows[0]["weight"] = 44.0
        layout_constraints_rows[0]["value"] = 1.5

        topology_rules = {
            **source_bundle.topology_rules,
            "families": {
                **source_bundle.topology_rules["families"],
                "hybrid_free": {
                    **source_bundle.topology_rules["families"]["hybrid_free"],
                    "max_active_pumps_per_route": 3,
                },
            },
        }
        scenario_settings = {
            **source_bundle.scenario_settings,
            "ui": {
                **source_bundle.scenario_settings.get("ui", {}),
                "default_layout_mode": "phase1_exit",
            },
        }

        with diagnostic_runtime_test_mode():
            saved = save_and_reopen_local_bundle(
                current_scenario_dir=scenario_dir,
                output_dir=save_dir,
                nodes_rows=nodes_rows,
                components_rows=components_rows,
                candidate_links_rows=candidate_links_rows,
                edge_component_rules_rows=edge_component_rules_rows,
                route_rows=route_rows,
                layout_constraints_rows=layout_constraints_rows,
                topology_rules_text=yaml.safe_dump(topology_rules, sort_keys=False, allow_unicode=True),
                scenario_settings_text=yaml.safe_dump(scenario_settings, sort_keys=False, allow_unicode=True),
            )
            result = run_decision_pipeline(
                save_dir,
                export_dir,
                allow_diagnostic_python_emulation=True,
            )

        summary = json.loads((export_dir / "summary.json").read_text(encoding="utf-8"))

        assert saved["scenario_dir"] == str(save_dir)
        assert saved["bundle"].bundle_manifest_path is not None
        assert saved["bundle"].resolved_files["components.csv"].name == "component_catalog.csv"
        assert saved["bundle"].nodes.iloc[0]["label"] == "W phase1 exit"
        assert float(saved["bundle"].components.iloc[0]["cost"]) == 222.0
        assert saved["bundle"].candidate_links.iloc[0]["notes"] == "phase1_exit_trace"
        assert int(saved["bundle"].edge_component_rules.iloc[0]["max_series_pumps"]) == 1
        assert float(saved["bundle"].route_requirements.iloc[0]["weight"]) == 44.0
        assert float(saved["bundle"].layout_constraints.iloc[0]["value"]) == 1.5
        assert saved["bundle"].topology_rules["families"]["hybrid_free"]["max_active_pumps_per_route"] == 3
        assert saved["bundle"].scenario_settings["ui"]["default_layout_mode"] == "phase1_exit"
        assert saved["result"] is not None
        assert saved["pipeline_error"] is None
        assert saved["bundle_io_summary"]["bundle_manifest"].endswith("scenario_bundle.yaml")
        assert saved["bundle_io_summary"]["bundle_files"]["components.csv"] == "component_catalog.csv"
        assert saved["bundle_io_summary"]["exported_files"]["bundle_manifest"].endswith("scenario_bundle.yaml")

        assert result["scenario_bundle_manifest"].endswith("scenario_bundle.yaml")
        assert result["scenario_bundle_files"]["components.csv"] == "component_catalog.csv"
        assert result["runtime"]["execution_mode"] == "diagnostic"
        assert result["runtime"]["official_gate_valid"] is False
        assert (export_dir / "catalog.csv").exists()
        assert (export_dir / "summary.json").exists()
        assert (export_dir / "selected_candidate.json").exists()
        assert summary["scenario_bundle_manifest"].endswith("scenario_bundle.yaml")
        assert summary["scenario_bundle_files"]["components.csv"] == "component_catalog.csv"
        assert summary["selected_candidate_id"] == result["selected_candidate_id"]
    finally:
        for path in (save_dir, export_dir):
            if path.exists():
                shutil.rmtree(path)
        cleanup_scenario_copy(scenario_dir)


@pytest.mark.fast
def test_phase1_exit_official_entrypoints_reject_legacy_layout() -> None:
    scenario_dir = prepare_maquete_v2_acceptance_scenario(
        "maquete_v2_phase1_exit_legacy",
        scenario_overrides={"hydraulic_engine": {"fallback": "python_emulated_julia"}},
    )
    save_dir = Path("tests/_tmp/maquete_v2_phase1_exit_legacy_saved")
    if save_dir.exists():
        shutil.rmtree(save_dir)
    try:
        bundle = load_scenario_bundle(scenario_dir)
        (Path(scenario_dir) / "scenario_bundle.yaml").unlink()

        with pytest.raises(OfficialRuntimeConfigError, match="requires a canonical scenario bundle"):
            run_decision_pipeline(
                scenario_dir,
                allow_diagnostic_python_emulation=True,
            )

        with pytest.raises(OfficialRuntimeConfigError, match="Decision Platform UI save/reopen requires a canonical scenario bundle"):
            save_and_reopen_local_bundle(
                current_scenario_dir=scenario_dir,
                output_dir=save_dir,
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

        assert not save_dir.exists()
    finally:
        if save_dir.exists():
            shutil.rmtree(save_dir)
        cleanup_scenario_copy(scenario_dir)
