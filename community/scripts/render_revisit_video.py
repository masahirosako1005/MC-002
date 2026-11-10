"""Edit real CUA captures into a narrated film; never drives the browser.

Screens are captured through CUA. Overlays explain real features and do not
replace UI values. Each revision is retained, decoded and contact-sheet checked.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import subprocess
import wave
from pathlib import Path

import imageio_ffmpeg
from PIL import Image, ImageDraw, ImageFont, ImageOps

ROOT = Path(__file__).resolve().parents[2]
WORK = ROOT / 'artifacts/video-revisit'
SCREENS = WORK / 'screens'
FF = imageio_ffmpeg.get_ffmpeg_exe()
SIZE = (1920, 1080)
INK, RED, GREEN, MUTED = '#332f25', '#9d3b2d', '#3c6252', '#716c5c'
BRUSH = WORK / 'YujiMai-Regular.ttf'
BODY = Path('C:/Windows/Fonts/meiryo.ttc')
BOLD = Path('C:/Windows/Fonts/meiryob.ttc')


def font(size, style='body'):
    return ImageFont.truetype(str({'body': BODY, 'bold': BOLD, 'brush': BRUSH}[style]), size)


def wrapped(draw, text, xy, size=34, width=800, fill=INK, style='body', spacing=14):
    x, y = xy
    f = font(size, style)
    line = ''
    for char in text + '\n':
        if char == '\n' or draw.textlength(line + char, font=f) > width:
            draw.text((x, y), line, font=f, fill=fill)
            y += size + spacing
            line = '' if char == '\n' else char
        else:
            line += char
    return y


def paste_fit(canvas, path, box):
    image = Image.open(path).convert('RGB')
    fit = ImageOps.contain(image, (box[2], box[3]), Image.Resampling.LANCZOS)
    x = box[0] + (box[2] - fit.width) // 2
    y = box[1] + (box[3] - fit.height) // 2
    canvas.paste(fit, (x, y))
    return x, y, fit.width, fit.height


def text_center(draw, text, y, size=36, fill=INK, style='body'):
    f = font(size, style)
    x = (SIZE[0] - draw.textlength(text, font=f)) / 2
    draw.text((x, y), text, font=f, fill=fill)


def heading_style(revision):
    return 'bold' if revision >= 7 else 'brush'


def heading_font(size, revision):
    return font(size, heading_style(revision))


def panel(draw, x, y, number, label, detail, width=700, heading='brush'):
    draw.rectangle((x, y + 10, x + 52, y + 62), outline=RED, width=2)
    draw.text((x + 15, y + 15), number, font=font(30, 'brush'), fill=RED)
    draw.text((x + 78, y), label, font=font(44, heading), fill=INK)
    wrapped(draw, detail, (x + 78, y + 70), 28, width - 78, MUTED)


def brush_rule(draw, start, end, fill, width=2):
    """A quiet, deterministic ink edge; never alters captured UI pixels."""
    x0, y0 = start
    x1, y1 = end
    points = [(x0 + (x1 - x0) * step / 80,
               y0 + (y1 - y0) * step / 80 + math.sin(step * .72) * .55)
              for step in range(81)]
    draw.line(points, fill=fill, width=width)


def seal(draw, box, label, size=32, filled=False):
    x0, y0, x1, y1 = box
    draw.polygon([(x0 + 1, y0 + 3), (x1 - 2, y0), (x1, y1 - 2), (x0, y1)],
                 fill=RED if filled else None, outline=RED, width=2)
    draw.rectangle((x0 + 5, y0 + 6, x1 - 5, y1 - 5), outline='#e4b4a0' if filled else RED, width=1)
    face = font(size, 'brush')
    bounds = draw.textbbox((0, 0), label, font=face)
    draw.text(((x0 + x1 - bounds[2] + bounds[0]) / 2,
               (y0 + y1 - bounds[3] + bounds[1]) / 2 - bounds[1]), label,
              font=face, fill='#fff6e3' if filled else RED)


def wa_mount(image):
    """Book/scroll mounting stays outside the area occupied by screens."""
    d = ImageDraw.Draw(image)
    for left, right in ((16, 38), (1882, 1904)):
        d.rectangle((left, 18, right, 1062), fill='#dbccb0')
        d.line((left + 3, 18, left + 3, 1062), fill='#b7a180', width=1)
        d.line((right - 3, 18, right - 3, 1062), fill='#eee0c5', width=2)
    d.line((46, 24, 46, 1058), fill='#c4b18e', width=1)
    d.line((1874, 24, 1874, 1058), fill='#c4b18e', width=1)
    brush_rule(d, (67, 93), (1851, 93), '#c2aa86')
    brush_rule(d, (67, 958), (1851, 958), '#c2aa86')


def base(scene, index, revision):
    paper = Image.open(ROOT / 'community/frontend/public/art/wa/washi-paper-v1.webp').convert('RGB')
    image = Image.blend(Image.new('RGB', SIZE, '#f7f3e8'), ImageOps.fit(paper, SIZE), .48 if revision >= 7 else .26)
    if revision >= 7:
        return wa_base(image, scene, index)
    d = ImageDraw.Draw(image)
    d.line((72, 66, 1848, 66), fill='#d6c7ad', width=2)
    d.rectangle((72, 30, 120, 82), fill='#f7f3e8', outline=RED, width=2)
    d.text((81, 34), '講', font=font(32, 'brush'), fill=RED)
    d.text((145, 30), scene['chapter'], font=font(26, 'bold'), fill=RED)
    d.text((1770, 30), f'{index + 1:02}/08', font=font(24), fill=MUTED)
    if scene['kind'] not in ('intro', 'closing'):
        d.text((80, 105), scene['title'], font=font(58, 'brush'), fill=INK)
    d.rectangle((0, 965, 1920, 1080), fill='#eee6d5')
    text_center(d, scene['subtitle'], 990, 31 if revision == 1 else 33)
    return image, d


def wa_base(image, scene, index):
    wa_mount(image)
    d = ImageDraw.Draw(image)
    seal(d, (76, 26, 126, 80), '講', 33)
    d.text((150, 32), scene['chapter'], font=font(30, 'bold'), fill=RED)
    d.text((1770, 34), '一二三四五六七八'[index] + ' / 八', font=font(27, 'brush'), fill=MUTED)
    if scene['kind'] not in ('intro', 'closing'):
        d.text((80, 112), scene['title'], font=font(58, 'bold'), fill=INK)
    d.rectangle((48, 965, 1872, 1046), fill='#eee5d2')
    text_center(d, scene['subtitle'], 990, 33)
    return image, d


def scene_intro_wa(im, d):
    paste_fit(im, ROOT / 'community/frontend/public/art/wa/travel-woodcut-v1.png', (720, 182, 1120, 700))
    for x in (706, 1850):
        d.rectangle((x, 166, x + 10, 890), fill='#b9a27b')
        d.line((x + 3, 166, x + 3, 890), fill='#e4d4b5', width=3)
    seal(d, (100, 190, 270, 378), '講', 126)
    d.text((293, 318), 'こう', font=font(32), fill=MUTED)
    wrapped(d, '目的で集まり、\n役割を持ち寄る。', (100, 438), 64, 590, style='bold', spacing=24)
    brush_rule(d, (105, 662), (572, 662), RED, 3)
    wrapped(d, '日帰りと再訪を支える\n仲間のプラットフォーム', (105, 712), 34, 580, MUTED)


def scene_intro(im, d):
    art = ROOT / 'community/frontend/public/art/wa/travel-woodcut-v1.png'
    paste_fit(im, art, (720, 170, 1120, 700))
    d.rectangle((90, 165, 266, 355), outline=RED, width=4)
    d.rectangle((100, 175, 256, 345), outline=RED, width=1)
    d.text((120, 170), '講', font=font(124, 'brush'), fill=RED)
    d.text((285, 295), 'こう', font=font(32), fill=MUTED)
    wrapped(d, '目的で集まり、\n役割を持ち寄る。', (90, 405), 72, 680, style='brush', spacing=26)
    wrapped(d, '日帰りと再訪を支える\n仲間のプラットフォーム', (95, 675), 34, 620, MUTED)


def scene_overview(im, d):
    # These are simultaneous real screenshots of the two independent roles.
    paste_fit(im, SCREENS / 'visitor-home.jpg', (90, 205, 410, 735))
    paste_fit(im, SCREENS / 'provider-overview.jpg', (670, 260, 1160, 640))
    d.text((180, 180), '利用者', font=font(32, 'bold'), fill=INK)
    d.text((1135, 210), '事業者', font=font(32, 'bold'), fill=INK)
    d.line((510, 540, 650, 540), fill='#b79b74', width=3)
    d.ellipse((561, 526, 590, 555), outline=RED, width=3)
    d.ellipse((580, 526, 609, 555), outline=RED, width=3)


def scene_visitor(im, d, revision, alternate):
    if revision >= 2:
        if not alternate:
            paste_fit(im, SCREENS / 'visitor-home.jpg', (160, 195, 465, 745))
            d.text((790, 285), '行き先を比較する', font=heading_font(64, revision), fill=INK)
            wrapped(d, '写真・日程・人数・料金。\n場所に合うクーポンも確認。', (800, 415), 38, 920, MUTED, spacing=24)
            d.line((800, 625, 1690, 625), fill='#d3c3a7', width=2)
            d.text((800, 690), '行き先を選ぶ  →  講で相談する', font=font(38, 'bold'), fill=RED)
            wrapped(d, '共有する内容を決めてから、\n事業者へ相談を送ります。', (800, 785), 32, 900, MUTED)
        else:
            paste_fit(im, SCREENS / 'visitor-chat.jpg', (1210, 195, 465, 745))
            d.text((125, 285), '同じ講で、事業者と話す', font=heading_font(60, revision), fill=INK)
            wrapped(d, '共有内容を決め、招待を承諾した\n事業者と日程や行程を相談。', (130, 420), 38, 980, MUTED, spacing=24)
            panel(d, 135, 625, '一', '仲間内の会話は分ける', '写真や個人の関心を自動で開示しない。', 1000, heading_style(revision))
            panel(d, 135, 795, '二', '相談内容を保存する', '実際に送信し、双方で確認した会話。', 1000, heading_style(revision))
    else:
        paste_fit(im, SCREENS / 'visitor-home.jpg', (100, 200, 420, 740))
        paste_fit(im, SCREENS / 'visitor-chat.jpg', (1310, 200, 420, 740))
        panel(d, 580, 300, '一', '行き先を選ぶ', '写真・日時・人数・料金で比較。', 640)
        panel(d, 580, 490, '二', '講で相談する', '仲間と決めて、事業者を招く。', 640)
        panel(d, 580, 680, '三', '共有して調整する', '承諾後、日程や行程を具体化。', 640)


def scene_provider(im, d, revision, alternate):
    if revision >= 3 and not alternate:
        paste_fit(im, SCREENS / 'provider-reply.jpg', (570, 220, 1270, 700))
        panel(d, 80, 270, '一', '相談に応じる', '承諾した講と相談。', 440, heading_style(revision))
        panel(d, 80, 470, '二', '条件をそろえる', '日程・人数・行程を確認。', 440, heading_style(revision))
        panel(d, 80, 670, '三', '返信を届ける', '双方の画面に保存。', 440, heading_style(revision))
    else:
        paste_fit(im, SCREENS / 'provider-chart.jpg', (570, 220, 1270, 700))
        panel(d, 80, 270, '一', '推移を見る', '来訪と再訪を期間別に。', 440, heading_style(revision))
        panel(d, 80, 470, '二', '地域を見る', 'どの地域から来ているか。', 440, heading_style(revision))
        panel(d, 80, 670, '三', '市を見渡す', '自社と市全体を切り替え。', 440, heading_style(revision))
        d.text((640, 905), '確認済みの記録を集計。個人の住所・会話は表示しません。', font=font(24), fill=MUTED)


def scene_program(im, d, revision=1):
    paste_fit(im, ROOT / 'community/assets/pottery.png', (90, 230, 830, 470))
    paste_fit(im, SCREENS / '03-program-phone.jpg', (1190, 200, 450, 740))
    for j, label in enumerate(('成形', '絵付け', '受け取り')):
        x = 110 + j * 280
        if revision >= 7:
            seal(d, (x, 735, x + 58, 793), '一二三'[j], 34, filled=j == 0)
        else:
            d.ellipse((x, 735, x + 58, 793), fill=RED if j == 0 else '#e4d4b4')
            d.text((x + 18, 741), str(j + 1), font=font(28, 'bold'), fill='white' if j == 0 else INK)
        d.text((x, 815), label, font=heading_font(40, revision), fill=INK)
        if j < 2:
            d.line((x + 75, 764, x + 255, 764), fill='#b99e79', width=3)
    d.text((95, 897), '別の日に参加し、次の工程へ。', font=font(28), fill=MUTED)


def scene_rank(im, d, revision=1):
    paste_fit(im, SCREENS / '06-rank-phone.jpg', (1260, 200, 430, 740))
    d.text((105, 240), '先達の追加点', font=heading_font(43, revision), fill=INK)
    d.text((90, 305), '+50', font=heading_font(160, revision), fill=RED)
    d.text((475, 405), '点', font=heading_font(54, revision), fill=RED)
    panel(d, 110, 560, '一', '企画・案内の協力を評価', '本人の承諾と全行程の参加確認が条件。', 950, heading_style(revision))
    panel(d, 110, 745, '二', '階級に応じた特典', '条件を満たす割引・クーポンの選択肢が増える。', 1000, heading_style(revision))


def scene_zone(im, d, revision):
    paste_fit(im, SCREENS / '07-zone-phone.jpg', (90, 200, 420, 740))
    d.text((610, 240), '片道', font=font(32), fill=MUTED)
    d.text((595, 290), '20—40', font=heading_font(110, revision), fill=RED)
    d.text((1130 if revision >= 2 else 1000, 352), 'km', font=font(42), fill=RED)
    d.text((610, 450), '基本5% → 条件を満たすと10%', font=font(43, 'bold'), fill=INK)
    wrapped(d, '対象市区町村の計画用参考距離で判定。\n1回の割引上限 1,000円。', (610, 535), 30, 1000, MUTED)
    if revision >= 2:
        d.text((610, 620), '表示中の利用者は地域未登録のため、基本5%。', font=font(25), fill=MUTED)
    paste_fit(im, SCREENS / 'provider-budget.jpg', (650, 700, 1120, 230))
    d.text((610, 660), '確保・利用分を数え、予算の超過を防ぐ。', font=font(29, 'bold'), fill=GREEN)


def scene_closing(im, d, scene, revision=1):
    text_center(d, scene['title'], 155, 72, style=heading_style(revision))
    specs = [('一', '通う目的', '複数回で進める体験', 'pottery.png'),
             ('二', '先達への特典', '次の企画を後押し', 'woodland.png'),
             ('三', '日帰りゾーン割引', '地域の条件に応じて追加', 'riverside.png')]
    for j, (num, label, detail, photo) in enumerate(specs):
        x = 100 + 595 * j
        paste_fit(im, ROOT / 'community/assets' / photo, (x, 350, 530, 340))
        d.rectangle((x + 18, 365, x + 80, 431), fill='#f7f3e8', outline=RED, width=2)
        d.text((x + 33, 370), num, font=font(38, 'brush'), fill=RED)
        d.text((x, 725), label, font=heading_font(44, revision), fill=INK)
        d.text((x, 795), detail, font=font(29), fill=MUTED)
    text_center(d, '一度で終わらない体験と、次の企画を支える特典。', 886, 32)


def make_scene(scene, index, revision, destination, alternate=False):
    im, d = base(scene, index, revision)
    kind = scene['kind']
    if kind == 'intro':
        (scene_intro_wa if revision >= 7 else scene_intro)(im, d)
    elif kind == 'overview':
        scene_overview(im, d)
    elif kind == 'visitor':
        scene_visitor(im, d, revision, alternate)
    elif kind == 'provider':
        scene_provider(im, d, revision, alternate)
    elif kind == 'program':
        scene_program(im, d, revision)
    elif kind == 'rank':
        scene_rank(im, d, revision)
    elif kind == 'zone':
        scene_zone(im, d, revision)
    else:
        scene_closing(im, d, scene, revision)
    im.save(destination)


def run(args, log=None):
    result = subprocess.run([FF, '-hide_banner', '-nostdin', *args], capture_output=True, check=False)
    if log:
        log.write_bytes(result.stderr)
    if result.returncode:
        raise RuntimeError(result.stderr.decode('utf-8', 'replace')[-1800:])
    return result


def narration_length(path):
    with wave.open(str(path)) as audio:
        return audio.getnframes() / audio.getframerate()


def new_revision_directory(revision, stills_only):
    out = WORK / f'v{revision}'
    video = ROOT / 'outputs' / f'kou-revisit-intro-v{revision}.mp4'
    if out.exists() or (not stills_only and video.exists()):
        raise FileExistsError('Revision already exists; choose a new revision number')
    out.mkdir(parents=True, exist_ok=False)
    return out


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('revision', type=int, choices=range(1, 10))
    parser.add_argument('--stills-only', action='store_true')
    args = parser.parse_args()
    out = new_revision_directory(args.revision, args.stills_only)
    scenes = json.loads((Path(__file__).with_name('revisit-video-scenes.json')).read_text(encoding='utf-8'))
    report = {'revision': args.revision, 'scenes': [], 'capture_method': 'Real CUA screenshots; edited framing and explanatory overlays; no simulated UI state.'}
    sheet = Image.new('RGB', (1920, 1080 * 2), '#f5eddd')
    for i, scene in enumerate(scenes):
        still = out / f'scene-{i:02}.png'
        make_scene(scene, i, args.revision, still)
        if args.revision >= 2 and scene['kind'] == 'visitor':
            make_scene(scene, i, args.revision, out / f'scene-{i:02}-alt.png', alternate=True)
        if args.revision >= 3 and scene['kind'] == 'provider':
            make_scene(scene, i, args.revision, out / f'scene-{i:02}-alt.png', alternate=True)
        sheet.paste(Image.open(still).resize((960, 540), Image.Resampling.LANCZOS), ((i % 2) * 960, (i // 2) * 540))
        if args.stills_only:
            continue
        duration = scene['duration']
        audio = WORK / 'audio' / f'voice-{i:02}.wav'
        tempo = max(1, narration_length(audio) / (duration - .55))
        # At most ~1.5x per short phrase; voiced content is never cut to fit.
        if tempo > 1.65:
            raise ValueError(f'Scene {i} narration too dense: {tempo:.2f}x')
        video = f"fps=30,format=yuv420p,fade=t=in:st=0:d=0.20,fade=t=out:st={duration-.16}:d=0.16,drawbox=x=72:y=1054:w=1776:h=3:color=0xd6c7ad:t=fill"
        af = f'atempo={tempo:.7f},adelay=220|220,apad,atrim=duration={duration},afade=t=out:st={duration-.10}:d=0.1'
        target = out / f'segment-{i:02}.mp4'
        run(['-y', '-loop', '1', '-framerate', '30', '-i', str(still), '-i', str(audio),
             '-t', str(duration), '-vf', video, '-af', af, '-c:v', 'libx264', '-preset', 'fast',
             '-crf', '19', '-threads', '2', '-c:a', 'aac', '-b:a', '160k', '-ar', '48000', '-ac', '2',
             '-movflags', '+faststart', str(target)], out / f'encode-{i:02}.log')
        report['scenes'].append({'scene': i + 1, 'seconds': duration, 'voice_seconds': narration_length(audio), 'tempo': round(tempo, 3)})
        print(f'Scene {i+1}/8 encoded', flush=True)
    sheet.save(out / 'contact-sheet.jpg', quality=94)
    if args.stills_only:
        print(str(out / 'contact-sheet.jpg'))
        return
    concat = out / 'segments.txt'
    concat.write_text(''.join(f"file 'segment-{i:02}.mp4'\n" for i in range(len(scenes))), encoding='utf-8')
    target = ROOT / 'outputs' / f'kou-revisit-intro-v{args.revision}.mp4'
    run(['-y', '-f', 'concat', '-safe', '1', '-i', str(concat), '-c', 'copy', '-movflags', '+faststart', str(target)])
    decode = run(['-i', str(target), '-progress', 'pipe:1', '-f', 'null', '-'], out / 'decode.log')
    frames = int(re.findall(rb'^frame=(\d+)', decode.stdout, re.MULTILINE)[-1])
    assert frames == 1800, frames
    info = decode.stderr.decode('utf-8', 'replace')
    assert '1920x1080' in info and 'Audio: aac' in info and 'h264' in info
    report.update({'output': target.relative_to(ROOT).as_posix(), 'frames': frames, 'duration_seconds': sum(s['duration'] for s in scenes), 'size': SIZE, 'fps': 30, 'audio': 'Installed Japanese Sayaka voice, time-fitted per scene', 'sha256': hashlib.sha256(target.read_bytes()).hexdigest(), 'bytes': target.stat().st_size, 'visual_review': 'pending'})
    (out / 'verification.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False))


if __name__ == '__main__':
    main()
