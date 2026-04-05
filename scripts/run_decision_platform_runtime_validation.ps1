[CmdletBinding()]
param(
    [ValidateSet("official", "diagnostic")]
    [string]$Mode = "official",
    [string]$ScenarioDir = "data/decision_platform/maquete_v2",
    [string]$OutputDir,
    [string]$LogsDir = "scripts/logs",
    [string]$ManifestPath = "docs/codex_dual_agent_runtime/phase_0_validation_manifest.json",
    [switch]$IncludeEngineComparison,
    [switch]$OfficialPreflight,
    [switch]$DisableRealJuliaProbe,
    [switch]$DryRun
)

Set-StrictMode -Version 3.0
$ErrorActionPreference = "Stop"

$script:RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$script:ProfilesPath = Join-Path $PSScriptRoot "decision_platform_runtime_validation_profiles.json"
$script:ProfilesConfig = Get-Content -LiteralPath $script:ProfilesPath -Raw | ConvertFrom-Json -AsHashtable
$script:SharedProfile = $script:ProfilesConfig["shared"]
$script:ProbeOverrideEnv = [string]$script:ProfilesConfig["probe_override_env"]
$script:PythonExe = Join-Path $script:RepoRoot ".venv\Scripts\python.exe"
$script:JuliaDepotDir = Join-Path $script:RepoRoot "julia_depot_runtime"
$script:ResolvedManifestPath = if ([System.IO.Path]::IsPathRooted($ManifestPath)) { $ManifestPath } else { Join-Path $script:RepoRoot $ManifestPath }
$script:ReportTimestamp = Get-Date
$script:ValidationProfile = if ($OfficialPreflight) {
    "official_preflight"
}
elseif ($Mode -eq "official") {
    "official"
}
elseif ($IncludeEngineComparison) {
    "diagnostic_comparison"
}
else {
    "diagnostic"
}
$script:ProfileConfig = $script:ProfilesConfig["profiles"][$script:ValidationProfile]
$script:RuntimeScenarioDir = $null
$script:TemporaryScenarioDir = $null
$script:PreflightResult = $null

if (-not $script:ProfileConfig) {
    throw ("Perfil de validação não encontrado em {0}: {1}" -f $script:ProfilesPath, $script:ValidationProfile)
}

if ([string]::IsNullOrWhiteSpace($OutputDir)) {
    $OutputDir = [string]$script:ProfileConfig["default_output_dir"]
}

$script:Report = [ordered]@{
    started_at = $script:ReportTimestamp.ToString("o")
    mode = $Mode
    validation_profile = $script:ValidationProfile
    profile_description = [string]$script:ProfileConfig["description"]
    validation_flow = [string]$script:ProfileConfig["validation_flow"]
    validation_sufficiency = [string]$script:ProfileConfig["validation_sufficiency"]
    official_gate_complete = ([string]$script:ProfileConfig["validation_sufficiency"] -eq "official_evidence")
    scenario_dir = $ScenarioDir
    output_dir = $OutputDir
    include_engine_comparison = [bool]$IncludeEngineComparison
    official_preflight = [bool]$OfficialPreflight
    disable_real_julia_probe = [bool]$DisableRealJuliaProbe
    dry_run = [bool]$DryRun
    repo_root = $script:RepoRoot
    profile_config_path = $script:ProfilesPath
    validation_manifest_path = $script:ResolvedManifestPath
    steps = @()
}

function Format-Duration {
    param(
        [Parameter(Mandatory = $true)]
        [TimeSpan]$Duration
    )

    return ("{0:00}:{1:00}:{2:00}.{3:000}" -f $Duration.Hours, $Duration.Minutes, $Duration.Seconds, $Duration.Milliseconds)
}

function Resolve-WorkspacePath {
    param(
        [Parameter(Mandatory = $true)]
        [string]$PathValue
    )

    if ([System.IO.Path]::IsPathRooted($PathValue)) {
        if (Test-Path -LiteralPath $PathValue) {
            return (Resolve-Path -LiteralPath $PathValue).Path
        }
        return $PathValue
    }

    $candidate = Join-Path $script:RepoRoot $PathValue
    if (Test-Path -LiteralPath $candidate) {
        return (Resolve-Path -LiteralPath $candidate).Path
    }
    return $candidate
}
function Read-JsonFile {
    param(
        [Parameter(Mandatory = $true)]
        [string]$PathValue
    )

    return Get-Content -LiteralPath $PathValue -Raw | ConvertFrom-Json -AsHashtable
}

function Write-JsonUtf8NoBom {
    param(
        [Parameter(Mandatory = $true)]
        [string]$PathValue,
        [Parameter(Mandatory = $true)]
        [object]$Payload
    )

    $json = $Payload | ConvertTo-Json -Depth 20
    $utf8NoBom = [System.Text.UTF8Encoding]::new($false)
    [System.IO.File]::WriteAllText($PathValue, $json, $utf8NoBom)
}

function Get-NestedValue {
    param(
        [Parameter(Mandatory = $true)]
        [hashtable]$Data,
        [Parameter(Mandatory = $true)]
        [string]$FieldPath
    )

    $current = $Data
    foreach ($segment in $FieldPath.Split(".")) {
        if ($current -isnot [hashtable] -or -not $current.ContainsKey($segment)) {
            throw ("Campo obrigatório ausente em {0}" -f $FieldPath)
        }
        $current = $current[$segment]
    }
    return $current
}

function Write-StepBanner {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Name
    )

    Write-Host ""
    Write-Host ("=== {0} ===" -f $Name) -ForegroundColor Cyan
}

function Save-Report {
    $logsPath = Resolve-WorkspacePath -PathValue $LogsDir
    if (-not (Test-Path -LiteralPath $logsPath)) {
        New-Item -ItemType Directory -Path $logsPath -Force | Out-Null
    }

    $reportPath = Join-Path $logsPath (
        "decision-platform-runtime-validation_{0}_{1}.json" -f $script:ValidationProfile, $script:ReportTimestamp.ToString("yyyyMMdd-HHmmss-fff")
    )
    $script:Report.report_path = $reportPath
    Write-JsonUtf8NoBom -PathValue $reportPath -Payload $script:Report
    return $reportPath
}

function Get-ReportStepDetails {
    param(
        [Parameter(Mandatory = $true)]
        [hashtable]$Report,
        [Parameter(Mandatory = $true)]
        [string]$StepName
    )

    foreach ($step in @($Report["steps"])) {
        if ([string]$step["name"] -eq $StepName) {
            if ($step.ContainsKey("details") -and $step["details"] -is [hashtable]) {
                return $step["details"]
            }
            return $null
        }
    }
    return $null
}

function New-ManifestProfileEntry {
    param(
        [Parameter(Mandatory = $true)]
        [string]$ProfileName,
        [Parameter(Mandatory = $true)]
        [hashtable]$ProfileDeclaration,
        [string]$LogsPath
    )

    $entry = [ordered]@{
        validation_profile = $ProfileName
        description = [string]$ProfileDeclaration["description"]
        validation_flow = [string]$ProfileDeclaration["validation_flow"]
        validation_sufficiency = [string]$ProfileDeclaration["validation_sufficiency"]
        official_gate_complete = ([string]$ProfileDeclaration["validation_sufficiency"] -eq "official_evidence")
        status = "not_run"
        success = $null
        last_report_path = $null
        started_at = $null
        finished_at = $null
        output_dir = Resolve-WorkspacePath -PathValue ([string]$ProfileDeclaration["default_output_dir"])
        runtime_scenario_dir = $null
        summary_path = $null
        evidence = $null
    }

    if (-not $LogsPath -or -not (Test-Path -LiteralPath $LogsPath)) {
        return $entry
    }

    $matchingReports = @()
    foreach ($candidateReport in @(Get-ChildItem -LiteralPath $LogsPath -Filter "decision-platform-runtime-validation_*.json")) {
        $candidateData = Read-JsonFile -PathValue $candidateReport.FullName
        if ([string]$candidateData["validation_profile"] -eq $ProfileName) {
            $matchingReports += [pscustomobject]@{
                File = $candidateReport
                Data = $candidateData
            }
        }
    }

    $latestReport = $matchingReports | Sort-Object { $_.File.LastWriteTime }, { $_.File.Name } | Select-Object -Last 1
    if (-not $latestReport) {
        return $entry
    }

    $report = $latestReport.Data
    $entry.status = if ([bool]$report["success"]) { "passed" } else { "failed" }
    $entry.success = [bool]$report["success"]
    $entry.last_report_path = $latestReport.File.FullName
    $entry.started_at = $report["started_at"]
    $entry.finished_at = $report["finished_at"]
    $entry.output_dir = $report["output_dir"]
    $entry.runtime_scenario_dir = $report["runtime_scenario_dir"]

    if ([string]$entry["validation_flow"] -eq "preflight") {
        $preflightDetails = Get-ReportStepDetails -Report $report -StepName "2. Executar preflight oficial"
        if ($preflightDetails) {
            $entry.evidence = [ordered]@{
                julia_available = $preflightDetails["julia_available"]
                watermodels_available = $preflightDetails["watermodels_available"]
                watermodels_probe_mode = $preflightDetails["watermodels_probe_mode"]
                runtime_policy_mode = $preflightDetails["runtime_policy_mode"]
                official_gate_valid = $preflightDetails["official_gate_valid"]
            }
        }
        return $entry
    }

    $summaryDetails = Get-ReportStepDetails -Report $report -StepName "3. Validar summary.json"
    $artifactDetails = Get-ReportStepDetails -Report $report -StepName "4. Validar artefatos principais"
    $profileArtifactDetails = Get-ReportStepDetails -Report $report -StepName "5. Validar artefatos do perfil"
    if ($summaryDetails) {
        $entry.summary_path = $summaryDetails["summary_path"]
    }
    $entry.evidence = [ordered]@{
        execution_mode = if ($summaryDetails) { $summaryDetails["execution_mode"] } else { $null }
        official_gate_valid = if ($summaryDetails) { $summaryDetails["official_gate_valid"] } else { $null }
        runtime_policy_mode = if ($summaryDetails) { $summaryDetails["runtime_policy_mode"] } else { $null }
        selected_candidate_id = if ($summaryDetails) { $summaryDetails["selected_candidate_id"] } else { $null }
        runtime_duration_s = if ($summaryDetails) { $summaryDetails["runtime_duration_s"] } else { $null }
        engine_used = if ($artifactDetails) { $artifactDetails["engine_used"] } else { $null }
        required_artifacts = if ($profileArtifactDetails) { @($profileArtifactDetails["required"]) } else { @() }
        forbidden_artifacts = if ($profileArtifactDetails) { @($profileArtifactDetails["forbidden"]) } else { @() }
    }
    return $entry
}

function Save-Phase0ValidationManifest {
    param(
        [Parameter(Mandatory = $true)]
        [string]$LogsPath
    )

    $manifestDirectory = Split-Path -Path $script:ResolvedManifestPath -Parent
    if (-not (Test-Path -LiteralPath $manifestDirectory)) {
        New-Item -ItemType Directory -Path $manifestDirectory -Force | Out-Null
    }

    $profiles = [ordered]@{}
    foreach ($profileName in @($script:ProfilesConfig["profiles"].Keys | Sort-Object)) {
        $profiles[$profileName] = New-ManifestProfileEntry -ProfileName ([string]$profileName) -ProfileDeclaration $script:ProfilesConfig["profiles"][[string]$profileName] -LogsPath $LogsPath
    }

    $manifest = [ordered]@{
        phase_id = "phase_0"
        generated_at = (Get-Date).ToString("o")
        script_path = $PSCommandPath
        profiles_path = $script:ProfilesPath
        logs_dir = $LogsPath
        official_validation_profile = "official"
        official_validation_sufficiency = "official_evidence"
        profiles = $profiles
    }

    if (Test-Path -LiteralPath $script:ResolvedManifestPath) {
        $existingManifest = Read-JsonFile -PathValue $script:ResolvedManifestPath
        foreach ($fieldName in @(
                "artifact_scope",
                "current_phase_exit",
                "current_phase_status",
                "next_functional_phase",
                "current_phase_handoff",
                "phase_0_runtime_handoff",
                "current_phase_guidance",
                "phase_1_additional_functional_waves_allowed",
                "final_operational_correction_wave",
                "phase_1_exit_validation"
            )) {
            if ($existingManifest.ContainsKey($fieldName)) {
                $manifest[$fieldName] = $existingManifest[$fieldName]
            }
        }
    }

    Write-JsonUtf8NoBom -PathValue $script:ResolvedManifestPath -Payload $manifest
    return $script:ResolvedManifestPath
}

function Invoke-ExternalCommand {
    param(
        [Parameter(Mandatory = $true)]
        [string]$FilePath,
        [string[]]$ArgumentList = @(),
        [hashtable]$Environment = @{},
        [string]$Description,
        [switch]$CaptureOutput
    )

    $displayCommand = if ($ArgumentList.Count -gt 0) {
        "{0} {1}" -f $FilePath, (($ArgumentList | ForEach-Object {
                    if ($_ -match "\s") { '"{0}"' -f $_ } else { $_ }
                }) -join " ")
    }
    else {
        $FilePath
    }

    if ($Description) {
        Write-Host $Description -ForegroundColor DarkGray
    }
    Write-Host ("> {0}" -f $displayCommand) -ForegroundColor DarkGray

    if ($DryRun) {
        return [pscustomobject]@{
            Command = $displayCommand
            ExitCode = 0
        }
    }

    $savedEnv = @{}
    foreach ($pair in $Environment.GetEnumerator()) {
        $savedEnv[$pair.Key] = [Environment]::GetEnvironmentVariable($pair.Key, "Process")
        [Environment]::SetEnvironmentVariable($pair.Key, $pair.Value, "Process")
    }

    try {
        if ($CaptureOutput) {
            $output = & $FilePath @ArgumentList 2>&1
        }
        else {
            & $FilePath @ArgumentList
            $output = @()
        }
        $exitCode = $LASTEXITCODE
        if ($exitCode -ne 0) {
            throw ("Falha ao executar comando: {0} (exit code {1})" -f $displayCommand, $exitCode)
        }
        foreach ($line in @($output)) {
            Write-Host $line
        }
        return [pscustomobject]@{
            Command = $displayCommand
            ExitCode = $exitCode
            Output = @($output)
        }
    }
    finally {
        foreach ($pair in $savedEnv.GetEnumerator()) {
            [Environment]::SetEnvironmentVariable($pair.Key, $pair.Value, "Process")
        }
    }
}

function Invoke-Step {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Name,
        [Parameter(Mandatory = $true)]
        [scriptblock]$Action
    )

    Write-StepBanner -Name $Name
    $stepStartedAt = Get-Date
    $timer = [System.Diagnostics.Stopwatch]::StartNew()
    $record = [ordered]@{
        name = $Name
        started_at = $stepStartedAt.ToString("o")
        status = "running"
    }

    try {
        $details = & $Action
        if ($details) {
            $record.details = $details
        }
        $record.status = "passed"
    }
    catch {
        $record.status = "failed"
        $record.error = $_.Exception.Message
        throw
    }
    finally {
        $timer.Stop()
        $record.finished_at = (Get-Date).ToString("o")
        $record.duration_seconds = [math]::Round($timer.Elapsed.TotalSeconds, 3)
        $record.duration_display = Format-Duration -Duration $timer.Elapsed
        $script:Report.steps += [pscustomobject]$record
        Write-Host ("Status: {0} | Duração: {1}" -f $record.status, $record.duration_display) -ForegroundColor Yellow
    }
}

function Assert-FieldPresent {
    param(
        [Parameter(Mandatory = $true)]
        [hashtable]$Data,
        [Parameter(Mandatory = $true)]
        [string]$FieldName,
        [Parameter(Mandatory = $true)]
        [string]$Context
    )

    if (-not $Data.ContainsKey($FieldName)) {
        throw ("Campo obrigatório ausente em {0}: {1}" -f $Context, $FieldName)
    }
    if ($null -eq $Data[$FieldName]) {
        throw ("Campo obrigatório nulo em {0}: {1}" -f $Context, $FieldName)
    }
    if ($Data[$FieldName] -is [string] -and [string]::IsNullOrWhiteSpace([string]$Data[$FieldName])) {
        throw ("Campo obrigatório vazio em {0}: {1}" -f $Context, $FieldName)
    }
}

function Assert-FieldEquals {
    param(
        [Parameter(Mandatory = $true)]
        [hashtable]$Data,
        [Parameter(Mandatory = $true)]
        [string]$FieldName,
        [Parameter(Mandatory = $true)]
        [object]$ExpectedValue,
        [Parameter(Mandatory = $true)]
        [string]$Context
    )

    Assert-FieldPresent -Data $Data -FieldName $FieldName -Context $Context
    if ($Data[$FieldName] -ne $ExpectedValue) {
        throw ("Campo {0} em {1} deveria ser '{2}', mas foi '{3}'." -f $FieldName, $Context, $ExpectedValue, $Data[$FieldName])
    }
}

function Assert-BooleanValue {
    param(
        [Parameter(Mandatory = $true)]
        [hashtable]$Data,
        [Parameter(Mandatory = $true)]
        [string]$FieldName,
        [Parameter(Mandatory = $true)]
        [bool]$ExpectedValue,
        [Parameter(Mandatory = $true)]
        [string]$Context
    )

    Assert-FieldPresent -Data $Data -FieldName $FieldName -Context $Context
    if ([bool]$Data[$FieldName] -ne $ExpectedValue) {
        throw ("Campo {0} em {1} deveria ser '{2}', mas foi '{3}'." -f $FieldName, $Context, $ExpectedValue, [bool]$Data[$FieldName])
    }
}

function Assert-ContainsText {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Value,
        [Parameter(Mandatory = $true)]
        [string]$ExpectedFragment,
        [Parameter(Mandatory = $true)]
        [string]$Context
    )

    if ($Value -notlike ("*{0}*" -f $ExpectedFragment)) {
        throw ("Valor em {0} não contém o trecho obrigatório '{1}'." -f $Context, $ExpectedFragment)
    }
}

function Test-ArtifactExists {
    param(
        [Parameter(Mandatory = $true)]
        [string]$PathValue
    )

    return Test-Path -LiteralPath $PathValue
}

function Get-ValidationEnvironment {
    $environment = @{
        PYTHONPATH = "src"
    }

    if ($script:ProfileConfig["use_julia_depot"]) {
        $environment["JULIA_DEPOT_PATH"] = Resolve-WorkspacePath -PathValue $script:JuliaDepotDir
    }

    $probeOverrideValue = $script:ProfileConfig["set_probe_override_env"]
    $environment[$script:ProbeOverrideEnv] = if ($null -eq $probeOverrideValue) { $null } else { [string]$probeOverrideValue }

    return $environment
}

function Get-PipelineArguments {
    $args = @(
        "-m", "decision_platform.api.run_pipeline",
        "--scenario", $script:RuntimeScenarioDir,
        "--output-dir", $OutputDir
    )

    if ($script:ProfileConfig["allow_diagnostic_python_emulation"]) {
        $args += "--allow-diagnostic-python-emulation"
    }
    if ($script:ProfileConfig["include_engine_comparison"]) {
        $args += "--include-engine-comparison"
    }

    return $args
}

function Get-OfficialPreflightArguments {
    $pythonCode = @'
import json
import subprocess
import sys
import tomllib
from pathlib import Path
from decision_platform.api.run_pipeline import _build_runtime_policy, _validate_runtime_policy
from decision_platform.data_io.loader import load_scenario_bundle
from decision_platform.julia_bridge.bridge import find_julia_executable

scenario_dir = sys.argv[1]
result = {"scenario_dir": scenario_dir}
try:
    bundle = load_scenario_bundle(scenario_dir)
    engine_cfg = bundle.scenario_settings.get("hydraulic_engine", {})
    julia_exe = find_julia_executable()
    julia_ok = False
    watermodels_ok = False
    watermodels_probe_mode = "project_manifest_inventory"
    if julia_exe:
        try:
            subprocess.run(
                [julia_exe, "--version"],
                check=True,
                capture_output=True,
                text=True,
                timeout=15,
            )
            julia_ok = True
        except Exception:
            julia_ok = False
        if julia_ok:
            try:
                repo_root = Path.cwd()
                required_packages = {"JSON3", "JuMP", "HiGHS", "WaterModels"}
                project_toml = tomllib.loads((repo_root / "julia" / "Project.toml").read_text(encoding="utf-8"))
                project_dependencies = set((project_toml.get("deps") or {}).keys())
                manifest_text = (repo_root / "julia" / "Manifest.toml").read_text(encoding="utf-8")
                manifest_dependencies = {
                    line.removeprefix("[[deps.").removesuffix("]]").strip()
                    for line in manifest_text.splitlines()
                    if line.startswith("[[deps.") and line.endswith("]]")
                }
                watermodels_ok = required_packages.issubset(project_dependencies) and required_packages.issubset(manifest_dependencies)
            except Exception:
                watermodels_ok = False
    runtime_policy = _build_runtime_policy(
        allow_diagnostic_python_emulation=False,
        include_engine_comparison=False,
    )
    result.update(
        {
            "scenario_load_valid": True,
            "scenario_primary_engine": str(engine_cfg.get("primary", "watermodels_jl")).strip(),
            "scenario_fallback_engine": str(engine_cfg.get("fallback", "none")).strip(),
            "julia_available": julia_ok,
            "watermodels_available": watermodels_ok,
            "watermodels_probe_mode": watermodels_probe_mode,
            "runtime_policy_mode": runtime_policy.get("policy_mode"),
            "runtime_policy_message": runtime_policy.get("policy_message"),
            "official_gate_valid": bool(runtime_policy.get("official_gate_valid")),
        }
    )
    try:
        _validate_runtime_policy(
            bundle,
            allow_diagnostic_python_emulation=False,
            include_engine_comparison=False,
        )
        result["runtime_policy_valid"] = True
    except Exception as exc:
        result["runtime_policy_valid"] = False
        result["runtime_policy_error"] = str(exc)
except Exception as exc:
    result.update(
        {
            "scenario_load_valid": False,
            "runtime_policy_valid": False,
            "runtime_policy_error": str(exc),
        }
    )

print(json.dumps(result, ensure_ascii=False))
'@
    return @("-c", $pythonCode, $script:RuntimeScenarioDir)
}

function Prepare-ScenarioForMode {
    $resolvedScenarioDir = Resolve-WorkspacePath -PathValue $ScenarioDir
    $fallbackOverride = $script:ProfileConfig["scenario_fallback_override"]
    if ($null -eq $fallbackOverride) {
        $script:RuntimeScenarioDir = $resolvedScenarioDir
        return $resolvedScenarioDir
    }

    $temporaryScenarioDir = Join-Path $script:RepoRoot ("tests/_tmp/runtime_validation_{0}_scenario" -f $script:ValidationProfile)
    if ((Test-Path -LiteralPath $temporaryScenarioDir) -and -not $DryRun) {
        Remove-Item -LiteralPath $temporaryScenarioDir -Recurse -Force
    }
    if (-not $DryRun) {
        Copy-Item -LiteralPath $resolvedScenarioDir -Destination $temporaryScenarioDir -Recurse
        $settingsPath = Join-Path $temporaryScenarioDir "scenario_settings.yaml"
        $settingsContent = Get-Content -LiteralPath $settingsPath -Raw
        if ($settingsContent -notmatch "(?m)^\s*fallback:\s*") {
            throw ("scenario_settings.yaml não contém hydraulic_engine.fallback em {0}" -f $settingsPath)
        }
        $updatedContent = [regex]::Replace(
            $settingsContent,
            "(?m)^(\s*fallback:\s*).+$",
            ('${1}' + [string]$fallbackOverride),
            1
        )
        Set-Content -LiteralPath $settingsPath -Value $updatedContent -Encoding utf8
    }

    $script:RuntimeScenarioDir = $temporaryScenarioDir
    $script:TemporaryScenarioDir = $temporaryScenarioDir
    return $temporaryScenarioDir
}

function Assert-PreflightResult {
    param(
        [Parameter(Mandatory = $true)]
        [hashtable]$PreflightResult
    )

    foreach ($field in @($script:SharedProfile["preflight_required_fields"])) {
        Assert-FieldPresent -Data $PreflightResult -FieldName ([string]$field) -Context "official_preflight"
    }

    $expectations = $script:ProfileConfig["preflight_expectations"]
    foreach ($pair in $expectations["string_fields"].GetEnumerator()) {
        Assert-FieldEquals -Data $PreflightResult -FieldName ([string]$pair.Key) -ExpectedValue ([string]$pair.Value) -Context "official_preflight"
    }
    foreach ($pair in $expectations["boolean_fields"].GetEnumerator()) {
        Assert-BooleanValue -Data $PreflightResult -FieldName ([string]$pair.Key) -ExpectedValue ([bool]$pair.Value) -Context "official_preflight"
    }
    foreach ($containsRule in @($expectations["contains"])) {
        Assert-ContainsText -Value ([string]$PreflightResult[[string]$containsRule["field"]]) -ExpectedFragment ([string]$containsRule["text"]) -Context "official_preflight"
    }
}

function Assert-TelemetryFields {
    param(
        [Parameter(Mandatory = $true)]
        [hashtable]$Runtime,
        [Parameter(Mandatory = $true)]
        [string]$Context
    )

    foreach ($field in @($script:SharedProfile["runtime_required_fields"])) {
        Assert-FieldPresent -Data $Runtime -FieldName ([string]$field) -Context $Context
    }

    if ([double]$Runtime["duration_s"] -lt 0) {
        throw ("Campo duration_s em {0} precisa ser não negativo." -f $Context)
    }
}

function Assert-ExpectedFields {
    param(
        [Parameter(Mandatory = $true)]
        [hashtable]$Summary,
        [Parameter(Mandatory = $true)]
        [hashtable]$Runtime,
        [Parameter(Mandatory = $true)]
        [hashtable]$Expectations
    )

    foreach ($pair in $Expectations["string_fields"].GetEnumerator()) {
        Assert-FieldEquals -Data $Summary -FieldName ([string]$pair.Key) -ExpectedValue ([string]$pair.Value) -Context "summary.json"
    }
    foreach ($pair in $Expectations["boolean_fields"].GetEnumerator()) {
        Assert-BooleanValue -Data $Summary -FieldName ([string]$pair.Key) -ExpectedValue ([bool]$pair.Value) -Context "summary.json"
    }
    foreach ($pair in $Expectations["runtime_string_fields"].GetEnumerator()) {
        Assert-FieldEquals -Data $Runtime -FieldName ([string]$pair.Key) -ExpectedValue ([string]$pair.Value) -Context "summary.json.runtime"
    }
    foreach ($pair in $Expectations["runtime_boolean_fields"].GetEnumerator()) {
        Assert-BooleanValue -Data $Runtime -FieldName ([string]$pair.Key) -ExpectedValue ([bool]$pair.Value) -Context "summary.json.runtime"
    }
    foreach ($containsRule in @($Expectations["contains"])) {
        $fieldPath = [string]$containsRule["field"]
        $value = if ($fieldPath.StartsWith("runtime.")) {
            [string](Get-NestedValue -Data $Summary -FieldPath $fieldPath)
        }
        else {
            [string](Get-NestedValue -Data $Summary -FieldPath $fieldPath)
        }
        Assert-ContainsText -Value $value -ExpectedFragment ([string]$containsRule["text"]) -Context ("summary.json.{0}" -f $fieldPath)
    }
}

function Assert-SummaryPolicy {
    param(
        [Parameter(Mandatory = $true)]
        [hashtable]$Summary
    )

    foreach ($field in @($script:SharedProfile["summary_required_fields"])) {
        Assert-FieldPresent -Data $Summary -FieldName ([string]$field) -Context "summary.json"
    }

    if (-not ($Summary["runtime"] -is [hashtable])) {
        throw "summary.json não contém runtime no formato esperado."
    }

    $runtime = $Summary["runtime"]
    Assert-TelemetryFields -Runtime $runtime -Context "summary.json.runtime"
    Assert-ExpectedFields -Summary $Summary -Runtime $runtime -Expectations $script:ProfileConfig["summary_expectations"]

    if ([int]$Summary["candidate_count"] -le 0) {
        throw "summary.json precisa expor candidate_count maior que zero."
    }
}

function Assert-CoreArtifacts {
    param(
        [Parameter(Mandatory = $true)]
        [string]$ResolvedOutputDir,
        [Parameter(Mandatory = $true)]
        [hashtable]$Summary
    )

    foreach ($artifact in @($script:SharedProfile["core_artifacts"])) {
        $artifactPath = Join-Path $ResolvedOutputDir ([string]$artifact)
        if (-not (Test-ArtifactExists -PathValue $artifactPath)) {
            throw ("Artefato obrigatório ausente: {0}" -f $artifactPath)
        }
    }

    $selectedCandidate = Read-JsonFile -PathValue (Join-Path $ResolvedOutputDir "selected_candidate.json")
    $selectedRoutes = Read-JsonFile -PathValue (Join-Path $ResolvedOutputDir "selected_candidate_routes.json")
    $selectedBreakdown = Read-JsonFile -PathValue (Join-Path $ResolvedOutputDir "selected_candidate_score_breakdown.json")
    $selectedRender = Read-JsonFile -PathValue (Join-Path $ResolvedOutputDir "selected_candidate_render.json")
    $selectedExplanation = Read-JsonFile -PathValue (Join-Path $ResolvedOutputDir "selected_candidate_explanation.json")
    $infeasibilitySummary = Read-JsonFile -PathValue (Join-Path $ResolvedOutputDir "infeasibility_summary.json")
    $familySummary = @(Import-Csv -LiteralPath (Join-Path $ResolvedOutputDir "family_summary.csv"))
    $selectedBom = @(Import-Csv -LiteralPath (Join-Path $ResolvedOutputDir "selected_candidate_bom.csv"))
    $selectedCandidateId = [string]$Summary["selected_candidate_id"]

    Assert-FieldEquals -Data $selectedCandidate -FieldName "candidate_id" -ExpectedValue $selectedCandidateId -Context "selected_candidate.json"
    Assert-FieldEquals -Data $selectedRoutes -FieldName "candidate_id" -ExpectedValue $selectedCandidateId -Context "selected_candidate_routes.json"
    Assert-FieldEquals -Data $selectedBreakdown -FieldName "candidate_id" -ExpectedValue $selectedCandidateId -Context "selected_candidate_score_breakdown.json"
    Assert-FieldEquals -Data $selectedRender -FieldName "candidate_id" -ExpectedValue $selectedCandidateId -Context "selected_candidate_render.json"
    Assert-FieldEquals -Data $selectedExplanation -FieldName "candidate_id" -ExpectedValue $selectedCandidateId -Context "selected_candidate_explanation.json"

    Assert-FieldPresent -Data $selectedCandidate -FieldName "metrics" -Context "selected_candidate.json"
    if (-not ($selectedCandidate["metrics"] -is [hashtable])) {
        throw "selected_candidate.json.metrics não está no formato esperado."
    }
    $metrics = $selectedCandidate["metrics"]
    foreach ($metricField in @($script:SharedProfile["selected_candidate_metric_fields"])) {
        $fieldName = [string]$metricField
        Assert-FieldEquals -Data $metrics -FieldName $fieldName -ExpectedValue ([string]$Summary[$fieldName]) -Context "selected_candidate.json.metrics"
    }

    if ($selectedExplanation.ContainsKey("winner")) {
        if (-not ($selectedExplanation["winner"] -is [hashtable])) {
            throw "selected_candidate_explanation.json.winner não está no formato esperado."
        }
        Assert-FieldEquals -Data $selectedExplanation["winner"] -FieldName "candidate_id" -ExpectedValue $selectedCandidateId -Context "selected_candidate_explanation.json.winner"
    }

    if ($familySummary.Count -le 0) {
        throw "family_summary.csv precisa conter ao menos uma linha."
    }
    if ($selectedBom.Count -le 0) {
        throw "selected_candidate_bom.csv precisa conter ao menos uma linha."
    }
    if (-not ($selectedBom[0].PSObject.Properties.Name -contains "candidate_id")) {
        throw "selected_candidate_bom.csv precisa conter a coluna candidate_id."
    }
    $invalidBomRows = @($selectedBom | Where-Object { $_.candidate_id -ne $selectedCandidateId })
    if ($invalidBomRows.Count -gt 0) {
        throw "selected_candidate_bom.csv contém candidate_id divergente do summary.json."
    }

    Assert-FieldPresent -Data $infeasibilitySummary -FieldName "total_infeasible_candidates" -Context "infeasibility_summary.json"
}

function Assert-EngineComparisonArtifacts {
    param(
        [Parameter(Mandatory = $true)]
        [string]$ResolvedOutputDir
    )

    $engineComparisonPath = Join-Path $ResolvedOutputDir "engine_comparison.json"
    $engineComparison = Read-JsonFile -PathValue $engineComparisonPath

    foreach ($field in @($script:SharedProfile["engine_comparison_required_fields"])) {
        Assert-FieldPresent -Data $engineComparison -FieldName ([string]$field) -Context "engine_comparison.json"
    }
    if (-not ($engineComparison["execution_policy"] -is [hashtable])) {
        throw "engine_comparison.json.execution_policy não está no formato esperado."
    }
    if (-not ($engineComparison["runtime"] -is [hashtable])) {
        throw "engine_comparison.json.runtime não está no formato esperado."
    }

    $executionPolicy = $engineComparison["execution_policy"]
    $runtime = $engineComparison["runtime"]
    $expectedRuntime = $script:ProfileConfig["summary_expectations"]
    foreach ($pair in $expectedRuntime["runtime_string_fields"].GetEnumerator()) {
        Assert-FieldEquals -Data $executionPolicy -FieldName ([string]$pair.Key) -ExpectedValue ([string]$pair.Value) -Context "engine_comparison.json.execution_policy"
        Assert-FieldEquals -Data $runtime -FieldName ([string]$pair.Key) -ExpectedValue ([string]$pair.Value) -Context "engine_comparison.json.runtime"
    }
    foreach ($pair in $expectedRuntime["runtime_boolean_fields"].GetEnumerator()) {
        Assert-BooleanValue -Data $executionPolicy -FieldName ([string]$pair.Key) -ExpectedValue ([bool]$pair.Value) -Context "engine_comparison.json.execution_policy"
        Assert-BooleanValue -Data $runtime -FieldName ([string]$pair.Key) -ExpectedValue ([bool]$pair.Value) -Context "engine_comparison.json.runtime"
    }
    Assert-TelemetryFields -Runtime $runtime -Context "engine_comparison.json.runtime"

    $engineComparisonCandidatesPath = Join-Path $ResolvedOutputDir "engine_comparison_candidates.csv"
    $engineComparisonCandidates = @(Import-Csv -LiteralPath $engineComparisonCandidatesPath)
    if ($engineComparisonCandidates.Count -le 0) {
        throw "engine_comparison_candidates.csv precisa conter ao menos uma linha."
    }
    if (-not ($engineComparisonCandidates[0].PSObject.Properties.Name -contains "engine")) {
        throw "engine_comparison_candidates.csv precisa conter a coluna engine."
    }
    $engineNames = @($engineComparisonCandidates | ForEach-Object { [string]$_.engine } | Sort-Object -Unique)
    foreach ($expectedEngine in @($script:SharedProfile["engine_comparison_candidate_engines"])) {
        if ($engineNames -notcontains [string]$expectedEngine) {
            throw ("engine_comparison_candidates.csv precisa conter o engine '{0}'." -f [string]$expectedEngine)
        }
    }
}

function Assert-ProfileArtifacts {
    param(
        [Parameter(Mandatory = $true)]
        [string]$ResolvedOutputDir
    )

    foreach ($artifact in @($script:ProfileConfig["artifacts"]["required"])) {
        $artifactPath = Join-Path $ResolvedOutputDir ([string]$artifact)
        if (-not (Test-ArtifactExists -PathValue $artifactPath)) {
            throw ("Artefato obrigatório ausente: {0}" -f $artifactPath)
        }
    }
    foreach ($artifact in @($script:ProfileConfig["artifacts"]["forbidden"])) {
        $artifactPath = Join-Path $ResolvedOutputDir ([string]$artifact)
        if (Test-ArtifactExists -PathValue $artifactPath) {
            throw ("Artefato proibido encontrado para o perfil {0}: {1}" -f $script:ValidationProfile, $artifactPath)
        }
    }

    if (@($script:ProfileConfig["artifacts"]["required"]).Count -gt 0) {
        Assert-EngineComparisonArtifacts -ResolvedOutputDir $ResolvedOutputDir
    }
}

function Show-FinalSummary {
    Write-Host ""
    Write-Host "Resumo por etapa" -ForegroundColor Cyan
    foreach ($step in $script:Report.steps) {
        Write-Host ("- {0}: {1} ({2})" -f $step.name, $step.status, $step.duration_display)
    }
}

Set-Location $script:RepoRoot

$reportPath = $null
$scriptFailed = $false
$resolvedOutputDir = Resolve-WorkspacePath -PathValue $OutputDir

try {
    Invoke-Step -Name "1. Preparar ambiente" -Action {
        if (-not (Test-Path -LiteralPath $script:PythonExe) -and -not $DryRun) {
            throw ("Python da virtualenv não encontrado: {0}" -f $script:PythonExe)
        }
        if ($OfficialPreflight -and $Mode -ne "official") {
            throw "O preflight oficial só pode ser usado com -Mode official."
        }
        if ($Mode -ne [string]$script:ProfileConfig["mode"]) {
            throw ("Os parâmetros informados não correspondem ao perfil {0}." -f $script:ValidationProfile)
        }

        if ([bool]$script:ProfileConfig["reject_disable_real_julia_probe_flag"] -and $DisableRealJuliaProbe) {
            throw ("O perfil {0} não aceita -DisableRealJuliaProbe." -f $script:ValidationProfile)
        }
        if ([bool]$script:ProfileConfig["require_disable_real_julia_probe_flag"] -and -not $DisableRealJuliaProbe) {
            throw ("O perfil {0} exige -DisableRealJuliaProbe." -f $script:ValidationProfile)
        }
        if ([bool]$script:ProfileConfig["reject_process_probe_override"] -and [Environment]::GetEnvironmentVariable($script:ProbeOverrideEnv, "Process")) {
            throw ("{0} está ativo no processo atual. O perfil {1} exige Julia-only sem override diagnóstico." -f $script:ProbeOverrideEnv, $script:ValidationProfile)
        }
        if ([bool]$script:ProfileConfig["use_julia_depot"] -and -not (Test-Path -LiteralPath $script:JuliaDepotDir) -and -not $DryRun) {
            throw ("Diretório do depot Julia não encontrado: {0}" -f $script:JuliaDepotDir)
        }

        $preparedScenarioDir = Prepare-ScenarioForMode

        if ([string]$script:ProfileConfig["validation_flow"] -eq "full") {
            if ((Test-Path -LiteralPath $resolvedOutputDir) -and -not $DryRun) {
                Remove-Item -LiteralPath $resolvedOutputDir -Recurse -Force
            }
            if (-not $DryRun) {
                New-Item -ItemType Directory -Path $resolvedOutputDir -Force | Out-Null
            }
        }

        return @{
            output_dir = $resolvedOutputDir
            scenario_dir = $preparedScenarioDir
            profile = $script:ValidationProfile
            profile_description = $script:ProfileConfig["description"]
        }
    }

    if ([string]$script:ProfileConfig["validation_flow"] -eq "preflight") {
        Invoke-Step -Name "2. Executar preflight oficial" -Action {
            $environment = Get-ValidationEnvironment
            $args = Get-OfficialPreflightArguments
            $commandResult = Invoke-ExternalCommand -FilePath $script:PythonExe -ArgumentList $args -Environment $environment -Description "Executando o preflight oficial da decision_platform" -CaptureOutput
            if ($DryRun) {
                $script:PreflightResult = @{
                    scenario_load_valid = $true
                    scenario_primary_engine = "watermodels_jl"
                    scenario_fallback_engine = "none"
                    julia_available = $true
                    watermodels_available = $true
                    runtime_policy_valid = $true
                    official_gate_valid = $true
                    runtime_policy_mode = "official_julia_only"
                    runtime_policy_message = "Official Julia-only gate: no diagnostic override or opt-in diagnostic feature is active."
                }
            }
            else {
                $jsonOutput = (@($commandResult.Output) | ForEach-Object { $_.ToString() }) -join "`n"
                $script:PreflightResult = $jsonOutput | ConvertFrom-Json -AsHashtable
            }
            return $script:PreflightResult
        }
        Invoke-Step -Name "3. Validar preflight oficial" -Action {
            Assert-PreflightResult -PreflightResult $script:PreflightResult
            return @{
                validation_profile = $script:ValidationProfile
                validation_sufficiency = $script:ProfileConfig["validation_sufficiency"]
                julia_available = $script:PreflightResult["julia_available"]
                watermodels_available = $script:PreflightResult["watermodels_available"]
                runtime_policy_valid = $script:PreflightResult["runtime_policy_valid"]
            }
        }
    }
    else {
        Invoke-Step -Name "2. Executar pipeline" -Action {
            $environment = Get-ValidationEnvironment
            $args = Get-PipelineArguments
            $null = Invoke-ExternalCommand -FilePath $script:PythonExe -ArgumentList $args -Environment $environment -Description "Executando o pipeline da decision_platform"
            return @{
                python = $script:PythonExe
                command = ((@($script:PythonExe) + $args) -join " ")
                output_dir = $resolvedOutputDir
                environment = $environment
            }
        }

        Invoke-Step -Name "3. Validar summary.json" -Action {
            $summaryPath = Join-Path $resolvedOutputDir "summary.json"
            if (-not (Test-ArtifactExists -PathValue $summaryPath) -and -not $DryRun) {
                throw ("Artefato obrigatório ausente: {0}" -f $summaryPath)
            }
            if ($DryRun) {
                $expectedSummary = $script:ProfileConfig["summary_expectations"]
                return @{
                    summary_path = $summaryPath
                    simulated = $true
                    candidate_count = 1
                    selected_candidate_id = "simulated_candidate"
                    execution_mode = $expectedSummary["string_fields"]["execution_mode"]
                    official_gate_valid = $expectedSummary["boolean_fields"]["official_gate_valid"]
                    runtime_policy_mode = $expectedSummary["string_fields"]["runtime_policy_mode"]
                    runtime_duration_s = 0.0
                }
            }

            $summary = Read-JsonFile -PathValue $summaryPath
            Assert-SummaryPolicy -Summary $summary

            return @{
                summary_path = $summaryPath
                candidate_count = $summary["candidate_count"]
                selected_candidate_id = $summary["selected_candidate_id"]
                execution_mode = $summary["execution_mode"]
                official_gate_valid = $summary["official_gate_valid"]
                runtime_policy_mode = $summary["runtime_policy_mode"]
                runtime_duration_s = $summary["runtime_duration_s"]
            }
        }

        Invoke-Step -Name "4. Validar artefatos principais" -Action {
            if ($DryRun) {
                return @{
                    output_dir = $resolvedOutputDir
                    simulated = $true
                    selected_candidate_id = "simulated_candidate"
                    engine_used = if ($script:ValidationProfile -eq "official") { "watermodels_jl" } else { "python_emulated_julia" }
                }
            }

            $summary = Read-JsonFile -PathValue (Join-Path $resolvedOutputDir "summary.json")
            Assert-CoreArtifacts -ResolvedOutputDir $resolvedOutputDir -Summary $summary
            return @{
                output_dir = $resolvedOutputDir
                selected_candidate_id = $summary["selected_candidate_id"]
                engine_used = $summary["engine_used"]
            }
        }

        Invoke-Step -Name "5. Validar artefatos do perfil" -Action {
            if ($DryRun) {
                return @{
                    profile = $script:ValidationProfile
                    simulated = $true
                    required = @($script:ProfileConfig["artifacts"]["required"])
                    forbidden = @($script:ProfileConfig["artifacts"]["forbidden"])
                }
            }

            Assert-ProfileArtifacts -ResolvedOutputDir $resolvedOutputDir
            return @{
                profile = $script:ValidationProfile
                required = @($script:ProfileConfig["artifacts"]["required"])
                forbidden = @($script:ProfileConfig["artifacts"]["forbidden"])
            }
        }
    }
}
catch {
    $scriptFailed = $true
    Write-Error $_
}
finally {
    $script:Report.finished_at = (Get-Date).ToString("o")
    $script:Report.output_dir = $resolvedOutputDir
    $script:Report.runtime_scenario_dir = $script:RuntimeScenarioDir
    $script:Report.success = -not $scriptFailed
    $reportPath = Save-Report
    $manifestPath = Save-Phase0ValidationManifest -LogsPath (Resolve-WorkspacePath -PathValue $LogsDir)

    if ($script:TemporaryScenarioDir -and (Test-Path -LiteralPath $script:TemporaryScenarioDir) -and -not $DryRun) {
        Remove-Item -LiteralPath $script:TemporaryScenarioDir -Recurse -Force
    }

    Show-FinalSummary
    Write-Host ""
    Write-Host ("Relatório salvo em: {0}" -f $reportPath) -ForegroundColor Green
    Write-Host ("Manifesto salvo em: {0}" -f $manifestPath) -ForegroundColor Green

    if ($scriptFailed) {
        exit 1
    }
}
