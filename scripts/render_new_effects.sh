#!/bin/sh
# Rooftop swing, two takes.
cd "$(dirname "$0")/.."
export COMFY_BASE_URL=http://127.0.0.1:8189
PY=.venv/Scripts/python.exe
run() { echo "== $*" ; $PY scripts/render_shot.py --seed 7 "$@" | grep -E '"(status|video|error|elapsed)"'; }
run rooftop-swing lena "Neon megacity" "grins with breathless exhilaration as she lands"
run rooftop-swing mei "Rooftop at golden hour" "whoops with delight mid-swing, then lands with a calm, satisfied smile"
