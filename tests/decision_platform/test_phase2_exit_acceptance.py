from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

import pytest
import yaml

from decision_platform.api.run_pipeline import OfficialRuntimeConfigError, run_decision_pipeline
from decision_platform.data_io.loader import load_scenario_bundle
from decision_platform.data_io.storage import save_authored_scenario_bundle
from decision_platform.ui_dash.app import (
    apply_edge_studio_edit,
    apply_node_studio_edit,
    create_edge_studio_link,
    create_node_studio_node,
    delete_edge_studio_selection,
    delete_node_studio_selection,
    duplicate_node_studio_selection,
    save_and_reopen_local_bundle,
)
from tests.decision_platform.scenario_utils import (
    cleanup_scenario_copy,
    diagnostic_runtime_test_mode,
    prepare_maquete_v2_acceptance_scenario,
    prepare_isolated_tmp_dir,
)


@pytest.mark.slow
def test_phase2_exit_studio_flow_is_structural_editable_and_canonical() -> None:
    scenario_dir = prepare_maquete_v2_acceptance_scenario(
        "maquete_v2_phase2_exit_source",
        scenario_overrides={"hydraulic_engine": {"fallback": "python_emulated_julia"}},
    )
    created_dir = prepare_isolated_tmp_dir("maquete_v2_phase2_exit_created")
    final_dir = prepare_isolated_tmp_dir("maquete_v2_phase2_exit_final")
    export_dir = prepare_isolated_tmp_dir("maquete_v2_phase2_exit_export")
    try:
        source_bundle = load_scenario_bundle(scenario_dir)

        nodes_rows, created_node_id = create_node_studio_node(
            source_bundle.nodes.to_dict("records"),
            selected_node_id="J4",
        )
        nodes_rows, duplicated_node_id = duplicate_node_studio_selection(
            nodes_rows,
            selected_node_id=created_node_id,
        )
        nodes_rows, created_node_id = apply_node_studio_edit(
            nodes_rows,
            selected_node_id=created_node_id,
            label="Studio phase2 node",
            node_type="junction",
            x_m=0.83,
            y_m=0.31,
            allow_inbound=True,
            allow_outbound=True,
            candidate_links_rows=source_bundle.candidate_links.to_dict("records"),
            route_rows=source_bundle.route_requirements.to_dict("records"),
        )
        candidate_links_rows, created_link_id = create_edge_studio_link(
            source_bundle.candidate_links.to_dict("records"),
            selected_link_id="L013",
            from_node=created_node_id,
            to_node=duplicated_node_id,
            archetype="vertical_link",
            length_m=0.19,
            bidirectional=False,
            family_hint="loop,hybrid",
            nodes_rows=nodes_rows,
            edge_component_rules_rows=source_bundle.edge_component_rules.to_dict("records"),
        )
        candidate_links_rows, created_link_id = apply_edge_studio_edit(
            candidate_links_rows,
            selected_link_id=created_link_id,
            link_id=f"{created_link_id}_EDITED",
            from_node=created_node_id,
            to_node=duplicated_node_id,
            archetype="upper_bypass_segment",
            length_m=0.27,
            bidirectional=True,
            family_hint="loop",
            nodes_rows=nodes_rows,
            edge_component_rules_rows=source_bundle.edge_component_rules.to_dict("records"),
        )

        with diagnostic_runtime_test_mode():
            created = save_and_reopen_local_bundle(
                current_scenario_dir=scenario_dir,
                output_dir=created_dir,
                nodes_rows=nodes_rows,
                components_rows=source_bundle.components.to_dict("records"),
                candidate_links_rows=candidate_links_rows,
                edge_component_rules_rows=source_bundle.edge_component_rules.to_dict("records"),
                route_rows=source_bundle.route_requirements.to_dict("records"),
                layout_constraints_rows=source_bundle.layout_constraints.to_dict("records"),
                topology_rules_text=yaml.safe_dump(source_bundle.topology_rules, sort_keys=False, allow_unicode=True),
                scenario_settings_text=yaml.safe_dump(source_bundle.scenario_settings, sort_keys=False, allow_unicode=True),
            )

        created_bundle = created["bundle"]
        created_row = created_bundle.nodes.loc[created_bundle.nodes["node_id"] == created_node_id].iloc[0]
        created_edge = created_bundle.candidate_links.loc[
            created_bundle.candidate_links["link_id"] == created_link_id
        ].iloc[0]
        assert created["pipeline_error"] is None
        assert created_bundle.bundle_manifest_path is not None
        assert created_bundle.resolved_files["components.csv"].name == "component_catalog.csv"
        assert created_row["label"] == "Studio phase2 node"
        assert float(created_row["x_m"]) == 0.83
        assert duplicated_node_id in created_bundle.nodes["node_id"].tolist()
        assert created_edge["from_node"] == created_node_id
        assert created_edge["to_node"] == duplicated_node_id
        assert created_edge["archetype"] == "upper_bypass_segment"
        assert float(created_edge["length_m"]) == 0.27
        assert bool(created_edge["bidirectional"]) is True
        assert created["bundle_io_summary"]["bundle_manifest"].endswith("scenario_bundle.yaml")
        assert created["bundle_io_summary"]["bundle_files"]["components.csv"] == "component_catalog.csv"

        created_nodes_rows = created_bundle.nodes.to_dict("records")
        created_links_rows = created_bundle.candidate_links.to_dict("records")
        created_links_rows, _ = delete_edge_studio_selection(
            created_links_rows,
            selected_link_id=created_link_id,
        )
        created_nodes_rows, _ = delete_node_studio_selection(
            created_nodes_rows,
            selected_node_id=duplicated_node_id,
            candidate_links_rows=created_links_rows,
            route_rows=created_bundle.route_requirements.to_dict("records"),
        )
        created_nodes_rows, _ = delete_node_studio_selection(
            created_nodes_rows,
            selected_node_id=created_node_id,
            candidate_links_rows=created_links_rows,
            route_rows=created_bundle.route_requirements.to_dict("records"),
        )

        with diagnostic_runtime_test_mode():
            deleted = save_and_reopen_local_bundle(
                current_scenario_dir=created["scenario_dir"],
                output_dir=final_dir,
                nodes_rows=created_nodes_rows,
                components_rows=created_bundle.components.to_dict("records"),
                candidate_links_rows=created_links_rows,
                edge_component_rules_rows=created_bundle.edge_component_rules.to_dict("records"),
                route_rows=created_bundle.route_requirements.to_dict("records"),
                layout_constraints_rows=created_bundle.layout_constraints.to_dict("records"),
                topology_rules_text=yaml.safe_dump(created_bundle.topology_rules, sort_keys=False, allow_unicode=True),
                scenario_settings_text=yaml.safe_dump(created_bundle.scenario_settings, sort_keys=False, allow_unicode=True),
            )
            result = run_decision_pipeline(
                final_dir,
                export_dir,
                allow_diagnostic_python_emulation=True,
            )

        deleted_bundle = deleted["bundle"]
        summary = json.loads((export_dir / "summary.json").read_text(encoding="utf-8"))
        assert deleted["pipeline_error"] is None
        assert created_node_id not in deleted_bundle.nodes["node_id"].tolist()
        assert duplicated_node_id not in deleted_bundle.nodes["node_id"].tolist()
        assert created_link_id not in deleted_bundle.candidate_links["link_id"].tolist()
        assert result["scenario_bundle_root"] == str(final_dir.resolve())
        assert result["scenario_bundle_manifest"].endswith("scenario_bundle.yaml")
        assert result["scenario_bundle_files"]["components.csv"] == "component_catalog.csv"
        assert result["runtime"]["scenario_provenance"]["requested_dir_matches_bundle_root"] is True
        assert summary["scenario_bundle_root"] == str(final_dir.resolve())
        assert summary["scenario_bundle_manifest"].endswith("scenario_bundle.yaml")
        assert summary["scenario_bundle_files"]["components.csv"] == "component_catalog.csv"
    finally:
        cleanup_scenario_copy(export_dir)
        cleanup_scenario_copy(final_dir)
        cleanup_scenario_copy(created_dir)
        cleanup_scenario_copy(scenario_dir)


@pytest.mark.fast
def test_phase2_exit_rejects_invalid_structural_references_fail_closed() -> None:
    scenario_dir = prepare_maquete_v2_acceptance_scenario(
        "maquete_v2_phase2_exit_invalid_references",
        scenario_overrides={"hydraulic_engine": {"fallback": "python_emulated_julia"}},
    )
    output_dir = prepare_isolated_tmp_dir("maquete_v2_phase2_exit_invalid_references_saved")
    try:
        bundle = load_scenario_bundle(scenario_dir)

        with pytest.raises(ValueError, match="requires explicit reconciliation"):
            delete_node_studio_selection(
                bundle.nodes.to_dict("records"),
                selected_node_id="P1",
                candidate_links_rows=bundle.candidate_links.to_dict("records"),
                route_rows=bundle.route_requirements.to_dict("records"),
            )

        nodes_rows = [
            row
            for row in bundle.nodes.to_dict("records")
            if str(row.get("node_id", "")).strip() != "P1"
        ]
        with pytest.raises(ValueError, match="references unknown nodes"):
            save_authored_scenario_bundle(
                scenario_dir,
                output_dir,
                nodes_rows=nodes_rows,
                candidate_links_rows=bundle.candidate_links.to_dict("records"),
                route_rows=bundle.route_requirements.to_dict("records"),
                topology_rules_text=yaml.safe_dump(bundle.topology_rules, sort_keys=False, allow_unicode=True),
                scenario_settings_text=yaml.safe_dump(bundle.scenario_settings, sort_keys=False, allow_unicode=True),
            )
    finally:
        cleanup_scenario_copy(output_dir)
        cleanup_scenario_copy(scenario_dir)


@pytest.mark.fast
def test_phase2_exit_entrypoints_still_reject_legacy_layout_without_manifest() -> None:
    scenario_dir = prepare_maquete_v2_acceptance_scenario(
        "maquete_v2_phase2_exit_legacy",
        scenario_overrides={"hydraulic_engine": {"fallback": "python_emulated_julia"}},
    )
    save_dir = prepare_isolated_tmp_dir("maquete_v2_phase2_exit_legacy_saved")
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
                scenario_settings_text=yaml.safe_dump(bundle.scenario_settings, sort_keys=False, allow_unicode=True),
            )

        assert not save_dir.exists()
    finally:
        cleanup_scenario_copy(save_dir)
        cleanup_scenario_copy(scenario_dir)


@pytest.mark.slow
def test_phase2_exit_structural_studio_validation_script_generates_ui_evidence() -> None:
    artifact_dir = prepare_isolated_tmp_dir("phase2_structural_ui_validation", create=True)
    script_path = Path("scripts/capture_decision_platform_ui_validation.py")
    try:
        completed = subprocess.run(
            [
                sys.executable,
                str(script_path),
                "--artifact-dir",
                str(artifact_dir),
            ],
            cwd=Path.cwd(),
            check=True,
            capture_output=True,
            text=True,
        )

        artifact_path = artifact_dir / "studio_structural_validation.json"
        readme_path = artifact_dir / "README.md"
        assert artifact_path.exists(), completed.stdout
        assert readme_path.exists(), completed.stdout

        payload = json.loads(artifact_path.read_text(encoding="utf-8"))
        assert payload["assertions"]["created_bundle_kept_canonical_manifest"] is True
        assert payload["assertions"]["created_bundle_kept_component_catalog"] is True
        assert payload["assertions"]["created_node_persisted"] is True
        assert payload["assertions"]["duplicated_node_persisted"] is True
        assert payload["assertions"]["created_edge_persisted"] is True
        assert payload["assertions"]["delete_node_blocked_when_referenced"] is True
        assert payload["assertions"]["final_bundle_removed_created_node"] is True
        assert payload["assertions"]["final_bundle_removed_duplicated_node"] is True
        assert payload["assertions"]["final_bundle_removed_created_edge"] is True
        assert payload["assertions"]["created_execution_kept_provenance"] is True
        assert payload["assertions"]["final_execution_kept_provenance"] is True
        assert payload["summaries"]["created_bundle_io_summary"]["bundle_files"]["components.csv"] == "component_catalog.csv"
        assert payload["summaries"]["final_bundle_io_summary"]["bundle_files"]["components.csv"] == "component_catalog.csv"
        assert payload["summaries"]["created_execution_summary"]["scenario_bundle_manifest"].endswith("scenario_bundle.yaml")
        assert payload["summaries"]["final_execution_summary"]["scenario_bundle_manifest"].endswith("scenario_bundle.yaml")
        assert any(item["step"] == "create_node" for item in payload["callback_trace"])
        assert any(item["step"] == "create_edge" for item in payload["callback_trace"])
        assert any(item["step"] == "save_final_bundle" for item in payload["callback_trace"])
    finally:
        cleanup_scenario_copy(artifact_dir)
