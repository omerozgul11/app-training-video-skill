"""Film a web (or browser-based desktop) application for a narrated training video.

Usage from a capture script (see capture_template.py):

    from recorder import Recorder, launch
    with Recorder('storyboard.json') as rec:
        page = rec.open('http://127.0.0.1:8000')
        with rec.segment('login'):
            rec.click(page.get_by_role('button', name='Sign in'))
        with rec.segment('report'):
            with rec.cut():                      # a long calculation: filmed, then cut out
                rec.click(page.get_by_role('button', name='Run report'))
                page.get_by_text('Report ready').wait_for(timeout=180_000)

How it works:
- Chrome's screencast stores every repaint as a sharp JPEG with its timestamp (no screen recorder, no blur).
- A visible arrow cursor and an orange click ripple are drawn into the page, because headless browsers
  have no cursor and viewers must see where to click.
- Real pointer movement (page.mouse) is used for every action, so hovers, tooltips and drags show.
- Each segment lasts at least as long as its narration (audio/manifest.json from narrate.py): when the
  actions finish early, the recorder holds the picture until the voice has finished.
- Time spent inside rec.cut() is removed when rendering, so waiting for calculations never shows.
- capture.json records frames, segment times and cuts for render.py.
"""
from pathlib import Path
import base64, contextlib, json, os, re, signal, subprocess, time
from playwright.sync_api import sync_playwright, expect
from common import load

CURSOR_JS = '''(accent) => {
  if (document.getElementById('film-cursor')) return;
  const c=document.createElement('div');c.id='film-cursor';
  c.innerHTML='<svg width="30" height="36" viewBox="0 0 29 34"><path d="M3 2L3 26L9 20L15 31L21 28L15 17L25 17Z" fill="white" stroke="#20232a" stroke-width="2"/></svg>';
  Object.assign(c.style,{position:'fixed',left:'0',top:'0',pointerEvents:'none',zIndex:'2147483647',transform:'translate(-60px,-60px)',filter:'drop-shadow(0 2px 3px #0005)'});
  document.body.append(c);
  document.addEventListener('mousemove',e=>c.style.transform=`translate(${e.clientX}px,${e.clientY}px)`,true);
  document.addEventListener('mousedown',e=>{const d=document.createElement('div');Object.assign(d.style,{position:'fixed',left:(e.clientX-22)+'px',top:(e.clientY-22)+'px',width:'44px',height:'44px',border:'3px solid '+accent,borderRadius:'50%',pointerEvents:'none',zIndex:'2147483646'});document.body.append(d);d.animate([{transform:'scale(.5)',opacity:1},{transform:'scale(1.5)',opacity:0}],{duration:600});setTimeout(()=>d.remove(),600)},true);
}'''


def launch(command, ready=r'https?://\S+', cwd=None, env=None, timeout=60):
    """Start a local app server and return (process, url). `ready` is a regex matched on its output;
    the first match (or group 1) is the URL. Give the app a fresh, empty data folder in `command`.
    Python servers must run unbuffered (`python -u ...`), or the ready line never arrives through the pipe."""
    proc = subprocess.Popen(command, cwd=cwd, env={**os.environ, **(env or {})}, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, text=True)
    deadline = time.time() + timeout
    while time.time() < deadline:
        line = proc.stdout.readline()
        if not line and proc.poll() is not None:
            raise RuntimeError(f'App exited before it was ready (code {proc.returncode})')
        m = re.search(ready, line or '')
        if m:
            return proc, (m.group(1) if m.groups() else m.group(0)).strip()
    proc.kill(); raise TimeoutError('App did not print a ready line matching ' + ready)


def stop(proc):
    if proc and proc.poll() is None:
        proc.send_signal(signal.SIGINT)
        try: proc.wait(timeout=20)
        except subprocess.TimeoutExpired: proc.terminate(); proc.wait(timeout=20)


class Recorder:
    def __init__(self, storyboard=None, width=1920, height=960, pad=0.9, headless=True):
        self.story, _, self.out = load(storyboard)
        self.W, self.H, self.pad, self.headless = width, height, pad, headless
        self.frames_dir = self.out / 'frames'
        self.frames_dir.mkdir(exist_ok=True)
        if any(self.frames_dir.iterdir()):
            raise SystemExit(f'{self.frames_dir} is not empty: move or delete the previous capture first.')
        manifest = self.out / 'audio/manifest.json'
        if not manifest.exists():
            raise SystemExit('Run narrate.py first: segments are paced to the narration.')
        self.narration = {a['id']: a['seconds'] for a in json.loads(manifest.read_text())}
        self.accent = self.story.get('brand', {}).get('accent', '#f26522')
        self.frames, self.segments, self.errors = [], {}, []
        self._state, self.ok = {}, False

    # --- lifecycle -------------------------------------------------------------
    def __enter__(self):
        self._pw = sync_playwright().start()
        self.browser = self._pw.chromium.launch(headless=self.headless)
        self.context = self.browser.new_context(viewport={'width': self.W, 'height': self.H}, device_scale_factor=1,
                                                accept_downloads=True)
        self.page = self.context.new_page()
        self.page.set_default_timeout(25000)
        self.page.on('pageerror', lambda e: self.errors.append(str(e)))
        self.cdp = self.context.new_cdp_session(self.page)
        self.cdp.on('Page.screencastFrame', self._frame)
        return self

    def _frame(self, event):
        name = f'{len(self.frames):06d}.jpg'
        (self.frames_dir / name).write_bytes(base64.b64decode(event['data']))
        self.frames.append([event['metadata']['timestamp'], name])
        self.cdp.send('Page.screencastFrameAck', {'sessionId': event['sessionId']})

    def open(self, url):
        """Load the app, draw the film cursor and start the screencast."""
        self.page.goto(url)
        self.page.evaluate('document.fonts.ready')
        self.page.evaluate(CURSOR_JS, self.accent)
        self.page.on('load', lambda *_: self.page.evaluate(CURSOR_JS, self.accent))
        self.cdp.send('Page.startScreencast', {'format': 'jpeg', 'quality': 92, 'maxWidth': self.W,
                                                'maxHeight': self.H, 'everyNthFrame': 1})
        self.park()
        return self.page

    def __exit__(self, exc_type, exc, tb):
        try:
            with contextlib.suppress(Exception): self.cdp.send('Page.stopScreencast')
            filmed = {s['id'] for s in self.story['segments'] if s.get('card') not in ('intro', 'outro')}
            missing = sorted(filmed - set(self.segments))
            self.ok = exc_type is None and not missing and not self.errors
            if missing: print('NOT FILMED:', ', '.join(missing))
            if self.errors: print('PAGE ERRORS:', self.errors[:5])
        finally:
            with contextlib.suppress(Exception): self.context.close(); self.browser.close()
            with contextlib.suppress(Exception): self._pw.stop()
            (self.out / 'capture.json').write_text(json.dumps({
                'status': 'passed' if self.ok else 'incomplete', 'size': [self.W, self.H], 'segments': self.segments,
                'frames': self.frames, 'errors': self.errors}, indent=1) + '\n')
            print('CAPTURE', 'passed' if self.ok else 'incomplete', len(self.frames), 'frames', flush=True)
        return False

    # --- pacing ----------------------------------------------------------------
    @contextlib.contextmanager
    def segment(self, sid):
        """Film one storyboard segment; holds the picture until its narration (+pad) has been spoken."""
        if sid not in self.narration:
            raise KeyError(f'{sid} is not in audio/manifest.json; run narrate.py after editing the storyboard')
        self._state = {'id': sid, 'start': time.time(), 'cuts': []}
        yield
        spoken = self.narration[sid] + self.pad
        cut_total = sum(b - a for a, b in self._state['cuts'])
        remaining = spoken - (time.time() - self._state['start'] - cut_total)
        if remaining > 0: self.hold(remaining)
        self.segments[sid] = {'start': self._state['start'], 'end': time.time(), 'cuts': self._state['cuts']}
        shown = self.segments[sid]['end'] - self._state['start'] - cut_total
        print(f'SEGMENT {sid:<16} {shown:5.1f} s (narration {spoken:4.1f} s)', flush=True)

    @contextlib.contextmanager
    def cut(self):
        """Wrap waits (calculations, uploads, page loads) that viewers should not sit through."""
        a = time.time(); yield; self._state['cuts'].append([a, time.time()])

    # --- actions (all with a visible cursor) ------------------------------------
    def hold(self, seconds): self.page.wait_for_timeout(int(seconds * 1000))
    def move(self, x, y, steps=24): self.page.mouse.move(x, y, steps=steps)
    def park(self, x=None, y=None): self.move(x if x is not None else self.W * .62, y if y is not None else self.H * .16)

    def _centre(self, locator):
        locator.scroll_into_view_if_needed(); expect(locator).to_be_visible()
        box = locator.bounding_box(); assert box, 'element has no box'
        return box['x'] + box['width'] / 2, box['y'] + box['height'] / 2

    def hover(self, locator, seconds=1.2):
        x, y = self._centre(locator); self.move(x, y); self.hold(seconds)

    def click(self, locator, settle=.3):
        expect(locator).to_be_enabled()
        x, y = self._centre(locator); self.move(x, y); self.hold(.2)
        self.page.mouse.click(x, y); self.hold(settle)

    def type(self, locator, text, delay=45):
        """Click into a field and type visibly (character by character)."""
        self.click(locator, .1); locator.fill(''); locator.press_sequentially(text, delay=delay); self.hold(.2)

    def drag(self, start, end, steps=40):
        self.move(*start); self.page.mouse.down(); self.move(*end, steps=steps); self.page.mouse.up()

    def scroll(self, selector, y, seconds=.9):
        """Smooth-scroll a scrollable element (CSS selector) to y pixels."""
        self.page.locator(selector).first.evaluate(f'e=>e.scrollTo({{top:{y},behavior:"smooth"}})'); self.hold(seconds)
