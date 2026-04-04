from __future__ import annotations

import pytest

from decision_platform.api.run_pipeline import run_decision_pipeline
from tests.decision_platform.scenario_utils import cleanup_scenario_copy, prepare_scenario_copy


@pytest.fixture(scope="session")
def maquete_v2_fallback_runtime() -> dict[str, object]:
    scenario_dir = prepare_scenario_copy(
        "data/decision_platform/maquete_v2",
        "maquete_v2_session_fallback_runtime",
        scenario_overrides={"hydraulic_engine": {"fallback": "python_emulated_julia"}},
    )
    try:
        result = run_decision_pipeline(
            scenario_dir,
            allow_diagnostic_python_emulation=True,
        )
        yield {
            "scenario_dir": scenario_dir,
            "result": result,
        }
    finally:
        cleanup_scenario_copy(scenario_dir)
