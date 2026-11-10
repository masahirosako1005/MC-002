"""Check duration boundaries with mocked video and one tiny PCM conversion."""
import importlib
import json
import sys
import wave
from pathlib import Path
from types import SimpleNamespace

import pytest


@pytest.fixture
def modules(monkeypatch):
    pytest.importorskip('PIL')
    pytest.importorskip('imageio_ffmpeg')
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[2] / 'scripts'))
    motion = importlib.import_module('animate_revisit_video')
    finish = importlib.import_module('finish_revisit_audio')
    monkeypatch.setattr(motion, 'image', lambda _path: motion.Image.new('RGB', (2, 2)))
    return motion, finish


def scene_file(tmp_path, seconds):
    total_frames = round(seconds * 30)
    base, remainder = divmod(total_frames, 8)
    data = [{'kind': 'test', 'duration': (base + (index < remainder)) / 30,
             'motion': {'highlights': []}} for index in range(8)]
    path = tmp_path / 'scenes.json'
    path.write_text(json.dumps(data), encoding='utf-8')
    return path


def write_pcm(path, seconds):
    with wave.open(str(path), 'wb') as stream:
        stream.setparams((2, 2, 48000, 0, 'NONE', 'not compressed'))
        # Write one second at a time, including any partial final second.
        remaining = round(seconds * 48000)
        while remaining:
            chunk = min(remaining, 48000)
            stream.writeframes(b'\0' * (chunk * 4))
            remaining -= chunk


@pytest.mark.parametrize('seconds', [15, 60, 90, 120])
def test_variable_duration_accepts_full_range(modules, tmp_path, seconds):
    motion, _ = modules
    scenes = motion.load_scenes(scene_file(tmp_path, seconds), tmp_path, expected_seconds=None)
    assert sum(item.frames for item in scenes) == seconds * 30


def test_legacy_default_requires_sixty_seconds(modules, tmp_path):
    motion, _ = modules
    assert sum(item.frames for item in motion.load_scenes(scene_file(tmp_path, 60), tmp_path)) == 1800
    with pytest.raises(ValueError, match='Expected 60 seconds'):
        motion.load_scenes(scene_file(tmp_path, 90), tmp_path)


@pytest.mark.parametrize('seconds', [14 + 29 / 30, 120 + 1 / 30])
def test_variable_duration_rejects_outside_range(modules, tmp_path, seconds):
    motion, _ = modules
    with pytest.raises(ValueError, match='total duration'):
        motion.load_scenes(scene_file(tmp_path, seconds), tmp_path, expected_seconds=None)


@pytest.mark.parametrize('seconds', [True, float('nan'), float('inf'), 60.01])
def test_expected_duration_rejects_invalid_values(modules, seconds):
    motion, _ = modules
    with pytest.raises((ValueError, TypeError)):
        motion.expected_frame_count(seconds)


def test_progress_reaches_exactly_one_for_variable_duration(modules, monkeypatch, tmp_path):
    motion, _ = modules
    scenes = motion.load_scenes(scene_file(tmp_path, 90), tmp_path, expected_seconds=None)
    progress = []
    monkeypatch.setattr(motion, 'playback_line', lambda _draw, value, _style: progress.append(value))
    motion.render_frame(scenes, 0, 0)
    motion.render_frame(scenes, 7, scenes[7].frames - 1)
    assert progress == [1 / 2700, 1]


def test_encode_uses_scene_total_without_real_encoder(modules, monkeypatch, tmp_path):
    motion, _ = modules
    scenes = motion.load_scenes(scene_file(tmp_path, 90), tmp_path, expected_seconds=None)
    commands, writes = [], []

    def fake_process(command, **_kwargs):
        commands.append(command)
        return SimpleNamespace(stdin=SimpleNamespace(write=lambda data: writes.append(len(data)),
                                                     close=lambda: None), wait=lambda: 0)

    monkeypatch.setattr(motion.subprocess, 'Popen', fake_process)
    motion.encode(scenes, tmp_path / 'voice.wav', tmp_path / 'video.mp4', tmp_path / 'encode.log',
                  frame_renderer=lambda *_args: motion.Image.new('RGB', (1, 1)))
    assert commands[0][commands[0].index('-t') + 1] == '90'
    assert len(writes) == 2700


@pytest.mark.parametrize('seconds', [15, 60])
def test_audio_total_and_legacy_filename(modules, monkeypatch, tmp_path, seconds):
    motion, _ = modules
    scenes = motion.load_scenes(scene_file(tmp_path, seconds), tmp_path, expected_seconds=None)
    source = tmp_path / 'original.wav'
    write_pcm(source, .1)
    voices = [{'source': source, 'seconds': .1, 'tempo': 1.0 if index % 2 == 0 else 1.1}
              for index, _ in enumerate(scenes)]
    commands = []

    def fitted_audio(arguments, _log):
        commands.append(arguments)
        write_pcm(Path(arguments[-1]), .1)

    monkeypatch.setattr(motion, 'run_ffmpeg', fitted_audio)
    destination, reports = motion.prepare_audio(scenes, voices, tmp_path / 'audio')
    assert destination.name == f'narration-{seconds}s.wav'
    assert motion.audio_info(destination)['frames'] == seconds * 48000
    assert all(report['trimmed'] is False for report in reports)
    for command, voice in zip(commands, voices, strict=True):
        assert ('-af' in command) == (voice['tempo'] != 1.0)


def test_unadjusted_pcm_preserves_trailing_samples(modules, tmp_path):
    motion, _ = modules
    source = tmp_path / 'original.wav'
    body = b'\x01\x00\xff\xff' * 12288 + b'\0' * (1024 * 4)
    with wave.open(str(source), 'wb') as stream:
        stream.setparams((2, 2, 48000, 0, 'NONE', 'not compressed'))
        stream.writeframes(body)
    scene = SimpleNamespace(index=0, seconds=15, frames=450)
    voice = {'source': source, 'seconds': len(body) / 4 / 48000, 'tempo': 1.0}
    # One small PCM conversion, no video encoder or application process.
    destination, reports = motion.prepare_audio([scene], [voice], tmp_path / 'audio')
    with wave.open(str(destination.parent / 'voice-00-fitted.wav'), 'rb') as fitted:
        assert fitted.getnframes() == len(body) // 4
        assert fitted.readframes(fitted.getnframes()) == body
    assert reports[0]['fitted_seconds'] == voice['seconds']


@pytest.mark.parametrize('seconds', [60, 90])
def test_verification_uses_expected_duration(modules, monkeypatch, tmp_path, seconds):
    motion, _ = modules
    output = tmp_path / 'video.mp4'
    output.write_bytes(b'verification fixture')
    result = SimpleNamespace(stdout=f'frame={seconds * 30}\nout_time_us={seconds * 1000000}\n'.encode(),
                             stderr=b'1920x1080 Audio: aac 30 fps h264')
    monkeypatch.setattr(motion, 'run_ffmpeg', lambda *_args: result)
    report = motion.verify(output, tmp_path, expected_seconds=seconds)
    assert report['duration_seconds'] == seconds
    assert report['frames'] == seconds * 30
    if seconds == 90:
        with pytest.raises(ValueError, match='frame count'):
            motion.verify(output, tmp_path)


def test_verification_rejects_wrong_audio_duration(modules, monkeypatch, tmp_path):
    motion, _ = modules
    result = SimpleNamespace(stdout=b'frame=2700\nout_time_us=91000000\n',
                             stderr=b'1920x1080 Audio: aac 30 fps h264')
    monkeypatch.setattr(motion, 'run_ffmpeg', lambda *_args: result)
    with pytest.raises(ValueError, match='differs from 90 seconds'):
        motion.verify(tmp_path / 'unused.mp4', tmp_path, expected_seconds=90)


def test_pcm_checks_variable_duration_and_keeps_legacy_default(modules, tmp_path):
    _, finish = modules
    pcm = tmp_path / 'voice.wav'
    write_pcm(pcm, 15)
    assert finish.pcm_info(pcm, expected_seconds=15)['seconds'] == 15
    with pytest.raises(ValueError, match='60-second'):
        finish.pcm_info(pcm)
    write_pcm(pcm, 60)
    assert finish.pcm_info(pcm)['seconds'] == 60


@pytest.mark.parametrize('seconds', [None, 90])
def test_finish_cli_duration_default_and_override(modules, monkeypatch, seconds):
    _, finish = modules
    monkeypatch.setattr(sys, 'argv', ['finish'] + (['--duration', str(seconds)] if seconds else []))
    assert finish.arguments().duration == (seconds or 60)
