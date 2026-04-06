from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from decision_platform.data_io.loader import load_scenario_bundle
from decision_platform.data_io.storage import save_authored_scenario_bundle
from decision_platform.ui_dash.app import (
    build_app,
    create_business_node_studio_node,
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
    prepare_isolated_tmp_dir,
    prepare_scenario_copy,
)


@pytest.mark.fast
def test_dash_app_exposes_structural_studio_controls() -> None:
    with diagnostic_runtime_test_mode():
        app = build_app("data/decision_platform/maquete_v2")

    layout_repr = repr(app.layout)
    assert "node-studio-create-button" in layout_repr
    assert "node-studio-duplicate-button" in layout_repr
    assert "node-studio-delete-button" in layout_repr
    assert "edge-studio-create-button" in layout_repr
    assert "edge-studio-delete-button" in layout_repr
    assert "studio-canvas-open-workbench-button" in layout_repr
    assert "studio-canvas-open-technical-guide-button" in layout_repr
    assert "studio-command-center-panel" in layout_repr
    assert "studio-add-source-node-button" in layout_repr
    assert "studio-add-product-node-button" in layout_repr
    assert "studio-add-mixer-node-button" in layout_repr
    assert "studio-add-service-node-button" in layout_repr
    assert "studio-add-outlet-node-button" in layout_repr
    assert "studio-quick-link-source" in layout_repr
    assert "studio-quick-link-target" in layout_repr
    assert "studio-quick-link-create-button" in layout_repr
    assert "studio-workspace-panel" in layout_repr
    assert "studio-context-detailed-panels" in layout_repr
    assert "runs-workspace-panel" in layout_repr
    assert "runs-context-detailed-panels" in layout_repr
    assert "decision-workspace-panel" in layout_repr
    assert "decision-context-detailed-panels" in layout_repr
    assert "audit-workspace-panel" in layout_repr
    assert "audit-context-detailed-panels" in layout_repr


@pytest.mark.fast
def test_studio_structure_helpers_create_duplicate_and_delete_items() -> None:
    bundle = load_scenario_bundle("data/decision_platform/maquete_v2")
    nodes_rows, created_node_id = create_node_studio_node(
        bundle.nodes.to_dict("records"),
        selected_node_id="P1",
    )
    nodes_rows, duplicated_node_id = duplicate_node_studio_selection(
        nodes_rows,
        selected_node_id=created_node_id,
    )
    candidate_links_rows, created_link_id = create_edge_studio_link(
        bundle.candidate_links.to_dict("records"),
        selected_link_id="L013",
        from_node=created_node_id,
        to_node=duplicated_node_id,
        archetype="vertical_link",
        length_m=0.22,
        bidirectional=False,
        family_hint="loop,hybrid",
        nodes_rows=nodes_rows,
        edge_component_rules_rows=bundle.edge_component_rules.to_dict("records"),
    )
    candidate_links_rows, next_link_id = delete_edge_studio_selection(
        candidate_links_rows,
        selected_link_id=created_link_id,
    )
    nodes_rows, next_node_id = delete_node_studio_selection(
        nodes_rows,
        selected_node_id=duplicated_node_id,
        candidate_links_rows=candidate_links_rows,
        route_rows=bundle.route_requirements.to_dict("records"),
    )

    assert created_node_id.startswith("NEW_NODE")
    assert duplicated_node_id.startswith(f"{created_node_id}_copy")
    assert created_link_id.startswith("L013_copy")
    assert any(row["node_id"] == created_node_id for row in nodes_rows)
    assert all(row["node_id"] != duplicated_node_id for row in nodes_rows)
    assert all(row["link_id"] != created_link_id for row in candidate_links_rows)
    assert next_link_id != created_link_id
    assert next_node_id in {str(row["node_id"]) for row in nodes_rows}
    assert next_node_id != duplicated_node_id


@pytest.mark.fast
def test_business_palette_presets_create_visible_business_nodes() -> None:
    bundle = load_scenario_bundle("data/decision_platform/maquete_v2")

    nodes_rows, source_node_id = create_business_node_studio_node(
        bundle.nodes.to_dict("records"),
        selected_node_id="W",
        preset_key="source",
    )
    nodes_rows, outlet_node_id = create_business_node_studio_node(
        nodes_rows,
        selected_node_id=source_node_id,
        preset_key="outlet",
    )

    created_source = next(row for row in nodes_rows if str(row["node_id"]) == source_node_id)
    created_outlet = next(row for row in nodes_rows if str(row["node_id"]) == outlet_node_id)

    assert created_source["zone"] == "supply"
    assert created_source["node_type"] == "water_tank"
    assert bool(created_source["allow_inbound"]) is False
    assert bool(created_source["allow_outbound"]) is True
    assert bool(created_source["is_candidate_hub"]) is False
    assert created_outlet["zone"] == "outlet"
    assert created_outlet["node_type"] == "external_outlet"
    assert bool(created_outlet["allow_outbound"]) is False
    assert "Criado pela paleta principal do Studio" in str(created_outlet["notes"])


@pytest.mark.fast
def test_delete_node_studio_rejects_orphaned_references() -> None:
    bundle = load_scenario_bundle("data/decision_platform/maquete_v2")

    with pytest.raises(ValueError, match="requires explicit reconciliation"):
        delete_node_studio_selection(
            bundle.nodes.to_dict("records"),
            selected_node_id="P1",
            candidate_links_rows=bundle.candidate_links.to_dict("records"),
            route_rows=bundle.route_requirements.to_dict("records"),
        )


@pytest.mark.fast
def test_save_authored_bundle_fails_closed_for_deleted_node_with_broken_references() -> None:
    source_bundle = load_scenario_bundle("data/decision_platform/maquete_v2")
    output_dir = prepare_isolated_tmp_dir("scenario_persistence_deleted_node_references")
    try:
        nodes_rows = [
            row
            for row in source_bundle.nodes.to_dict("records")
            if str(row.get("node_id", "")).strip() != "P1"
        ]

        with pytest.raises(ValueError, match="references unknown nodes"):
            save_authored_scenario_bundle(
                "data/decision_platform/maquete_v2",
                output_dir,
                nodes_rows=nodes_rows,
                candidate_links_rows=source_bundle.candidate_links.to_dict("records"),
                route_rows=source_bundle.route_requirements.to_dict("records"),
                topology_rules_text=yaml.safe_dump(
                    source_bundle.topology_rules,
                    sort_keys=False,
                    allow_unicode=True,
                ),
                scenario_settings_text=yaml.safe_dump(
                    source_bundle.scenario_settings,
                    sort_keys=False,
                    allow_unicode=True,
                ),
            )
    finally:
        cleanup_scenario_copy(output_dir)


@pytest.mark.slow
def test_studio_structure_round_trip_persists_created_and_deleted_items() -> None:
    scenario_dir = prepare_scenario_copy(
        "data/decision_platform/maquete_v2",
        "maquete_v2_structural_studio_round_trip",
        scenario_overrides={"hydraulic_engine": {"fallback": "python_emulated_julia"}},
    )
    created_output_dir = prepare_isolated_tmp_dir("maquete_v2_structural_studio_created")
    deleted_output_dir = prepare_isolated_tmp_dir("maquete_v2_structural_studio_deleted")
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
        candidate_links_rows, created_link_id = create_edge_studio_link(
            source_bundle.candidate_links.to_dict("records"),
            selected_link_id="L013",
            from_node=created_node_id,
            to_node=duplicated_node_id,
            archetype="vertical_link",
            length_m=0.18,
            bidirectional=False,
            family_hint="loop,hybrid",
            nodes_rows=nodes_rows,
            edge_component_rules_rows=source_bundle.edge_component_rules.to_dict("records"),
        )

        with diagnostic_runtime_test_mode():
            created = save_and_reopen_local_bundle(
                current_scenario_dir=scenario_dir,
                output_dir=created_output_dir,
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
        assert created["pipeline_error"] is None
        assert created_node_id in created_bundle.nodes["node_id"].tolist()
        assert duplicated_node_id in created_bundle.nodes["node_id"].tolist()
        assert created_link_id in created_bundle.candidate_links["link_id"].tolist()

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
                output_dir=deleted_output_dir,
                nodes_rows=created_nodes_rows,
                components_rows=created_bundle.components.to_dict("records"),
                candidate_links_rows=created_links_rows,
                edge_component_rules_rows=created_bundle.edge_component_rules.to_dict("records"),
                route_rows=created_bundle.route_requirements.to_dict("records"),
                layout_constraints_rows=created_bundle.layout_constraints.to_dict("records"),
                topology_rules_text=yaml.safe_dump(created_bundle.topology_rules, sort_keys=False, allow_unicode=True),
                scenario_settings_text=yaml.safe_dump(created_bundle.scenario_settings, sort_keys=False, allow_unicode=True),
            )

        deleted_bundle = deleted["bundle"]
        assert deleted["pipeline_error"] is None
        assert created_node_id not in deleted_bundle.nodes["node_id"].tolist()
        assert duplicated_node_id not in deleted_bundle.nodes["node_id"].tolist()
        assert created_link_id not in deleted_bundle.candidate_links["link_id"].tolist()
        assert Path(created["scenario_dir"]).name == created_output_dir.name
        assert Path(deleted["scenario_dir"]).name == deleted_output_dir.name
    finally:
        cleanup_scenario_copy(deleted_output_dir)
        cleanup_scenario_copy(created_output_dir)
        cleanup_scenario_copy(scenario_dir)
