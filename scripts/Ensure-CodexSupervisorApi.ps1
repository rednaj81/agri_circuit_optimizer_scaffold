param(
    [string]$BindHost = "127.0.0.1",
    [int]$Port = 8787
)

$ErrorActionPreference = "Stop"

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$runtimeRoot = Join-Path $repoRoot "docs\\codex_dual_agent_runtime\\api"
$statePath = Join-Path $runtimeRoot "server_state.json"
$runScript = Join-Path $repoRoot "scripts\\run_codex_supervisor_api.ps1"
$pwshPath = (Get-Command pwsh -ErrorAction SilentlyContinue).Source
if (-not $pwshPath) {
    $pwshPath = (Get-Command powershell -ErrorAction Stop).Source
}

New-Item -ItemType Directory -Force -Path $runtimeRoot | Out-Null

$healthy = $false
try {
    $response = Invoke-WebRequest -UseBasicParsing -Uri ("http://{0}:{1}/health" -f $BindHost, $Port) -TimeoutSec 3
    if ($response.StatusCode -eq 200) {
        $healthy = $true
    }
}
catch {
    $healthy = $false
}

if ($healthy) {
    Write-Host "Supervisor API already healthy at http://$BindHost`:$Port"
    exit 0
}

$stdoutPath = Join-Path $runtimeRoot "server.stdout.log"
$stderrPath = Join-Path $runtimeRoot "server.stderr.log"

$process = Start-Process -FilePath $pwshPath -ArgumentList @(
    '-ExecutionPolicy', 'Bypass',
    '-NoLogo',
    '-NoProfile',
    '-File', $runScript,
    '-BindHost', $BindHost,
    '-Port', $Port
) -WorkingDirectory $repoRoot -WindowStyle Hidden -PassThru -RedirectStandardOutput $stdoutPath -RedirectStandardError $stderrPath

$maxAttempts = 10
for ($attempt = 1; $attempt -le $maxAttempts; $attempt++) {
    Start-Sleep -Seconds 1
    try {
        $response = Invoke-WebRequest -UseBasicParsing -Uri ("http://{0}:{1}/health" -f $BindHost, $Port) -TimeoutSec 3
        if ($response.StatusCode -eq 200) {
            Write-Host "Supervisor API healthy at http://$BindHost`:$Port (pid=$($process.Id))"
            exit 0
        }
    }
    catch {
    }
}

Write-Host "Supervisor API start requested at http://$BindHost`:$Port but healthcheck did not pass in time."
if (Test-Path -LiteralPath $stderrPath) {
    Get-Content -LiteralPath $stderrPath | Write-Host
}
exit 1
