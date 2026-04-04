[CmdletBinding()]
param(
    [ValidateSet('architect', 'developer', 'auditor')]
    [string]$Role = 'developer',
    [string]$ProfileName,
    [string]$ConfigPath = 'automation/execution-profiles.json',
    [string]$LocalOverridePath = 'automation/execution-profiles.local.json'
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Resolve-RelativePath {
    param(
        [Parameter(Mandatory)][string]$BasePath,
        [Parameter(Mandatory)][string]$ChildPath
    )

    if ([System.IO.Path]::IsPathRooted($ChildPath)) { return $ChildPath }
    return [System.IO.Path]::GetFullPath((Join-Path $BasePath $ChildPath))
}

function Get-ObjectPropertyValue {
    param(
        [Parameter(Mandatory)]$Object,
        [Parameter(Mandatory)][string]$Name,
        $Default = $null
    )

    if ($null -eq $Object) { return $Default }
    $property = $Object.PSObject.Properties[$Name]
    if ($null -eq $property) { return $Default }
    return $property.Value
}

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot '..')
$configFullPath = Resolve-RelativePath -BasePath $repoRoot -ChildPath $ConfigPath
$localOverrideFullPath = Resolve-RelativePath -BasePath $repoRoot -ChildPath $LocalOverridePath

if (-not (Test-Path -LiteralPath $configFullPath)) {
    throw "Config file not found: $configFullPath"
}

$baseConfig = Get-Content -LiteralPath $configFullPath -Raw | ConvertFrom-Json
$activeProfile = if ($ProfileName) { $ProfileName } else { [string]$baseConfig.active_profile }

$profiles = @{}
foreach ($profileProp in $baseConfig.profiles.PSObject.Properties) {
    $profiles[$profileProp.Name] = $profileProp.Value
}

if (Test-Path -LiteralPath $localOverrideFullPath) {
    $localConfig = Get-Content -LiteralPath $localOverrideFullPath -Raw | ConvertFrom-Json
    if (-not $ProfileName -and $localConfig.active_profile) {
        $activeProfile = [string]$localConfig.active_profile
    }
    foreach ($profileProp in $localConfig.profiles.PSObject.Properties) {
        $profiles[$profileProp.Name] = $profileProp.Value
    }
}

if (-not $profiles.ContainsKey($activeProfile)) {
    throw "Profile not found: $activeProfile"
}

$selected = $profiles[$activeProfile]
$defaults = Get-ObjectPropertyValue -Object $selected -Name 'defaults' -Default ([pscustomobject]@{})
$roles = Get-ObjectPropertyValue -Object $selected -Name 'roles' -Default ([pscustomobject]@{})
$roleConfig = Get-ObjectPropertyValue -Object $roles -Name $Role

if ($null -eq $roleConfig) {
    throw "Role '$Role' not found in profile '$activeProfile'"
}

$result = [pscustomobject]@{
    profile_name = $activeProfile
    engine = [string](Get-ObjectPropertyValue -Object $selected -Name 'engine' -Default 'openai-codex-cli')
    command = [string](Get-ObjectPropertyValue -Object $selected -Name 'command' -Default 'codex')
    working_directory = [string](Get-ObjectPropertyValue -Object $selected -Name 'working_directory' -Default '.')
    runner_profile = [string](Get-ObjectPropertyValue -Object $selected -Name 'runner_profile' -Default '')
    model = [string](Get-ObjectPropertyValue -Object $roleConfig -Name 'model' -Default (Get-ObjectPropertyValue -Object $defaults -Name 'model' -Default 'gpt-5.4'))
    reasoning_effort = [string](Get-ObjectPropertyValue -Object $roleConfig -Name 'reasoning_effort' -Default (Get-ObjectPropertyValue -Object $defaults -Name 'reasoning_effort' -Default 'medium'))
    mode = [string](Get-ObjectPropertyValue -Object $roleConfig -Name 'mode' -Default 'agent')
    entrypoint = [string](Get-ObjectPropertyValue -Object $roleConfig -Name 'entrypoint' -Default '')
    config_path = $configFullPath
    local_override_path = $localOverrideFullPath
}

$result | ConvertTo-Json -Depth 10
