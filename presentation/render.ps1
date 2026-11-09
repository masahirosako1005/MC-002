param(
    [string]$Deck = 'outputs/tang-you-chi-presentation.pptx',
    [string]$Destination = 'artifacts/presentation'
)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$deckPath = (Resolve-Path -LiteralPath (Join-Path $projectRoot $Deck)).Path
$renderPath = [IO.Path]::GetFullPath((Join-Path $projectRoot $Destination))
if (-not $renderPath.StartsWith($projectRoot + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) {
    throw 'Rendering destination must stay inside the project.'
}
[IO.Directory]::CreateDirectory($renderPath) | Out-Null
$powerPoint = $null
$presentation = $null
try {
    $powerPoint = New-Object -ComObject PowerPoint.Application
    $powerPoint.AutomationSecurity = 3
    $presentation = $powerPoint.Presentations.Open($deckPath, -1, 0, 0)
    $report = [Collections.Generic.List[object]]::new()
    foreach ($slide in $presentation.Slides) {
        $index = $slide.SlideIndex
        $imagePath = Join-Path $renderPath ('slide-{0:d2}.png' -f $index)
        $slide.Export($imagePath, 'PNG', 1280, 720)
        foreach ($shape in $slide.Shapes) {
            if ($shape.HasTextFrame -eq -1 -and $shape.TextFrame.HasText -eq -1) {
                $range = $shape.TextFrame2.TextRange
                $report.Add([pscustomobject]@{
                    slide = $index
                    shape = $shape.Name
                    text = $range.Text
                    box = @($shape.Left, $shape.Top, $shape.Width, $shape.Height)
                    textBounds = @($range.BoundLeft, $range.BoundTop, $range.BoundWidth, $range.BoundHeight)
                })
            }
        }
        Write-Output ('Rendered slide {0}' -f $index)
    }
    $presentation.SaveAs((Join-Path $renderPath 'presentation-preview.pdf'), 32)
    $report | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $renderPath 'powerpoint-text-layout.json') -Encoding UTF8
    Write-Output ('PowerPoint {0}; slides: {1}' -f $powerPoint.Version, $presentation.Slides.Count)
}
finally {
    if ($null -ne $presentation) { $presentation.Close() }
    if ($null -ne $powerPoint) { $powerPoint.Quit() }
}
