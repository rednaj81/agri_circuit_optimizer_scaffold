from __future__ import annotations

import shutil
from pathlib import Path
from uuid import uuid4

import pandas as pd
import yaml


EXAMPLE_SCENARIO = Path("data/scenario/example")
MAQUETE_SCENARIO = Path("data/scenario/maquete_core")
MAQUETE_BUS_SCENARIO = Path("data/scenario/maquete_bus_manual")


def copy_example_scenario() -> Path:
    return _copy_scenario(EXAMPLE_SCENARIO, "scenario-test")


def copy_maquete_scenario() -> Path:
    return _copy_scenario(MAQUETE_SCENARIO, "maquete-test")


def copy_maquete_bus_scenario() -> Path:
    return _copy_scenario(MAQUETE_BUS_SCENARIO, "maquete-bus-test")


def _copy_scenario(source: Path, prefix: str) -> Path:
    base_dir = Path("tests/_tmp") / f"{prefix}-{uuid4().hex}"
    base_dir.mkdir(parents=True, exist_ok=False)
    scenario_dir = base_dir / "scenario"
    shutil.copytree(source, scenario_dir)
    return scenario_dir


def read_csv(path: Path, name: str) -> pd.DataFrame:
    return pd.read_csv(path / f"{name}.csv")


def write_csv(path: Path, name: str, frame: pd.DataFrame) -> None:
    frame.to_csv(path / f"{name}.csv", index=False)


def keep_routes(path: Path, route_ids: list[str]) -> None:
    routes = read_csv(path, "routes")
    write_csv(path, "routes", routes[routes["route_id"].isin(route_ids)].copy())


def read_settings(path: Path) -> dict:
    return yaml.safe_load((path / "settings.yaml").read_text(encoding="utf-8"))


def write_settings(path: Path, settings: dict) -> None:
    (path / "settings.yaml").write_text(yaml.safe_dump(settings, sort_keys=False), encoding="utf-8")
