---
name: app-training-video
description: Produce a narrated, captioned training or walkthrough video of a software application by driving the real app in a browser and recording it - storyboard, offline AI voice-over, screen capture paced to the narration, chapter/title cards, burned-in captions, .srt subtitles, chapter list and poster, as a ready-to-publish 1080p MP4. Use this whenever someone wants a training video, tutorial video, product demo or walkthrough video, onboarding video, how-to video or "video showing how to use the app" for a web app, SaaS product, internal tool or desktop app with a web UI, or wants an existing training video re-recorded after the interface changed - even if they don't mention narration, captions or screen recording.
---

# App training video

Make a professional training video of a real application. The video is about 1920 × 1080 H.264 with
AAC narration. Each spoken sentence is captioned, every chapter opens with a card, and long waits are cut
out. It is reproducible: when the UI changes, re-run the capture and render and the video is current again.

How it works:
1. A **storyboard** holds the narration text, chapters and branding.
2. `narrate.py` speaks every segment with the offline **Kokoro** voice: no cloud service, no account, no cost.
3. A **capture script** drives the real app with Playwright (real mouse movement, a visible cursor
   and click ripples). It records Chrome's screencast frames and holds each segment until its narration ends.
4. `render.py` assembles the clips, cards, caption band and the loudness-normalised narration track.
5. `review.py` checks the result and builds a contact sheet to look at before anything is published.

Scripts are in `scripts/` next to this file. Read `references/storyboard.md` before writing the
narration and `references/capture-guide.md` before writing the capture script. Both hold lessons that
prevent the usual re-recordings.

## 0. One-time setup

```bash
bash <skill>/scripts/setup.sh
```
This creates `~/.cache/app-training-video/` (override with `TRAINING_VIDEO_HOME`) containing:
- a private Python 3.10–3.13 environment with pinned packages;
- the Kokoro voice model (~350 MB) and the Inter typeface, SHA-256 checked;
- Chromium.

Run every script with that environment's Python (`PY=~/.cache/app-training-video/venv/bin/python`) and
pass the storyboard path. If the model files already exist somewhere, run `MODEL_SOURCE=<dir>` first to
reuse them. ffmpeg comes bundled (imageio-ffmpeg); nothing is installed system-wide.

## 1. Understand the app and the audience

Before writing anything, use the app yourself (or read its user guide) and find out:
- **Who watches:** new customers, field staff, internal users.
- **The one workflow** they must master: from input to result.
- **What demo data** is safe to show.
- **How to start the app** in a clean state: URL or launch command, plus a fresh data folder or demo account.
- **Branding:** company name, product name, version, logo PNG, accent colour, contact lines for the outro.

Ask the user for anything you cannot find. Six to seven minutes is right for a full workflow, and
60–90 seconds for a single feature.

## 2. Write the storyboard

Copy `assets/storyboard.example.json` next to the project as `storyboard.json` and write it following
`references/storyboard.md`. In short:
- 10–35 seconds of speech per segment;
- chapters `"n · Title"`, with `card: "chapter"` on the first segment of each chapter;
- `intro` and `outro` cards;
- acronyms spelled for the voice, with `caption_replacements` restoring the written form.

Show the narration to the user before filming: it is cheap to change now and expensive later.

## 3. Narrate

```bash
$PY <skill>/scripts/narrate.py storyboard.json
```
It prints the length of every segment. It re-speaks only segments whose text changed. Listen to one
or two WAVs in `video-build/audio/` if pronunciation matters, adjust the spelling and run it again.

## 4. Write and run the capture script

Copy `scripts/capture_template.py` to `capture.py` beside the storyboard, set the path to the skill's
`scripts/`, and write one `with rec.segment('<id>'):` block per filmed segment, in storyboard order.
Inside it, perform exactly what the narration describes:
- `rec.click`, `rec.hover`, `rec.type`, `rec.drag`, `rec.scroll`, `rec.park`;
- `rec.cut()` around anything slow, waiting for a visible result.

The recorder refuses a non-empty `frames/` folder, so old frames are never mixed in.

```bash
$PY capture.py storyboard.json
```
Every segment prints its filmed length against its narration. The run fails (status `incomplete`) on
the first broken step, any page error or any segment that wasn't filmed. Fix the step, empty
`video-build/frames/`, and run it again.

## 5. Render and review

```bash
$PY <skill>/scripts/render.py storyboard.json
$PY <skill>/scripts/review.py storyboard.json
```
Outputs in the build folder:
- `<output_name>.mp4`
- `.srt` subtitles
- `-chapters.txt` (paste into a YouTube description)
- `-poster.jpg`
- `-timeline.json`
- `-review.jpg`: one still per segment.

**Open the contact sheet and look at it**, and spot-check the MP4 itself. Check for:
- the right screen in every segment;
- no error banners, empty plots or stray dialogs;
- the cursor never covering what is being explained;
- captions that read correctly.

Selectors can match while the screen is wrong, so this look is required before you call the video done.

## 6. Deliver

Give the user the MP4, the SRT (most players load it automatically when the names match) and the
chapter list. Mention the length and the size. To publish, upload the MP4 and SRT together. Keep
`storyboard.json` and `capture.py` with the project: after the next UI change, re-run steps 4–5 (and
step 3 if the wording changed).

## Troubleshooting

| Symptom | Fix |
|---|---|
| `Need Python 3.10–3.13` | Install python3.12, or set `PYTHON=` before running setup.sh |
| `launch()` times out although the app started | The app buffers its output: run Python servers with `python -u`, or check the `ready` regex |
| Chromium fails to start on Linux | `$PY -m playwright install --with-deps chromium` |
| Locator times out or matches two elements | Scope it to a region, or use `get_by_role` with `exact=True` (see the capture guide) |
| Segment much longer than its narration | Something slow is not inside `rec.cut()` |
| Wrong pronunciation | Respell it in `speech`, add a `caption_replacements` rule, re-run narrate.py |
| Captions out of sync | Caption timing follows the narration length: shorten long sentences, or split the segment |
