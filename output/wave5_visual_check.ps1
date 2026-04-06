New-Item -ItemType Directory -Force output\playwright | Out-Null
$proc = Start-Process -FilePath .\.venv\Scripts\python.exe -ArgumentList 'output\run_wave5_dash.py' -WorkingDirectory 'C:\d\dev\agri_circuit_optimizer_scaffold' -PassThru
try {
  $ready = $false
  for ($i = 0; $i -lt 30; $i++) {
    Start-Sleep -Seconds 1
    try {
      $status = (Invoke-WebRequest -Uri http://127.0.0.1:8060 -UseBasicParsing -TimeoutSec 2).StatusCode
      if ($status -eq 200) { $ready = $true; break }
    } catch {}
  }
  if (-not $ready) { throw 'Dash app did not become ready on http://127.0.0.1:8060' }
  @'
const { chromium } = require('playwright');
(async() => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1440, height: 1600 } });
  await page.goto('http://127.0.0.1:8060', { waitUntil: 'networkidle' });
  await page.screenshot({ path: 'output/playwright/wave5-studio.png', fullPage: true });
  await browser.close();
})();
'@ | npx -y -p playwright node -
}
finally {
  if ($proc -and !$proc.HasExited) { Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue }
}
