#!/bin/sh
# Preview renders for library moves that have no render in outputs/ yet.
cd "$(dirname "$0")/.."
export COMFY_BASE_URL=http://127.0.0.1:8189
PY=.venv/Scripts/python.exe
run() { echo "== $*" ; $PY scripts/render_shot.py --seed 7 "$@" | grep -E '"(status|video|error|elapsed)"'; }
run crash-zoom-in amber-main "Arctic shore" "expression shifts from blank and neutral into dawning realization and slight shock"
run eyes-in kate "Old library" "expression moves from calm into quiet wonder, eyes steady on the lens"
run yoyo-zoom sofia "Rooftop at golden hour" "her easy smile turns to startled bewilderment as the world tears away and slams back"
run split-screen allie "Rain-soaked city street" "expression moves from guarded and tired into quiet resolve"
