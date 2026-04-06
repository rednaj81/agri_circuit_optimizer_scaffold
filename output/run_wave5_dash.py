import sys
from pathlib import Path
repo = Path(r'C:\d\dev\agri_circuit_optimizer_scaffold')
sys.path.insert(0, str(repo / 'src'))
sys.path.insert(0, str(repo))
from decision_platform.ui_dash.app import build_app
from tests.decision_platform.scenario_utils import diagnostic_runtime_test_mode
with diagnostic_runtime_test_mode():
    app = build_app('data/decision_platform/maquete_v2')
app.run(host='127.0.0.1', port=8060, debug=False)
