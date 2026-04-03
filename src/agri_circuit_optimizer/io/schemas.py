from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass(frozen=True)
class ScenarioPaths:
    base_dir: Path
    nodes_csv: Path
    routes_csv: Path
    components_csv: Path
    source_branch_templates_csv: Path
    destination_branch_templates_csv: Path
    trunk_templates_csv: Path
    settings_yaml: Path
    edges_csv: Path
    topology_rules_yaml: Path


@dataclass(frozen=True)
class NodeRecord:
    node_id: str
    node_type: str
    is_source: bool
    is_sink: bool
    is_pure_source: bool
    is_final_sink: bool
    x_m: Optional[float] = None
    y_m: Optional[float] = None
    footprint_w_m: Optional[float] = None
    footprint_d_m: Optional[float] = None
    mount_height_m: Optional[float] = None
    node_role: Optional[str] = None
    preferred_topology_family: Optional[str] = None
    allow_service_loop: bool = False


@dataclass(frozen=True)
class RouteRecord:
    route_id: str
    source: str
    sink: str
    mandatory: bool
    q_min_delivered_lpm: float
    measurement_required: bool
    dose_min_l: float
    dose_error_max_pct: float
    weight: float
    need_pump: bool
    route_group: str = "core"
    allow_multi_stage_path: bool = False
    max_active_pumps: Optional[int] = None
    max_reading_meters: Optional[int] = None
    route_notes: str = ""


@dataclass(frozen=True)
class ComponentRecord:
    component_id: str
    category: str
    subtype: str
    cost: float
    available_qty: int
    sys_diameter_class: str
    q_min_lpm: float
    q_max_lpm: float
    loss_lpm_equiv: float
    internal_volume_l: float
    meter_error_pct: Optional[float] = None
    meter_batch_min_l: Optional[float] = None
    meter_dose_q_max_lpm: Optional[float] = None
    has_check: bool = False
    has_valve: bool = False
    is_bypass: bool = False
    is_empty_option: bool = False
    hose_length_m: Optional[float] = None
    hose_loss_pct_per_m: Optional[float] = None
    is_extra: bool = False
    extra_penalty_group: Optional[str] = None
    consume_connector_in_trunk: Optional[bool] = None
    preferred_for_maquette: Optional[bool] = None


@dataclass(frozen=True)
class ScenarioTableSchema:
    required_columns: tuple[str, ...]
    boolean_columns: tuple[str, ...] = ()
    integer_columns: tuple[str, ...] = ()
    float_columns: tuple[str, ...] = ()
    nullable_float_columns: tuple[str, ...] = ()
    string_columns: tuple[str, ...] = ()
    optional_boolean_columns: tuple[str, ...] = ()
    optional_integer_columns: tuple[str, ...] = ()
    optional_float_columns: tuple[str, ...] = ()
    optional_nullable_float_columns: tuple[str, ...] = ()
    optional_string_columns: tuple[str, ...] = ()
    allow_blank_string_columns: tuple[str, ...] = ()


SCENARIO_TABLE_SCHEMAS = {
    "nodes": ScenarioTableSchema(
        required_columns=(
            "node_id",
            "node_type",
            "is_source",
            "is_sink",
            "is_pure_source",
            "is_final_sink",
        ),
        boolean_columns=("is_source", "is_sink", "is_pure_source", "is_final_sink"),
        string_columns=("node_id", "node_type"),
        optional_float_columns=("x_m", "y_m", "footprint_w_m", "footprint_d_m", "mount_height_m"),
        optional_string_columns=("node_role", "preferred_topology_family"),
        optional_boolean_columns=("allow_service_loop",),
    ),
    "routes": ScenarioTableSchema(
        required_columns=(
            "route_id",
            "source",
            "sink",
            "mandatory",
            "q_min_delivered_lpm",
            "measurement_required",
            "dose_min_l",
            "dose_error_max_pct",
            "weight",
            "need_pump",
        ),
        boolean_columns=("mandatory", "measurement_required", "need_pump"),
        float_columns=("q_min_delivered_lpm", "dose_min_l", "dose_error_max_pct", "weight"),
        string_columns=("route_id", "source", "sink"),
        optional_string_columns=("route_group", "route_notes"),
        optional_boolean_columns=("allow_multi_stage_path",),
        optional_integer_columns=("max_active_pumps", "max_reading_meters"),
    ),
    "components": ScenarioTableSchema(
        required_columns=(
            "component_id",
            "category",
            "subtype",
            "cost",
            "available_qty",
            "sys_diameter_class",
            "q_min_lpm",
            "q_max_lpm",
            "loss_lpm_equiv",
            "internal_volume_l",
            "meter_error_pct",
            "meter_batch_min_l",
            "meter_dose_q_max_lpm",
            "has_check",
            "has_valve",
            "is_bypass",
            "is_empty_option",
        ),
        boolean_columns=("has_check", "has_valve", "is_bypass", "is_empty_option"),
        integer_columns=("available_qty",),
        float_columns=(
            "cost",
            "q_min_lpm",
            "q_max_lpm",
            "loss_lpm_equiv",
            "internal_volume_l",
        ),
        nullable_float_columns=(
            "meter_error_pct",
            "meter_batch_min_l",
            "meter_dose_q_max_lpm",
        ),
        string_columns=("component_id", "category", "subtype", "sys_diameter_class"),
        optional_nullable_float_columns=("hose_length_m", "hose_loss_pct_per_m"),
        optional_boolean_columns=("is_extra", "consume_connector_in_trunk", "preferred_for_maquette"),
        optional_string_columns=("extra_penalty_group",),
    ),
    "source_branch_templates": ScenarioTableSchema(
        required_columns=(
            "template_id",
            "allowed_node_ids",
            "require_valve",
            "require_check",
            "allowed_hose_diameters",
            "allowed_adaptor_pairs",
            "notes",
        ),
        boolean_columns=("require_valve", "require_check"),
        string_columns=(
            "template_id",
            "allowed_node_ids",
            "allowed_hose_diameters",
            "allowed_adaptor_pairs",
            "notes",
        ),
        allow_blank_string_columns=("allowed_adaptor_pairs",),
        optional_string_columns=("branch_role",),
    ),
    "destination_branch_templates": ScenarioTableSchema(
        required_columns=(
            "template_id",
            "allowed_node_ids",
            "require_valve",
            "require_check",
            "allowed_hose_diameters",
            "allowed_adaptor_pairs",
            "notes",
        ),
        boolean_columns=("require_valve", "require_check"),
        string_columns=(
            "template_id",
            "allowed_node_ids",
            "allowed_hose_diameters",
            "allowed_adaptor_pairs",
            "notes",
        ),
        allow_blank_string_columns=("allowed_adaptor_pairs",),
        optional_string_columns=("branch_role",),
    ),
    "trunk_templates": ScenarioTableSchema(
        required_columns=("template_id", "stage_kind", "allowed_diameters", "notes"),
        string_columns=("template_id", "stage_kind", "allowed_diameters", "notes"),
        optional_boolean_columns=("consume_connector",),
    ),
    "edges": ScenarioTableSchema(
        required_columns=(
            "edge_id",
            "from_node",
            "to_node",
            "edge_kind",
            "direction_mode",
            "can_be_active",
            "must_be_closed_if_unused",
            "default_installed",
            "component_ids",
        ),
        boolean_columns=("can_be_active", "must_be_closed_if_unused", "default_installed"),
        string_columns=(
            "edge_id",
            "from_node",
            "to_node",
            "edge_kind",
            "direction_mode",
            "component_ids",
        ),
        optional_float_columns=("length_m",),
        optional_boolean_columns=(
            "counts_towards_hose_total",
            "counts_towards_connector_total",
        ),
        optional_string_columns=("topology_family", "group_id", "notes", "branch_role"),
        allow_blank_string_columns=("topology_family", "group_id", "notes", "branch_role"),
    ),
}


REQUIRED_SETTINGS_KEYS = (
    "u_max_slots",
    "v_max_slots",
    "optional_route_reward",
    "robustness_weight",
    "cleaning_cost_liters_per_operation",
    "default_solver",
)
