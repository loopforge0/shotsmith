#!/bin/sh
# Crash zoom snap wording vs the first takes, same seed and scene.
cd "$(dirname "$0")/.."
export COMFY_BASE_URL=http://127.0.0.1:8189
PY=.venv/Scripts/python.exe
run() { echo "== $*" ; $PY scripts/render_shot.py --seed 7 "$@" | grep -E '"(status|video|error|elapsed)"'; }
run crash-zoom-out-snap mei "Tokyo alley" "holds a calm, neutral expression through the close-up, then her eyes flick wide in alarm as the zoom snaps out, lips closed"
run crash-zoom-in-snap amber-main "Arctic shore" "stands blank and still, then her eyes widen and her brow lifts the instant the zoom lands"
