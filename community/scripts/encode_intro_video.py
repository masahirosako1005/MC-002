"""Trim the real recording at its caption's first visible frame, then verify H.264 output."""
from pathlib import Path
import hashlib
import json
import re
import subprocess
import sys

import imageio_ffmpeg
from PIL import Image,ImageDraw,ImageFont

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'community/artifacts/intro-video'
TARGET=ROOT/'outputs/community-intro.mp4'
FFMPEG=imageio_ffmpeg.get_ffmpeg_exe()


def run(args):
    result=subprocess.run([FFMPEG,'-hide_banner',*args],capture_output=True)
    if result.returncode:
        raise RuntimeError(result.stderr.decode('utf-8','replace')[-1800:])
    return result


def main():
    source=Path(sys.argv[1]).resolve()
    if not source.is_relative_to(ROOT):
        raise ValueError('Recording must stay inside the workspace')
    OUT.mkdir(parents=True,exist_ok=True);TARGET.parent.mkdir(parents=True,exist_ok=True)
    # The opaque caption background is an existing visible annotation, not a
    # hidden timing marker. Sample the same pixel at 30 fps before trimming.
    pixels=run(['-i',str(source),'-vf','fps=30,crop=2:2:270:30,scale=1:1','-pix_fmt','rgb24','-f','rawvideo','pipe:1']).stdout
    matching=[]
    for index in range(len(pixels)//3):
        pixel=pixels[index*3:index*3+3]
        if all(abs(value-reference)<24 for value,reference in zip(pixel,(111,48,36))):
            matching.append(index)
    if not matching:
        raise RuntimeError('Visible caption start could not be identified')
    matched=set(matching)
    first=next((i for i in matching if all(j in matched for j in range(i,i+12))),None)
    if first is None:
        raise RuntimeError('No stable caption opening')
    start=first/30
    filters=f'trim=start={start:.6f}:duration=20,setpts=PTS-STARTPTS,fps=30,setsar=1,fade=t=in:st=0:d=0.15,fade=t=out:st=19.7:d=0.3'
    run(['-y','-i',str(source),'-t','20','-vf',filters,'-an','-c:v','libx264','-preset','medium','-crf','18','-pix_fmt','yuv420p','-movflags','+faststart',str(TARGET)])
    decoded=run(['-i',str(TARGET),'-map','0:v:0','-progress','pipe:1','-f','null','-'])
    info=decoded.stderr.decode('utf-8','replace')
    progress=decoded.stdout.decode('utf-8','replace')
    frames=int(re.findall(r'^frame=(\d+)',progress,re.M)[-1])
    duration_match=re.search(r'Duration: (\d+):(\d+):(\d+\.\d+)',info)
    if not duration_match:
        raise RuntimeError('Encoded duration missing')
    h,m,s=map(float,duration_match.groups());duration=h*3600+m*60+s
    assert 19<=duration<=21 and frames==600,(duration,frames)
    assert 'h264' in info and '1440x900' in info and '30 fps' in info and 'Audio:' not in info
    images=[]
    for index,seconds in enumerate((.8,5.5,9.7,12.6,15,18.3)):
        filename=OUT/f'frame-{index+1:02}.png'
        run(['-y','-ss',str(seconds),'-i',str(TARGET),'-frames:v','1',str(filename)])
        image=Image.open(filename).convert('RGB');image.thumbnail((720,450));images.append((seconds,image))
    sheet=Image.new('RGB',(1440,3*486),'#e8ded0');draw=ImageDraw.Draw(sheet)
    font_path=Path('C:/Windows/Fonts/meiryo.ttc')
    font=ImageFont.truetype(str(font_path),21) if font_path.exists() else ImageFont.load_default()
    for index,(seconds,image) in enumerate(images):
        x=(index%2)*720;y=(index//2)*486
        sheet.paste(image,(x,y));draw.text((x+18,y+456),f'{seconds:.1f} 秒',font=font,fill='#39271f')
    sheet.save(OUT/'contact-sheet.jpg',quality=93)
    Image.open(OUT/'frame-02.png').save(ROOT/'outputs/community-intro-poster.png')
    report=dict(output=str(TARGET.relative_to(ROOT)).replace('\\','/'),duration_seconds=duration,decoded_frames=frames,width=1440,height=900,fps=30,codec='H.264',pixel_format='yuv420p',audio=False,fade_in_seconds=.15,fade_out_seconds=.3,trim_start_seconds=start,source=str(source.relative_to(ROOT)).replace('\\','/'),sha256=hashlib.sha256(TARGET.read_bytes()).hexdigest(),bytes=TARGET.stat().st_size,ffmpeg=imageio_ffmpeg.get_ffmpeg_version(),visual_review='pending',proof='Full output decoded with FFmpeg; 600 frames and header dimensions/duration checked. Raw footage is not sped up or synthesized.')
    (OUT/'verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({key:report[key] for key in ('output','duration_seconds','decoded_frames','width','height','bytes')}))


if __name__=='__main__':
    main()
