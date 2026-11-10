"""Render the preparation-to-return story from recorded application frames.

Editorial text is separate from the captured UI. Recordings play at their
captured timing and hold their final frame; no application state is invented.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from functools import lru_cache

import animate_revisit_video as motion
import render_revisit_guide as guide
import render_revisit_video as art
from PIL import Image, ImageDraw, ImageOps
from revisit_operation_clips import OperationClips, fitted_frame

ROOT = art.ROOT
WORK = art.WORK / 'v13'
SCRIPT = ROOT / 'scripts/revisit-video-female-v13-scenes.json'
GUIDE = ROOT / 'assets/revisit-guide/guide-female-v1.png'
NUMERALS = ('一', '二', '三', '四', '五', '六', '七', '八', '九', '十', '十一', '十二')
PHONE = (150, 205, 440, 740)
WIDE = (430, 255, 1400, 690)
STAGE = (100, 105, 1720, 850)
ZOOM_BOX = (720, 275, 1060, 620)
ZOOM_REGIONS = {
    'phone-photo': [(0, (25, 380, 405, 575), 'タグ候補を確認')],
    'phone-photo-publish': [(0, (20, 90, 410, 340), '公開して保存を確認')],
    'phone-photo-profile': [(0, (25, 390, 405, 745), '自分の関心と利用許可を選ぶ')],
    'phone-match': [(0, (25, 370, 405, 830), '共通の関心から候補を探す')],
    'phone-match-selected': [(0, (25, 285, 405, 535), '誘う人を自分で選ぶ')],
    'phone-select-pottery': [(0, (25, 370, 405, 605), 'プラン名と人数を確認'),
                             (4, (25, 730, 405, 890), '料金と共有の入口を確認')],
    'phone-chat-pottery': [(0, (10, 275, 420, 585), '集合と行程を相談')],
    'phone-reflection': [(0, (25, 430, 405, 645), '利用申告と同意の条件を確認')],
    'phone-program-received': [(0, (10, 600, 420, 780), '事業者から次の体験が届く')],
    'phone-program-course': [(0, (25, 580, 405, 830), '次の工程と料金を確認')],
}
CAPTURES = []
DATA = []
BACKGROUNDS = {}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


@lru_cache(maxsize=12)
def recordings(directory):
    return OperationClips(motion.project_path(directory))


def base(scene, index, count):
    with Image.open(ROOT / 'frontend/public/art/wa/washi-paper-v1.webp') as paper:
        image = Image.blend(Image.new('RGB', motion.SIZE, '#f7f3e8'),
                            ImageOps.fit(paper.convert('RGB'), motion.SIZE), .48)
    art.wa_mount(image)
    draw = ImageDraw.Draw(image)
    art.seal(draw, (76, 26, 126, 80), '講', 33)
    draw.text((150, 32), scene['chapter'], font=art.font(30, 'bold'), fill=art.RED)
    draw.text((1740, 34), NUMERALS[index] + ' / ' + NUMERALS[count - 1],
              font=art.font(27, 'brush'), fill=art.MUTED)
    if scene['layout'] not in ('title', 'stage'):
        draw.text((80, 112), scene['title'], font=art.font(56, 'bold'), fill=art.INK)
    draw.rectangle((48, 965, 1872, 1046), fill='#eee5d2')
    art.text_center(draw, scene['subtitle'], 990, 31)
    return image, draw


def write_scene(draw, scene):
    layout = scene['layout']
    if layout != 'title':
        return
    if layout == 'title':
        guide.words(draw, scene['title'], 620, 260, 76, 1180, bold=True)
        guide.words(draw, scene['headline'], 625, 545, 47, 1170, art.RED, True)
        guide.words(draw, scene['body'], 630, 695, 35, 1140)
        return


def capture_spec(image, scene):
    box = {'wide': WIDE, 'stage': STAGE}.get(scene['layout'], PHONE)
    spec = scene.get('capture')
    if not spec:
        if scene['layout'] != 'title':
            raise ValueError('An application scene requires real captured evidence')
        return
    if 'group' in spec:
        path = recordings(spec['directory']).first(spec['group'])
    else:
        path = motion.project_path(spec['image'])
    actual = art.paste_fit(image, path, box)
    if spec.get('group', '').startswith('phone-'):
        paint_zoom(image, path, spec['group'], 0)
    CAPTURES.append({'source': path.relative_to(ROOT).as_posix(), 'box': list(actual),
                     'sha256': digest(path), 'capture_spec': spec})


@lru_cache(maxsize=3)
def sprite(width, height):
    with Image.open(GUIDE) as original:
        return ImageOps.contain(original.convert('RGBA'), (width, height), Image.Resampling.LANCZOS)


def paint_guide(image, scene, local):
    boxes = {'title': (78, 176, 510, 760), 'phone': (55, 810, 80, 120),
             'wide': (55, 810, 80, 120), 'stage': (65, 700, 145, 218)}
    x, y, width, height = boxes[scene['layout']]
    entrance = round(28 * (1 - motion.smooth(local / .42)))
    picture = sprite(width, height)
    image.paste(picture, (x - entrance, y), picture)
    return image


def render_frame(scenes, index, frame, style):
    image = motion.render_frame(scenes, index, frame, style)
    scene = DATA[index]
    spec = scene.get('capture', {})
    if 'group' in spec:
        spec, local = capture_at(spec, frame / motion.FPS)
        box = STAGE if scene['layout'] == 'stage' else WIDE if spec['group'].startswith('pc-') else PHONE
        area = (145, 205, 1850, 955)
        image.paste(BACKGROUNDS[index].crop(area), area[:2])
        paint_recording(image, spec, local, box)
    return paint_guide(image, scene, frame / motion.FPS)


def capture_at(spec, local):
    sequence = spec.get('sequence', [])
    active = next((part for part in reversed(sequence) if part['at'] <= local), None)
    if active is not None:
        return spec | {'group': active['group']}, active.get('source_seconds', 0) + local - active['at']
    return spec, playback_time(spec, local)


def playback_time(spec, local):
    segments = spec.get('playback_segments', [])
    active = next((part for part in reversed(segments) if part['at'] <= local), None)
    if active is not None:
        return active['source_seconds'] + local - active['at']
    return local + float(spec.get('source_offset_seconds', 0))


def paint_recording(image, spec, local, box):
    recording = recordings(spec['directory'])
    frames = recording.groups[spec['group']]
    source_ms = frames[0]['started'] + max(0, local) * 1000
    selected = next((f for f in reversed(frames) if f['started'] <= source_ms), frames[0])
    picture = fitted_frame(recording.directory / selected['file'], box[2], box[3])
    x = box[0] + (box[2] - picture.width) // 2
    y = box[1] + (box[3] - picture.height) // 2
    image.paste(picture, (x, y))
    if spec['group'].startswith('phone-'):
        paint_zoom(image, recording.directory / selected['file'], spec['group'], local)
    click_hint(image, recording, spec['group'], selected['file'], source_ms,
               (x, y, picture.width, picture.height))


@lru_cache(maxsize=48)
def zoom_frame(path, bounds):
    with Image.open(path) as original:
        if not (0 <= bounds[0] < bounds[2] <= original.width
                and 0 <= bounds[1] < bounds[3] <= original.height):
            raise ValueError('Zoom must use pixels inside the real recorded frame')
        return ImageOps.contain(original.convert('RGB').crop(bounds), ZOOM_BOX[2:], Image.Resampling.LANCZOS)


def paint_zoom(image, path, group, local):
    options = ZOOM_REGIONS[group]
    _, bounds, label = next((item for item in reversed(options) if item[0] <= local), options[0])
    picture = zoom_frame(path, bounds)
    x, y, width, height = ZOOM_BOX
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((x - 12, y - 12, x + width + 12, y + height + 12),
                           radius=8, fill='#fdf9ef', outline='#bbaa8b', width=2)
    draw.text((x, y - 59), '拡大：' + label, font=art.font(31, 'bold'), fill=art.RED)
    image.paste(picture, (x + (width - picture.width) // 2, y + (height - picture.height) // 2))


@lru_cache(maxsize=64)
def capture_size(path):
    with Image.open(path) as original:
        return original.size


def click_hint(image, recording, group, filename, source_ms, box):
    action = recording.actions.get(group)
    if not action or action['action'] != 'click':
        return
    elapsed = (source_ms - action['at']) / 1000
    if not 0 <= elapsed < .55:
        return
    width, height = capture_size(recording.directory / filename)
    rect = action['rect']
    if (rect['x'] < 0 or rect['y'] < 0 or rect['x'] + rect['width'] > width
            or rect['y'] + rect['height'] > height):
        return
    cx = box[0] + (rect['x'] + rect['width'] / 2) * box[2] / width
    cy = box[1] + (rect['y'] + rect['height'] / 2) * box[3] / height
    radius = 15 + elapsed * 22
    draw = ImageDraw.Draw(image, 'RGBA')
    draw.ellipse((cx - radius, cy - radius, cx + radius, cy + radius),
                 outline=(157, 59, 45, round(220 * (1 - elapsed / .55))), width=3)


def compose(data):
    layers = WORK / 'layers'
    layers.mkdir(exist_ok=True)
    sheet = Image.new('RGB', (1920, 540 * math.ceil(len(data) / 2)), '#f7f3e8')
    for index, scene in enumerate(data):
        image, draw = base(scene, index, len(data))
        write_scene(draw, scene)
        BACKGROUNDS[index] = image.copy()
        capture_spec(image, scene)
        image.save(layers / f'scene-{index:02}.png')
        preview = paint_guide(image.copy(), scene, 1.5)
        preview.save(WORK / f'scene-{index:02}.png')
        sheet.paste(preview.resize((960, 540), Image.Resampling.LANCZOS),
                    ((index % 2) * 960, (index // 2) * 540))
    sheet.save(WORK / 'contact-sheet.jpg', quality=95)
    return layers


def load_scenes(data, layers):
    if not 8 <= len(data) <= 12:
        raise ValueError('The story requires eight to twelve scenes')
    scenes, elapsed = [], 0
    for index, item in enumerate(data):
        seconds = motion.checked_number(item['duration'], 3, 16, 'scene duration')
        frames = round(seconds * motion.FPS)
        if abs(frames / motion.FPS - seconds) > 1e-7:
            raise ValueError('Scene duration must contain a whole number of frames')
        source = layers / f'scene-{index:02}.png'
        scenes.append(motion.Scene(index, item['kind'], seconds, frames, elapsed,
            motion.image(source), None, seconds / 2, [], source, None))
        elapsed += frames
    if elapsed > 80 * motion.FPS:
        raise ValueError('The film must be no longer than eighty seconds')
    return scenes


def verification(data, scenes, source_json):
    return {'source_scene_json': source_json.relative_to(ROOT).as_posix(),
        'source_scene_json_sha256': digest(source_json), 'character_sha256': digest(GUIDE),
        'character_path': GUIDE.relative_to(ROOT).as_posix(), 'capture_regions': CAPTURES,
        'font': 'Meiryo / Meiryo Bold; brush only for seals and chapter numerals',
        'audio_speed_policy': 'No post-generation acceleration or speech trimming; measured source audio determines scene fit',
        'narration_engine': data[0].get('voice_engine', 'unspecified'),
        'zoom_regions': ZOOM_REGIONS,
        'zoom_policy': 'Whole phone and magnified region use the exact same selected real frame',
        'operations': [s.get('capture') for s in data if s.get('capture')],
        'recording_manifests': recording_evidence(data),
        'script_sha256': digest(motion.project_path('scripts/render_revisit_v13.py')),
        'scenes': [{'index': s.index, 'kind': s.kind, 'seconds': s.seconds,
            'source': s.source.relative_to(ROOT).as_posix(), 'source_sha256': digest(s.source),
            'alternate': None, 'alternate_sha256': None} for s in scenes]}


def recording_evidence(data):
    directories = sorted({s['capture']['directory'] for s in data
                          if 'directory' in s.get('capture', {})})
    result = []
    for directory in directories:
        recording = recordings(directory)
        manifest = recording.directory / 'recording.json'
        result.append({'path': manifest.relative_to(ROOT).as_posix(), 'sha256': digest(manifest),
            'frames': [{'file': frame['file'], 'sha256': digest(recording.directory / frame['file'])}
                       for frame in recording.manifest['frames']]})
    return result


def main():
    global DATA
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--encode', action='store_true')
    parser.add_argument('--audio-dir', type=motion.project_path, default=WORK / 'audio')
    args = parser.parse_args()
    WORK.mkdir(parents=True, exist_ok=True)
    target = WORK / 'guide-raw.mp4'
    if target.exists():
        raise FileExistsError('Preserve the existing encoding; use a new revision')
    DATA = json.loads(SCRIPT.read_text(encoding='utf-8'))
    source_json = WORK / 'scenes.json'
    source_json.write_text(json.dumps(DATA, ensure_ascii=False, indent=2), encoding='utf-8')
    scenes = load_scenes(DATA, compose(DATA))
    report = verification(DATA, scenes, source_json)
    report['audio_input_directory'] = args.audio_dir.relative_to(ROOT).as_posix()
    if args.encode:
        voices = motion.voice_plan(scenes, args.audio_dir)
        if any(voice['tempo'] != 1 for voice in voices):
            raise ValueError('Shorten narration instead of accelerating it')
        audio, report['voice_plan'] = motion.prepare_audio(scenes, voices, WORK / 'pcm')
        motion.encode(scenes, audio, target, WORK / 'encode.log', 'wa', frame_renderer=render_frame)
        report.update(motion.verify(target, WORK, expected_seconds=sum(s.seconds for s in scenes)))
        report['output'] = target.relative_to(ROOT).as_posix()
    name = 'motion-verification.json' if args.encode else 'layout-verification.json'
    (WORK / name).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'encoded': args.encode, 'scenes': len(scenes), 'seconds': sum(s.seconds for s in scenes)}))


if __name__ == '__main__':
    main()
