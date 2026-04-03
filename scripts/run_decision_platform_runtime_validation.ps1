[CmdletBinding()]
param(
    [string]$Branch = "codex/new-architecture-platform",
    [string]$ScenarioDir = "data/decision_platform/maquete_v2",
    [string]$OutputDir = "data/output/decision_platform/maquete_v2",
    [string]$LogsDir = "scripts/logs",
    [switch]$SkipUi,
    [switch]$WaitForUi,
    [int]$UiStartupWaitSeconds = 5,
    [switch]$DryRun
)

Set-StrictMode -Version 3.0
$ErrorActionPreference = "Stop"

$script:RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$script:PythonExe = Join-Path $script:RepoRoot ".venv\Scripts\python.exe"
$script:ActivateScript = Join-Path $script:RepoRoot ".venv\Scripts\Activate.ps1"
$script:JuliaDepotDir = Join-Path $script:RepoRoot "julia_depot_runtime"
$script:ExpectedArtifacts = @(
    "summary.json",
    "catalog.csv",
    "catalog_detailed.json",
    "ranking_profiles.json",
    "selected_candidate.json",
    "selected_candidate_routes.json",
    "selected_candidate_score_breakdown.json",
    "selected_candidate_render.json",
    "selected_candidate_bom.csv",
    "selected_candidate.svg",
    "selected_candidate.png"
)
$script:PipelineStepStartedAt = $null
$script:ReportTimestamp = Get-Date
$script:Report = [ordered]@{
    started_at = $script:ReportTimestamp.ToString("o")
    repo_root = $script:RepoRoot
    branch = $Branch
    scenario_dir = $ScenarioDir
    output_dir = $OutputDir
    dry_run = [bool]$DryRun
    steps = @()
}

function Format-Duration {
    param(
        [Parameter(Mandatory = $true)]
        [TimeSpan]$Duration
    )

    return ("{0:00}:{1:00}:{2:00}.{3:000}" -f $Duration.Hours, $Duration.Minutes, $Duration.Seconds, $Duration.Milliseconds)
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
    $logsPath = Join-Path $script:RepoRoot $LogsDir
    if (-not (Test-Path -LiteralPath $logsPath)) {
        New-Item -ItemType Directory -Path $logsPath -Force | Out-Null
    }

    $reportPath = Join-Path $logsPath ("decision-platform-runtime-validation_{0}.json" -f $script:ReportTimestamp.ToString("yyyyMMdd-HHmmss"))
    ($script:Report | ConvertTo-Json -Depth 20) | Set-Content -LiteralPath $reportPath -Encoding utf8
    return $reportPath
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

function Invoke-ExternalCommand {
    param(
        [Parameter(Mandatory = $true)]
        [string]$FilePath,
        [string[]]$ArgumentList = @(),
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
            Output = @()
        }
    }

    if ($CaptureOutput) {
        $output = & $FilePath @ArgumentList 2>&1
        $exitCode = $LASTEXITCODE
        foreach ($line in @($output)) {
            Write-Host $line
        }
        if ($exitCode -ne 0) {
            throw ("Falha ao executar comando: {0} (exit code {1})" -f $displayCommand, $exitCode)
        }
        return [pscustomobject]@{
            Command = $displayCommand
            ExitCode = $exitCode
            Output = @($output)
        }
    }

    & $FilePath @ArgumentList
    $exitCode = $LASTEXITCODE
    if ($exitCode -ne 0) {
        throw ("Falha ao executar comando: {0} (exit code {1})" -f $displayCommand, $exitCode)
    }
    return [pscustomobject]@{
        Command = $displayCommand
        ExitCode = $exitCode
        Output = @()
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

function Add-SkippedStep {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Name,
        [string]$Reason
    )

    Write-StepBanner -Name $Name
    $record = [pscustomobject]@{
        name = $Name
        started_at = (Get-Date).ToString("o")
        finished_at = (Get-Date).ToString("o")
        status = "skipped"
        duration_seconds = 0.0
        duration_display = "00:00:00.000"
        details = @{
            reason = $Reason
        }
    }
    $script:Report.steps += $record
    Write-Host ("Status: skipped | Motivo: {0}" -f $Reason) -ForegroundColor Yellow
}

function Get-JuliaCommand {
    $existingJuliaVar = Get-Variable -Name JuliaCommand -Scope Script -ErrorAction SilentlyContinue
    if ($existingJuliaVar -and $null -ne $existingJuliaVar.Value -and -not [string]::IsNullOrWhiteSpace([string]$existingJuliaVar.Value)) {
        return $existingJuliaVar.Value
    }

    if ($DryRun) {
        $script:JuliaCommand = "julia"
        return $script:JuliaCommand
    }

    $resolved = Get-Command julia -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($resolved) {
        $script:JuliaCommand = $resolved.Source
        return $script:JuliaCommand
    }

    if ($env:JULIA_EXE) {
        if (-not (Test-Path -LiteralPath $env:JULIA_EXE)) {
            throw ("JULIA_EXE foi definido, mas o caminho não existe: {0}" -f $env:JULIA_EXE)
        }
        $script:JuliaCommand = (Resolve-Path -LiteralPath $env:JULIA_EXE).Path
        return $script:JuliaCommand
    }

    throw "Julia não foi encontrado no PATH. Defina JULIA_EXE se o alias do sistema não estiver disponível."
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
    if ([string]::IsNullOrWhiteSpace([string]$Data[$FieldName])) {
        throw ("Campo obrigatório vazio em {0}: {1}" -f $Context, $FieldName)
    }
}

function Assert-BooleanTrue {
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
    if (-not [bool]$Data[$FieldName]) {
        throw ("Campo {0} em {1} deveria ser true." -f $FieldName, $Context)
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

try {
    Invoke-Step -Name "1. Branch e ambiente" -Action {
        if (-not (Test-Path -LiteralPath $script:PythonExe) -and -not $DryRun) {
            throw ("Python da virtualenv não encontrado: {0}" -f $script:PythonExe)
        }

        $null = Invoke-ExternalCommand -FilePath "git" -ArgumentList @("checkout", $Branch) -Description "Trocando para a branch alvo"

        if (-not $DryRun) {
            if (-not (Test-Path -LiteralPath $script:ActivateScript)) {
                throw ("Script de ativação não encontrado: {0}" -f $script:ActivateScript)
            }
            . $script:ActivateScript
        }
        else {
            Write-Host ("> . {0}" -f $script:ActivateScript) -ForegroundColor DarkGray
        }

        $env:PYTHONPATH = "src"
        if (-not (Test-Path -LiteralPath $script:JuliaDepotDir) -and -not $DryRun) {
            throw ("Diretório do depot Julia não encontrado: {0}" -f $script:JuliaDepotDir)
        }
        $env:JULIA_DEPOT_PATH = Resolve-WorkspacePath -PathValue $script:JuliaDepotDir

        $branchOutput = Invoke-ExternalCommand -FilePath "git" -ArgumentList @("branch", "--show-current") -Description "Branch ativa" -CaptureOutput
        $activeBranch = if ($DryRun) {
            $Branch
        }
        else {
            (@($branchOutput.Output) | Select-Object -Last 1).ToString().Trim()
        }
        if (-not $DryRun -and $activeBranch -ne $Branch) {
            throw ("Branch ativa inesperada após checkout: {0}" -f $activeBranch)
        }

        $pythonVersion = Invoke-ExternalCommand -FilePath $script:PythonExe -ArgumentList @("--version") -Description "Versão do Python da virtualenv" -CaptureOutput
        $pythonVersionText = if ($DryRun) {
            "python --version"
        }
        else {
            (@($pythonVersion.Output) | Select-Object -Last 1).ToString().Trim()
        }

        return @{
            active_branch = $activeBranch
            pythonpath = $env:PYTHONPATH
            julia_depot_path = $env:JULIA_DEPOT_PATH
            python_version = $pythonVersionText
        }
    }

    Invoke-Step -Name "2. Validar Julia" -Action {
        $juliaCommand = Get-JuliaCommand
        $versionResult = Invoke-ExternalCommand -FilePath $juliaCommand -ArgumentList @("--version") -Description "Validando acesso ao Julia" -CaptureOutput
        $depotResult = Invoke-ExternalCommand -FilePath $juliaCommand -ArgumentList @("-e", "println(DEPOT_PATH)") -Description "Listando DEPOT_PATH" -CaptureOutput

        $versionLine = if ($DryRun) {
            "julia --version"
        }
        else {
            (@($versionResult.Output) | Select-Object -Last 1).ToString().Trim()
        }
        $depotLines = if ($DryRun) {
            @($env:JULIA_DEPOT_PATH)
        }
        else {
            @($depotResult.Output | ForEach-Object { $_.ToString().Trim() }) | Where-Object { $_ }
        }
        $depotVisible = $DryRun -or (($depotLines -join "`n") -match [regex]::Escape((Split-Path $env:JULIA_DEPOT_PATH -Leaf)))
        if (-not $depotVisible) {
            throw ("O JULIA_DEPOT_PATH atual não apareceu na saída de DEPOT_PATH: {0}" -f $env:JULIA_DEPOT_PATH)
        }

        return @{
            julia_command = $juliaCommand
            julia_version = $versionLine
            depot_visible = $depotVisible
            depot_path = $env:JULIA_DEPOT_PATH
        }
    }

    Invoke-Step -Name "3. Suíte rápida" -Action {
        $null = Invoke-ExternalCommand -FilePath $script:PythonExe -ArgumentList @(
            "-m", "pytest",
            "tests/decision_platform",
            "-p", "no:tmpdir",
            "--basetemp", "tests/_tmp/pytest-basetemp-fast",
            "-m", "not slow and not requires_julia",
            "-q"
        ) -Description "Executando a suíte rápida"

        return @{
            marker = "not slow and not requires_julia"
            basetemp = "tests/_tmp/pytest-basetemp-fast"
        }
    }

    Invoke-Step -Name "4. Suíte com Julia real" -Action {
        $null = Invoke-ExternalCommand -FilePath $script:PythonExe -ArgumentList @(
            "-m", "pytest",
            "tests/decision_platform",
            "-p", "no:tmpdir",
            "--basetemp", "tests/_tmp/pytest-basetemp-julia",
            "-m", "requires_julia",
            "-vv",
            "-s"
        ) -Description "Executando a suíte marcada com requires_julia"

        return @{
            marker = "requires_julia"
            basetemp = "tests/_tmp/pytest-basetemp-julia"
            expected_engine = "watermodels_jl"
            expected_mode = "real_julia"
        }
    }

    Invoke-Step -Name "5. Pipeline maquete_v2" -Action {
        $script:PipelineStepStartedAt = Get-Date
        $null = Invoke-ExternalCommand -FilePath $script:PythonExe -ArgumentList @(
            "-m", "decision_platform.api.run_pipeline",
            "--scenario", $ScenarioDir,
            "--output-dir", $OutputDir
        ) -Description "Executando o pipeline principal"

        $summaryPath = Join-Path (Resolve-WorkspacePath -PathValue $OutputDir) "summary.json"
        $summary = if ((Test-Path -LiteralPath $summaryPath) -and -not $DryRun) { Read-JsonFile -PathValue $summaryPath } else { @{} }

        return @{
            output_dir = Resolve-WorkspacePath -PathValue $OutputDir
            selected_candidate_id = $summary["selected_candidate_id"]
            engine_requested = $summary["engine_requested"]
            engine_used = $summary["engine_used"]
            engine_mode = $summary["engine_mode"]
        }
    }

    Invoke-Step -Name "6. Conferir artefatos de saída" -Action {
        if ($DryRun) {
            return @{
                artifact_count_checked = $script:ExpectedArtifacts.Count
                output_dir = Resolve-WorkspacePath -PathValue $OutputDir
                simulated = $true
            }
        }

        $resolvedOutputDir = Resolve-WorkspacePath -PathValue $OutputDir
        if (-not (Test-Path -LiteralPath $resolvedOutputDir) -and -not $DryRun) {
            throw ("Diretório de saída não encontrado: {0}" -f $resolvedOutputDir)
        }

        $missing = New-Object System.Collections.Generic.List[string]
        $stale = New-Object System.Collections.Generic.List[string]
        foreach ($artifact in $script:ExpectedArtifacts) {
            $artifactPath = Join-Path $resolvedOutputDir $artifact
            if (-not (Test-Path -LiteralPath $artifactPath)) {
                $missing.Add($artifactPath)
                continue
            }
            if ($script:PipelineStepStartedAt) {
                $artifactItem = Get-Item -LiteralPath $artifactPath
                if ($artifactItem.LastWriteTime -lt $script:PipelineStepStartedAt.AddSeconds(-2)) {
                    $stale.Add($artifactPath)
                }
            }
        }

        if ($missing.Count -gt 0) {
            throw ("Artefatos ausentes após o pipeline:`n- {0}" -f ($missing -join "`n- "))
        }
        if ($stale.Count -gt 0) {
            throw ("Artefatos não foram atualizados nesta execução:`n- {0}" -f ($stale -join "`n- "))
        }

        return @{
            artifact_count_checked = $script:ExpectedArtifacts.Count
            output_dir = $resolvedOutputDir
        }
    }

    Invoke-Step -Name "7. Checklist de consistência" -Action {
        if ($DryRun) {
            return @{
                selected_candidate_id = "dry-run"
                default_profile_id = "balanced"
                topology_family = "dry-run"
                score_final = 0
                simulated = $true
            }
        }

        $resolvedOutputDir = Resolve-WorkspacePath -PathValue $OutputDir
        $summary = Read-JsonFile -PathValue (Join-Path $resolvedOutputDir "summary.json")
        $selectedCandidate = Read-JsonFile -PathValue (Join-Path $resolvedOutputDir "selected_candidate.json")
        $selectedRoutes = Read-JsonFile -PathValue (Join-Path $resolvedOutputDir "selected_candidate_routes.json")
        $selectedRender = Read-JsonFile -PathValue (Join-Path $resolvedOutputDir "selected_candidate_render.json")
        $selectedBreakdown = Read-JsonFile -PathValue (Join-Path $resolvedOutputDir "selected_candidate_score_breakdown.json")
        $rankingProfiles = Read-JsonFile -PathValue (Join-Path $resolvedOutputDir "ranking_profiles.json")
        $selectedBom = Import-Csv -LiteralPath (Join-Path $resolvedOutputDir "selected_candidate_bom.csv")

        Assert-FieldPresent -Data $summary -FieldName "default_profile_id" -Context "summary.json"
        Assert-FieldPresent -Data $summary -FieldName "selected_candidate_id" -Context "summary.json"
        Assert-FieldPresent -Data $summary -FieldName "engine_requested" -Context "summary.json"
        Assert-FieldPresent -Data $summary -FieldName "engine_used" -Context "summary.json"
        Assert-FieldPresent -Data $summary -FieldName "engine_mode" -Context "summary.json"

        $selectedCandidateId = [string]$summary["selected_candidate_id"]
        $defaultProfileId = [string]$summary["default_profile_id"]

        if ([string]$summary["engine_requested"] -ne "watermodels_jl") {
            throw ("engine_requested inesperado em summary.json: {0}" -f $summary["engine_requested"])
        }
        if ([string]$summary["engine_used"] -ne "watermodels_jl") {
            throw ("engine_used inesperado em summary.json: {0}" -f $summary["engine_used"])
        }
        if ([string]$summary["engine_mode"] -ne "real_julia") {
            throw ("engine_mode inesperado em summary.json: {0}" -f $summary["engine_mode"])
        }
        Assert-BooleanTrue -Data $summary -FieldName "julia_available" -Context "summary.json"
        Assert-BooleanTrue -Data $summary -FieldName "watermodels_available" -Context "summary.json"

        Assert-FieldPresent -Data $selectedCandidate -FieldName "candidate_id" -Context "selected_candidate.json"
        Assert-FieldPresent -Data $selectedCandidate -FieldName "topology_family" -Context "selected_candidate.json"
        if ([string]$selectedCandidate["candidate_id"] -ne $selectedCandidateId) {
            throw "candidate_id de selected_candidate.json difere de summary.json."
        }

        $metrics = $selectedCandidate["metrics"]
        if (-not ($metrics -is [hashtable])) {
            throw "selected_candidate.json não contém metrics no formato esperado."
        }
        foreach ($field in @("feasible", "install_cost", "fallback_cost", "quality_score_raw", "flow_out_score", "resilience_score", "cleaning_score", "engine_requested", "engine_used", "engine_mode")) {
            if (-not $metrics.ContainsKey($field)) {
                throw ("Campo obrigatório ausente em selected_candidate.json.metrics: {0}" -f $field)
            }
        }
        if ([string]$metrics["engine_used"] -ne "watermodels_jl") {
            throw ("selected_candidate.json.metrics.engine_used inesperado: {0}" -f $metrics["engine_used"])
        }
        if ([string]$metrics["engine_mode"] -ne "real_julia") {
            throw ("selected_candidate.json.metrics.engine_mode inesperado: {0}" -f $metrics["engine_mode"])
        }

        Assert-FieldPresent -Data $selectedRoutes -FieldName "candidate_id" -Context "selected_candidate_routes.json"
        Assert-FieldPresent -Data $selectedRoutes -FieldName "topology_family" -Context "selected_candidate_routes.json"
        if ([string]$selectedRoutes["candidate_id"] -ne $selectedCandidateId) {
            throw "candidate_id de selected_candidate_routes.json difere do selecionado."
        }
        if ([string]$selectedRoutes["topology_family"] -ne [string]$selectedCandidate["topology_family"]) {
            throw "topology_family de selected_candidate_routes.json difere de selected_candidate.json."
        }

        Assert-FieldPresent -Data $selectedRender -FieldName "candidate_id" -Context "selected_candidate_render.json"
        Assert-FieldPresent -Data $selectedRender -FieldName "topology_family" -Context "selected_candidate_render.json"
        if ([string]$selectedRender["candidate_id"] -ne $selectedCandidateId) {
            throw "candidate_id de selected_candidate_render.json difere do selecionado."
        }
        if ([string]$selectedRender["topology_family"] -ne [string]$selectedCandidate["topology_family"]) {
            throw "topology_family de selected_candidate_render.json difere de selected_candidate.json."
        }

        Assert-FieldPresent -Data $selectedBreakdown -FieldName "candidate_id" -Context "selected_candidate_score_breakdown.json"
        Assert-FieldPresent -Data $selectedBreakdown -FieldName "profile_id" -Context "selected_candidate_score_breakdown.json"
        foreach ($field in @("quality_score_breakdown", "quality_flags", "rules_triggered", "selection_log")) {
            if (-not $selectedBreakdown.ContainsKey($field)) {
                throw ("Campo obrigatório ausente em selected_candidate_score_breakdown.json: {0}" -f $field)
            }
        }
        if ([string]$selectedBreakdown["candidate_id"] -ne $selectedCandidateId) {
            throw "candidate_id de selected_candidate_score_breakdown.json difere do selecionado."
        }
        if ([string]$selectedBreakdown["profile_id"] -ne $defaultProfileId) {
            throw "profile_id de selected_candidate_score_breakdown.json difere do perfil padrão."
        }

        if (-not $rankingProfiles.ContainsKey($defaultProfileId)) {
            throw ("Perfil padrão ausente em ranking_profiles.json: {0}" -f $defaultProfileId)
        }
        $rankingRecords = @($rankingProfiles[$defaultProfileId])
        if ($rankingRecords.Count -eq 0) {
            throw ("ranking_profiles.json não contém registros para o perfil padrão: {0}" -f $defaultProfileId)
        }
        if ([string]$rankingRecords[0]["candidate_id"] -ne $selectedCandidateId) {
            throw "O candidato selecionado não é o primeiro do ranking do perfil padrão."
        }
        if (-not $rankingRecords[0].ContainsKey("score_final")) {
            throw "ranking_profiles.json não expôs o campo score_final para o candidato selecionado."
        }

        if ($selectedBom.Count -eq 0) {
            throw "selected_candidate_bom.csv não contém linhas."
        }
        if (-not ($selectedBom[0].PSObject.Properties.Name -contains "candidate_id")) {
            throw "selected_candidate_bom.csv não contém a coluna candidate_id."
        }
        $invalidBomRows = @($selectedBom | Where-Object { $_.candidate_id -ne $selectedCandidateId })
        if ($invalidBomRows.Count -gt 0) {
            throw "selected_candidate_bom.csv contém linhas com candidate_id diferente do candidato selecionado."
        }

        return @{
            selected_candidate_id = $selectedCandidateId
            default_profile_id = $defaultProfileId
            topology_family = $selectedCandidate["topology_family"]
            score_final = $rankingRecords[0]["score_final"]
            install_cost = $metrics["install_cost"]
            fallback_cost = $metrics["fallback_cost"]
            quality_score_raw = $metrics["quality_score_raw"]
            resilience_score = $metrics["resilience_score"]
            cleaning_score = $metrics["cleaning_score"]
        }
    }

    if ($SkipUi) {
        Add-SkippedStep -Name "8. UI local" -Reason "Execução da UI foi desabilitada via -SkipUi."
    }
    else {
        Invoke-Step -Name "8. UI local" -Action {
            $argumentList = @("-m", "decision_platform.ui_dash.app")

            if ($DryRun) {
                Write-Host ("> {0} {1}" -f $script:PythonExe, ($argumentList -join " ")) -ForegroundColor DarkGray
                return @{
                    launched = $true
                    mode = "dry_run"
                    url_hint = "http://127.0.0.1:8050"
                }
            }

            if ($WaitForUi) {
                & $script:PythonExe @argumentList
                $exitCode = $LASTEXITCODE
                if ($exitCode -ne 0) {
                    throw ("A UI encerrou com exit code {0}." -f $exitCode)
                }
                return @{
                    launched = $true
                    mode = "wait"
                    url_hint = "http://127.0.0.1:8050"
                }
            }

            $process = Start-Process -FilePath $script:PythonExe -ArgumentList $argumentList -WorkingDirectory $script:RepoRoot -PassThru
            Start-Sleep -Seconds $UiStartupWaitSeconds
            $process.Refresh()
            if ($process.HasExited -and $process.ExitCode -ne 0) {
                throw ("A UI encerrou logo após o start com exit code {0}." -f $process.ExitCode)
            }

            return @{
                launched = $true
                mode = "background"
                pid = $process.Id
                url_hint = "http://127.0.0.1:8050"
                wait_seconds = $UiStartupWaitSeconds
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
    $script:Report.success = -not $scriptFailed
    $reportPath = Save-Report
    $script:Report.report_path = $reportPath

    Show-FinalSummary
    Write-Host ""
    Write-Host ("Relatório salvo em: {0}" -f $reportPath) -ForegroundColor Green

    if ($scriptFailed) {
        exit 1
    }
}
