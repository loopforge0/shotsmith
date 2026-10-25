#!/bin/sh
# Test renders for the dolly zoom recipes in shotstudio/moves.
cd "$(dirname "$0")/.."
export COMFY_BASE_URL=http://127.0.0.1:8189
PY=.venv/Scripts/python.exe
run() { echo "== $1 $2" ; $PY scripts/render_shot.py "$@" --seed 7 | grep -E '"(status|video|error|elapsed)"'; }
DREAD="expression shifts from blank and neutral into dawning realization and slight shock, her eyes widening and her lips parting slightly, settling into a held, wide-eyed stillness by the end"
run dolly-zoom sofia "Rain-soaked city street" "$DREAD" --slot "BACKGROUND=the glowing shopfronts, the street lamps and the parked cars"
run dolly-zoom amber-main "Autumn forest track" "$DREAD" --slot "BACKGROUND=the tall tree trunks, the low mist between them and the shafts of sunlight"
run dolly-zoom-in kate "Rain-soaked city street" "$DREAD" --slot "BACKGROUND=the glowing shopfronts, the street lamps and the parked cars"
