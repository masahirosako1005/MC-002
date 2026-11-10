$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$taskRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$taskDirectory = Join-Path $taskRoot 'artifacts/video-revisit/v13/audio/login-intro-07'
if (Test-Path -LiteralPath $taskDirectory) { throw 'This intro take is already saved.' }
New-Item -ItemType Directory -Path $taskDirectory | Out-Null
$taskText = '利用者は、こうを感じる和の画面。事業者は、数字が読みやすい管理画面。ログインして、使ってみましょう。'
$taskUtf8 = [System.Text.UTF8Encoding]::new($false)
$clauses = [regex]::Matches($taskText, '[^。？！!?]+[。？！!?]?')
$parts = @($clauses | ForEach-Object {
    $escaped = [System.Security.SecurityElement]::Escape($_.Value)
    $escaped = $escaped.Replace('ログイン', '<prosody volume="95">ログイン</prosody>')
    '<prosody pitch="medium" volume="85">' + $escaped + '</prosody>'
})
$ssml = '<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="ja-JP">' + ($parts -join '<break time="80ms"/>') + '</speak>'
[System.IO.File]::WriteAllText((Join-Path $taskDirectory 'voice-00.ssml'), $ssml, $taskUtf8)
Add-Type -AssemblyName System.Speech
$speaker = [System.Speech.Synthesis.SpeechSynthesizer]::new()
try {
    $speaker.SelectVoice('Microsoft Sayaka')
    if ($speaker.Voice.Gender.ToString() -ne 'Female' -or $speaker.Voice.Culture.Name -ne 'ja-JP') { throw 'Unexpected voice.' }
    $speaker.Rate = 2
    $speaker.Volume = 90
    $format = [System.Speech.AudioFormat.SpeechAudioFormatInfo]::new(48000,
        [System.Speech.AudioFormat.AudioBitsPerSample]::Sixteen,
        [System.Speech.AudioFormat.AudioChannel]::Mono)
    $speaker.SetOutputToWaveFile((Join-Path $taskDirectory 'voice-00.wav'), $format)
    $speaker.SpeakSsml($ssml)
    $speaker.SetOutputToNull()
    $record = @{voice=$speaker.Voice.Name;rate=2;volume=90;text=$taskText;pitch='medium';sentence_pause_ms=80;
        emphasis='Only the word login, volume 85 to 95';tempo_processing='None';human_listening='Not performed';
        script_sha256=(Get-FileHash -LiteralPath $PSCommandPath).Hash.ToLower();
        executable=(Get-Process -Id $PID).Path;version=$PSVersionTable.PSVersion.ToString()}
    [System.IO.File]::WriteAllText((Join-Path $taskDirectory 'settings.json'), ($record | ConvertTo-Json -Depth 5), $taskUtf8)
} finally { $speaker.Dispose() }
Write-Output $taskDirectory
