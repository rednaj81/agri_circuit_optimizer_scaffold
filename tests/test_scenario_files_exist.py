from pathlib import Path

from agri_circuit_optimizer.config import REQUIRED_SCENARIO_FILES


def test_example_scenario_files_exist():
    base = Path("data/scenario/example")
    for name in REQUIRED_SCENARIO_FILES:
        assert (base / name).exists(), f"Missing scenario file: {name}"
