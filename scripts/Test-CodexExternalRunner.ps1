[CmdletBinding()]
param(
    [ValidateSet('architect', 'developer', 'auditor')]
    [string]$Role = 'architect',
    [string]$ProfileName,
    [string]$Model,
    [string]$ReasoningEffort,
    [string]$PromptText = 'Return exactly {"status":"ok","role":"architect"}',
    [switch]$PreflightOnly,
    [switch]$RunProbe
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function New-Directory {
    param([Parameter(Mandatory)][string]$Path)
    if (-not (Test-Path -LiteralPath $Path)) {
        New-Item -ItemType Directory -Path $Path -Force | Out-Null
    }
}

function Get-ExistingCodexHomePath {
    $candidates = @()
    if (-not [string]::IsNullOrWhiteSpace($env:CODEX_HOME)) {
        $candidates += $env:CODEX_HOME
    }
    if (-not [string]::IsNullOrWhiteSpace($env:USERPROFILE)) {
        $candidates += (Join-Path $env:USERPROFILE '.codex')
    }
    if (-not [string]::IsNullOrWhiteSpace($env:HOME)) {
        $candidates += (Join-Path $env:HOME '.codex')
    }

    foreach ($candidate in @($candidates | Select-Object -Unique)) {
        if (-not [string]::IsNullOrWhiteSpace($candidate) -and (Test-Path -LiteralPath $candidate)) {
            return (Resolve-Path -LiteralPath $candidate).Path
        }
    }

    return $null
}

function Get-PreferredCodexCommand {
    $whereOutput = @()
    try {
        $whereOutput = @(where.exe codex 2>$null)
    }
    catch {
        $whereOutput = @()
    }

    foreach ($preferredExtension in @('.cmd', '.exe', '.bat', '')) {
        foreach ($candidate in $whereOutput) {
            $extension = [System.IO.Path]::GetExtension([string]$candidate).ToLowerInvariant()
            if ($extension -eq $preferredExtension) {
                return [string]$candidate
            }
        }
    }

    $fallback = Get-Command codex -ErrorAction SilentlyContinue
    if ($fallback) {
        return [string]$fallback.Source
    }

    return $null
}

function ConvertTo-PowerShellSingleQuotedLiteral {
    param([Parameter(Mandatory)][string]$Value)
    return "'" + ($Value -replace "'", "''") + "'"
}

function Initialize-IsolatedCodexHome {
    param(
        [Parameter(Mandatory)][string]$TargetPath,
        [Parameter(Mandatory)][string]$ConfigContent
    )

    $allowedNames = @(
        'auth.json',
        'cap_sid',
        '.sandbox-secrets',
        'sessions',
        'rules',
        'version.json',
        '.codex-global-state.json',
        'models_cache.json'
    )

    New-Directory -Path $TargetPath
    $sourcePath = Get-ExistingCodexHomePath
    if ($sourcePath) {
        foreach ($item in Get-ChildItem -LiteralPath $sourcePath -Force -ErrorAction SilentlyContinue) {
            if (-not ($allowedNames -contains $item.Name)) {
                continue
            }
            $destination = Join-Path $TargetPath $item.Name
            try {
                if ($item.PSIsContainer) {
                    Copy-Item -LiteralPath $item.FullName -Destination $destination -Recurse -Force -ErrorAction Stop
                }
                else {
                    Copy-Item -LiteralPath $item.FullName -Destination $destination -Force -ErrorAction Stop
                }
            }
            catch {
                continue
            }
        }
    }

    [System.IO.File]::WriteAllText((Join-Path $TargetPath 'config.toml'), $ConfigContent, [System.Text.UTF8Encoding]::new($false))
    return $sourcePath
}

function Get-IsolatedCodexConfigContent {
    param(
        [Parameter(Mandatory)][string]$RunnerProfile,
        [Parameter(Mandatory)][string]$Model,
        [Parameter(Mandatory)][string]$ReasoningEffort
    )

    @(
        "profile = ""$RunnerProfile"""
        "model = ""$Model"""
        "model_reasoning_effort = ""$ReasoningEffort"""
        'approval_policy = "never"'
        'sandbox_mode = "workspace-write"'
        ''
        '[sandbox_workspace_write]'
        'network_access = true'
        ''
        "[profiles.$RunnerProfile]"
        "model = ""$Model"""
        "model_reasoning_effort = ""$ReasoningEffort"""
        'approval_policy = "never"'
        ''
    ) -join "`n"
}

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$runtimeRoot = Join-Path $repoRoot 'docs\codex_dual_agent_runtime\probe'
New-Directory -Path $runtimeRoot

$profileJson = & (Join-Path $PSScriptRoot 'Get-CodexExecutionProfile.ps1') -Role $Role -ProfileName $ProfileName
$profile = $profileJson | ConvertFrom-Json
if (-not [string]::IsNullOrWhiteSpace($Model)) {
    $profile.model = $Model
}
if (-not [string]::IsNullOrWhiteSpace($ReasoningEffort)) {
    $profile.reasoning_effort = $ReasoningEffort
}

$codexCommandPath = Get-PreferredCodexCommand
$pwshCommand = Get-Command pwsh -ErrorAction SilentlyContinue
if (-not $pwshCommand) {
    $pwshCommand = Get-Command powershell -ErrorAction SilentlyContinue
}
$sourceCodexHome = Get-ExistingCodexHomePath

$result = [ordered]@{
    role = $Role
    profile_name = $profile.profile_name
    codex_cli_found = -not [string]::IsNullOrWhiteSpace($codexCommandPath)
    codex_cli_path = $codexCommandPath
    pwsh_found = ($null -ne $pwshCommand)
    pwsh_path = if ($pwshCommand) { $pwshCommand.Source } else { $null }
    codex_home_seed_found = -not [string]::IsNullOrWhiteSpace($sourceCodexHome)
    codex_home_seed_path = $sourceCodexHome
    probe_requested = [bool]$RunProbe
    probe_executed = $false
    probe_ok = $false
    probe_exit_code = $null
    probe_last_message_path = $null
    probe_stdout_path = $null
    probe_stderr_path = $null
    notes = @()
}

if (-not $result.codex_cli_found) {
    $result.notes += 'Codex CLI não encontrado no PATH.'
}
if (-not $result.pwsh_found) {
    $result.notes += 'PowerShell não encontrado no PATH.'
}
if (-not $result.codex_home_seed_found) {
    $result.notes += 'Nenhum CODEX_HOME local foi encontrado para seed.'
}
if (-not $RunProbe) {
    $result.notes += 'Probe real não executado. Use -RunProbe em um shell externo ao Codex.'
}

if ($PreflightOnly -or -not $RunProbe) {
    $result | ConvertTo-Json -Depth 20
    exit 0
}

if (-not $result.codex_cli_found -or -not $result.pwsh_found -or -not $result.codex_home_seed_found) {
    $result.notes += 'Probe abortado por preflight incompleto.'
    $result | ConvertTo-Json -Depth 20
    exit 1
}

$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$runRoot = Join-Path $runtimeRoot ("$stamp-$Role")
New-Directory -Path $runRoot

$codexHome = Join-Path $runRoot 'codex-home'
$promptPath = Join-Path $runRoot 'probe.prompt.md'
$schemaPath = Join-Path $runRoot 'probe.schema.json'
$lastMessagePath = Join-Path $runRoot 'probe.last-message.json'
$stdoutPath = Join-Path $runRoot 'probe.stdout.log'
$stderrPath = Join-Path $runRoot 'probe.stderr.log'
$runnerPath = Join-Path $runRoot 'probe_runner.ps1'

$sharedCodexHome = Get-ExistingCodexHomePath
if (-not $sharedCodexHome) {
    throw "Nenhum CODEX_HOME real foi encontrado para autenticação."
}
[System.IO.Directory]::CreateDirectory($codexHome) | Out-Null
[System.IO.File]::WriteAllText($promptPath, $PromptText + [Environment]::NewLine, [System.Text.UTF8Encoding]::new($false))
[System.IO.File]::WriteAllText($schemaPath, "{""type"":""object"",""properties"":{},""required"":[],""additionalProperties"":false}" + [Environment]::NewLine, [System.Text.UTF8Encoding]::new($false))

$runnerLines = @(
    '$ErrorActionPreference = ''Stop'''
    ('$env:CODEX_HOME = ' + (ConvertTo-PowerShellSingleQuotedLiteral -Value $sharedCodexHome))
    ('$commandPath = ' + (ConvertTo-PowerShellSingleQuotedLiteral -Value $codexCommandPath))
    ('$promptPath = ' + (ConvertTo-PowerShellSingleQuotedLiteral -Value $promptPath))
    ('$schemaPath = ' + (ConvertTo-PowerShellSingleQuotedLiteral -Value $schemaPath))
    ('$lastMessagePath = ' + (ConvertTo-PowerShellSingleQuotedLiteral -Value $lastMessagePath))
    '$args = @(''exec'', ''-'', ''--json'', ''--skip-git-repo-check'')'
    '$args += ''--cd'''
    ('$args += ' + (ConvertTo-PowerShellSingleQuotedLiteral -Value $repoRoot))
    '$args += ''--sandbox'''
    '$args += ''workspace-write'''
    '$args += ''--add-dir'''
    ('$args += ' + (ConvertTo-PowerShellSingleQuotedLiteral -Value $repoRoot))
    '$args += ''--output-schema'''
    ('$args += ' + (ConvertTo-PowerShellSingleQuotedLiteral -Value $schemaPath))
    '$args += ''-o'''
    ('$args += ' + (ConvertTo-PowerShellSingleQuotedLiteral -Value $lastMessagePath))
)

if (-not [string]::IsNullOrWhiteSpace([string]$profile.runner_profile)) {
    $runnerLines += '$args += ''--profile'''
    $runnerLines += ('$args += ' + (ConvertTo-PowerShellSingleQuotedLiteral -Value ([string]$profile.runner_profile)))
}

if (-not [string]::IsNullOrWhiteSpace([string]$profile.model)) {
    $runnerLines += '$args += ''--model'''
    $runnerLines += ('$args += ' + (ConvertTo-PowerShellSingleQuotedLiteral -Value ([string]$profile.model)))
}

if (-not [string]::IsNullOrWhiteSpace([string]$profile.reasoning_effort)) {
    $runnerLines += '$args += ''-c'''
    $runnerLines += ('$args += ' + (ConvertTo-PowerShellSingleQuotedLiteral -Value ('model_reasoning_effort="' + [string]$profile.reasoning_effort + '"')))
}

$runnerLines += @(
    '$prompt = [System.IO.File]::ReadAllText($promptPath, [System.Text.UTF8Encoding]::new($false))'
    '$prompt | & $commandPath @args'
    'exit $LASTEXITCODE'
)

[System.IO.File]::WriteAllText($runnerPath, ($runnerLines -join [Environment]::NewLine) + [Environment]::NewLine, [System.Text.UTF8Encoding]::new($false))

$process = Start-Process -FilePath $pwshCommand.Source -ArgumentList @('-NoLogo', '-NoProfile', '-NonInteractive', '-File', $runnerPath) -WorkingDirectory $repoRoot -NoNewWindow -PassThru -RedirectStandardOutput $stdoutPath -RedirectStandardError $stderrPath
$process.WaitForExit()
$process.Refresh()

$result.probe_executed = $true
$effectiveExitCode = if ($null -ne $process.ExitCode) { [int]$process.ExitCode } else { -1 }
$result.probe_exit_code = $effectiveExitCode
$result.probe_ok = (
    $effectiveExitCode -eq 0 -and
    (Test-Path -LiteralPath $lastMessagePath) -and
    ((Get-Item -LiteralPath $lastMessagePath).Length -gt 0)
)
$result.probe_last_message_path = $lastMessagePath
$result.probe_stdout_path = $stdoutPath
$result.probe_stderr_path = $stderrPath

if (-not $result.probe_ok) {
    $result.notes += 'Probe executado, mas não concluiu com sucesso. Verifique stdout/stderr.'
}

$result | ConvertTo-Json -Depth 20
