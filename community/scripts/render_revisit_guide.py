"""Compose a character-led film from real captures and an original guide asset.

The guide illustrates narration, never impersonates a customer or changes the
captured application. All narration is local, original-speed Japanese speech.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from functools import lru_cache

import animate_revisit_video as motion
import render_revisit_video as art
from finish_revisit_audio import loudness
from PIL import Image, ImageOps

ROOT, WORK = art.ROOT, art.WORK / 'v9'
SCRIPT = ROOT / 'community/scripts/revisit-video-guide-scenes.json'
GUIDE = ROOT / 'community/assets/revisit-guide/guide-pointing-v1.png'
INK, RED, MUTED = art.INK, art.RED, art.MUTED
CAPTURES = []


def capture(canvas, name, box):
    path = art.SCREENS / name
    actual = art.paste_fit(canvas, path, box)
    CAPTURES.append({'source': path.relative_to(ROOT).as_posix(), 'box': list(actual),
                     'sha256': hashlib.sha256(path.read_bytes()).hexdigest()})


def words(draw, value, x, y, size=38, width=1000, color=INK, bold=False):
    return art.wrapped(draw, value, (x, y), size, width, color,
                       'bold' if bold else 'body', spacing=18)


def question(draw, value, x=450, y=265, width=770):
    # An editorial question outside all application screens.
    draw.rounded_rectangle((x - 24, y - 18, x + width, y + 96), radius=18,
                           fill='#fffaf0', outline='#b9a27b', width=2)
    draw.polygon([(x - 24, y + 48), (x - 53, y + 74), (x - 24, y + 78)],
                  fill='#fffaf0', outline='#b9a27b')
    words(draw, value, x, y, 41, width - 20, RED, True)


def starting_frame(scene, index):
    image, draw = art.base(scene, index, 9)
    return image, draw


def intro(image, draw, alternate):
    del alternate
    art.seal(draw, (650, 153, 767, 280), '講', 84)
    words(draw, 'こう', 800, 222, 34, color=MUTED)
    words(draw, '一度来て、\nおしまい？', 650, 330, 100, 1150, bold=True)
    art.brush_rule(draw, (655, 613), (1730, 613), RED, 4)
    words(draw, 'もったいない！', 650, 668, 70, 1100, RED, True)
    words(draw, '次に来る理由を、3つの仕組みで。', 655, 815, 35, 1120)


def overview(image, draw, alternate):
    del alternate
    question(draw, '「講」って、どんな仲間？', 420, 270, 1260)
    words(draw, '行き先を選ぶ → 講で相談 → 体験を記録', 540, 417, 38, 1200, bold=True)
    capture(image, 'visitor-home.jpg', (600, 505, 265, 424))
    capture(image, 'provider-overview.jpg', (960, 535, 850, 390))
    words(draw, '利用者', 640, 463, 27, bold=True)
    words(draw, '事業者', 1300, 475, 27, bold=True)
    art.brush_rule(draw, (870, 710), (948, 710), RED, 3)


def visitor(image, draw, alternate):
    question(draw, 'どこに行く？誰と相談する？')
    words(draw, '行き先を選び、講で共有。' if not alternate else '承諾した事業者と、同じ講で。',
          450, 446, 45, 760, bold=True)
    words(draw, '写真・日程・料金を比較。\n場所に合うクーポンも確認。' if not alternate
          else '日程や人数、行程を詰める。\n仲間内の会話は分けて保存。', 455, 590, 35, 730, MUTED)
    capture(image, 'visitor-chat.jpg' if alternate else 'visitor-home.jpg', (1285, 205, 500, 740))
    words(draw, '選ぶ → 共有を決める → 相談', 455, 822, 32, 760, RED, True)


def provider(image, draw, alternate):
    question(draw, '受け入れる側も、出番だ！', 130, 260, 1620)
    capture(image, 'provider-chart.jpg' if alternate else 'provider-reply.jpg', (615, 407, 1230, 520))
    words(draw, '市全体の\n来訪・再訪を確認。' if alternate else '届いた相談に返信。\n行程や見積を調整。',
          90, 411, 31, 470, bold=True)


def program(image, draw, alternate):
    del alternate
    question(draw, '一回で、完成しなくてもいい！')
    words(draw, '陶芸は、3回通う体験に。', 450, 441, 46, 770, bold=True)
    for index, label in enumerate(('成形', '絵付け', '受け取り')):
        x = 465 + index * 252
        art.seal(draw, (x, 570, x + 62, 635), '一二三'[index], 38, filled=index == 0)
        words(draw, label, x, 677, 36, 240, bold=True)
        if index < 2:
            art.brush_rule(draw, (x + 77, 604), (x + 223, 604), '#bba686', 3)
    words(draw, '次の工程が、次に来る目的になる。', 455, 826, 32, 760, RED, True)
    capture(image, '03-program-phone.jpg', (1285, 205, 500, 740))


def rank(image, draw, alternate):
    del alternate
    question(draw, '次の企画、誰が引っ張る？')
    words(draw, '先達の追加点', 450, 445, 40, 760, bold=True)
    words(draw, '+50', 445, 500, 146, 720, RED, True)
    words(draw, '点', 790, 603, 45, 140, RED, True)
    words(draw, '本人承諾・全行程の参加確認後。\n階級が上がると、特典の選択肢も。',
          455, 727, 33, 780)
    capture(image, '06-rank-phone.jpg', (1285, 205, 500, 740))


def zone(image, draw, alternate):
    del alternate
    question(draw, '限りある割引、どこに届ける？', 420, 250, 1380)
    words(draw, '片道 20–40 km', 440, 410, 74, 1040, RED, True)
    words(draw, '日帰り圏と想定し、条件に応じて追加。', 447, 523, 33, 1020)
    words(draw, '基本 5% → 条件を満たすと 10%', 447, 603, 42, 1200, bold=True)
    words(draw, '登録地域の参考距離で判定。1回上限1,000円。', 447, 682, 29, 1100, MUTED)
    capture(image, 'provider-budget.jpg', (465, 728, 1350, 175))
    words(draw, '確保・利用分を数え、予算を管理。', 450, 910, 24, 1100, art.GREEN)


def closing(image, draw, alternate):
    del alternate
    words(draw, '次に来る理由をつくる。', 615, 163, 65, 1200, bold=True)
    specs = [('一', '通う目的', '複数回で進める体験'),
             ('二', '先達の特典', '次の企画を後押し'),
             ('三', '日帰り圏への割引', '日帰りで、また訪れるきっかけに')]
    for index, (number, label, detail) in enumerate(specs):
        y = 340 + index * 186
        art.seal(draw, (635, y, 702, y + 72), number, 44)
        words(draw, label, 745, y - 4, 48, 1060, bold=True)
        words(draw, detail, 748, y + 79, 32, 1060, MUTED)


BUILDERS = [intro, overview, visitor, provider, program, rank, zone, closing]
GUIDE_BOXES = [(78, 176, 510, 760), (80, 470, 310, 465), (75, 470, 330, 495),
               (105, 581, 245, 367), (75, 470, 330, 495), (75, 470, 330, 495),
               (70, 470, 330, 495), (75, 222, 475, 712)]


@lru_cache(maxsize=10)
def sprite(width, height):
    with Image.open(GUIDE) as original:
        return ImageOps.contain(original.convert('RGBA'), (width, height), Image.Resampling.LANCZOS)


def guide_on_frame(frame, index, local):
    x, y, width, height = GUIDE_BOXES[index]
    # A short entrance and two small emphasis beats, not continuous motion or lip sync.
    entrance = round(28 * (1 - motion.smooth(local / .42)))
    beat = sum(-5 * math.sin(math.pi * (local - start) / .45)
               for start in (.8, 2.0) if start <= local <= start + .45)
    picture = sprite(width, height)
    frame.paste(picture, (x - entrance, y + round(beat)), picture)
    return frame


def render_frame(scenes, index, frame, style):
    image = motion.render_frame(scenes, index, frame, style)
    return guide_on_frame(image, index, frame / motion.FPS)


def compose(data):
    layers = WORK / 'layers'
    layers.mkdir(exist_ok=True)
    sheet = Image.new('RGB', (1920, 2160), '#f7f3e8')
    for index, scene in enumerate(data):
        for alternate in ([False, True] if scene['kind'] in ('visitor', 'provider') else [False]):
            image, draw = starting_frame(scene, index)
            BUILDERS[index](image, draw, alternate)
            suffix = '-alt' if alternate else ''
            image.save(layers / f'scene-{index:02}{suffix}.png')
            preview = guide_on_frame(image.copy(), index, 1.5)
            preview.save(WORK / f'scene-{index:02}{suffix}.png')
            if not alternate:
                sheet.paste(preview.resize((960, 540), Image.Resampling.LANCZOS),
                            ((index % 2) * 960, (index // 2) * 540))
    sheet.save(WORK / 'contact-sheet.jpg', quality=95)
    return layers


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--encode', action='store_true')
    args = parser.parse_args()
    target = WORK / 'guide-raw.mp4'
    if target.exists():
        raise FileExistsError('Preserve previous encoding; select a new revision')
    data = json.loads(SCRIPT.read_text(encoding='utf-8'))
    for scene in data:
        scene['motion'] = {'highlights': []}
    source_json = WORK / 'scenes.json'
    source_json.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    layers = compose(data)
    scenes = motion.load_scenes(source_json, layers, 'wa')
    report = {'source_scene_json': source_json.relative_to(ROOT).as_posix(),
        'source_scene_json_sha256': hashlib.sha256(source_json.read_bytes()).hexdigest(),
        'character_sha256': hashlib.sha256(GUIDE.read_bytes()).hexdigest(),
        'capture_regions': CAPTURES, 'character_motion': 'Entrance 0.42s; two 0.45s emphasis beats; no lip-sync claim',
        'font': 'Meiryo / Meiryo Bold for explanations; brush only for seals and decorative numerals',
        'scenes': [{'index': s.index, 'kind': s.kind, 'seconds': s.seconds,
            'source': s.source.relative_to(ROOT).as_posix(),
            'source_sha256': hashlib.sha256(s.source.read_bytes()).hexdigest(),
            'alternate': s.alternate_source.relative_to(ROOT).as_posix() if s.alternate_source else None,
            'alternate_sha256': hashlib.sha256(s.alternate_source.read_bytes()).hexdigest() if s.alternate_source else None}
            for s in scenes]}
    if args.encode:
        voices = motion.voice_plan(scenes, WORK / 'audio')
        if any(voice['tempo'] != 1 for voice in voices):
            raise ValueError('Narration must fit at its original speed')
        audio, report['voice_plan'] = motion.prepare_audio(scenes, voices, WORK / 'pcm')
        report['pcm_loudness'] = loudness(audio, WORK / 'pcm-loudness.log')
        motion.encode(scenes, audio, target, WORK / 'encode.log', 'wa', frame_renderer=render_frame)
        report.update(motion.verify(target, WORK))
        report['output'] = target.relative_to(ROOT).as_posix()
    (WORK / ('motion-verification.json' if args.encode else 'layout-verification.json')).write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'encoded': args.encode, 'captures': len(CAPTURES), 'scenes': len(scenes)}))


if __name__ == '__main__':
    main()
