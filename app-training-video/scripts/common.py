"""Shared helpers: storyboard loading, output folders and the spoken-to-written caption rules."""
from pathlib import Path
import json, os, re, sys

SKILL = Path(__file__).resolve().parents[1]
HOME = Path(os.environ.get('TRAINING_VIDEO_HOME', Path.home() / '.cache/app-training-video'))
FONTS = HOME / 'fonts'  # Inter 500/600/700, installed by setup.sh (SIL Open Font License)


def load(path=None):
    """Return (story, storyboard_path, output_dir). The storyboard path comes from argv[1] when not given."""
    if path is None:
        if len(sys.argv) < 2:
            sys.exit(f'Usage: {Path(sys.argv[0]).name} <storyboard.json>')
        path = sys.argv[1]
    path = Path(path).resolve()
    story = json.loads(path.read_text(encoding='utf-8'))
    out = Path(story.get('output_dir', 'video-build'))
    out = out if out.is_absolute() else path.parent / out
    out.mkdir(parents=True, exist_ok=True)
    ids = [s['id'] for s in story['segments']]
    assert len(ids) == len(set(ids)), 'Segment ids must be unique'
    return story, path, out


def written(story, text):
    """Narration is spelled for the voice ("S Q L", "two D"); captions show the written form ("SQL", "2D")."""
    for pattern, replacement in story.get('caption_replacements', []):
        text = re.sub(pattern, replacement, text)
    return text


def sentences(text):
    return [s.strip() for s in re.split(r'(?<=[.!?])\s+', text) if s.strip()]
