#!/bin/sh
# Incline take 2: slide direction named. Same character, scene and seed as take 1.
cd "$(dirname "$0")/.."
export COMFY_BASE_URL=http://127.0.0.1:8189
.venv/Scripts/python.exe scripts/render_shot.py --seed 7 incline amber-main "Wild West town" "grins as things slide past" \
  --slot "LOOSE_THINGS=a metal bucket bouncing end over end, a rolling barrel, a skidding wooden chair and a tumbleweed" \
  | grep -E '"(status|video|error|elapsed)"'
