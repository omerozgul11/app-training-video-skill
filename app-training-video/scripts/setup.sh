#!/usr/bin/env bash
# One-time setup: a private Python environment, the offline Kokoro voice model, the Inter font and a Chromium for recording.
# Everything goes into $TRAINING_VIDEO_HOME (default ~/.cache/app-training-video); nothing is installed system-wide.
#   bash setup.sh                         # downloads the voice model (~350 MB) once
#   MODEL_SOURCE=/path/with/models bash setup.sh   # reuse kokoro-v1.0.onnx + voices-v1.0.bin already on disk
set -euo pipefail
HOME_DIR="${TRAINING_VIDEO_HOME:-$HOME/.cache/app-training-video}"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
mkdir -p "$HOME_DIR/models"

pick_python() {
  for c in ${PYTHON:-} python3.12 python3.11 python3.13 python3.10 python3; do
    command -v "$c" >/dev/null 2>&1 || continue
    if "$c" -c 'import sys; sys.exit(0 if (3,10) <= sys.version_info[:2] <= (3,13) else 1)'; then echo "$c"; return; fi
  done
  echo "Need Python 3.10–3.13 (the voice engine has no wheels for newer Pythons). Set PYTHON=/path/to/python3.12." >&2; exit 1
}
VENV="$HOME_DIR/venv"
if [ ! -x "$VENV/bin/python" ]; then
  PY="$(pick_python)"
  if command -v uv >/dev/null 2>&1; then uv venv -q --python "$PY" "$VENV"; else "$PY" -m venv "$VENV"; fi
fi
if command -v uv >/dev/null 2>&1; then uv pip install -q --python "$VENV/bin/python" -r "$HERE/requirements.txt"
else "$VENV/bin/python" -m pip install -q --upgrade pip && "$VENV/bin/python" -m pip install -q -r "$HERE/requirements.txt"; fi

# Voice model files (Apache-2.0, github.com/thewh1teagle/kokoro-onnx), checked against pinned SHA-256 digests.
fetch() {  # name url sha256
  local target="$HOME_DIR/models/$1"
  if [ -f "$target" ] && echo "$3  $target" | sha256sum -c --status; then return; fi
  if [ -n "${MODEL_SOURCE:-}" ] && [ -f "$MODEL_SOURCE/$1" ]; then cp "$MODEL_SOURCE/$1" "$target.part"
  else echo "Downloading $1 ..."; curl -fsSL --retry 3 -o "$target.part" "$2"; fi
  echo "$3  $target.part" | sha256sum -c --status || { echo "Checksum mismatch for $1" >&2; rm -f "$target.part"; exit 1; }
  mv "$target.part" "$target"
}
BASE=https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.1
fetch kokoro-v1.0.onnx "$BASE/kokoro-v1.0.onnx" beb0d1848dee9a49da392cc3df26958d46cfa35d321edf434f52949153f0df3a
fetch voices-v1.0.bin  "$BASE/voices-v1.0.bin"  bca610b8308e8d99f32e6fe4197e7ec01679264efed0cac9140fe9c29f1fbf7d

# Inter typeface for cards and captions (SIL Open Font License 1.1, github.com/rsms/inter).
if [ ! -f "$HOME_DIR/fonts/Inter-700.ttf" ]; then
  mkdir -p "$HOME_DIR/fonts"; Z="$HOME_DIR/fonts/inter.zip.part"
  echo "Downloading the Inter font ..."
  curl -fsSL --retry 3 -o "$Z" https://github.com/rsms/inter/releases/download/v4.1/Inter-4.1.zip
  echo "9883fdd4a49d4fb66bd8177ba6625ef9a64aa45899767dde3d36aa425756b11e  $Z" | sha256sum -c --status || { echo "Checksum mismatch for Inter-4.1.zip" >&2; rm -f "$Z"; exit 1; }
  "$VENV/bin/python" - "$Z" "$HOME_DIR/fonts" <<'PY'
import sys, zipfile
z = zipfile.ZipFile(sys.argv[1])
for weight, name in ((500, 'Medium'), (600, 'SemiBold'), (700, 'Bold')):
    open(f'{sys.argv[2]}/Inter-{weight}.ttf', 'wb').write(z.read(f'extras/ttf/Inter-{name}.ttf'))
open(f'{sys.argv[2]}/LICENSE.txt', 'wb').write(z.read('LICENSE.txt'))
PY
  rm -f "$Z"
fi

# Chromium for the screen capture (skipped when PLAYWRIGHT_BROWSERS_PATH already holds one).
"$VENV/bin/python" -m playwright install chromium || {
  echo "Chromium install failed. On Linux try: $VENV/bin/python -m playwright install --with-deps chromium" >&2; exit 1; }

echo "Ready. Use: $VENV/bin/python $HERE/<script>.py <storyboard.json>"
