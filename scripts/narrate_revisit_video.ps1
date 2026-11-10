$ErrorActionPreference = 'Stop'
$taskRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$taskAudio = Join-Path $taskRoot 'artifacts\video-revisit\audio'
New-Item -ItemType Directory -Path $taskAudio -Force | Out-Null
Add-Type -AssemblyName System.Speech
$scenes = Get-Content (Join-Path $PSScriptRoot 'revisit-video-scenes.json') -Raw -Encoding utf8 | ConvertFrom-Json
$speaker = [System.Speech.Synthesis.SpeechSynthesizer]::new()
try {
  $speaker.SelectVoice('Microsoft Sayaka')
  $speaker.Rate = 1
  $speaker.Volume = 90
  for ($i = 0; $i -lt $scenes.Count; $i++) {
    $speaker.SetOutputToWaveFile((Join-Path $taskAudio ('voice-{0:D2}.wav' -f $i)))
    $speaker.Speak($scenes[$i].voice)
    $speaker.SetOutputToNull()
  }
} finally { $speaker.Dispose() }
Write-Output '8 scenes narrated with installed Japanese voice; no network calls.'
