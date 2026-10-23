# Storyboard reference

The storyboard (`storyboard.json`) is the single source for the narration, the captions, the chapters
and the branding. Everything else is generated from it.

## Top-level fields

| Field | Meaning |
|---|---|
| `title` | Fallback product name and output file name |
| `output_dir` | Build folder, relative to the storyboard (audio/, frames/, render/ and the results) |
| `voice`, `voice_language`, `voice_speed` | Kokoro voice. `af_heart` (US English, female) is clear and warm; `am_michael` and `bm_george` are good male voices; 0.95–1.05 speed |
| `brand` | `company`, `product`, `tagline`, `subtitle` (version line), `accent` (hex), `logo` (PNG with transparency, relative path), `outro` (lines: the first is highlighted, the second is white, the rest are grey), `output_name` (file name without extension) |
| `caption_replacements` | `[regex, written form]` pairs that turn the spoken spelling into the caption text |
| `chapter_card_seconds` | Optional, default 2.4 |
| `segments` | The video, in order |

## Segments

```json
{"id": "pick", "chapter": "4 · Dispersion and picking", "card": "chapter", "speech": "..."}
```

- `id`: unique, short, used to name files and to match `rec.segment('id')` in the capture script.
- `chapter`: shown in the caption band, written as `"<number> · <title>"`. Repeat it on every segment of the chapter.
- `card`:
  - `"intro"` and `"outro"`: drawn title and closing cards, not filmed;
  - `"chapter"`: a 2.4-second chapter card is shown before this filmed segment;
  - omit it for ordinary filmed segments.
- `speech`: what the voice says. Captions are made from it.

## Writing the narration

- **One idea per segment, 10–35 seconds** (about 25–80 words). The voice speaks about 2.6 words per
  second. Longer segments are hard to film in one take; shorter ones feel choppy.
- **Say what is on screen, in the order it happens.** The viewer hears "choose Save" while the cursor
  moves to Save. Name buttons exactly as they are labelled.
- **Spell for the voice, not the eye.** The voice mispronounces acronyms, file extensions and unit
  symbols. Write them out in `speech` and add a `caption_replacements` rule so the captions stay correct.
  - "S Q L" → SQL
  - "dot C S V" → .csv
  - "V s 30" → Vs30
  - "two D" → 2D
  - "twenty four channel" → 24-channel
  - Spell product names the way they are said: "Quake Logic" → QuakeLogic.
- Short sentences. Commas split long captions; each caption shows two lines at most.
- The first segment is the promise (what the viewer will be able to do). The last is where to get help.
- Use only demo or synthetic data, and say so if it could be mistaken for real results.

## Typical shape (6–7 minutes)

intro → getting started (layout, help) → importing or creating data → the core workflow, one chapter
per main screen → results and export → library/projects → help and support → outro.
About 25 segments in 8–9 chapters.
