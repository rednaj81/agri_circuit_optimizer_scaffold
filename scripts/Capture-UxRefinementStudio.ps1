param(
    [int]$Port = 8060,
    [string]$OutputPath = "output/playwright/studio-fullhd-wave9.png"
)

$ErrorActionPreference = "Stop"
$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$pythonExe = Join-Path $repoRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $pythonExe)) {
    $pythonExe = "python"
}
$edgeExe = "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
$serverScript = Join-Path $repoRoot "output\run_wave5_dash.py"
$profileDir = Join-Path $repoRoot "output\edge-wave9-headless-profile"
$resolvedOutput = Join-Path $repoRoot $OutputPath
$assessmentOutput = Join-Path $repoRoot "output\playwright\studio-fullhd-wave9-assessment.json"
$serverLog = Join-Path $repoRoot "output\playwright\wave9-server.log"
$serverJobLog = Join-Path $repoRoot "output\playwright\wave9-server-job.log"
$edgeStdoutLog = Join-Path $repoRoot "output\playwright\wave9-edge-native.stdout.log"
$edgeStderrLog = Join-Path $repoRoot "output\playwright\wave9-edge-native.stderr.log"
$targetUrl = "http://127.0.0.1:$Port/?tab=studio"

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
            $status = (Invoke-WebRequest -Uri $targetUrl -UseBasicParsing -TimeoutSec 2).StatusCode
            if ($status -eq 200) {
                $ready = $true
                break
            }
        } catch {}
    }
    if (-not $ready) {
        throw "Studio server did not become ready on $targetUrl"
    }

    if (-not (Test-Path $edgeExe)) {
        throw "Edge executable not found at $edgeExe"
    }

    if (Test-Path $resolvedOutput) {
        Remove-Item $resolvedOutput -Force
    }

    foreach ($edgeLog in @($edgeStdoutLog, $edgeStderrLog)) {
        if (Test-Path $edgeLog) {
            Remove-Item $edgeLog -Force
        }
    }

    $edgeProcess = Start-Process `
        -FilePath $edgeExe `
        -ArgumentList @(
            "--user-data-dir=$profileDir",
            "--headless=new",
            "--disable-gpu",
            "--disable-extensions",
            "--no-first-run",
            "--no-default-browser-check",
            "--window-size=1920,1080",
            "--screenshot=$resolvedOutput",
            $targetUrl
        ) `
        -RedirectStandardOutput $edgeStdoutLog `
        -RedirectStandardError $edgeStderrLog `
        -PassThru `
        -Wait

    $edgeExitCode = $edgeProcess.ExitCode

    @"
from __future__ import annotations
import json
import sys
from pathlib import Path
from PIL import Image, ImageStat

output_path = Path(sys.argv[1])
assessment_path = Path(sys.argv[2])
edge_log_path = Path(sys.argv[3])
edge_stderr_log_path = Path(sys.argv[4])
target_url = sys.argv[5]
edge_exit_code = int(sys.argv[6])

result = {
    "url": target_url,
    "output": str(output_path),
    "edge_stdout_log": str(edge_log_path),
    "edge_stderr_log": str(edge_stderr_log_path),
    "edge_exit_code": edge_exit_code,
    "output_exists": output_path.exists(),
}

if output_path.exists():
    image = Image.open(output_path).convert("RGBA")
    colors = image.getcolors(maxcolors=10_000_000)
    extrema = image.getextrema()
    stat = ImageStat.Stat(image)
    unique_colors = len(colors) if colors else -1
    max_channel_spread = max(high - low for (low, high) in extrema[:3])
    stddev = [round(float(value), 3) for value in stat.stddev]
    result.update(
        {
            "size": [image.size[0], image.size[1]],
            "unique_colors": unique_colors,
            "extrema": extrema,
            "stddev": stddev,
            "max_channel_spread": max_channel_spread,
            "visually_useful": unique_colors != 1 and max_channel_spread > 8 and max(stddev[:3]) > 3.0,
        }
    )
else:
    result["visually_useful"] = False

assessment_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
if not result["visually_useful"]:
    raise SystemExit(1)
"@ | & $pythonExe - $resolvedOutput $assessmentOutput $edgeStdoutLog $edgeStderrLog $targetUrl $edgeExitCode

    if (Test-Path $resolvedOutput) {
        Get-Item $resolvedOutput, $assessmentOutput | Select-Object FullName, Length, LastWriteTime
    } else {
        Get-Item $assessmentOutput | Select-Object FullName, Length, LastWriteTime
    }
} finally {
    Receive-Job $serverJob -Keep | Out-String | Set-Content $serverJobLog
    Stop-Job $serverJob -ErrorAction SilentlyContinue
    Remove-Job $serverJob -ErrorAction SilentlyContinue
}
