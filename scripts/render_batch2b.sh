#!/bin/sh
# Batch 2, round 2: each move on another character and location, seed 11.
cd "$(dirname "$0")/.."
export COMFY_BASE_URL=http://127.0.0.1:8189
PY=.venv/Scripts/python.exe
run() { echo "== $*" ; $PY scripts/render_shot.py --seed 11 "$@" | grep -E '"(status|video|error|elapsed)"'; }
run crash-zoom-out claire "Castle dungeon" "holds a calm, neutral expression, then her eyes flick wide in alarm as the zoom snaps out, lips closed"
run super-dolly-out kate "Subway platform" "her expression falls from calm into quiet dread as the platform opens up around her, lips closed" --slot "THE_SPACE=the platform" --slot "NEAR_OBJECTS=two steel pillars" --slot "FURTHER_OBJECTS=rows of pillars and light tubes" --slot "GROUND=the yellow safety line"
run arc-left mei "Space station" "gazes out at the Earth, then turns her eyes toward the camera with a faint smile, lips closed"
run crane-down lena "Beach at sunset" "looks up at the camera, then lowers her gaze with a slow smile"
run truck-right sofia "Neon megacity" "walks with a calm, purposeful expression, glancing at the lights as she passes, lips closed"
run static amber-main "Glowing forest" "laughs softly at something off camera, then the laugh fades into a thoughtful look and she tucks her hair behind her ear"
run jib-up allie "Surface of Mars" "turns her face up toward the rising camera, her expression opening from wariness into awe"
