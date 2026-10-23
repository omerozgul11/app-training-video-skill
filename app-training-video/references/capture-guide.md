# Capture guide: filming the app

The capture script drives the real application in a headless Chromium with real pointer events and
records Chrome's screencast frames. These lessons come from producing several releases of a product
training video. They are the difference between a watchable video and one that has to be redone.

## Before filming
- **Fresh state, demo data only.** Start the app with a new, empty data folder (or a demo account), and
  use bundled or synthetic example files. No customer data, real e-mail addresses, tokens or internal
  URLs may appear in a frame.
- **Close first-run noise deliberately.** If a welcome dialog, cookie banner or tour appears, film it on
  purpose (it is useful) or dismiss it before `rec.open()` finishes. Never leave it to chance.
- **Viewport 1920 × 960.** The renderer adds a 120-px caption band below, giving 1920 × 1080. Keep the
  app's own text readable at this size; zoom the page with CSS only if the UI is tiny.
- **Starting the app from the script.** `launch(command, ready=...)` waits for the app's "listening on"
  line. Run Python servers unbuffered (`python -u`), or the line stays in a buffer and the launch times out.
- **Narrate first.** `narrate.py` must run before capturing, because each segment's length comes from
  its narration.

## Finding controls reliably
- Prefer `page.get_by_role('button', name='Save')` and `get_by_label('Title')`. They follow what users
  see and survive restyling.
- **Duplicate names break scripts.** If the same button appears in a toolbar and a side panel, scope it:
  `page.locator('.toolbar').get_by_role('button', name='Save')`. Playwright's strict mode refuses
  ambiguous matches.
- Help icons, tooltips and "i" buttons often carry an `aria-label` that contains the setting's name. A
  plain `get_by_label('Gain')` can then match the icon too. Use the role
  (`get_by_role('checkbox', name='Gain')`) or `exact=True`.
- To click inside a plot or canvas, compute screen coordinates from the chart's own data (for Plotly:
  `_fullLayout.xaxis.d2p`). Don't hard-code pixels.

## Pacing
- `with rec.segment('id'):` holds the picture until the narration has finished. So act first, then let
  the recorder wait. Don't add sleeps to "fill" time.
- Wrap every wait for the app (calculations, uploads, reports, page loads) in `with rec.cut():` and wait
  inside it for a **visible result** (`expect(...).to_be_visible(timeout=...)`), never a fixed time.
  The cut is removed from the video, so a 40-second calculation appears instant.
- Move the cursor to whatever the voice is describing (`rec.hover(locator, seconds)`) and park it
  (`rec.park()`) when nothing is happening, so it never covers the content being explained.
- Type visibly with `rec.type(locator, text)` when typing is part of the lesson; use `locator.fill()`
  when it is not.
- Let results settle on screen for a second before the segment ends: viewers need time to read.

## When something fails
- The script stops at the first failure and `capture.json` is marked incomplete; `render.py` refuses
  to use it. Fix the step, empty `frames/`, and re-run the capture. Narration is reused.
- An error banner or a page error (`pageerror`) also fails the capture. Fix the cause; don't film around it.
- After any interface change (renamed buttons, moved panels, new dialogs), re-run capture and render,
  then **look at the contact sheet** from `review.py`. Selectors may still match while showing the wrong screen.

## Desktop applications
Apps whose window is a web view (Electron, Tauri, Qt WebEngine, a local web server with a native shell)
are filmed through their web UI: start the app's local server or dev build and open its URL with
`rec.open()`. A purely native UI cannot be driven this way. Use a screen recorder for those frames, then
reuse narrate.py and the card and caption parts of render.py.
