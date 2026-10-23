"""Quality check of the finished video: stream facts plus a contact sheet to look at before publishing.

    python review.py storyboard.json

Prints duration, resolution, audio presence and file size, checks the video against the narration, and
writes <name>-review.jpg: one still per segment (taken mid-segment), labelled with its id, so a wrong
screen, a stray dialog, an error banner or an unreadable caption is visible at a glance.
"""
import json, re, subprocess
import imageio_ffmpeg
from PIL import Image, ImageDraw, ImageFont
from common import FONTS, load

story, _, OUT = load()
brand = story.get('brand', {})
name = brand.get('output_name') or story.get('title', 'training-video').replace(' ', '-')
video = OUT / f'{name}.mp4'
FF = imageio_ffmpeg.get_ffmpeg_exe()
info = subprocess.run([FF, '-hide_banner', '-i', str(video)], capture_output=True, text=True).stderr
h, m, s = re.search(r'Duration: (\d+):(\d+):([\d.]+)', info).groups()
seconds = int(h) * 3600 + int(m) * 60 + float(s)
size = re.search(r'Video: .*?(\d{3,5})x(\d{3,5})', info).groups()
spoken = sum(a['seconds'] for a in json.loads((OUT / 'audio/manifest.json').read_text()))
timeline = json.loads((OUT / f'{name}-timeline.json').read_text())
facts = {'video': str(video), 'seconds': round(seconds, 1), 'resolution': 'x'.join(size), 'audio': 'Audio:' in info,
         'megabytes': round(video.stat().st_size / 1e6, 1), 'narration_seconds': round(spoken, 1),
         'captions': (OUT / f'{name}.srt').read_text().count(' --> '), 'segments': len(timeline)}
print(json.dumps(facts, indent=1))
problems = [p for p, bad in [('no audio stream', not facts['audio']), ('not 1920x1080', size != ('1920', '1080')),
                              ('video shorter than the narration', seconds + 0.5 < spoken),
                              ('segments missing from the video', len(timeline) != len(story['segments']))] if bad]
thumbs = []
for seg in timeline:
    png = OUT / 'render' / f"review-{seg['id']}.png"
    t = (seg['start'] + seg['end']) / 2
    subprocess.run([FF, '-hide_banner', '-nostdin', '-y', '-ss', f'{t:.2f}', '-i', str(video), '-frames:v', '1',
                    '-vf', 'scale=480:-1', str(png)], capture_output=True)
    if png.exists(): thumbs.append((f"{seg['id']}  @{int(t // 60)}:{t % 60:04.1f}", Image.open(png).convert('RGB')))
if thumbs:
    w, hh = thumbs[0][1].size; cols = 4; rows = (len(thumbs) + cols - 1) // cols
    sheet = Image.new('RGB', (cols * w, rows * (hh + 28)), 'white'); d = ImageDraw.Draw(sheet)
    f = ImageFont.truetype(str(FONTS / 'Inter-600.ttf'), 18)
    for k, (label, im) in enumerate(thumbs):
        x, y = (k % cols) * w, (k // cols) * (hh + 28)
        sheet.paste(im, (x, y + 28)); d.text((x + 8, y + 4), label, font=f, fill='black')
    out = OUT / f'{name}-review.jpg'; sheet.save(out, quality=85); print('contact sheet:', out)
print('PROBLEMS: ' + '; '.join(problems) if problems else 'OK: streams and length look right. Now look at the contact sheet.')
