"""Capture script template: copy it next to your storyboard, then write one `with rec.segment(...)` block
per filmed storyboard segment (intro/outro cards are drawn by render.py and are not filmed).

    python capture.py storyboard.json

Rules that keep the video watchable (see references/capture-guide.md):
- Use a fresh, empty data folder and demo data only - never customer data, accounts or secrets.
- Find controls by role and accessible name (get_by_role), scoped to a region when names repeat.
- Wrap anything slow in rec.cut() and wait for a visible result inside it, never for a fixed time.
- Move the cursor to what the narration talks about (rec.hover) and park it when idle (rec.park()).
"""
import sys
from pathlib import Path
SKILL_SCRIPTS = Path(__file__).resolve().parent  # edit if this copy lives elsewhere
sys.path.insert(0, str(SKILL_SCRIPTS))
from playwright.sync_api import expect
from recorder import Recorder, launch, stop

APP = None
try:
    # Option A: the app is already running (dev server, staging site). Option B: start it here, e.g.
    # APP, URL = launch(['python', 'serve.py', '--port', '0', '--data-dir', '/tmp/demo-data'], ready=r'(http://127\.0\.0\.1:\d+)')
    URL = 'http://127.0.0.1:8000'
    with Recorder(sys.argv[1] if len(sys.argv) > 1 else 'storyboard.json') as rec:
        page = rec.open(URL)

        with rec.segment('overview'):              # ids must match the storyboard
            rec.hover(page.get_by_role('navigation'), 2)
            rec.park()

        with rec.segment('create'):
            rec.click(page.get_by_role('button', name='New item'))
            rec.type(page.get_by_label('Title'), 'Site visit report')
            with rec.cut():                         # slow server work is removed from the video
                rec.click(page.get_by_role('button', name='Save'))
                expect(page.get_by_text('Saved')).to_be_visible(timeout=120_000)
            rec.park()
finally:
    stop(APP)
