param(
    [int]$Port = 8060,
    [string]$OutputPath = "output/playwright/studio-fullhd-wave7.png"
)

$ErrorActionPreference = "Stop"
$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$pythonExe = Join-Path $repoRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $pythonExe)) {
    $pythonExe = "python"
}
$serverScript = Join-Path $repoRoot "output\run_wave5_dash.py"
$captureScript = Join-Path $repoRoot "scripts\capture_edge_window.py"
$profileDir = Join-Path $repoRoot "output\edge-wave7-profile"
$resolvedOutput = Join-Path $repoRoot $OutputPath
$serverLog = Join-Path $repoRoot "output\playwright\wave7-server.log"
$serverJobLog = Join-Path $repoRoot "output\playwright\wave7-server-job.log"

New-Item -ItemType Directory -Force -Path (Split-Path -Parent $resolvedOutput) | Out-Null
New-Item -ItemType Directory -Force -Path $profileDir | Out-Null

$serverJob = Start-Job -ScriptBlock {
    param($Root, $PythonExe, $ServerScript, $ServerLog)
    Set-Location $Root
    & $PythonExe $ServerScript *>&1 | Tee-Object -FilePath $ServerLog
} -ArgumentList $repoRoot, $pythonExe, $serverScript, $serverLog

try {
    $ready = $false
    for ($i = 0; $i -lt 30; $i++) {
        Start-Sleep -Seconds 1
        try {
            $status = (Invoke-WebRequest -Uri "http://127.0.0.1:$Port/?tab=studio" -UseBasicParsing -TimeoutSec 2).StatusCode
            if ($status -eq 200) {
                $ready = $true
                break
            }
        } catch {}
    }
    if (-not $ready) {
        throw "Studio server did not become ready on http://127.0.0.1:$Port/?tab=studio"
    }

    & $pythonExe $captureScript `
        --url "http://127.0.0.1:$Port/?tab=studio" `
        --output $resolvedOutput `
        --profile-dir $profileDir `
        --width 1920 `
        --height 1080 `
        --wait-seconds 12

    Get-Item $resolvedOutput | Select-Object FullName, Length, LastWriteTime
} finally {
    Receive-Job $serverJob -Keep | Out-String | Set-Content $serverJobLog
    Stop-Job $serverJob -ErrorAction SilentlyContinue
    Remove-Job $serverJob -ErrorAction SilentlyContinue
}
