from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from decision_platform.data_io.loader import load_scenario_bundle
from decision_platform.data_io.storage import save_authored_scenario_bundle
from decision_platform.ui_dash.app import (
    STUDIO_CONTEXT_MENU,
    _route_choice_options,
    apply_studio_context_menu_action,
    apply_route_intent_from_edge_context,
    apply_route_studio_edit,
    create_route_between_business_nodes,
    create_route_from_edge_studio_selection,
    reverse_edge_studio_selection,
    build_app,
    build_primary_node_studio_elements,
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
    assert "studio-workspace-context-panel" in layout_repr
    assert "studio-workspace-priority-flow" in layout_repr
    assert "studio-workspace-context-direct-actions" in layout_repr
    assert "studio-workspace-require-measurement-button" in layout_repr
    assert "studio-workspace-create-route-button" in layout_repr
    assert "studio-workspace-reverse-edge-button" in layout_repr
    assert "studio-workspace-intent-actions" in layout_repr
    assert "studio-workspace-intent-mandatory-button" in layout_repr
    assert "studio-workspace-intent-desirable-button" in layout_repr
    assert "studio-workspace-intent-optional-button" in layout_repr
    assert "studio-workspace-supply-rail" in layout_repr
    assert "studio-workspace-quick-edit-panel" in layout_repr
    assert "studio-workspace-local-actions-panel" in layout_repr
    assert "studio-route-editor-shell" in layout_repr
    assert "studio-business-flow-panel" in layout_repr
    assert "studio-route-editor-panel" in layout_repr
    assert "studio-route-focus-dropdown" in layout_repr
    assert "studio-route-intent" in layout_repr
    assert "studio-route-apply-button" in layout_repr
    assert "studio-route-start-from-node-button" in layout_repr
    assert "studio-route-complete-to-node-button" in layout_repr
    assert "studio-route-cancel-draft-button" in layout_repr
    assert "studio-route-create-from-edge-button" in layout_repr
    assert "studio-route-compose-intent" in layout_repr
    assert "studio-route-compose-q-min-lpm" in layout_repr
    assert "studio-route-compose-dose-min-l" in layout_repr
    assert "studio-route-compose-measurement-required" in layout_repr
    assert "studio-route-compose-confirm-button" in layout_repr
    assert "studio-route-composer-preview-panel" in layout_repr
    assert "studio-route-draft-source-id" not in layout_repr
    assert "studio-readiness-action-queue" in layout_repr
    assert "studio-readiness-action-0-button" in layout_repr
    assert "studio-route-intent-mandatory-button" in layout_repr
    assert "studio-route-intent-desirable-button" in layout_repr
    assert "studio-route-intent-optional-button" in layout_repr
    assert "studio-focus-node-label" in layout_repr
    assert "studio-focus-node-apply-button" in layout_repr
    assert "studio-focus-edge-length-m" in layout_repr
    assert "studio-focus-edge-family-hint" in layout_repr
    assert "studio-focus-edge-apply-button" in layout_repr
    assert "studio-focus-edge-reverse-button" in layout_repr
    assert "studio-focus-edge-flow-preview" in layout_repr
    assert "studio-context-detailed-panels" in layout_repr
    assert "Paleta e criação rápida" in layout_repr
    assert "runs-workspace-panel" in layout_repr
    assert "runs-context-detailed-panels" in layout_repr
    assert "decision-workspace-panel" in layout_repr
    assert "decision-context-detailed-panels" in layout_repr
    assert "audit-workspace-panel" in layout_repr
    assert "audit-context-detailed-panels" in layout_repr


@pytest.mark.fast
def test_dash_app_http_entrypoints_resolve_primary_tabs_without_error() -> None:
    with diagnostic_runtime_test_mode():
        app = build_app("data/decision_platform/maquete_v2")

    client = app.server.test_client()

    assert client.get("/?tab=studio").status_code == 200
    assert client.get("/?tab=decision").status_code == 200


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
def test_context_menu_action_creates_and_removes_business_elements() -> None:
    bundle = load_scenario_bundle("data/decision_platform/maquete_v2")
    nodes_rows = bundle.nodes.to_dict("records")
    candidate_links_rows = bundle.candidate_links.to_dict("records")
    route_rows = bundle.route_requirements.to_dict("records")

    updated_nodes, updated_links, updated_routes, next_node_id, next_link_id, status, open_workbench = apply_studio_context_menu_action(
        context_menu_data={"menuItemId": "add-product-node", "x": 420, "y": 180},
        nodes_rows=nodes_rows,
        candidate_links_rows=candidate_links_rows,
        selected_node_id="P1",
        selected_link_id="L013",
        route_rows=route_rows,
    )

    created_node = next(row for row in updated_nodes if str(row["node_id"]) == next_node_id)
    assert updated_links == candidate_links_rows
    assert updated_routes == route_rows
    assert status == "Entidade de negócio adicionada pelo menu contextual."
    assert open_workbench is False
    assert created_node["node_type"] == "product_tank"
    assert created_node["x_m"] == pytest.approx(0.42)
    assert created_node["y_m"] == pytest.approx(0.3)

    updated_nodes, updated_links, updated_routes, _, removed_link_id, status, open_workbench = apply_studio_context_menu_action(
        context_menu_data={"menuItemId": "remove-edge", "elementId": "L013"},
        nodes_rows=updated_nodes,
        candidate_links_rows=updated_links,
        selected_node_id=next_node_id,
        selected_link_id="L013",
        route_rows=route_rows,
    )

    assert all(str(row["link_id"]) != "L013" for row in updated_links)
    assert updated_routes == route_rows
    assert removed_link_id != "L013"
    assert status == "Conexão removida pelo menu contextual."
    assert open_workbench is False


@pytest.mark.fast
def test_reverse_edge_studio_selection_swaps_business_flow_direction() -> None:
    bundle = load_scenario_bundle("data/decision_platform/maquete_v2")

    updated_links, next_selected_link_id = reverse_edge_studio_selection(
        bundle.candidate_links.to_dict("records"),
        selected_link_id="L013",
        nodes_rows=bundle.nodes.to_dict("records"),
        edge_component_rules_rows=bundle.edge_component_rules.to_dict("records"),
    )

    reversed_link = next(row for row in updated_links if str(row["link_id"]) == "L013")
    original_link = next(row for row in bundle.candidate_links.to_dict("records") if str(row["link_id"]) == "L013")

    assert next_selected_link_id == "L013"
    assert reversed_link["from_node"] == original_link["to_node"]
    assert reversed_link["to_node"] == original_link["from_node"]
    assert reversed_link["length_m"] == original_link["length_m"]


@pytest.mark.fast
def test_route_focus_edit_updates_intent_and_measurement_flags() -> None:
    bundle = load_scenario_bundle("data/decision_platform/maquete_v2")

    updated_routes, selected_route_id = apply_route_studio_edit(
        bundle.route_requirements.to_dict("records"),
        selected_route_id="R010",
        intent="desirable",
        measurement_required=True,
        dose_min_l=3.5,
        q_min_delivered_lpm=12,
        notes="Premix desejável perto do canvas",
    )

    updated_route = next(row for row in updated_routes if str(row["route_id"]) == "R010")
    assert selected_route_id == "R010"
    assert bool(updated_route["mandatory"]) is False
    assert updated_route["route_group"] == "desirable"
    assert bool(updated_route["measurement_required"]) is True
    assert updated_route["dose_min_l"] == pytest.approx(3.5)
    assert updated_route["q_min_delivered_lpm"] == pytest.approx(12.0)
    assert updated_route["notes"] == "Premix desejável perto do canvas"


@pytest.mark.fast
def test_create_route_between_business_nodes_adds_visible_route() -> None:
    bundle = load_scenario_bundle("data/decision_platform/maquete_v2")
    route_rows = [
        row
        for row in bundle.route_requirements.to_dict("records")
        if str(row["route_id"]) != "R018"
    ]

    updated_routes, created_route_id = create_route_between_business_nodes(
        route_rows,
        source_node_id="I",
        sink_node_id="IR",
    )

    created_route = next(row for row in updated_routes if str(row["route_id"]) == created_route_id)
    assert created_route["source"] == "I"
    assert created_route["sink"] == "IR"
    assert created_route["route_group"] == "optional"
    assert bool(created_route["mandatory"]) is False
    assert "Rota criada no canvas" in str(created_route["notes"])


@pytest.mark.fast
def test_apply_route_intent_from_edge_context_updates_matching_route() -> None:
    bundle = load_scenario_bundle("data/decision_platform/maquete_v2")
    route_rows = bundle.route_requirements.to_dict("records")
    route_rows, created_route_id = create_route_from_edge_studio_selection(
        route_rows,
        selected_link_id="L018",
        candidate_links_rows=bundle.candidate_links.to_dict("records"),
    )

    updated_routes, selected_route_id = apply_route_intent_from_edge_context(
        route_rows,
        selected_link_id="L018",
        candidate_links_rows=bundle.candidate_links.to_dict("records"),
        intent="desirable",
    )

    updated_route = next(row for row in updated_routes if str(row["route_id"]) == created_route_id)
    assert selected_route_id == created_route_id
    assert updated_route["route_group"] == "desirable"
    assert bool(updated_route["mandatory"]) is False


@pytest.mark.fast
def test_primary_studio_projection_marks_desirable_routes_in_canvas_classes() -> None:
    bundle = load_scenario_bundle("data/decision_platform/maquete_v2")
    route_rows = bundle.route_requirements.to_dict("records")
    for route in route_rows:
        if str(route["route_id"]) == "R010":
            route["mandatory"] = 0
            route["route_group"] = "desirable"

    elements = build_primary_node_studio_elements(
        bundle.nodes.to_dict("records"),
        bundle.candidate_links.to_dict("records"),
        route_rows,
    )

    route_element = next(element for element in elements if element.get("data", {}).get("route_id") == "R010")
    assert "desirable" in str(route_element.get("classes") or "")
    assert route_element["data"]["intent"] == "desirable"


@pytest.mark.fast
def test_primary_studio_projection_includes_route_composer_preview_edge() -> None:
    bundle = load_scenario_bundle("data/decision_platform/maquete_v2")

    elements = build_primary_node_studio_elements(
        bundle.nodes.to_dict("records"),
        bundle.candidate_links.to_dict("records"),
        bundle.route_requirements.to_dict("records"),
        route_composer_state={
            "source_node_id": "W",
            "sink_node_id": "M",
            "intent": "mandatory",
        },
    )

    preview_edge = next(element for element in elements if element.get("data", {}).get("preview") is True)
    assert preview_edge["data"]["source"] == "W"
    assert preview_edge["data"]["target"] == "M"
    assert "route-composer-preview" in str(preview_edge.get("classes") or "")
    assert "mandatory" in str(preview_edge.get("classes") or "")


@pytest.mark.fast
def test_studio_context_menu_declares_business_first_actions() -> None:
    menu_ids = {item["id"] for item in STUDIO_CONTEXT_MENU}
    assert "add-product-node" in menu_ids
    assert "add-mixer-node" in menu_ids
    assert "add-outlet-node" in menu_ids
    assert "start-route-from-node" in menu_ids
    assert "create-route-from-edge" in menu_ids
    assert "mark-route-mandatory" in menu_ids
    assert "mark-route-desirable" in menu_ids
    assert "mark-route-optional" in menu_ids
    assert "duplicate-node" in menu_ids
    assert "reverse-edge" in menu_ids
    assert "remove-edge" in menu_ids
    assert "open-workbench" in menu_ids


@pytest.mark.fast
def test_context_menu_action_reverses_edge_and_reports_readiness_change() -> None:
    bundle = load_scenario_bundle("data/decision_platform/maquete_v2")
    candidate_links_rows = bundle.candidate_links.to_dict("records")
    original_link = next(row for row in candidate_links_rows if str(row["link_id"]) == "L013")

    updated_nodes, updated_links, updated_routes, next_node_id, next_link_id, status, open_workbench = apply_studio_context_menu_action(
        context_menu_data={"menuItemId": "reverse-edge", "elementId": "L013"},
        nodes_rows=bundle.nodes.to_dict("records"),
        candidate_links_rows=candidate_links_rows,
        selected_node_id="P1",
        selected_link_id="L013",
        route_rows=bundle.route_requirements.to_dict("records"),
    )

    reversed_link = next(row for row in updated_links if str(row["link_id"]) == "L013")
    assert updated_nodes == bundle.nodes.to_dict("records")
    assert updated_routes == bundle.route_requirements.to_dict("records")
    assert next_node_id == "P1"
    assert next_link_id == "L013"
    assert reversed_link["from_node"] == original_link["to_node"]
    assert reversed_link["to_node"] == original_link["from_node"]
    assert "Conexão invertida pelo menu contextual." in status
    assert "Agora" in status
    assert "Runs" in status
    assert open_workbench is False


@pytest.mark.fast
def test_context_menu_action_starts_route_draft_from_selected_node() -> None:
    bundle = load_scenario_bundle("data/decision_platform/maquete_v2")
    route_rows = [
        row
        for row in bundle.route_requirements.to_dict("records")
        if str(row["route_id"]) != "R018"
    ]

    updated_nodes, updated_links, updated_routes, next_node_id, next_link_id, status, open_workbench = apply_studio_context_menu_action(
        context_menu_data={"menuItemId": "start-route-from-node", "elementId": "I"},
        nodes_rows=bundle.nodes.to_dict("records"),
        candidate_links_rows=bundle.candidate_links.to_dict("records"),
        selected_node_id="I",
        selected_link_id="L013",
        route_rows=route_rows,
    )

    assert updated_nodes == bundle.nodes.to_dict("records")
    assert updated_links == bundle.candidate_links.to_dict("records")
    assert updated_routes == route_rows
    assert next_node_id == "I"
    assert next_link_id == "L013"
    assert status == ""
    assert open_workbench is False


@pytest.mark.fast
def test_route_choice_options_use_business_labels_before_technical_ids() -> None:
    bundle = load_scenario_bundle("data/decision_platform/maquete_v2")

    labels = [
        str(option["label"])
        for option in _route_choice_options(
            bundle.route_requirements.to_dict("records"),
            nodes_rows=bundle.nodes.to_dict("records"),
        )[:3]
    ]

    assert labels
    assert labels[0].startswith("Tanque de água para Misturador")
    assert all("R00" not in label for label in labels)
    assert all("->" not in label for label in labels)


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
