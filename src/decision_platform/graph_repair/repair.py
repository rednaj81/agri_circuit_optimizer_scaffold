from __future__ import annotations

from typing import Any

from decision_platform.data_io.loader import ScenarioBundle


def normalize_candidate(candidate: dict[str, Any], bundle: ScenarioBundle) -> dict[str, Any]:
    normalized = dict(candidate)
    normalized["installed_links"] = dict(candidate["installed_links"])
    normalized["installed_link_ids"] = sorted(candidate["installed_links"])
    return normalized
