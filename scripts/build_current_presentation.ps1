param(
    [string]$Deck = 'outputs/kou-current-20261110.pptx',
    [string]$Preview = 'artifacts/presentation-current/rendered',
    [string]$Pdf = 'outputs/kou-current-20261110.pdf'
)
$ErrorActionPreference = 'Stop'
$taskRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
$taskDeck = [System.IO.Path]::GetFullPath((Join-Path $taskRoot $Deck))
$taskPreview = [System.IO.Path]::GetFullPath((Join-Path $taskRoot $Preview))
$taskPdf = [System.IO.Path]::GetFullPath((Join-Path $taskRoot $Pdf))
foreach ($taskPath in @($taskDeck, $taskPreview, $taskPdf)) {
    if (-not $taskPath.StartsWith($taskRoot + [System.IO.Path]::DirectorySeparatorChar, [System.StringComparison]::OrdinalIgnoreCase)) { throw 'All files must stay inside the project.' }
}
if (Test-Path -LiteralPath $taskPdf) { throw 'Preserve the existing PDF; choose a new output.' }
New-Item -ItemType Directory -Path $taskPreview -Force | Out-Null
$taskBefore = (Get-FileHash -LiteralPath $taskDeck -Algorithm SHA256).Hash
$taskApp = New-Object -ComObject PowerPoint.Application
$taskInitiallyOpen = $taskApp.Presentations.Count
$taskPresentation = $null
try {
    $taskPresentation = $taskApp.Presentations.Open($taskDeck, $true, $false, $false)
    $taskRows = @()
    for ($taskIndex = 1; $taskIndex -le $taskPresentation.Slides.Count; $taskIndex++) {
        $taskSlide = $taskPresentation.Slides.Item($taskIndex)
        $taskSlide.Export((Join-Path $taskPreview ('slide-{0:D2}.png' -f $taskIndex)), 'PNG', 1600, 900)
        foreach ($taskShape in $taskSlide.Shapes) {
            if ($taskShape.HasTextFrame -and $taskShape.TextFrame.HasText) {
                $taskText = $taskShape.TextFrame2.TextRange
                $taskRows += [pscustomobject]@{slide=$taskIndex;name=$taskShape.Name;left=$taskShape.Left;top=$taskShape.Top;width=$taskShape.Width;height=$taskShape.Height;boundHeight=$taskText.BoundHeight;boundWidth=$taskText.BoundWidth}
            }
        }
    }
    $taskPresentation.SaveAs($taskPdf, 32)
    $taskReport = [pscustomobject]@{slides=$taskPresentation.Slides.Count;renderer='Microsoft PowerPoint';readOnly=$true;sourceSha256=$taskBefore;text=$taskRows}
    $taskReport | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $taskPreview 'powerpoint-layout.json') -Encoding utf8
} finally {
    if ($null -ne $taskPresentation) { $taskPresentation.Close() }
    if ($taskInitiallyOpen -eq 0) { $taskApp.Quit() }
    [void][System.Runtime.InteropServices.Marshal]::ReleaseComObject($taskApp)
}
if ((Get-FileHash -LiteralPath $taskDeck -Algorithm SHA256).Hash -ne $taskBefore) { throw 'Read-only deck source changed.' }
Write-Output ('Rendered to ' + $taskPreview + ' and ' + $taskPdf)
