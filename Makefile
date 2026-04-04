.PHONY: install test smoke decision-platform-validate decision-platform-validate-official decision-platform-validate-diagnostic decision-platform-validate-diagnostic-comparison

install:
	python -m pip install --upgrade pip
	pip install -r requirements.txt
	pip install -e .

smoke:
	python -m agri_circuit_optimizer.solve.run_case --scenario data/scenario/example --dry-run

test:
	pytest -q

decision-platform-validate: decision-platform-validate-official

decision-platform-validate-official:
	pwsh -NoProfile -File scripts/run_decision_platform_runtime_validation.ps1 -Mode official

decision-platform-validate-diagnostic:
	pwsh -NoProfile -File scripts/run_decision_platform_runtime_validation.ps1 -Mode diagnostic -DisableRealJuliaProbe

decision-platform-validate-diagnostic-comparison:
	pwsh -NoProfile -File scripts/run_decision_platform_runtime_validation.ps1 -Mode diagnostic -DisableRealJuliaProbe -IncludeEngineComparison
