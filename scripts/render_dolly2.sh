#!/bin/sh
# Dolly zoom with large amplitude, against the concert-stage take (H3ShotStudio_00036_, seed 11).
cd "$(dirname "$0")/.."
export COMFY_BASE_URL=http://127.0.0.1:8189
PY=.venv/Scripts/python.exe
P="expression shifts from blank and neutral into dawning realization and slight shock, her eyes widening and her lips parting slightly, settling into a held, wide-eyed stillness by the end"
run() { echo "== $*" ; $PY scripts/render_shot.py --seed 11 "$@" | grep -E '"(status|video|error|elapsed)"'; }
run dolly-zoom-large claire "Concert stage" "$P" --image
run dolly-zoom-large claire "Concert stage" "$P"
