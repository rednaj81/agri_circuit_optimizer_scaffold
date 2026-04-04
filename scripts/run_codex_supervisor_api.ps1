param(
    [string]$BindHost = "127.0.0.1",
    [int]$Port = 8787
)

$ErrorActionPreference = "Stop"

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$pythonExe = Join-Path $repoRoot ".venv\\Scripts\\python.exe"
$apiScript = Join-Path $repoRoot "automation\\codex_supervisor_api.py"

if (-not (Test-Path $pythonExe)) {
    throw "Python virtualenv not found at $pythonExe"
}

if (-not (Test-Path $apiScript)) {
    throw "Supervisor API script not found at $apiScript"
}

Write-Host "Running Codex supervisor API"
Write-Host "repo-root: $repoRoot"
Write-Host "host: $BindHost"
Write-Host "port: $Port"

& $pythonExe $apiScript --repo-root $repoRoot --host $BindHost --port $Port
