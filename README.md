# app-training-video: a Claude skill for narrated software training videos

A [Claude](https://claude.com/claude-code) skill from QuakeLogic that produces a **narrated, captioned
training or walkthrough video of a real application**. It drives the app in a browser, records it
paced to an offline AI voice-over, and renders a ready-to-publish 1080p MP4.

It is the method used for the MASW Studio training video, generalised for any web app or desktop app
with a web UI (Electron, Tauri, Qt WebEngine, local web servers).

## What you get

- **Narration** from a storyboard, spoken by the offline Kokoro voice. No cloud service, account or cost.
- **Screen capture** of the real app with real mouse movement, a visible cursor and click ripples.
  Every segment is held until its narration ends, and long waits (calculations, uploads) are cut out.
- **Title, chapter and closing cards** with your branding: company, product, logo, accent colour and contacts.
- **Burned-in captions**, plus an `.srt` subtitle file, a YouTube chapter list and a poster image.
- **A review contact sheet**: one frame per segment, to check before publishing.

## Install

### Option A: the packaged skill
Download [`dist/app-training-video.skill`](dist/app-training-video.skill) (or the file attached to
the [latest release](../../releases/latest)).
- **Claude.ai / Claude desktop:** upload it under *Settings → Capabilities → Skills*.
- **Claude Code:** unzip it into your skills folder: `unzip app-training-video.skill -d ~/.claude/skills/`

### Option B: from this repository (Claude Code)
```bash
git clone <this repo> && cp -r app-training-video-skill/app-training-video ~/.claude/skills/
```
Restart Claude Code. The skill is listed as `app-training-video`.

### First-time setup (done by Claude when the skill first runs)
`app-training-video/scripts/setup.sh` creates `~/.cache/app-training-video/` (override with
`TRAINING_VIDEO_HOME`) containing:
- a private Python environment;
- the voice model (~350 MB);
- the Inter font;
- Chromium.

Every download is SHA-256 checked. It needs **Python 3.10–3.13** and internet access once; nothing is
installed system-wide. On Windows, run it in WSL or Git Bash.

## Use

Ask Claude, for example:

> Make a 5-minute training video of our app at http://localhost:3000 showing how to create a project
> and export a report. Use our logo (logo.png) and the accent colour #f26522.

Claude will:
1. plan the chapters and narration with you;
2. narrate them;
3. write and run the capture script;
4. render the video and show you the contact sheet.

After an interface change, ask it to re-record. The storyboard and capture script are kept, so only
capture and render run again.

## Contents

| Path | Purpose |
|---|---|
| `app-training-video/SKILL.md` | The workflow Claude follows |
| `app-training-video/scripts/setup.sh` | One-time environment, voice, font and browser setup |
| `app-training-video/scripts/narrate.py` | Speaks the storyboard (Kokoro, offline) |
| `app-training-video/scripts/recorder.py` | Playwright recorder: cursor, pacing to narration, cuts |
| `app-training-video/scripts/capture_template.py` | Starting point for an app's capture script |
| `app-training-video/scripts/render.py` | Cards, caption band, narration mix, MP4/SRT/chapters/poster |
| `app-training-video/scripts/review.py` | Stream checks and the review contact sheet |
| `app-training-video/references/` | Storyboard format and capture lessons |
| `app-training-video/assets/storyboard.example.json` | Example storyboard |
| `dist/app-training-video.skill` | The packaged skill |

## Third-party components

These are downloaded at setup, not included here:
- the Kokoro voice model ([kokoro-onnx](https://github.com/thewh1teagle/kokoro-onnx), Apache-2.0);
- the [Inter](https://github.com/rsms/inter) typeface (SIL Open Font License 1.1);
- Playwright/Chromium and ffmpeg (via imageio-ffmpeg), under their own licences.

© QuakeLogic Inc.
