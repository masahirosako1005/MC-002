#Requires -RunAsAdministrator
[CmdletBinding()]
param()
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$logDirectory = Join-Path $projectRoot '.tools'
New-Item -ItemType Directory -Path $logDirectory -Force | Out-Null
$logPath = Join-Path $logDirectory 'wsl-feature-setup.log'
function Write-SetupLog([string]$Message) {
    $Message | Tee-Object -FilePath $logPath -Append
}
try {
    $feature = Get-WindowsOptionalFeature -Online -FeatureName VirtualMachinePlatform
    if ($feature.State -ne 'Enabled') {
        $result = Enable-WindowsOptionalFeature -Online -FeatureName VirtualMachinePlatform -All -NoRestart
        Write-SetupLog "VirtualMachinePlatform enabled. RestartNeeded=$($result.RestartNeeded)"
    }
    else {
        Write-SetupLog 'VirtualMachinePlatform is already enabled.'
    }
    $feature = Get-WindowsOptionalFeature -Online -FeatureName VirtualMachinePlatform
    Write-SetupLog "VirtualMachinePlatform state: $($feature.State)"
    $wingetCommand = Get-Command winget.exe -ErrorAction SilentlyContinue
    if ($wingetCommand) {
        & $wingetCommand.Source install --id Microsoft.WSL --exact --source winget --silent --accept-package-agreements --accept-source-agreements --disable-interactivity
        Write-SetupLog "WSL package installer exit code: $LASTEXITCODE"
    }
    else {
        Write-SetupLog 'winget was not found in the administrator context; WSL package installation remains pending.'
    }
    Write-SetupLog 'No automatic restart was requested. If restart is needed, save work before restarting Windows.'
}
catch {
    Write-SetupLog 'Setup failed. Inspect the command error locally; no automatic restart was requested.'
    throw
}
