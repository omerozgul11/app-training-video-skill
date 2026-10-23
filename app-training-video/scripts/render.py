"""Assemble the finished training video: 1920 x 1080 H.264/AAC MP4 with a caption band, title/chapter/outro
cards and the narration, plus an .srt subtitle file, a chapter list (YouTube format) and a poster image.

    python render.py storyboard.json

Inputs: audio/ from narrate.py and frames/ + capture.json from the capture script.
Branding comes from the storyboard's "brand" block (company, product, tagline, subtitle, accent, logo, outro).
"""
from pathlib import Path
import bisect, json, subprocess
import numpy as np
import soundfile as sf
import imageio_ffmpeg
from PIL import Image, ImageDraw, ImageFont
from common import FONTS, load, written, sentences

story, story_path, OUT = load()
brand = story.get('brand', {})
FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
W, H, FPS = 1920, 1080, 30
REN = OUT / 'render'; REN.mkdir(exist_ok=True)
capture = json.loads((OUT / 'capture.json').read_text())
assert capture['status'] == 'passed', 'The capture did not finish cleanly; fix and re-run it first.'
UI_H = capture['size'][1]; BAND = H - UI_H
assert capture['size'][0] == W and BAND >= 100, 'Capture at 1920 x 960 (Recorder default) for the caption band.'
frames = capture['frames']; stamps = [f[0] for f in frames]
audio = {a['id']: a for a in json.loads((OUT / 'audio/manifest.json').read_text())}
CHAPTER_CARD, LEAD_IN = float(story.get('chapter_card_seconds', 2.4)), 0.25


def rgb(value, default):
    value = (value or default).lstrip('#'); return tuple(int(value[i:i + 2], 16) for i in (0, 2, 4))
ACCENT = rgb(brand.get('accent'), 'f26522')
WHITE, MUTED, INK = (245, 246, 248), (168, 177, 191), (18, 21, 27)


def font(size, weight=500):
    return ImageFont.truetype(str(FONTS / f'Inter-{weight}.ttf'), size)


def wrap(draw, text, f, width):
    rows, row = [], ''
    for word in text.split():
        candidate = (row + ' ' + word).strip()
        if row and draw.textlength(candidate, font=f) > width: rows.append(row); row = word
        else: row = candidate
    return rows + ([row] if row else [])


def caption_chunks(text):
    """Sentences, split further at commas so every caption fits on two lines."""
    probe = ImageDraw.Draw(Image.new('RGB', (10, 10))); f = font(31); out = []
    for s in sentences(text):
        if len(wrap(probe, s, f, 1500)) <= 2: out.append(s); continue
        cur = ''
        for part in [p.strip() for p in s.split(', ')]:
            candidate = (cur + ', ' + part) if cur else part
            if cur and len(wrap(probe, candidate, f, 1500)) > 2: out.append(cur + ','); cur = part
            else: cur = candidate
        out.append(cur)
    return out


def band(chapter, text):
    img = Image.new('RGB', (W, BAND), INK); d = ImageDraw.Draw(img)
    d.rectangle([0, 0, W, 3], fill=ACCENT)
    if chapter: d.text((40, 12), written(story, chapter).upper(), font=font(16, 700), fill=ACCENT)
    rows = wrap(d, text, font(31), 1500) if text else []
    y = 38 + (2 - len(rows)) * 20
    for row in rows:
        d.text(((W - d.textlength(row, font=font(31))) / 2, y), row, font=font(31), fill=WHITE); y += 40
    return img


def background():
    top, bottom = np.array([17, 20, 27.]), np.array([33, 38, 49.])
    mix = np.linspace(0, 1, H)[:, None, None]
    return Image.fromarray(np.broadcast_to(top * (1 - mix) + bottom * mix, (H, W, 3)).astype(np.uint8).copy())


def logo(img, cx, y, side):
    path = brand.get('logo')
    if not path: return 0
    path = Path(path) if Path(path).is_absolute() else story_path.parent / path
    mark = Image.open(path).convert('RGBA'); mark.thumbnail((side * 3, side), Image.Resampling.LANCZOS)
    img.paste(mark, (cx - mark.width // 2, y), mark); return mark.height


def card(kind, chapter=''):
    img = background(); d = ImageDraw.Draw(img)
    def centre(text, y, size, weight=500, fill=WHITE):
        if text:
            f = font(size, weight); d.text(((W - d.textlength(text, font=f)) / 2, y), text, font=f, fill=fill)
    if kind == 'intro':
        logo(img, W // 2, 170, 120)
        centre(brand.get('company', ''), 310, 40, 700)
        centre(brand.get('product', story.get('title', '')), 400, 96, 700)
        centre(brand.get('tagline', ''), 530, 38, 500, MUTED)
        centre(brand.get('subtitle', ''), 600, 26, 500, ACCENT)
    elif kind == 'outro':
        logo(img, W // 2, 140, 100)
        centre(brand.get('product', story.get('title', '')), 270, 72, 700)
        y = 380
        for i, line in enumerate(brand.get('outro', [])):
            centre(line, y, 34 if i == 0 else 32 if i == 1 else 30, 600 if i == 0 else 500, ACCENT if i == 0 else WHITE if i == 1 else MUTED)
            y += 52 if i else 52
    else:
        text = written(story, chapter)
        number, title = text.split(' · ', 1) if ' · ' in text else ('', text)
        if number: centre(f'CHAPTER {number}', 380, 30, 700, ACCENT)
        centre(title, 430, 76, 700)
        d.rectangle([W // 2 - 60, 545, W // 2 + 60, 549], fill=ACCENT)
    return img.crop((0, 0, W, UI_H)) if kind != 'chapter' else img


def run(args, label):
    result = subprocess.run([FFMPEG, '-hide_banner', '-nostdin', '-y', *args], capture_output=True, text=True)
    (REN / f'{label}.log').write_text(result.stderr)
    if result.returncode: raise RuntimeError(label + ': ' + result.stderr[-3000:])


def frame_list(start, end, cuts):
    """(file, seconds) pairs covering [start, end) minus the cut intervals."""
    spans, t = [], start
    for a, b in sorted(cuts):
        if a > t: spans.append((t, a))
        t = max(t, b)
    if end > t: spans.append((t, end))
    items = []
    for a, b in spans:
        i = max(0, bisect.bisect_right(stamps, a) - 1); t = a
        while t < b:
            nxt = stamps[i + 1] if i + 1 < len(stamps) else b
            stop = min(max(nxt, t), b)
            if stop > t: items.append((frames[i][1], stop - t))
            t = stop; i += 1
            if i >= len(frames): break
    return items


def encode(sid, video_args, captions, duration, chapter):
    """`duration` seconds: the UI (or a card) on top, the caption band below with timed captions."""
    inputs, filters = list(video_args), []
    blank = REN / f'{sid}-band-0.png'; band(chapter, '').save(blank)
    inputs += ['-loop', '1', '-t', f'{duration:.3f}', '-i', str(blank)]
    base = len([a for a in video_args if a == '-i'])
    filters.append(f'[0:v]fps={FPS},scale={W}:{UI_H}:flags=lanczos,setsar=1,tpad=stop_mode=clone:stop_duration={duration:.3f},trim=duration={duration:.3f}[ui]')
    filters.append(f'[ui]pad={W}:{H}:0:0[v0]')
    filters.append(f'[v0][{base}:v]overlay=0:{UI_H}[c0]')
    last = 'c0'
    for k, (a, b, text) in enumerate(captions, 1):
        png = REN / f'{sid}-band-{k}.png'; band(chapter, text).save(png)
        inputs += ['-loop', '1', '-t', f'{duration:.3f}', '-i', str(png)]
        filters.append(f"[{last}][{base + k}:v]overlay=0:{UI_H}:enable='between(t,{a:.3f},{b:.3f})'[c{k}]"); last = f'c{k}'
    out = REN / f'{sid}.mp4'
    run([*inputs, '-filter_complex', ';'.join(filters), '-map', f'[{last}]', '-t', f'{duration:.3f}', '-r', str(FPS),
         '-c:v', 'libx264', '-preset', 'medium', '-crf', '17', '-pix_fmt', 'yuv420p', '-an', str(out)], sid)
    return out


def timed_captions(sid, offset):
    """Captions follow the voice: each chunk gets screen time in proportion to its length."""
    spoken = audio[sid]['seconds']; chunks = caption_chunks(audio[sid]['caption'])
    weights = np.array([len(c) for c in chunks], float); weights /= weights.sum()
    edges = offset + np.concatenate([[0], np.cumsum(weights)]) * spoken
    return [(edges[i], edges[i + 1] + (0.4 if i == len(chunks) - 1 else 0), c) for i, c in enumerate(chunks)]


clips, track, srt, chapters, timeline, clock = [], [], [], [], [], 0.0
rate = sf.info(str(OUT / 'audio' / audio[story['segments'][0]['id']]['file'])).samplerate
for seg in story['segments']:
    sid, chapter = seg['id'], seg.get('chapter', '')
    if seg.get('card') == 'chapter':
        png = REN / f'{sid}-chapter.png'; card('chapter', chapter).save(png)
        out = REN / f'{sid}-chapter.mp4'
        run(['-loop', '1', '-t', f'{CHAPTER_CARD}', '-i', str(png), '-vf', f'fps={FPS},format=yuv420p', '-c:v', 'libx264',
             '-crf', '17', '-pix_fmt', 'yuv420p', '-an', str(out)], f'{sid}-chapter')
        chapters.append((clock, written(story, chapter))); clips.append(out); clock += CHAPTER_CARD
    spoken = audio[sid]['seconds']
    if seg.get('card') in ('intro', 'outro'):
        duration = spoken + LEAD_IN + 1.6
        png = REN / f'{sid}-card.png'; card(seg['card']).save(png)
        video_args = ['-loop', '1', '-t', f'{duration:.3f}', '-i', str(png)]
        if seg['card'] == 'intro': chapters.append((clock, 'Introduction'))
    else:
        s = capture['segments'][sid]
        items = frame_list(s['start'], s['end'], s['cuts'])
        assert items, f'{sid}: no frames captured'
        listing = REN / f'{sid}-frames.txt'
        listing.write_text(''.join(f"file '{OUT / 'frames' / name}'\nduration {d:.4f}\n" for name, d in items) +
                           f"file '{OUT / 'frames' / items[-1][0]}'\n")
        duration = max(sum(d for _, d in items), spoken + LEAD_IN + 0.6)
        video_args = ['-f', 'concat', '-safe', '0', '-i', str(listing)]
    captions = timed_captions(sid, LEAD_IN)
    clips.append(encode(sid, video_args, captions, duration, chapter))
    timeline.append({'id': sid, 'start': round(clock, 3), 'end': round(clock + duration, 3)})
    track.append((clock + LEAD_IN, OUT / 'audio' / audio[sid]['file']))
    srt += [(clock + a, clock + b, c) for a, b, c in captions]
    clock += duration
    print(f'{sid:<16} {duration:5.1f} s   total {clock:6.1f} s', flush=True)

mix = np.zeros(int((clock + 0.5) * rate), dtype=np.float32)
for at, path in track:
    data, r = sf.read(str(path), dtype='float32'); assert r == rate
    i = int(at * rate); mix[i:i + len(data)] += data[: len(mix) - i]
sf.write(str(REN / 'narration.wav'), mix, rate, subtype='PCM_16')

listing = REN / 'clips.txt'; listing.write_text(''.join(f"file '{c}'\n" for c in clips))
name = brand.get('output_name') or story.get('title', 'training-video').replace(' ', '-')
final = OUT / f'{name}.mp4'
run(['-f', 'concat', '-safe', '0', '-i', str(listing), '-i', str(REN / 'narration.wav'), '-map', '0:v', '-map', '1:a',
     '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k', '-ar', '48000', '-af', 'loudnorm=I=-16:TP=-1.5:LRA=11',
     '-shortest', '-movflags', '+faststart', str(final)], 'final')


def ts(t, sep=','):
    h, rem = divmod(t, 3600); m, s = divmod(rem, 60)
    return f'{int(h):02d}:{int(m):02d}:{int(s):02d}{sep}{int(round((s % 1) * 1000)) % 1000:03d}'
(OUT / f'{name}.srt').write_text(''.join(f'{i}\n{ts(a)} --> {ts(b)}\n{c}\n\n' for i, (a, b, c) in enumerate(srt, 1)))
(OUT / f'{name}-timeline.json').write_text(json.dumps(timeline, indent=1) + '\n')
(OUT / f'{name}-chapters.txt').write_text(''.join(f'{ts(t)[3:8] if t < 3600 else ts(t)[:8]} {title}\n' for t, title in chapters))
poster = background(); poster.paste(card('intro'), (0, (H - UI_H) // 2)); poster.save(OUT / f'{name}-poster.jpg', quality=92)
print(f'VIDEO {final}  {clock:.1f} s  {final.stat().st_size / 1e6:.1f} MB')
