import base64
import json
import subprocess
import time
from pathlib import Path

import requests
import websocket

ROOT = Path(r'C:\d\dev\agri_circuit_optimizer_scaffold')
OUT = ROOT / 'output' / 'playwright'
OUT.mkdir(parents=True, exist_ok=True)
server = subprocess.Popen([str(ROOT / '.venv' / 'Scripts' / 'python.exe'), str(ROOT / 'output' / 'run_wave5_dash.py')], cwd=ROOT)
chrome = None
ws = None
try:
    for _ in range(40):
        try:
            if requests.get('http://127.0.0.1:8060', timeout=2).status_code == 200:
                break
        except Exception:
            time.sleep(1)
    else:
        raise RuntimeError('Dash app did not become ready')

    chrome_profile = ROOT / 'output' / 'chrome-cdp'
    chrome_profile.mkdir(parents=True, exist_ok=True)
    chrome = subprocess.Popen([
        r'C:\Program Files\Google\Chrome\Application\chrome.exe',
        '--headless=new',
        '--disable-gpu',
        '--no-sandbox',
        '--remote-debugging-port=9222',
        '--window-size=1440,2200',
        f'--user-data-dir={chrome_profile}',
        'about:blank',
    ], cwd=ROOT)
    for _ in range(20):
        try:
            version = requests.get('http://127.0.0.1:9222/json/version', timeout=2).json()
            if version.get('Browser'):
                break
        except Exception:
            time.sleep(1)
    else:
        raise RuntimeError('Chrome CDP did not become ready')

    target = requests.put('http://127.0.0.1:9222/json/new?http://127.0.0.1:8060').json()
    ws = websocket.create_connection(target['webSocketDebuggerUrl'], timeout=15)
    msg_id = [0]

    def send(method, params=None):
        msg_id[0] += 1
        current = msg_id[0]
        ws.send(json.dumps({'id': current, 'method': method, 'params': params or {}}))
        while True:
            raw = ws.recv()
            payload = json.loads(raw)
            if payload.get('id') == current:
                return payload

    def eval_js(script):
        result = send('Runtime.evaluate', {'expression': script, 'awaitPromise': True, 'returnByValue': True})
        return (((result.get('result') or {}).get('result') or {}).get('value'))

    def screenshot(name):
        snap = send('Page.captureScreenshot', {'format': 'png', 'captureBeyondViewport': True, 'fromSurface': True})
        data = ((snap.get('result') or {}).get('data'))
        (OUT / name).write_bytes(base64.b64decode(data))

    send('Page.enable')
    send('Runtime.enable')
    send('Emulation.setDeviceMetricsOverride', {'width': 1440, 'height': 2200, 'deviceScaleFactor': 1, 'mobile': False})
    send('Page.navigate', {'url': 'http://127.0.0.1:8060'})
    time.sleep(5)
    screenshot('wave5-studio.png')

    tab_script = """(label => {
      const tabs = [...document.querySelectorAll('[role=\"tab\"]')];
      const target = tabs.find(el => (el.textContent || '').trim() === label);
      if (!target) return false;
      target.click();
      return true;
    })(TAB_LABEL)"""

    for label, filename in [('Runs', 'wave5-runs.png'), ('Decisão', 'wave5-decisao.png'), ('Auditoria', 'wave5-auditoria.png')]:
        eval_js(tab_script.replace('TAB_LABEL', json.dumps(label)))
        time.sleep(2)
        screenshot(filename)

    print('ok')
finally:
    try:
        if ws is not None:
            ws.close()
    except Exception:
        pass
    if chrome is not None:
        chrome.terminate()
        try:
            chrome.wait(timeout=5)
        except Exception:
            chrome.kill()
    if server is not None:
        server.terminate()
        try:
            server.wait(timeout=5)
        except Exception:
            server.kill()
