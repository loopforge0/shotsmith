#!/bin/sh
# Effects group test renders, one per effect, on varied characters and locations.
cd "$(dirname "$0")/.."
export COMFY_BASE_URL=http://127.0.0.1:8189
PY=.venv/Scripts/python.exe
run() { echo "== $*" ; $PY scripts/render_shot.py --seed 7 "$@" | grep -E '"(status|video|error|elapsed)"'; }
run set-on-fire lena "Desert highway" "stays calm, then her eyes widen as the fire takes her"
run disintegration kate "Old library" "her warm smile fades into a puzzled frown"
run melting sofia "Fifties diner" "keeps smiling as her features soften"
run vanish claire "Subway platform" "smiles at the lens before she vanishes"
run levitation allie "Glass greenhouse" "her expression eases from surprise into serene wonder"
run thunder-god mei "Neon megacity" "her cool look hardens into fierce focus"
run architecture-wave lena "Tokyo alley" "glances up once with a faint smile"
run incline amber-main "Wild West town" "grins as things slide past" --slot "LOOSE_THINGS=a metal bucket bouncing end over end, a rolling barrel, a skidding wooden chair and a tumbleweed"
run giant claire "Beach at sunset" "looks around with curiosity"
run battle-knight mei "Castle dungeon" "shows grim resolve giving way to exhaustion"
