from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

import yaml


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


def cleanup_scenario_copy(target: str | Path) -> None:
    target_path = Path(target)
    if target_path.exists():
        shutil.rmtree(target_path)


def _deep_update(target: dict[str, Any], updates: dict[str, Any]) -> None:
    for key, value in updates.items():
        if isinstance(value, dict) and isinstance(target.get(key), dict):
            _deep_update(target[key], value)
            continue
        target[key] = value
