from __future__ import annotations

from contextlib import contextmanager
from copy import deepcopy
import shutil
from pathlib import Path
from typing import Any, Callable

import pandas as pd
import yaml

from decision_platform.julia_bridge.bridge import disable_real_julia_probe


MAQUETE_V2_ACCEPTANCE_OVERRIDES: dict[str, Any] = {
    "candidate_generation": {
        "population_size": 12,
        "generations": 3,
        "keep_top_n_per_family": 6,
    },
}


def prepare_scenario_copy(
    source_dir: str | Path,
    target_name: str,
    *,
    scenario_overrides: dict[str, Any] | None = None,
) -> Path:
    source = Path(source_dir)
    target = Path("tests/_tmp") / target_name
    if target.exists():
        shutil.rmtree(target)
    shutil.copytree(source, target)
    if scenario_overrides:
        settings_path = target / "scenario_settings.yaml"
        settings = yaml.safe_load(settings_path.read_text(encoding="utf-8")) or {}
        _deep_update(settings, scenario_overrides)
        settings_path.write_text(yaml.safe_dump(settings, sort_keys=False), encoding="utf-8")
    return target


def prepare_maquete_v2_acceptance_scenario(
    target_name: str,
    *,
    scenario_overrides: dict[str, Any] | None = None,
) -> Path:
    merged_overrides = deepcopy(MAQUETE_V2_ACCEPTANCE_OVERRIDES)
    if scenario_overrides:
        _deep_update(merged_overrides, scenario_overrides)
    return prepare_scenario_copy(
        "data/decision_platform/maquete_v2",
        target_name,
        scenario_overrides=merged_overrides,
    )


def cleanup_scenario_copy(target: str | Path) -> None:
    target_path = Path(target)
    if target_path.exists():
        shutil.rmtree(target_path)


def update_scenario_table(
    scenario_dir: str | Path,
    filename: str,
    updater: Callable[[pd.DataFrame], pd.DataFrame],
) -> Path:
    table_path = Path(scenario_dir) / filename
    frame = pd.read_csv(table_path)
    updated = updater(frame.copy())
    if updated is None:
        raise ValueError(f"Scenario table updater for '{filename}' must return a DataFrame.")
    updated.to_csv(table_path, index=False, lineterminator="\n")
    return table_path


@contextmanager
def diagnostic_runtime_test_mode():
    with disable_real_julia_probe():
        yield


def _deep_update(target: dict[str, Any], updates: dict[str, Any]) -> None:
    for key, value in updates.items():
        if isinstance(value, dict) and isinstance(target.get(key), dict):
            _deep_update(target[key], value)
            continue
        target[key] = value
