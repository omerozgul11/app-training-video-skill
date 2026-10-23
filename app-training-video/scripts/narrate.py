"""Speak every storyboard segment with the offline Kokoro voice (CPU only, no internet needed).

    python narrate.py storyboard.json            # (re)speaks segments whose text or voice changed
    python narrate.py storyboard.json --all      # speak everything again

Writes <output_dir>/audio/<id>.wav and audio/manifest.json (seconds per segment and the caption text).
"""
import hashlib, json, shutil, sys, tempfile
from pathlib import Path
import espeakng_loader
import numpy as np, onnxruntime as ort, soundfile as sf
from kokoro_onnx import EspeakConfig, Kokoro
from common import HOME, load, written


def espeak_config():
    """espeak-ng cannot use a data folder whose real path is long (deep home or temp folders); it then
    fails with "Error processing file .../phontab". A link does not help (it resolves to the long path),
    so copy the small data folder (~20 MB) to a short location once and use that."""
    data = espeakng_loader.get_data_path()
    if len(data) > 100:
        short = Path(tempfile.gettempdir()) / ('espeak-ng-data-' + hashlib.sha256(data.encode()).hexdigest()[:8])
        if short.is_symlink(): short.unlink()
        if not (short / 'phontab').is_file():
            shutil.copytree(data, short, dirs_exist_ok=True)
        data = str(short)
    return EspeakConfig(lib_path=espeakng_loader.get_library_path(), data_path=data)

story, _, out = load()
audio = out / 'audio'; audio.mkdir(exist_ok=True)
old = {}
if (audio / 'manifest.json').exists() and '--all' not in sys.argv:
    old = {m['id']: m for m in json.loads((audio / 'manifest.json').read_text())}
voice_name, speed, lang = story.get('voice', 'af_heart'), story.get('voice_speed', 1.0), story.get('voice_language', 'en-us')
settings = ort.SessionOptions(); settings.intra_op_num_threads = 4; settings.inter_op_num_threads = 1
voice = None
manifest = []
for seg in story['segments']:
    key = hashlib.sha256(json.dumps([seg['speech'], voice_name, speed, lang]).encode()).hexdigest()[:16]
    target = audio / f"{seg['id']}.wav"
    if seg['id'] in old and old[seg['id']].get('key') == key and target.exists():
        manifest.append({**old[seg['id']], 'caption': written(story, seg['speech'])}); continue
    if voice is None:
        session = ort.InferenceSession(str(HOME / 'models/kokoro-v1.0.onnx'), settings, providers=['CPUExecutionProvider'])
        voice = Kokoro.from_session(session, str(HOME / 'models/voices-v1.0.bin'), espeak_config=espeak_config())
    samples, rate = voice.create(seg['speech'], voice=voice_name, speed=speed, lang=lang)
    assert np.isfinite(samples).all() and len(samples) > rate, f"{seg['id']}: empty narration"
    peak = float(np.max(np.abs(samples)))
    if peak > 0.95: samples = samples * (0.95 / peak)
    sf.write(target, samples, rate, subtype='PCM_16')
    manifest.append({'id': seg['id'], 'file': target.name, 'rate': rate, 'seconds': round(len(samples) / rate, 3),
                     'key': key, 'caption': written(story, seg['speech'])})
    print(f"{seg['id']:<16} {manifest[-1]['seconds']:6.1f} s", flush=True)
(audio / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
print(f"narration total {sum(m['seconds'] for m in manifest):.1f} s in {len(manifest)} segments")
