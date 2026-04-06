$proc = Start-Process -FilePath .\.venv\Scripts\python.exe -ArgumentList 'output\run_wave5_dash.py' -WorkingDirectory 'C:\d\dev\agri_circuit_optimizer_scaffold' -PassThru
$proc.Id | Set-Content output\run_wave5_dash.pid
Start-Sleep -Seconds 6
try { Write-Output ((Invoke-WebRequest -Uri http://127.0.0.1:8060 -UseBasicParsing -TimeoutSec 2).StatusCode) } catch { Write-Output $_.Exception.Message }
