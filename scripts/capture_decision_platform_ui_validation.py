from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path
from typing import Any, Callable
from uuid import uuid4

import yaml


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from decision_platform.data_io.loader import load_scenario_bundle
from decision_platform.julia_bridge.bridge import disable_real_julia_probe
from decision_platform.ui_dash.app import build_app


DEFAULT_ARTIFACT_DIR = ROOT / "data" / "output" / "decision_platform" / "ui_validation"
DEFAULT_SOURCE_SCENARIO = ROOT / "data" / "decision_platform" / "maquete_v2"


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Capture reproducible structural Studio validation evidence.")
    parser.add_argument(
        "--artifact-dir",
        default=str(DEFAULT_ARTIFACT_DIR),
        help="Directory where the validation JSON and README should be written.",
    )
    parser.add_argument(
        "--source-scenario",
        default=str(DEFAULT_SOURCE_SCENARIO),
        help="Canonical source scenario to copy before running the UI validation flow.",
    )
    return parser.parse_args()


def _prepare_tmp_dir(prefix: str) -> Path:
    target = ROOT / "tests" / "_tmp" / f"{prefix}_{uuid4().hex}"
    target.parent.mkdir(parents=True, exist_ok=True)
    return target


def _cleanup(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path)


def _deep_update(target: dict[str, Any], updates: dict[str, Any]) -> None:
    for key, value in updates.items():
        if isinstance(value, dict) and isinstance(target.get(key), dict):
            _deep_update(target[key], value)
        else:
            target[key] = value


def _prepare_scenario_copy(source_dir: Path) -> Path:
    target = _prepare_tmp_dir("studio_ui_validation_source")
    shutil.copytree(source_dir, target)
    settings_path = target / "scenario_settings.yaml"
    settings = yaml.safe_load(settings_path.read_text(encoding="utf-8")) or {}
    _deep_update(
        settings,
        {
            "candidate_generation": {
                "population_size": 12,
                "generations": 3,
                "keep_top_n_per_family": 6,
            },
            "hydraulic_engine": {"fallback": "python_emulated_julia"},
        },
    )
    settings_path.write_text(yaml.safe_dump(settings, sort_keys=False, allow_unicode=True), encoding="utf-8")
    return target


def _get_callback(app: object, *, output_prefix: str | None = None, input_id: str | None = None) -> Callable[..., Any]:
    callback_map = getattr(app, "callback_map", {})
    for callback_key, metadata in callback_map.items():
        if output_prefix is not None and not str(callback_key).startswith(output_prefix):
            continue
        if input_id is not None and not any(item["id"] == input_id for item in metadata.get("inputs", [])):
            continue
        callback = metadata.get("callback")
        if callback is None:
            continue
        return getattr(callback, "__wrapped__", callback)
    raise KeyError(f"Callback not found for output_prefix={output_prefix!r} input_id={input_id!r}")


def _write_readme(artifact_dir: Path, payload: dict[str, Any]) -> None:
    lines = [
        "# Structural Studio UI Validation",
        "",
        "- Evidence generated from the real Dash callback map of the Studio tab.",
        f"- Source scenario copy: `{payload['scenario_dirs']['source_copy']}`",
        f"- Created bundle: `{payload['scenario_dirs']['created_bundle']}`",
        f"- Final bundle: `{payload['scenario_dirs']['final_bundle']}`",
        "",
        "## Assertions",
        "",
    ]
    for key, value in payload["assertions"].items():
        lines.append(f"- `{key}`: `{value}`")
    lines.append("")
    lines.append("## Callback Trace")
    lines.append("")
    for trace in payload["callback_trace"]:
        lines.append(f"- `{trace['step']}`: selected=`{trace.get('selected_id')}` status=`{trace.get('status')}`")
    (artifact_dir / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_validation(*, artifact_dir: Path, source_scenario: Path) -> Path:
    artifact_dir.mkdir(parents=True, exist_ok=True)
    source_copy_dir = _prepare_scenario_copy(source_scenario)
    created_bundle_dir = artifact_dir / "bundle_created"
    final_bundle_dir = artifact_dir / "bundle_final"
    _cleanup(created_bundle_dir)
    _cleanup(final_bundle_dir)

    callback_trace: list[dict[str, Any]] = []

    try:
        with disable_real_julia_probe():
            app = build_app(source_copy_dir)

            bundle = load_scenario_bundle(source_copy_dir)
            create_node_callback = _get_callback(app, input_id="node-studio-create-button")
            duplicate_node_callback = _get_callback(app, input_id="node-studio-duplicate-button")
            apply_node_callback = _get_callback(app, input_id="node-studio-apply-button")
            delete_node_callback = _get_callback(app, input_id="node-studio-delete-button")
            sync_node_callback = _get_callback(app, output_prefix="..node-studio-selected-id.data")
            create_edge_callback = _get_callback(app, input_id="edge-studio-create-button")
            apply_edge_callback = _get_callback(app, input_id="edge-studio-apply-button")
            delete_edge_callback = _get_callback(app, input_id="edge-studio-delete-button")
            sync_edge_callback = _get_callback(app, output_prefix="..edge-studio-selected-id.data")
            refresh_studio_callback = _get_callback(app, output_prefix="..node-studio-cytoscape.elements")
            save_callback = _get_callback(app, input_id="save-reopen-bundle-button")

            nodes_rows = bundle.nodes.to_dict("records")
            candidate_links_rows = bundle.candidate_links.to_dict("records")
            edge_component_rules_rows = bundle.edge_component_rules.to_dict("records")
            route_rows = bundle.route_requirements.to_dict("records")
            layout_constraints_rows = bundle.layout_constraints.to_dict("records")
            components_rows = bundle.components.to_dict("records")
            topology_rules_text = yaml.safe_dump(bundle.topology_rules, sort_keys=False, allow_unicode=True)
            scenario_settings_text = yaml.safe_dump(bundle.scenario_settings, sort_keys=False, allow_unicode=True)

            nodes_rows, created_node_id, status = create_node_callback(1, nodes_rows, "J4")
            callback_trace.append({"step": "create_node", "selected_id": created_node_id, "status": status})
            selected_node_form = sync_node_callback(nodes_rows, {"id": created_node_id}, "J4")

            nodes_rows, created_node_id, status = apply_node_callback(
                1,
                nodes_rows,
                created_node_id,
                created_node_id,
                "Studio callback node",
                "junction",
                0.81,
                0.28,
                ["allow_inbound"],
                ["allow_outbound"],
                candidate_links_rows,
                route_rows,
            )
            callback_trace.append({"step": "edit_node", "selected_id": created_node_id, "status": status})

            nodes_rows, duplicated_node_id, status = duplicate_node_callback(1, nodes_rows, created_node_id)
            callback_trace.append({"step": "duplicate_node", "selected_id": duplicated_node_id, "status": status})
            duplicated_node_form = sync_node_callback(nodes_rows, {"id": duplicated_node_id}, created_node_id)

            candidate_links_rows, created_link_id, status = create_edge_callback(
                1,
                candidate_links_rows,
                "L013",
                created_node_id,
                duplicated_node_id,
                "vertical_link",
                0.19,
                [],
                "loop,hybrid",
                nodes_rows,
                edge_component_rules_rows,
            )
            callback_trace.append({"step": "create_edge", "selected_id": created_link_id, "status": status})
            created_edge_form = sync_edge_callback(candidate_links_rows, {"link_id": created_link_id}, "L013")

            candidate_links_rows, created_link_id, status = apply_edge_callback(
                1,
                candidate_links_rows,
                created_link_id,
                f"{created_link_id}_EDITED",
                created_node_id,
                duplicated_node_id,
                "upper_bypass_segment",
                0.27,
                ["bidirectional"],
                "loop",
                nodes_rows,
                edge_component_rules_rows,
            )
            callback_trace.append({"step": "edit_edge", "selected_id": created_link_id, "status": status})

            _, _, node_summary_text, edge_summary_text, studio_status = refresh_studio_callback(
                nodes_rows,
                candidate_links_rows,
                created_node_id,
                created_link_id,
                status,
            )
            callback_trace.append({"step": "refresh_studio", "selected_id": created_link_id, "status": studio_status})

            created_callback_result = save_callback(
                1,
                str(source_copy_dir),
                str(created_bundle_dir),
                nodes_rows,
                components_rows,
                candidate_links_rows,
                edge_component_rules_rows,
                route_rows,
                layout_constraints_rows,
                topology_rules_text,
                scenario_settings_text,
            )
            created_bundle_summary = json.loads(created_callback_result[1])
            created_execution_summary = json.loads(created_callback_result[10])
            callback_trace.append(
                {
                    "step": "save_created_bundle",
                    "selected_id": created_callback_result[0],
                    "status": created_execution_summary["error"],
                }
            )

            _, _, blocked_delete_status = delete_node_callback(
                1,
                created_callback_result[2],
                created_node_id,
                created_callback_result[4],
                created_callback_result[6],
            )
            callback_trace.append(
                {
                    "step": "delete_node_blocked_while_referenced",
                    "selected_id": created_node_id,
                    "status": blocked_delete_status,
                }
            )

            candidate_links_rows, next_edge_selected_id, status = delete_edge_callback(
                1,
                created_callback_result[4],
                created_link_id,
            )
            callback_trace.append({"step": "delete_edge", "selected_id": next_edge_selected_id, "status": status})

            nodes_rows, next_node_selected_id, status = delete_node_callback(
                1,
                created_callback_result[2],
                duplicated_node_id,
                candidate_links_rows,
                created_callback_result[6],
            )
            callback_trace.append({"step": "delete_duplicated_node", "selected_id": next_node_selected_id, "status": status})

            nodes_rows, next_node_selected_id, status = delete_node_callback(
                1,
                nodes_rows,
                created_node_id,
                candidate_links_rows,
                created_callback_result[6],
            )
            callback_trace.append({"step": "delete_created_node", "selected_id": next_node_selected_id, "status": status})

            final_callback_result = save_callback(
                1,
                created_callback_result[0],
                str(final_bundle_dir),
                nodes_rows,
                created_callback_result[3],
                candidate_links_rows,
                created_callback_result[5],
                created_callback_result[6],
                created_callback_result[7],
                created_callback_result[8],
                created_callback_result[9],
            )
            final_bundle_summary = json.loads(final_callback_result[1])
            final_execution_summary = json.loads(final_callback_result[10])
            callback_trace.append(
                {
                    "step": "save_final_bundle",
                    "selected_id": final_callback_result[0],
                    "status": final_execution_summary["error"],
                }
            )

        created_bundle = load_scenario_bundle(created_bundle_dir)
        final_bundle = load_scenario_bundle(final_bundle_dir)

        payload = {
            "scenario_dirs": {
                "source_copy": str(source_copy_dir.resolve()),
                "created_bundle": str(created_bundle_dir.resolve()),
                "final_bundle": str(final_bundle_dir.resolve()),
            },
            "callback_trace": callback_trace,
            "selected_forms": {
                "created_node": {
                    "selected_node_id": selected_node_form[0],
                    "node_id": selected_node_form[1],
                    "label": selected_node_form[2],
                },
                "duplicated_node": {
                    "selected_node_id": duplicated_node_form[0],
                    "node_id": duplicated_node_form[1],
                    "label": duplicated_node_form[2],
                },
                "created_edge": {
                    "selected_link_id": created_edge_form[0],
                    "link_id": created_edge_form[1],
                    "from_node": created_edge_form[2],
                    "to_node": created_edge_form[3],
                },
            },
            "summaries": {
                "node_summary": json.loads(node_summary_text),
                "edge_summary": json.loads(edge_summary_text),
                "created_bundle_io_summary": created_bundle_summary,
                "created_execution_summary": created_execution_summary,
                "final_bundle_io_summary": final_bundle_summary,
                "final_execution_summary": final_execution_summary,
            },
            "assertions": {
                "created_bundle_kept_canonical_manifest": created_bundle.bundle_manifest_path is not None,
                "created_bundle_kept_component_catalog": created_bundle.resolved_files["components.csv"].name == "component_catalog.csv",
                "created_node_persisted": created_node_id in created_bundle.nodes["node_id"].tolist(),
                "duplicated_node_persisted": duplicated_node_id in created_bundle.nodes["node_id"].tolist(),
                "created_edge_persisted": created_link_id in created_bundle.candidate_links["link_id"].tolist(),
                "delete_node_blocked_when_referenced": "requires explicit reconciliation" in blocked_delete_status,
                "final_bundle_removed_created_node": created_node_id not in final_bundle.nodes["node_id"].tolist(),
                "final_bundle_removed_duplicated_node": duplicated_node_id not in final_bundle.nodes["node_id"].tolist(),
                "final_bundle_removed_created_edge": created_link_id not in final_bundle.candidate_links["link_id"].tolist(),
                "created_execution_has_no_error": created_execution_summary["error"] is None,
                "final_execution_has_no_error": final_execution_summary["error"] is None,
                "created_execution_kept_provenance": (
                    created_execution_summary["scenario_provenance"]["requested_dir_matches_bundle_root"] is True
                ),
                "final_execution_kept_provenance": (
                    final_execution_summary["scenario_provenance"]["requested_dir_matches_bundle_root"] is True
                ),
            },
        }

        artifact_path = artifact_dir / "studio_structural_validation.json"
        artifact_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        _write_readme(artifact_dir, payload)
        return artifact_path
    finally:
        _cleanup(source_copy_dir)


def main() -> None:
    args = _parse_args()
    artifact_dir = Path(args.artifact_dir).expanduser().resolve()
    source_scenario = Path(args.source_scenario).expanduser().resolve()
    artifact_path = run_validation(artifact_dir=artifact_dir, source_scenario=source_scenario)
    print(artifact_path)


if __name__ == "__main__":
    main()
