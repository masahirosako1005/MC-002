"""Adjust narration gain from original PCM and copy the verified H.264 stream.

No trim, limiter, time fitting or background sound is applied. All preceding
revisions remain unchanged; v6 references their inputs instead of copying stills.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import shutil
import wave
from pathlib import Path

from animate_revisit_video import ROOT, project_path, run_ffmpeg, verify

WORK = ROOT / 'artifacts/video-revisit'
TARGET_LUFS = -18.0
MAX_PEAK_DBFS = -1.5
ENCODER_HEADROOM_DB = .35


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def loudness(path, log):
    result = run_ffmpeg(['-threads', '2', '-i', str(path), '-map', '0:a:0', '-vn',
        '-af', 'ebur128=peak=true', '-filter_threads', '1', '-f', 'null', '-'], log)
    summary = result.stderr.decode('utf-8', 'replace').split('Summary:')[-1]
    patterns = {'integrated_lufs': r'\bI:\s*(-?\d+(?:\.\d+)?)\s+LUFS',
                'true_peak_dbfs': r'\bPeak:\s*(-?\d+(?:\.\d+)?)\s+dBFS',
                'loudness_range_lu': r'\bLRA:\s*(-?\d+(?:\.\d+)?)\s+LU\b'}
    values = {}
    for key, pattern in patterns.items():
        match = re.search(pattern, summary)
        if match is None:
            raise ValueError(f'Could not measure {key}; see {log.name}')
        values[key] = float(match[1])
        if not math.isfinite(values[key]):
            raise ValueError('Non-finite audio measurement')
    return values


def video_digest(path, log):
    # Canonical Annex B compressed packets, not container bytes or a re-encode.
    result = run_ffmpeg(['-threads', '2', '-i', str(path), '-map', '0:v:0', '-an',
        '-c:v', 'copy', '-bsf:v', 'h264_mp4toannexb', '-f', 'hash', '-hash', 'sha256', '-'], log)
    match = re.search(rb'SHA256=([a-f0-9]{64})', result.stdout)
    if match is None:
        raise ValueError('Compressed video stream hash is missing')
    return match[1].decode('ascii')


def pcm_info(path):
    with wave.open(str(path), 'rb') as audio:
        frames, rate = audio.getnframes(), audio.getframerate()
        if (rate, audio.getnchannels(), audio.getsampwidth(), frames) != (48000, 2, 2, 2880000):
            raise ValueError('Expected the original 60-second 48kHz stereo PCM16 narration')
        return {'frames': frames, 'sample_rate': rate, 'channels': 2, 'seconds': frames / rate}


def input_manifest(source, narration, previous):
    references = []
    for scene in previous['scenes']:
        for kind in ('source', 'alternate'):
            if scene[kind]:
                path = ROOT / scene[kind]
                saved_hash = scene['source_sha256' if kind == 'source' else 'alternate_sha256']
                if digest(path) != saved_hash:
                    raise ValueError('A referenced v5 still has changed')
                references.append({'path': scene[kind], 'sha256': saved_hash})
    scene_json = ROOT / previous['source_scene_json']
    if digest(scene_json) != previous['source_scene_json_sha256']:
        raise ValueError('The saved v5 scene description has changed')
    return {'source_video': source.relative_to(ROOT).as_posix(), 'source_video_sha256': digest(source),
        'source_pcm': narration.relative_to(ROOT).as_posix(), 'source_pcm_sha256': digest(narration),
        'scenes_json': scene_json.relative_to(ROOT).as_posix(), 'scenes_json_sha256': digest(scene_json),
        'stills_referenced_not_duplicated': references,
        'source_pcm_format': pcm_info(narration)}


def encode(source, narration, destination, gain, directory):
    # Omit -t, -shortest and all trim filters: consume the complete original PCM.
    run_ffmpeg(['-y', '-threads', '2', '-i', str(source), '-i', str(narration),
        '-map', '0:v:0', '-map', '1:a:0', '-c:v', 'copy', '-af', f'volume={gain:.6f}dB',
        '-filter_threads', '1', '-c:a', 'aac', '-b:a', '160k', '-ar', '48000', '-ac', '2',
        '-threads', '2', '-movflags', '+faststart', str(destination)], directory / 'audio-encode.log')


def validate_loudness(measured):
    if measured['true_peak_dbfs'] > MAX_PEAK_DBFS:
        raise ValueError('Encoded AAC exceeds the true-peak ceiling; no final output was published')
    if abs(measured['integrated_lufs'] - TARGET_LUFS) > .4:
        raise ValueError('Encoded AAC misses the internal loudness target; no final output was published')


def arguments():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=project_path, default=ROOT / 'outputs/kou-revisit-intro-v5.mp4')
    parser.add_argument('--pcm', type=project_path, default=WORK / 'v5/motion-audio/narration-60s.wav')
    parser.add_argument('--directory', type=project_path, default=WORK / 'v6')
    parser.add_argument('--output', type=project_path, default=ROOT / 'outputs/kou-revisit-intro-v6.mp4')
    return parser.parse_args()


def main():
    args = arguments()
    args.directory.mkdir(parents=True, exist_ok=True)
    candidate = args.directory / 'v6-audio.mp4'
    if candidate.exists() or args.output.exists():
        raise FileExistsError('Refusing to replace an existing candidate or output')
    prior_paths = [ROOT / f'outputs/kou-revisit-intro-v{revision}.mp4' for revision in range(1, 6)]
    prior = {path.relative_to(ROOT).as_posix(): digest(path) for path in prior_paths}
    previous = json.loads((WORK / 'v5/motion-verification.json').read_text(encoding='utf-8'))
    manifest = input_manifest(args.source, args.pcm, previous)
    (args.directory / 'input-manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    before = loudness(args.pcm, args.directory / 'source-pcm-loudness.txt')
    gain = round(min(TARGET_LUFS - before['integrated_lufs'],
                     MAX_PEAK_DBFS - before['true_peak_dbfs'] - ENCODER_HEADROOM_DB), 6)
    encode(args.source, args.pcm, candidate, gain, args.directory)
    after = loudness(candidate, args.directory / 'audio-loudness.txt')
    validate_loudness(after)
    source_video_hash = video_digest(args.source, args.directory / 'source-video-hash.log')
    final_video_hash = video_digest(candidate, args.directory / 'final-video-hash.log')
    if source_video_hash != final_video_hash:
        raise ValueError('The compressed video stream changed')
    decoded = verify(candidate, args.directory)
    preserved = {path: digest(ROOT / path) == value for path, value in prior.items()}
    if not all(preserved.values()):
        raise ValueError('A preceding revision changed')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(candidate, args.output)
    report = decoded | {'output': args.output.relative_to(ROOT).as_posix(),
        'script_sha256': digest(Path(__file__)), 'method': 'Original PCM scalar gain; H.264 stream copy',
        'source_pcm_loudness': before, 'final_aac_loudness': after, 'gain_db': gain,
        'target_integrated_lufs': TARGET_LUFS, 'maximum_true_peak_dbfs': MAX_PEAK_DBFS,
        'audio_codec': 'AAC 160 kbps / 48000 Hz / stereo', 'trimmed': False, 'bgm_added': False,
        'silence_handling': 'Complete original PCM consumed; scalar multiplication preserves its silent padding',
        'video_stream_sha256': final_video_hash, 'source_video_stream_sha256': source_video_hash,
        'video_hash_method': 'SHA256 of stream-copied H.264 Annex B packets',
        'preserved_revisions': preserved, 'input_manifest': 'input-manifest.json',
        'visual_review': 'Inherited unchanged v5 compressed video; same 1800 frames verified',
        'audio_listening_review': 'Not performed; loudness/true peak measured and all audio/video decoded'}
    (args.directory / 'verification.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'output': report['output'], 'gain_db': gain, 'loudness': after,
                     'frames': report['frames'], 'decoded_seconds': report['decoded_duration_seconds']}, indent=2))


if __name__ == '__main__':
    main()
