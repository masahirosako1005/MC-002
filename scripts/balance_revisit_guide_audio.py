"""Gently control narration peaks without changing pitch, speed or duration."""
from __future__ import annotations

import argparse
import hashlib
import json
import wave

from animate_revisit_video import ROOT, project_path, run_ffmpeg
from finish_revisit_audio import loudness, pcm_info

FILTER = 'acompressor=threshold=0.125:ratio=2:attack=8:release=120:makeup=1:knee=2.828'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory', type=project_path, default=ROOT / 'artifacts/video-revisit/v9')
    parser.add_argument('--verify-existing', action='store_true')
    parser.add_argument('--duration', type=float, default=60)
    args = parser.parse_args()
    source = args.directory / f'pcm/narration-{args.duration:g}s.wav'
    target = args.directory / 'pcm/narration-balanced.wav'
    pcm_info(source, expected_seconds=args.duration)
    if target.exists() and not args.verify_existing:
        raise FileExistsError('Choose a new revision or verify the existing audio')
    result = run_ffmpeg(['-i', str(source), '-af', FILTER, '-c:a', 'pcm_s16le', '-ar', '48000',
        '-ac', '2', '-threads', '2', '-filter_threads', '1', '-f', 's16le', 'pipe:1'],
        args.directory / 'audio-balance-verify.log')
    if target.exists():
        pcm_info(target, expected_seconds=args.duration)
        with wave.open(str(target), 'rb') as stream:
            if stream.readframes(stream.getnframes()) != result.stdout:
                raise ValueError('Existing audio differs from the documented processing')
    else:
        with wave.open(str(target), 'wb') as stream:
            stream.setparams((2, 2, 48000, 0, 'NONE', 'not compressed'))
            stream.writeframes(result.stdout)
    pcm_info(target, expected_seconds=args.duration)
    report = {'source': source.relative_to(ROOT).as_posix(),
        'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
        'output': target.relative_to(ROOT).as_posix(),
        'output_sha256': hashlib.sha256(target.read_bytes()).hexdigest(),
        'filter': FILTER, 'speed': 1.0, 'trimmed': False, 'seconds': args.duration,
        'pitch_changed': False, 'bgm_added': False, 'reproduced_pcm_equal': True,
        'before': loudness(source, args.directory / 'balance-before.log'),
        'after': loudness(target, args.directory / 'balance-after.log'),
        'next_step': 'Scalar gain and AAC encoding; final measurements in final/verification.json'}
    (args.directory / 'audio-balance.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report['after']))


if __name__ == '__main__':
    main()
