from __future__ import annotations

import shutil
from uuid import uuid4
from pathlib import Path

import pandas as pd
import pytest

from agri_circuit_optimizer.io.load_data import ScenarioValidationError, load_scenario


EXAMPLE_SCENARIO = Path("data/scenario/example")


def _copy_example() -> Path:
    base_dir = Path("tests/_tmp") / f"scenario-test-{uuid4().hex}"
    base_dir.mkdir(parents=True, exist_ok=False)
    scenario_dir = base_dir / "scenario"
    shutil.copytree(EXAMPLE_SCENARIO, scenario_dir)
    return scenario_dir


def test_loader_normalizes_boolean_and_numeric_types():
    data = load_scenario(EXAMPLE_SCENARIO)

    assert data["nodes"]["is_source"].dtype == bool
    assert data["routes"]["mandatory"].dtype == bool
    assert data["components"]["available_qty"].dtype.kind in {"i", "u"}
    assert data["routes"]["q_min_delivered_lpm"].dtype.kind == "f"


def test_loader_fails_with_missing_required_column():
    scenario_dir = _copy_example()
    routes = pd.read_csv(scenario_dir / "routes.csv").drop(columns=["sink"])
    routes.to_csv(scenario_dir / "routes.csv", index=False)

    with pytest.raises(ScenarioValidationError, match="missing required columns"):
        load_scenario(scenario_dir)


def test_loader_rejects_route_into_w():
    scenario_dir = _copy_example()
    routes = pd.read_csv(scenario_dir / "routes.csv")
    routes.loc[0, "sink"] = "W"
    routes.to_csv(scenario_dir / "routes.csv", index=False)

    with pytest.raises(ScenarioValidationError, match="entering 'W'"):
        load_scenario(scenario_dir)


def test_loader_requires_recirculation_route():
    scenario_dir = _copy_example()
    routes = pd.read_csv(scenario_dir / "routes.csv")
    routes = routes[~((routes["source"] == "I") & (routes["sink"] == "IR"))]
    routes.to_csv(scenario_dir / "routes.csv", index=False)

    with pytest.raises(ScenarioValidationError, match="I -> IR"):
        load_scenario(scenario_dir)
