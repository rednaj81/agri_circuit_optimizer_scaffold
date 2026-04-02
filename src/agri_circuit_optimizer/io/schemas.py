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
}


REQUIRED_SETTINGS_KEYS = (
    "u_max_slots",
    "v_max_slots",
    "optional_route_reward",
    "robustness_weight",
    "cleaning_cost_liters_per_operation",
    "default_solver",
)
