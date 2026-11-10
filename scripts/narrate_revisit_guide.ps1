param(
    [ValidatePattern('^take-[0-9]{2}$')]
    [string]$Take = 'take-01'
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$taskRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$taskScenePath = Join-Path $PSScriptRoot 'revisit-video-guide-scenes.json'
$taskAudio = Join-Path $taskRoot 'artifacts\video-revisit\v9\audio'
$taskTake = Join-Path $taskAudio $Take
$taskVtt = Join-Path $taskRoot 'outputs\kou-revisit-intro-v9-ja.vtt'
if (Test-Path -LiteralPath $taskTake) {
    throw 'This take already exists. Select a new take number; earlier audio is retained.'
}
New-Item -ItemType Directory -Path $taskTake -Force | Out-Null
$taskUtf8 = [System.Text.UTF8Encoding]::new($false)
Add-Type -AssemblyName System.Speech

# SSML 1.0 is accepted by System.Speech. Engine response is measured separately;
# successful parsing alone does not prove that a voice honored a prosody setting.
# https://learn.microsoft.com/en-us/dotnet/api/system.speech.synthesis.speechsynthesizer.speakssml
# https://learn.microsoft.com/en-us/dotnet/api/system.speech.synthesis.ttsengine.prosody
if (-not ('RevisitGuideWaveStats' -as [type])) {
    Add-Type -TypeDefinition @'
using System;
using System.IO;
using System.Security.Cryptography;
public sealed class RevisitGuideWaveStats {
    public int SampleRate, Channels, Bits, PeakSample, ClippedSamples;
    public long Frames;
    public double Seconds, PeakDbfs, RmsDbfs;
    public string PcmSha256;
    public static RevisitGuideWaveStats Read(string path) {
        var result = new RevisitGuideWaveStats();
        byte[] samples = null;
        using (var reader = new BinaryReader(File.OpenRead(path))) {
            if (new string(reader.ReadChars(4)) != "RIFF") throw new InvalidDataException("Expected RIFF");
            reader.ReadUInt32();
            if (new string(reader.ReadChars(4)) != "WAVE") throw new InvalidDataException("Expected WAVE");
            while (reader.BaseStream.Position + 8 <= reader.BaseStream.Length) {
                string tag = new string(reader.ReadChars(4));
                uint length = reader.ReadUInt32();
                long next = reader.BaseStream.Position + length + (length & 1);
                if (tag == "fmt ") {
                    if (reader.ReadUInt16() != 1) throw new InvalidDataException("Expected PCM");
                    result.Channels = reader.ReadUInt16();
                    result.SampleRate = reader.ReadInt32();
                    reader.ReadUInt32(); reader.ReadUInt16();
                    result.Bits = reader.ReadUInt16();
                } else if (tag == "data") {
                    samples = reader.ReadBytes(checked((int)length));
                }
                reader.BaseStream.Position = next;
            }
        }
        if (samples == null || samples.Length == 0 || result.Bits != 16 || result.Channels < 1)
            throw new InvalidDataException("Expected nonempty 16-bit PCM");
        double squares = 0;
        for (int i = 0; i + 1 < samples.Length; i += 2) {
            int sample = BitConverter.ToInt16(samples, i);
            result.PeakSample = Math.Max(result.PeakSample, Math.Abs(sample));
            if (sample == short.MinValue || sample == short.MaxValue) result.ClippedSamples++;
            squares += (double)sample * sample;
        }
        result.Frames = samples.Length / (2 * result.Channels);
        result.Seconds = (double)result.Frames / result.SampleRate;
        result.PeakDbfs = result.PeakSample == 0 ? -120 : 20 * Math.Log10(result.PeakSample / 32768.0);
        result.RmsDbfs = squares == 0 ? -120 : 20 * Math.Log10(Math.Sqrt(squares / (samples.Length / 2)) / 32768.0);
        using (var hash = SHA256.Create()) {
            result.PcmSha256 = BitConverter.ToString(hash.ComputeHash(samples)).Replace("-", "").ToLowerInvariant();
        }
        return result;
    }
}
'@
}

function Get-SceneSsml {
    param([string]$Text, [string]$Focus)
    if (-not $Text.Contains($Focus)) { throw 'The emphasis word is missing from the script.' }
    $clauses = [regex]::Matches($Text, '[^。？！!?]+[。？！!?]?')
    $body = [System.Text.StringBuilder]::new()
    for ($part = 0; $part -lt $clauses.Count; $part++) {
        $escaped = [System.Security.SecurityElement]::Escape($clauses[$part].Value)
        $focusEscaped = [System.Security.SecurityElement]::Escape($Focus)
        $escaped = $escaped.Replace($focusEscaped, ('<emphasis level="strong">{0}</emphasis>' -f $focusEscaped))
        $pitch = if ($part -eq 0) { 'high' } else { 'medium' }
        [void]$body.Append(('<prosody pitch="{0}" rate="medium">{1}</prosody>' -f $pitch, $escaped))
        if ($part -lt $clauses.Count - 1) { [void]$body.Append('<break time="100ms"/>') }
    }
    return '<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="ja-JP">' + $body + '</speak>'
}

function Write-Voice {
    param($Speaker, [string]$Ssml, [string]$Stem)
    $xml = [xml]$Ssml
    $wavPath = Join-Path $taskTake ($Stem + '.wav')
    [System.IO.File]::WriteAllText((Join-Path $taskTake ($Stem + '.ssml')), $Ssml, $taskUtf8)
    $format = [System.Speech.AudioFormat.SpeechAudioFormatInfo]::new(
        48000, [System.Speech.AudioFormat.AudioBitsPerSample]::Sixteen,
        [System.Speech.AudioFormat.AudioChannel]::Mono)
    $Speaker.SetOutputToWaveFile($wavPath, $format)
    try { $Speaker.SpeakSsml($Ssml) } finally { $Speaker.SetOutputToNull() }
    return [ordered]@{
        file = $wavPath.Substring($taskRoot.Length + 1).Replace('\', '/')
        ssml = $Ssml
        spoken_text = $xml.DocumentElement.InnerText
        sha256 = (Get-FileHash -LiteralPath $wavPath -Algorithm SHA256).Hash.ToLowerInvariant()
        measurements = [RevisitGuideWaveStats]::Read($wavPath)
    }
}

function Format-VttTime {
    param([double]$Seconds)
    $ms = [int][Math]::Round($Seconds * 1000)
    return '{0:00}:{1:00}:{2:00}.{3:000}' -f [int][Math]::Floor($ms / 3600000),
        [int][Math]::Floor(($ms % 3600000) / 60000), [int][Math]::Floor(($ms % 60000) / 1000), ($ms % 1000)
}

$scenes = @(Get-Content -LiteralPath $taskScenePath -Raw -Encoding utf8 | ConvertFrom-Json)
if ($scenes.Count -ne 8 -or ($scenes | Measure-Object duration -Sum).Sum -ne 60) {
    throw 'Eight scenes totaling 60 seconds are required.'
}
Copy-Item -LiteralPath $taskScenePath -Destination (Join-Path $taskTake 'scenes.json')
$focusWords = @('一度', '役割', '共有', '出番', '目的', '五十点', '予算', '仕組み')
$speaker = [System.Speech.Synthesis.SpeechSynthesizer]::new()
$records = @()
$probes = @()
try {
    $speaker.SelectVoice('Microsoft Ichiro')
    $speaker.Rate = 0
    $speaker.Volume = 90
    $selected = $speaker.Voice
    if ($selected.Name -ne 'Microsoft Ichiro' -or $selected.Gender.ToString() -ne 'Male' -or $selected.Culture.Name -ne 'ja-JP') {
        throw 'The requested Japanese male voice was not selected.'
    }
    for ($i = 0; $i -lt $scenes.Count; $i++) {
        $ssml = Get-SceneSsml -Text $scenes[$i].voice -Focus $focusWords[$i]
        $record = Write-Voice -Speaker $speaker -Ssml $ssml -Stem ('voice-{0:D2}' -f $i)
        if ($record.spoken_text -ne $scenes[$i].voice) { throw 'Spoken text differs from the script.' }
        $record['scene'] = $i
        $record['slot_seconds'] = $scenes[$i].duration
        $record['lead_seconds'] = 0.22
        $record['trailing_seconds'] = $scenes[$i].duration - 0.22 - $record.measurements.Seconds
        $record['fits_without_acceleration'] = $record.measurements.Seconds -le ($scenes[$i].duration - 0.55)
        $records += $record
    }
    $probeText = '次の訪問を後押しします。'
    $base = '<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="ja-JP">{0}</speak>'
    $probeBodies = [ordered]@{
        neutral = $probeText
        repeat = $probeText
        pitch = '<prosody pitch="high">' + $probeText + '</prosody>'
        emphasis = '<emphasis level="strong">' + $probeText + '</emphasis>'
        pause = '次の訪問を<break time="120ms"/>後押しします。'
    }
    foreach ($name in $probeBodies.Keys) {
        $probes += Write-Voice -Speaker $speaker -Ssml ($base -f $probeBodies[$name]) -Stem ('probe-' + $name)
    }
} finally { $speaker.Dispose() }

$probeMeasure = @($probes | ForEach-Object { $_.measurements })
$report = [ordered]@{
    take = $Take
    voice = @{ name = $selected.Name; gender = $selected.Gender.ToString(); culture = $selected.Culture.Name }
    runtime = @{ executable = (Get-Process -Id $PID).Path; version = $PSVersionTable.PSVersion.ToString(); is_64_bit = [Environment]::Is64BitProcess }
    rate = 0
    volume = 90
    pitch_requested = @('high', 'medium')
    emphasis_requested = 'strong on short focus words only'
    explicit_sentence_pause_ms = 100
    speed_processing = 'none; no atempo, trimming, or time compression'
    text_characters = ($scenes | ForEach-Object { $_.voice.Length } | Measure-Object -Sum).Sum
    script_sha256 = (Get-FileHash -LiteralPath $PSCommandPath -Algorithm SHA256).Hash.ToLowerInvariant()
    scenes_sha256 = (Get-FileHash -LiteralPath $taskScenePath -Algorithm SHA256).Hash.ToLowerInvariant()
    sources = @('https://learn.microsoft.com/en-us/dotnet/api/system.speech.synthesis.speechsynthesizer.speakssml',
                'https://learn.microsoft.com/en-us/dotnet/api/system.speech.synthesis.ttsengine.prosody')
    scenes = $records
    probes = $probes
    engine_checks = @{
        repeated_plain_pcm_identical = $probeMeasure[0].PcmSha256 -eq $probeMeasure[1].PcmSha256
        pitch_pcm_changed = $probeMeasure[0].PcmSha256 -ne $probeMeasure[2].PcmSha256
        emphasis_pcm_changed = $probeMeasure[0].PcmSha256 -ne $probeMeasure[3].PcmSha256
        pause_duration_delta_seconds = $probeMeasure[4].Seconds - $probeMeasure[0].Seconds
        meaning = 'PCM differences show engine output changed; perceptual clarity and naturalness still require listening.'
    }
    listening_review = 'not performed'
}
$accepted = @($records | Where-Object { -not $_.fits_without_acceleration -or $_.measurements.ClippedSamples -gt 0 }).Count -eq 0
$report['status'] = if ($accepted) { 'fits_without_acceleration' } else { 'needs_shorter_script_or_level_revision' }
$vtt = [System.Text.StringBuilder]::new("WEBVTT`n`n")
$elapsed = 0.0
for ($i = 0; $i -lt $scenes.Count; $i++) {
    [void]$vtt.AppendLine(($i + 1).ToString())
    [void]$vtt.AppendLine(('{0} --> {1}' -f (Format-VttTime ($elapsed + 0.22)),
        (Format-VttTime ([Math]::Min($elapsed + $scenes[$i].duration, $elapsed + 0.22 + $records[$i].measurements.Seconds)))))
    [void]$vtt.AppendLine($scenes[$i].voice)
    [void]$vtt.AppendLine()
    $elapsed += $scenes[$i].duration
}
[System.IO.File]::WriteAllText((Join-Path $taskTake 'narration.vtt'), $vtt.ToString(), $taskUtf8)
[System.IO.File]::WriteAllText((Join-Path $taskTake 'measurements.json'), ($report | ConvertTo-Json -Depth 10), $taskUtf8)
if ($accepted) {
    $destinations = @(0..7 | ForEach-Object { Join-Path $taskAudio ('voice-{0:D2}.wav' -f $_) }) + @($taskVtt)
    if (@($destinations | Where-Object { Test-Path -LiteralPath $_ }).Count -gt 0) {
        throw 'Final audio or VTT already exists. The take is preserved; no final file was overwritten.'
    }
    for ($i = 0; $i -lt 8; $i++) {
        Copy-Item -LiteralPath (Join-Path $taskTake ('voice-{0:D2}.wav' -f $i)) -Destination $destinations[$i]
    }
    Copy-Item -LiteralPath (Join-Path $taskTake 'narration.vtt') -Destination $taskVtt
}
$records | ForEach-Object {
    [PSCustomObject]@{ scene = $_.scene; seconds = [Math]::Round($_.measurements.Seconds, 3); slot = $_.slot_seconds;
        peak_dbfs = [Math]::Round($_.measurements.PeakDbfs, 2); clipped = $_.measurements.ClippedSamples; fits = $_.fits_without_acceleration }
} | ConvertTo-Json
Write-Output $report.status
