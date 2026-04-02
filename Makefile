.PHONY: install test smoke

install:
	python -m pip install --upgrade pip
	pip install -r requirements.txt
	pip install -e .

smoke:
	python -m agri_circuit_optimizer.solve.run_case --scenario data/scenario/example --dry-run

test:
	pytest -q
