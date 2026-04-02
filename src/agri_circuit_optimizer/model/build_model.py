from __future__ import annotations

from typing import Any, Dict

from agri_circuit_optimizer.model.constraints_capacity import add_capacity_constraints
from agri_circuit_optimizer.model.constraints_hydraulics import add_hydraulic_constraints
from agri_circuit_optimizer.model.constraints_metering import add_metering_constraints
from agri_circuit_optimizer.model.constraints_structure import add_structure_constraints
from agri_circuit_optimizer.model.objective import add_objective
from agri_circuit_optimizer.model.sets_params import build_sets_and_parameters
from agri_circuit_optimizer.model.variables import declare_variables


def build_model(data: Dict[str, Any], options: Dict[str, Any]) -> Any:
    """Build a Pyomo model.

    The current scaffold returns an empty Pyomo ConcreteModel with metadata attached.
    Codex should expand this function across V1, V2 and V3.
    """
    try:
        import pyomo.environ as pyo
    except ModuleNotFoundError as exc:
        raise RuntimeError("Pyomo is required. Install requirements.txt first.") from exc

    payload = build_sets_and_parameters(data, options)
    model = pyo.ConcreteModel(name="agri_circuit_optimizer")
    model._payload = payload

    declare_variables(model)
    add_structure_constraints(model)
    add_capacity_constraints(model)
    add_metering_constraints(model)
    add_hydraulic_constraints(model)
    add_objective(model)

    return model
