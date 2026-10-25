#!/bin/sh
# Batch 2 test renders: the simple camera presets, on the generated locations.
cd "$(dirname "$0")/.."
export COMFY_BASE_URL=http://127.0.0.1:8189
PY=.venv/Scripts/python.exe
run() { echo "== $*" ; $PY scripts/render_shot.py --seed 7 "$@" | grep -E '"(status|video|error|elapsed)"'; }
run crash-zoom-out mei "Tokyo alley" "holds a calm, neutral expression through the close-up, then her eyes flick wide in alarm as the zoom snaps out, lips closed"
run super-dolly-out lena "Throne room" "her expression falls from defiance into quiet dread as the hall opens up around her, lips closed" --slot "THE_SPACE=the long red carpet" --slot "NEAR_OBJECTS=two stone columns" --slot "FURTHER_OBJECTS=rows of columns and banners" --slot "GROUND=the red carpet"
run arc-left claire "Old library" "looks down at an open book in her hands, then slowly lifts her eyes with a faint smile, lips closed"
run crane-down sofia "Wild West town" "squints up into the sun, then lowers her gaze to the camera with a slow, confident smile"
run truck-right allie "Glass greenhouse" "walks with an easy, contented expression, glancing at the plants as she passes, lips closed"
run static kate "Fifties diner" "laughs at something off camera, then the laugh fades into a thoughtful look and she tucks her hair behind her ear"
run jib-up amber-main "Jungle temple ruins" "turns her face up toward the rising camera, her expression opening from wariness into awe"
