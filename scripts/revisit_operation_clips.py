"""Replay CUA-captured real actions with short reading holds and click cues.

No UI is reconstructed. Each frame comes from the actual local app. Pauses
between recordings are omitted; within an action the recorded timing is kept.
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageDraw, ImageOps


@lru_cache(maxsize=48)
def fitted_frame(path, width, height):
    with Image.open(path) as image:
        return ImageOps.contain(image.convert('RGB'), (width, height), Image.Resampling.LANCZOS)


class OperationClips:
    def __init__(self, directory: Path):
        self.directory = directory
        self.manifest = json.loads((directory / 'recording.json').read_text(encoding='utf-8'))
        self.groups = {}
        for frame in self.manifest['frames']:
            path = (directory / frame['file']).resolve()
            if path.parent != directory.resolve() or not path.is_file():
                raise ValueError('Recording frame must be inside the recording directory')
            self.groups.setdefault(frame['group'], []).append(frame)
        self.actions = {action['group']: action for action in self.manifest['actions']}

    def first(self, group):
        return self.directory / self.groups[group][0]['file']

    def paint(self, canvas, group, elapsed, box):
        frames = self.groups[group]
        start = frames[0]['started']
        # Extra time is a reading hold, never accelerated app processing.
        source_ms = start + max(0, elapsed - .35) * 1000
        selected = next((f for f in reversed(frames) if f['started'] <= source_ms), frames[0])
        image = fitted_frame(self.directory / selected['file'], box[2], box[3])
        x = box[0] + (box[2] - image.width) // 2
        y = box[1] + (box[3] - image.height) // 2
        canvas.paste(image, (x, y))
        action = self.actions[group]
        click_at = .35 + (action['at'] - start) / 1000
        since_click = elapsed - click_at
        if action['action'] == 'click' and 0 <= since_click < .55:
            rect = action['rect']
            original_width, original_height = ((430, 900) if group.startswith('phone') else (1280, 720))
            cx = x + (rect['x'] + rect['width'] / 2) * image.width / original_width
            cy = y + (rect['y'] + rect['height'] / 2) * image.height / original_height
            radius = 15 + since_click * 22
            draw = ImageDraw.Draw(canvas, 'RGBA')
            draw.ellipse((cx - radius, cy - radius, cx + radius, cy + radius),
                         outline=(157, 59, 45, round(220 * (1 - since_click / .55))), width=3)
        return canvas

    def paint_scene(self, canvas, scene, elapsed):
        if scene == 3:
            group, local = ('pc-city', elapsed) if elapsed < 3.4 else ('pc-revisit', elapsed - 3.4)
            return self.paint(canvas, group, local, (430, 205, 1400, 740))
        if scene == 4:
            group, local = ('phone-open', elapsed) if elapsed < 2.4 else ('phone-scroll', elapsed - 2.4)
            return self.paint(canvas, group, local, (1285, 205, 500, 740))
        return canvas
