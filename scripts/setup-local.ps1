[CmdletBinding()]
param([string]$PythonExecutable = '')
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
Push-Location $projectRoot
try {
    if (-not (Test-Path -LiteralPath '.venv/Scripts/python.exe')) {
        if (-not $PythonExecutable) {
            $installedPython = Join-Path $env:LOCALAPPDATA 'Programs/Python/Python313/python.exe'
            if (Test-Path -LiteralPath $installedPython) {
                $PythonExecutable = $installedPython
            }
            else {
                throw 'Python 3.12 or newer is required. Specify -PythonExecutable with its installed path.'
            }
        }
        & $PythonExecutable -m venv .venv
        if ($LASTEXITCODE -ne 0) { throw 'Python virtual environment creation failed.' }
    }
    & ./.venv/Scripts/python.exe -m pip install -r community/backend/requirements-dev.txt
    if ($LASTEXITCODE -ne 0) { throw 'Python dependency installation failed.' }
    & ./.venv/Scripts/python.exe -m pip check
    if ($LASTEXITCODE -ne 0) { throw 'Python dependency validation failed.' }
    Push-Location community/frontend
    try {
        & npm.cmd ci
        if ($LASTEXITCODE -ne 0) { throw 'Frontend dependency installation failed.' }
        & npm.cmd run build
        if ($LASTEXITCODE -ne 0) { throw 'Frontend build failed.' }
    }
    finally { Pop-Location }
    Push-Location test/browser
    try {
        & npm.cmd ci
        if ($LASTEXITCODE -ne 0) { throw 'Browser test dependency installation failed.' }
    }
    finally { Pop-Location }
    Write-Output 'Local dependencies and frontend build are ready.'
}
finally { Pop-Location }
