[CmdletBinding()]
param(
    [ValidateSet("official", "diagnostic")]
    [string]$Mode = "official",
    [string]$ScenarioDir = "data/decision_platform/maquete_v2",
    [string]$OutputDir,
    [string]$LogsDir = "scripts/logs",
    [switch]$IncludeEngineComparison,
    [switch]$DisableRealJuliaProbe,
    [switch]$DryRun
)

Set-StrictMode -Version 3.0
$ErrorActionPreference = "Stop"

$script:RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$script:PythonExe = Join-Path $script:RepoRoot ".venv\Scripts\python.exe"
$script:JuliaDepotDir = Join-Path $script:RepoRoot "julia_depot_runtime"
$script:ProbeOverrideEnv = "DECISION_PLATFORM_DISABLE_REAL_JULIA_PROBE"
$script:ReportTimestamp = Get-Date
$script:ValidationProfile = if ($Mode -eq "official") {
    "official"
}
elseif ($IncludeEngineComparison) {
    "diagnostic_comparison"
}
else {
    "diagnostic"
}
$script:RuntimeScenarioDir = $null
$script:TemporaryScenarioDir = $null
$script:Report = [ordered]@{
    started_at = $script:ReportTimestamp.ToString("o")
    mode = $Mode
    validation_profile = $script:ValidationProfile
    scenario_dir = $ScenarioDir
    include_engine_comparison = [bool]$IncludeEngineComparison
    disable_real_julia_probe = [bool]$DisableRealJuliaProbe
    dry_run = [bool]$DryRun
    repo_root = $script:RepoRoot
    steps = @()
}

if ([string]::IsNullOrWhiteSpace($OutputDir)) {
    $OutputDir = if ($script:ValidationProfile -eq "official") {
        "data/output/decision_platform/runtime_validation_official"
    }
    elseif ($script:ValidationProfile -eq "diagnostic_comparison") {
        "data/output/decision_platform/runtime_validation_diagnostic_comparison"
    }
    else {
        "data/output/decision_platform/runtime_validation_diagnostic"
    }
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
    ($script:Report | ConvertTo-Json -Depth 20) | Set-Content -LiteralPath $reportPath -Encoding utf8
    return $reportPath
}

function Invoke-ExternalCommand {
    param(
        [Parameter(Mandatory = $true)]
        [string]$FilePath,
        [string[]]$ArgumentList = @(),
        [hashtable]$Environment = @{},
        [string]$Description
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
        & $FilePath @ArgumentList
        $exitCode = $LASTEXITCODE
        if ($exitCode -ne 0) {
            throw ("Falha ao executar comando: {0} (exit code {1})" -f $displayCommand, $exitCode)
        }
        return [pscustomobject]@{
            Command = $displayCommand
            ExitCode = $exitCode
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

    if ($Mode -eq "official") {
        $environment[$script:ProbeOverrideEnv] = $null
        $environment["JULIA_DEPOT_PATH"] = Resolve-WorkspacePath -PathValue $script:JuliaDepotDir
        return $environment
    }

    if ($DisableRealJuliaProbe) {
        $environment[$script:ProbeOverrideEnv] = "1"
    }
    else {
        $environment[$script:ProbeOverrideEnv] = $null
    }

    if (-not $DisableRealJuliaProbe -and (Test-Path -LiteralPath $script:JuliaDepotDir)) {
        $environment["JULIA_DEPOT_PATH"] = Resolve-WorkspacePath -PathValue $script:JuliaDepotDir
    }

    return $environment
}

function Get-PipelineArguments {
    $args = @(
        "-m", "decision_platform.api.run_pipeline",
        "--scenario", $script:RuntimeScenarioDir,
        "--output-dir", $OutputDir
    )

    if ($Mode -eq "diagnostic") {
        $args += "--allow-diagnostic-python-emulation"
    }
    if ($IncludeEngineComparison) {
        $args += "--include-engine-comparison"
    }

    return $args
}

function Prepare-ScenarioForMode {
    $resolvedScenarioDir = Resolve-WorkspacePath -PathValue $ScenarioDir
    if ($Mode -eq "official") {
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
            '${1}python_emulated_julia',
            1
        )
        Set-Content -LiteralPath $settingsPath -Value $updatedContent -Encoding utf8
    }

    $script:RuntimeScenarioDir = $temporaryScenarioDir
    $script:TemporaryScenarioDir = $temporaryScenarioDir
    return $temporaryScenarioDir
}

function Assert-TelemetryFields {
    param(
        [Parameter(Mandatory = $true)]
        [hashtable]$Runtime,
        [Parameter(Mandatory = $true)]
        [string]$Context
    )

    foreach ($field in @("started_at", "finished_at", "duration_s", "execution_mode", "official_gate_valid", "policy_mode", "policy_message")) {
        Assert-FieldPresent -Data $Runtime -FieldName $field -Context $Context
    }

    if ([double]$Runtime["duration_s"] -lt 0) {
        throw ("Campo duration_s em {0} precisa ser não negativo." -f $Context)
    }
}

function Assert-SummaryPolicy {
    param(
        [Parameter(Mandatory = $true)]
        [hashtable]$Summary
    )

    foreach ($field in @("candidate_count", "selected_candidate_id", "engine_requested", "engine_used", "engine_mode", "runtime")) {
        Assert-FieldPresent -Data $Summary -FieldName $field -Context "summary.json"
    }

    if (-not ($Summary["runtime"] -is [hashtable])) {
        throw "summary.json não contém runtime no formato esperado."
    }

    $runtime = $Summary["runtime"]
    Assert-TelemetryFields -Runtime $runtime -Context "summary.json.runtime"

    if ($Mode -eq "official") {
        Assert-FieldEquals -Data $Summary -FieldName "execution_mode" -ExpectedValue "official" -Context "summary.json"
        Assert-BooleanValue -Data $Summary -FieldName "official_gate_valid" -ExpectedValue $true -Context "summary.json"
        Assert-BooleanValue -Data $Summary -FieldName "real_julia_probe_disabled" -ExpectedValue $false -Context "summary.json"
        Assert-FieldEquals -Data $Summary -FieldName "runtime_policy_mode" -ExpectedValue "official_julia_only" -Context "summary.json"
        Assert-FieldEquals -Data $runtime -FieldName "execution_mode" -ExpectedValue "official" -Context "summary.json.runtime"
        Assert-BooleanValue -Data $runtime -FieldName "official_gate_valid" -ExpectedValue $true -Context "summary.json.runtime"
        Assert-BooleanValue -Data $runtime -FieldName "real_julia_probe_disabled" -ExpectedValue $false -Context "summary.json.runtime"
        Assert-FieldEquals -Data $runtime -FieldName "policy_mode" -ExpectedValue "official_julia_only" -Context "summary.json.runtime"
    }
    else {
        Assert-FieldEquals -Data $Summary -FieldName "execution_mode" -ExpectedValue "diagnostic" -Context "summary.json"
        Assert-BooleanValue -Data $Summary -FieldName "official_gate_valid" -ExpectedValue $false -Context "summary.json"
        Assert-FieldEquals -Data $runtime -FieldName "execution_mode" -ExpectedValue "diagnostic" -Context "summary.json.runtime"
        Assert-BooleanValue -Data $runtime -FieldName "official_gate_valid" -ExpectedValue $false -Context "summary.json.runtime"

        if ($DisableRealJuliaProbe) {
            Assert-BooleanValue -Data $Summary -FieldName "real_julia_probe_disabled" -ExpectedValue $true -Context "summary.json"
            Assert-FieldEquals -Data $Summary -FieldName "runtime_policy_mode" -ExpectedValue "diagnostic_override_probe_disabled" -Context "summary.json"
            Assert-BooleanValue -Data $runtime -FieldName "real_julia_probe_disabled" -ExpectedValue $true -Context "summary.json.runtime"
            Assert-FieldEquals -Data $runtime -FieldName "policy_mode" -ExpectedValue "diagnostic_override_probe_disabled" -Context "summary.json.runtime"
            Assert-ContainsText -Value ([string]$Summary["runtime_policy_message"]) -ExpectedFragment $script:ProbeOverrideEnv -Context "summary.json.runtime_policy_message"
            Assert-ContainsText -Value ([string]$runtime["policy_message"]) -ExpectedFragment $script:ProbeOverrideEnv -Context "summary.json.runtime.policy_message"
        }
        else {
            Assert-FieldEquals -Data $Summary -FieldName "runtime_policy_mode" -ExpectedValue "diagnostic_opt_in" -Context "summary.json"
            Assert-FieldEquals -Data $runtime -FieldName "policy_mode" -ExpectedValue "diagnostic_opt_in" -Context "summary.json.runtime"
        }
    }

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

    $requiredArtifacts = @(
        "selected_candidate.json",
        "selected_candidate_routes.json",
        "selected_candidate_score_breakdown.json",
        "selected_candidate_bom.csv",
        "selected_candidate_render.json",
        "selected_candidate_explanation.json",
        "selected_candidate_explanation.md",
        "family_summary.csv",
        "infeasibility_summary.json"
    )
    foreach ($artifact in $requiredArtifacts) {
        $artifactPath = Join-Path $ResolvedOutputDir $artifact
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
    $familySummary = Import-Csv -LiteralPath (Join-Path $ResolvedOutputDir "family_summary.csv")
    $selectedBom = Import-Csv -LiteralPath (Join-Path $ResolvedOutputDir "selected_candidate_bom.csv")
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
    Assert-FieldEquals -Data $metrics -FieldName "engine_requested" -ExpectedValue ([string]$Summary["engine_requested"]) -Context "selected_candidate.json.metrics"
    Assert-FieldEquals -Data $metrics -FieldName "engine_used" -ExpectedValue ([string]$Summary["engine_used"]) -Context "selected_candidate.json.metrics"
    Assert-FieldEquals -Data $metrics -FieldName "engine_mode" -ExpectedValue ([string]$Summary["engine_mode"]) -Context "selected_candidate.json.metrics"

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

function Assert-EngineComparisonPolicy {
    param(
        [Parameter(Mandatory = $true)]
        [hashtable]$EngineComparison,
        [Parameter(Mandatory = $true)]
        [string]$ResolvedOutputDir
    )

    foreach ($field in @("execution_policy", "runtime")) {
        Assert-FieldPresent -Data $EngineComparison -FieldName $field -Context "engine_comparison.json"
    }
    if (-not ($EngineComparison["execution_policy"] -is [hashtable])) {
        throw "engine_comparison.json.execution_policy não está no formato esperado."
    }
    if (-not ($EngineComparison["runtime"] -is [hashtable])) {
        throw "engine_comparison.json.runtime não está no formato esperado."
    }

    $executionPolicy = $EngineComparison["execution_policy"]
    $runtime = $EngineComparison["runtime"]
    Assert-TelemetryFields -Runtime $runtime -Context "engine_comparison.json.runtime"

    Assert-BooleanValue -Data $executionPolicy -FieldName "official_gate_valid" -ExpectedValue $false -Context "engine_comparison.json.execution_policy"
    Assert-FieldEquals -Data $executionPolicy -FieldName "execution_mode" -ExpectedValue "diagnostic" -Context "engine_comparison.json.execution_policy"
    Assert-BooleanValue -Data $runtime -FieldName "official_gate_valid" -ExpectedValue $false -Context "engine_comparison.json.runtime"
    Assert-FieldEquals -Data $runtime -FieldName "execution_mode" -ExpectedValue "diagnostic" -Context "engine_comparison.json.runtime"

    if ($DisableRealJuliaProbe) {
        Assert-BooleanValue -Data $executionPolicy -FieldName "real_julia_probe_disabled" -ExpectedValue $true -Context "engine_comparison.json.execution_policy"
        Assert-BooleanValue -Data $runtime -FieldName "real_julia_probe_disabled" -ExpectedValue $true -Context "engine_comparison.json.runtime"
    }

    $engineComparisonCandidatesPath = Join-Path $ResolvedOutputDir "engine_comparison_candidates.csv"
    if (-not (Test-ArtifactExists -PathValue $engineComparisonCandidatesPath)) {
        throw ("Artefato obrigatório ausente: {0}" -f $engineComparisonCandidatesPath)
    }
    $engineComparisonCandidates = Import-Csv -LiteralPath $engineComparisonCandidatesPath
    if ($engineComparisonCandidates.Count -le 0) {
        throw "engine_comparison_candidates.csv precisa conter ao menos uma linha."
    }
    if (-not ($engineComparisonCandidates[0].PSObject.Properties.Name -contains "engine")) {
        throw "engine_comparison_candidates.csv precisa conter a coluna engine."
    }
    $engineNames = @($engineComparisonCandidates | ForEach-Object { [string]$_.engine } | Sort-Object -Unique)
    foreach ($expectedEngine in @("julia", "python")) {
        if ($engineNames -notcontains $expectedEngine) {
            throw ("engine_comparison_candidates.csv precisa conter o engine '{0}'." -f $expectedEngine)
        }
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
        if ($Mode -eq "official" -and $IncludeEngineComparison) {
            throw "O modo official não aceita --include-engine-comparison."
        }
        if ($Mode -eq "official" -and $DisableRealJuliaProbe) {
            throw "O modo official não aceita override diagnóstico da sonda Julia."
        }
        if ($Mode -eq "diagnostic" -and -not $DisableRealJuliaProbe) {
            throw "O gate canônico de diagnostic da fase 0 exige -DisableRealJuliaProbe para marcar explicitamente que a execução não compõe o caminho oficial."
        }
        if ($Mode -eq "official" -and [Environment]::GetEnvironmentVariable($script:ProbeOverrideEnv, "Process")) {
            throw ("{0} está ativo no processo atual. O modo official exige Julia-only sem override diagnóstico." -f $script:ProbeOverrideEnv)
        }
        if ($Mode -eq "official" -and -not (Test-Path -LiteralPath $script:JuliaDepotDir) -and -not $DryRun) {
            throw ("Diretório do depot Julia não encontrado: {0}" -f $script:JuliaDepotDir)
        }
        $preparedScenarioDir = Prepare-ScenarioForMode

        if ((Test-Path -LiteralPath $resolvedOutputDir) -and -not $DryRun) {
            Remove-Item -LiteralPath $resolvedOutputDir -Recurse -Force
        }
        if (-not $DryRun) {
            New-Item -ItemType Directory -Path $resolvedOutputDir -Force | Out-Null
        }

        return @{
            output_dir = $resolvedOutputDir
            scenario_dir = $preparedScenarioDir
            mode = $Mode
            validation_profile = $script:ValidationProfile
        }
    }

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
            return @{
                summary_path = $summaryPath
                simulated = $true
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
        $summaryPath = Join-Path $resolvedOutputDir "summary.json"
        if ($DryRun) {
            return @{
                output_dir = $resolvedOutputDir
                simulated = $true
            }
        }

        $summary = Read-JsonFile -PathValue $summaryPath
        Assert-CoreArtifacts -ResolvedOutputDir $resolvedOutputDir -Summary $summary
        return @{
            output_dir = $resolvedOutputDir
            selected_candidate_id = $summary["selected_candidate_id"]
            engine_used = $summary["engine_used"]
        }
    }

    Invoke-Step -Name "5. Validar artefatos diagnósticos" -Action {
        $engineComparisonPath = Join-Path $resolvedOutputDir "engine_comparison.json"
        $engineComparisonCandidatesPath = Join-Path $resolvedOutputDir "engine_comparison_candidates.csv"
        $engineComparisonExists = Test-ArtifactExists -PathValue $engineComparisonPath
        $engineComparisonCandidatesExists = Test-ArtifactExists -PathValue $engineComparisonCandidatesPath

        if ($Mode -eq "official") {
            if ($engineComparisonExists) {
                throw ("engine_comparison.json não pode existir no modo official: {0}" -f $engineComparisonPath)
            }
            if ($engineComparisonCandidatesExists) {
                throw ("engine_comparison_candidates.csv não pode existir no modo official: {0}" -f $engineComparisonCandidatesPath)
            }
            return @{
                engine_comparison_expected = $false
                engine_comparison_found = $engineComparisonExists
                engine_comparison_candidates_found = $engineComparisonCandidatesExists
            }
        }

        if ($IncludeEngineComparison) {
            if (-not $engineComparisonExists -and -not $DryRun) {
                throw ("engine_comparison.json era obrigatório no modo diagnostic com comparação explícita: {0}" -f $engineComparisonPath)
            }
            if ($DryRun) {
                return @{
                    engine_comparison_expected = $true
                    engine_comparison_found = $true
                    simulated = $true
                }
            }

            $engineComparison = Read-JsonFile -PathValue $engineComparisonPath
            Assert-EngineComparisonPolicy -EngineComparison $engineComparison -ResolvedOutputDir $resolvedOutputDir
            return @{
                engine_comparison_expected = $true
                engine_comparison_found = $true
                engine_comparison_candidates_found = $true
                execution_mode = $engineComparison["runtime"]["execution_mode"]
                official_gate_valid = $engineComparison["runtime"]["official_gate_valid"]
            }
        }

        if ($engineComparisonExists) {
            throw ("engine_comparison.json não pode existir sem comparação explícita no modo diagnostic: {0}" -f $engineComparisonPath)
        }
        if ($engineComparisonCandidatesExists) {
            throw ("engine_comparison_candidates.csv não pode existir sem comparação explícita no modo diagnostic: {0}" -f $engineComparisonCandidatesPath)
        }

        return @{
            engine_comparison_expected = $false
            engine_comparison_found = $false
            engine_comparison_candidates_found = $false
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

    if ($script:TemporaryScenarioDir -and (Test-Path -LiteralPath $script:TemporaryScenarioDir) -and -not $DryRun) {
        Remove-Item -LiteralPath $script:TemporaryScenarioDir -Recurse -Force
    }

    Show-FinalSummary
    Write-Host ""
    Write-Host ("Relatório salvo em: {0}" -f $reportPath) -ForegroundColor Green

    if ($scriptFailed) {
        exit 1
    }
}
