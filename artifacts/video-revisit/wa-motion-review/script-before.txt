"""Animate real, already-composed captures without driving or inventing UI.

The progress line is film time, not application progress. Outlines only direct
attention; they never simulate a click or change a displayed value.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import shutil
import subprocess
import wave
from dataclasses import dataclass
from pathlib import Path

import imageio_ffmpeg
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
WORK = ROOT / 'artifacts/video-revisit'
SIZE, FPS, SAMPLE_RATE = (1920, 1080), 30, 48000
TRANSITION, AUDIO_LEAD, AUDIO_RESERVE = .28, .22, .55
MAX_TEMPO = 1.55
FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
PAPER = (247, 243, 232)
RED = (157, 59, 45)

# x, y, width, height. These surround existing explanatory/screen regions, not
# fictional controls. A scene's motion.highlights can replace them entirely.
DEFAULT_HIGHLIGHTS = {
    'intro': [(.9, 1.5, (84, 394, 650, 226))],
    'overview': [(.8, 1.4, (94, 207, 408, 730)), (3.4, 1.5, (665, 255, 1170, 650))],
    'visitor': [(1.0, 1.4, (155, 190, 475, 755)), (4.2, 1.5, (1205, 190, 475, 755))],
    'provider': [(1.0, 1.6, (578, 255, 1260, 650)), (4.6, 1.4, (80, 650, 460, 170))],
    'program': [(1.0, 1.5, (100, 724, 805, 160)), (4.8, 1.6, (1185, 200, 460, 740))],
    'rank': [(1.0, 1.6, (92, 296, 445, 180)), (4.7, 1.5, (1255, 200, 440, 740))],
    'zone': [(1.0, 1.5, (594, 450, 1030, 75)), (6.1, 1.7, (640, 697, 1140, 236))],
    'closing': [(.6, 1.1, (95, 345, 540, 510)), (1.9, 1.1, (690, 345, 540, 510)), (3.2, 1.1, (1285, 345, 540, 510))],
}


@dataclass
class Scene:
    index: int
    kind: str
    seconds: float
    frames: int
    start_frame: int
    image: Image.Image
    alternate: Image.Image | None
    alternate_at: float
    highlights: list[dict]
    source: Path
    alternate_source: Path | None


def project_path(value):
    path = Path(value).resolve()
    if not path.is_relative_to(ROOT):
        raise ValueError('All inputs and outputs must stay inside the project')
    return path


def checked_number(value, lower, upper, label):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f'{label} must be numeric')
    if not math.isfinite(value) or not lower <= value <= upper:
        raise ValueError(f'Invalid {label}')
    return float(value)


def image(path):
    with Image.open(path) as source:
        if source.size != SIZE:
            raise ValueError(f'{path.name}: expected 1920x1080, got {source.size}')
        return source.convert('RGB')


def highlights_for(data, seconds):
    defaults = [{'start': start, 'duration': duration, 'box': list(box)}
                for start, duration, box in DEFAULT_HIGHLIGHTS.get(data['kind'], [])]
    highlights = data.get('motion', {}).get('highlights', defaults)
    for mark in highlights:
        start = checked_number(mark['start'], 0, seconds, 'highlight start')
        checked_number(mark['duration'], .6, seconds - start, 'highlight duration')
        if len(mark['box']) != 4:
            raise ValueError('Highlight box must be [x,y,width,height]')
        x, y, width, height = mark['box']
        for value in (x, y, width, height):
            checked_number(value, 0, SIZE[0], 'highlight box')
        if not width or not height or x + width > SIZE[0] or y + height > SIZE[1]:
            raise ValueError('Highlight box extends beyond the image')
    return highlights


def load_scenes(scene_file, directory):
    data = json.loads(scene_file.read_text(encoding='utf-8'))
    if not isinstance(data, list) or len(data) != 8:
        raise ValueError('Exactly eight scene descriptions are required')
    scenes, elapsed = [], 0
    for index, item in enumerate(data):
        seconds = checked_number(item['duration'], 1, 60, 'scene duration')
        frames = round(seconds * FPS)
        if abs(frames / FPS - seconds) > 1e-7:
            raise ValueError('Scene duration must contain a whole number of frames')
        source = directory / f'scene-{index:02}.png'
        alternate = directory / f'scene-{index:02}-alt.png'
        alt_at = item.get('motion', {}).get('alt_at', 3.0 if item['kind'] == 'visitor' else seconds / 2)
        checked_number(alt_at, TRANSITION, seconds - TRANSITION, 'alternate switch')
        scenes.append(Scene(index, item['kind'], seconds, frames, elapsed, image(source),
            image(alternate) if alternate.exists() else None, alt_at,
            highlights_for(item, seconds), source, alternate if alternate.exists() else None))
        elapsed += frames
    if elapsed != 1800:
        raise ValueError(f'Expected 60 seconds / 1800 frames, got {elapsed} frames')
    return scenes


def smooth(value):
    value = max(0.0, min(1.0, value))
    return 1 - (1 - value) ** 3


def still_at(scene, local):
    if scene.alternate is None or local < scene.alternate_at:
        return scene.image
    phase = (local - scene.alternate_at) / TRANSITION
    if phase >= 1:
        return scene.alternate
    return Image.blend(scene.image, scene.alternate, smooth(phase))


def outline(draw, mark, local):
    elapsed = local - mark['start']
    duration = mark['duration']
    if not 0 <= elapsed <= duration:
        return
    alpha = min(smooth(elapsed / .25), smooth((duration - elapsed) / .35))
    x, y, width, height = mark['box']
    # Translucent, 3px framing preserves all original text and image pixels.
    draw.rounded_rectangle((x, y, x + width, y + height), radius=12,
                           outline=(*RED, round(185 * alpha)), width=3)


def render_frame(scenes, index, local_frame):
    scene = scenes[index]
    local = local_frame / FPS
    current = still_at(scene, local)
    if index > 0 and local < TRANSITION:
        previous = still_at(scenes[index - 1], scenes[index - 1].seconds)
        frame = Image.blend(previous, current, smooth(local / TRANSITION))
    else:
        frame = current.copy()
    draw = ImageDraw.Draw(frame, 'RGBA')
    for mark in scene.highlights:
        outline(draw, mark, local)
    # A linear, outside-the-UI playback indicator; it never represents a task.
    progress = (scene.start_frame + local_frame + 1) / 1800
    draw.rectangle((72, 1053, 1848, 1056), fill=(214, 199, 173, 220))
    draw.rectangle((72, 1053, 72 + 1776 * progress, 1056), fill=(*RED, 230))
    return frame


def run_ffmpeg(arguments, log):
    result = subprocess.run([FFMPEG, '-hide_banner', '-nostdin', *arguments], capture_output=True, check=False)
    log.write_bytes(result.stderr)
    if result.returncode:
        raise RuntimeError(f'FFmpeg failed; see {log.relative_to(ROOT)}')
    return result


def audio_info(path):
    with wave.open(str(path), 'rb') as stream:
        return {'seconds': stream.getnframes() / stream.getframerate(),
                    'sample_rate': stream.getframerate(), 'channels': stream.getnchannels(), 'frames': stream.getnframes()}


def voice_plan(scenes, directory):
    result = []
    for scene in scenes:
        path = directory / f'voice-{scene.index:02}.wav'
        info = audio_info(path)
        tempo = max(1.0, info['seconds'] / (scene.seconds - AUDIO_RESERVE))
        if tempo > MAX_TEMPO:
            raise ValueError(f'Scene {scene.index}: voice needs {tempo:.3f}x; shorten narration, never cut it')
        result.append({'source': path, 'seconds': info['seconds'], 'tempo': tempo})
    return result


def prepare_audio(scenes, voices, directory):
    directory.mkdir(exist_ok=True)
    destination = directory / 'narration-60s.wav'
    reports = []
    with wave.open(str(destination), 'wb') as combined:
        combined.setparams((2, 2, SAMPLE_RATE, 0, 'NONE', 'not compressed'))
        for scene, voice in zip(scenes, voices, strict=True):
            fitted = directory / f'voice-{scene.index:02}-fitted.wav'
            run_ffmpeg(['-y', '-i', str(voice['source']), '-af', f"atempo={voice['tempo']:.10f}",
                '-c:a', 'pcm_s16le', '-ar', str(SAMPLE_RATE), '-ac', '2', '-threads', '2',
                '-filter_threads', '1', str(fitted)], directory / f'voice-{scene.index:02}.log')
            with wave.open(str(fitted), 'rb') as stream:
                frames = stream.getnframes()
                body = stream.readframes(frames)
            lead = round(AUDIO_LEAD * SAMPLE_RATE)
            tail = round(scene.seconds * SAMPLE_RATE) - lead - frames
            if tail < round(.12 * SAMPLE_RATE):
                raise ValueError(f'Scene {scene.index}: narration lacks safe trailing silence; no audio was trimmed')
            combined.writeframes(b'\0' * (lead * 4))
            combined.writeframes(body)
            combined.writeframes(b'\0' * (tail * 4))
            reports.append({'scene': scene.index, 'original_seconds': voice['seconds'], 'tempo': voice['tempo'],
                'fitted_seconds': frames / SAMPLE_RATE, 'lead_seconds': AUDIO_LEAD, 'trailing_seconds': tail / SAMPLE_RATE,
                'original_sha256': hashlib.sha256(voice['source'].read_bytes()).hexdigest(), 'trimmed': False})
    if audio_info(destination)['frames'] != 60 * SAMPLE_RATE:
        raise ValueError('Combined narration is not exactly 60 seconds')
    return destination, reports


def contact_sheet(scenes, destination):
    sheet = Image.new('RGB', (1920, 1080), PAPER)
    samples = []
    for scene in scenes:
        first = min(scene.highlights[0]['start'] + .5, scene.seconds - .5) if scene.highlights else 1.0
        second = max(scene.alternate_at + .6, scene.seconds - 1.0)
        for slot, local in enumerate((first, second)):
            local_frame = min(scene.frames - 1, round(local * FPS))
            thumb = render_frame(scenes, scene.index, local_frame).resize((480, 270), Image.Resampling.LANCZOS)
            draw = ImageDraw.Draw(thumb)
            draw.rectangle((0, 0, 150, 18), fill=PAPER)
            draw.text((6, 3), f'{scene.index + 1:02}  +{local_frame / FPS:.2f}s', fill=RED)
            position = scene.index * 2 + slot
            sheet.paste(thumb, ((position % 4) * 480, (position // 4) * 270))
            samples.append({'scene': scene.index, 'local_frame': local_frame})
    sheet.save(destination, quality=94)
    return samples


def encode(scenes, narration, destination, log):
    command = [FFMPEG, '-hide_banner', '-nostdin', '-y', '-f', 'rawvideo', '-pixel_format', 'rgb24',
        '-video_size', '1920x1080', '-framerate', str(FPS), '-i', 'pipe:0', '-i', str(narration),
        '-map', '0:v:0', '-map', '1:a:0', '-c:v', 'libx264', '-preset', 'fast', '-crf', '19',
        '-pix_fmt', 'yuv420p', '-threads', '2', '-filter_threads', '1', '-c:a', 'aac', '-b:a', '160k',
        '-ar', str(SAMPLE_RATE), '-ac', '2', '-t', '60', '-movflags', '+faststart', str(destination)]
    with log.open('wb') as errors:
        process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=errors)
        try:
            for scene in scenes:
                for frame in range(scene.frames):
                    process.stdin.write(render_frame(scenes, scene.index, frame).tobytes())
                print(f'Animated scene {scene.index + 1}/8', flush=True)
            process.stdin.close()
            code = process.wait()
        except BaseException:
            process.terminate()
            process.wait()
            raise
    if code:
        raise RuntimeError(f'Encoding failed; see {log.relative_to(ROOT)}')


def verify(destination, directory):
    result = run_ffmpeg(['-v', 'info', '-xerror', '-err_detect', 'explode', '-threads', '2',
        '-i', str(destination), '-progress', 'pipe:1', '-f', 'null', '-'], directory / 'motion-decode.log')
    matches = re.findall(rb'^frame=(\d+)', result.stdout, re.MULTILINE)
    frames = int(matches[-1]) if matches else 0
    information = result.stderr.decode('utf-8', 'replace')
    times = re.findall(rb'^out_time_us=(\d+)', result.stdout, re.MULTILINE)
    decoded_seconds = int(times[-1]) / 1_000_000 if times else 0
    if frames != 1800 or not all(value in information for value in ('1920x1080', 'Audio: aac', '30 fps', 'h264')):
        raise ValueError('Output failed dimensions, audio, frame count, or frame rate checks')
    if abs(decoded_seconds - 60) > .08:
        raise ValueError('Decoded audio/video duration differs from 60 seconds')
    return {'frames': frames, 'duration_seconds': 60, 'fps': FPS, 'size': list(SIZE), 'decode': 'passed',
                'decoded_duration_seconds': decoded_seconds,
                'sha256': hashlib.sha256(destination.read_bytes()).hexdigest(), 'bytes': destination.stat().st_size}


def decoded_contact_sheet(destination, directory, samples, scenes):
    indices = [scenes[item['scene']].start_frame + item['local_frame'] for item in samples]
    selection = '+'.join(f'eq(n\\,{number})' for number in indices)
    target = directory / 'motion-decoded-contact-sheet.jpg'
    run_ffmpeg(['-y', '-threads', '2', '-i', str(destination),
        '-vf', f'select={selection},scale=480:270:flags=lanczos,tile=4x4',
        '-frames:v', '1', '-update', '1', '-threads', '2', '-filter_threads', '1', '-q:v', '2', str(target)],
        directory / 'motion-contact-decode.log')
    return target.relative_to(ROOT).as_posix()


def arguments():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--scene-dir', type=project_path, default=WORK / 'v2')
    parser.add_argument('--scene-json', type=project_path, default=Path(__file__).with_name('revisit-video-scenes.json'))
    parser.add_argument('--audio-dir', type=project_path, default=WORK / 'audio')
    parser.add_argument('--output', type=project_path, default=ROOT / 'outputs/kou-revisit-intro-v2.mp4')
    parser.add_argument('--preview-only', action='store_true')
    parser.add_argument('--overwrite', action='store_true')
    return parser.parse_args()


def main():
    args = arguments()
    scenes = load_scenes(args.scene_json, args.scene_dir)
    voices = voice_plan(scenes, args.audio_dir)
    samples = contact_sheet(scenes, args.scene_dir / 'motion-contact-sheet.jpg')
    report = {'source_scene_json': args.scene_json.relative_to(ROOT).as_posix(),
        'source_scene_json_sha256': hashlib.sha256(args.scene_json.read_bytes()).hexdigest(),
        'script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'method': 'Real captured UI; crossfades and short attention outlines only; no simulated clicks or UI state changes',
        'transition_seconds': TRANSITION, 'playback_indicator': 'Elapsed film time only', 'max_voice_tempo': MAX_TEMPO,
        'contact_sheet_samples': samples, 'visual_review': 'pending', 'audio_listening_review': 'pending',
        'scenes': [{'index': scene.index, 'kind': scene.kind, 'seconds': scene.seconds, 'frames': scene.frames,
            'source': scene.source.relative_to(ROOT).as_posix(), 'source_sha256': hashlib.sha256(scene.source.read_bytes()).hexdigest(),
            'alternate': scene.alternate_source.relative_to(ROOT).as_posix() if scene.alternate_source else None,
            'alternate_sha256': hashlib.sha256(scene.alternate_source.read_bytes()).hexdigest() if scene.alternate_source else None,
            'alternate_at': scene.alternate_at if scene.alternate else None, 'highlights': scene.highlights} for scene in scenes]}
    if args.preview_only:
        report['status'] = 'preview_only_not_encoded'
    else:
        destination = args.scene_dir / f'{args.scene_dir.name}-motion.mp4'
        if args.output.suffix.lower() != '.mp4':
            raise ValueError('Output must be an MP4 file')
        if not args.overwrite and (destination.exists() or args.output.exists()):
            raise FileExistsError('Output already exists; choose a new path or explicitly use --overwrite')
        narration, report['audio'] = prepare_audio(scenes, voices, args.scene_dir / 'motion-audio')
        encode(scenes, narration, destination, args.scene_dir / 'motion-encode.log')
        report.update(verify(destination, args.scene_dir))
        report['decoded_contact_sheet'] = decoded_contact_sheet(destination, args.scene_dir, samples, scenes)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(destination, args.output)
        report.update(status='encoded_and_decoded', output=args.output.relative_to(ROOT).as_posix())
    name = 'motion-preview.json' if args.preview_only else 'motion-verification.json'
    (args.scene_dir / name).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'status': report['status'], 'report': (args.scene_dir / name).relative_to(ROOT).as_posix()}, ensure_ascii=False))


if __name__ == '__main__':
    main()
