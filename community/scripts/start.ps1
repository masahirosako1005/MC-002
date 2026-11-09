param([switch]$Build)
$ErrorActionPreference = 'Stop'
$communityRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
$composePath = Join-Path $communityRoot 'compose.yaml'
foreach ($required in @('models', 'assets')) {
    $directory = Join-Path $communityRoot $required
    if (-not (Test-Path -LiteralPath $directory -PathType Container)) {
        throw "Required project directory is missing: $directory"
    }
}
if ($Build) {
    & docker compose -p kou-community --project-directory $communityRoot -f $composePath build app
    if ($LASTEXITCODE -ne 0) { throw 'Community image build failed.' }
}
& docker compose -p kou-community --project-directory $communityRoot -f $composePath up -d --wait
if ($LASTEXITCODE -ne 0) { throw 'Community startup failed.' }
Write-Output 'Community: http://127.0.0.1:8081 (the existing app on 8080 is unchanged).'
