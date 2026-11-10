"""Generate public video narration; never used by the offline application.

Only the explicitly authored narration below is sent to the speech service.
No application data, source code, photographs, conversations, or keys are sent.
Development dependency: edge-tts==7.3.1, https://github.com/rany2/edge-tts.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
from pathlib import Path

import edge_tts

ROOT = Path(__file__).resolve().parents[1]
DESTINATION = ROOT / 'artifacts/video-revisit/v13/neural-nanami-01'
NARRATION = [
    ('intro', '利用者には、講を感じる和の画面。事業者には、数字が読みやすい管理画面。では、ログインして使ってみましょう。'),
    ('photo', '写真から、タグの候補が出てきます。合うものを選んで、次の仲間探しに。'),
    ('match', '同じコミュニティから、共通の趣味を持つ仲間を提案。気になる人を選んで、誘えます。'),
    ('select', '行きたい場所は、自分たちで選びます。事業者を講に招いて、ここから直接相談。'),
    ('chat', '人数や日程、行程に見積もり。あちこち連絡せず、同じ場所で話せるのがうれしいですね。'),
    ('reflection', 'よかったことも、気になったことも。同意した旅の振り返りを、事業者選びの参考に。'),
    ('program', '事業者からは、次の絵付けのお誘いが。作って、色を付けて、受け取る。何度か通う楽しみが、次に訪れる理由になります。'),
    ('closing', '仲間探しと旅先との相談を、講でまとめましょう。'),
]


async def generate(index, kind, text, semaphore):
    async with semaphore:
        path = DESTINATION / f'voice-{index:02}.mp3'
        if path.exists():
            raise FileExistsError('Preserve previous recordings; use a new take.')
        # Kana fixes the product name pronunciation without changing the subtitle.
        spoken = text.replace('講', 'こう')
        request = edge_tts.Communicate(spoken, 'ja-JP-NanamiNeural', rate='+0%',
                                       pitch='-2Hz', volume='+0%')
        await request.save(str(path))
        result = {'index': index, 'kind': kind, 'text': text, 'spoken_text': spoken,
                  'path': path.relative_to(ROOT).as_posix(),
                  'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
        print(f'Generated {index + 1}/8: {kind}', flush=True)
        return result


async def main():
    DESTINATION.mkdir(parents=True, exist_ok=True)
    semaphore = asyncio.Semaphore(2)
    scenes = await asyncio.gather(*(generate(i, kind, text, semaphore)
                                   for i, (kind, text) in enumerate(NARRATION)))
    report = {'voice': 'ja-JP-NanamiNeural', 'rate': '+0%', 'pitch': '-2Hz',
              'post_generation_speed_change': False, 'dependency': 'edge-tts==7.3.1',
              'scope': 'Development-time public narration only. Application remains offline MOC.',
              'source': 'https://github.com/rany2/edge-tts', 'scenes': scenes}
    (DESTINATION / 'manifest.json').write_text(json.dumps(report, ensure_ascii=False, indent=2),
                                             encoding='utf-8')


if __name__ == '__main__':
    asyncio.run(main())
