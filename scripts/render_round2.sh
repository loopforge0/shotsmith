#!/bin/sh
# Round 2: the new moves on other characters and the generated locations.
cd "$(dirname "$0")/.."
export COMFY_BASE_URL=http://127.0.0.1:8189
PY=.venv/Scripts/python.exe
run() { echo "== $*" ; $PY scripts/render_shot.py --seed 11 "$@" | grep -E '"(status|video|error|elapsed)"'; }
run fisheye lena "Neon megacity" "leans into the lens with a slow, mischievous grin that breaks into a laugh"
run low-angle-hero mei "Desert highway" "expression moves from calm watchfulness to quiet, steely resolve, chin lifting slightly, lips closed"
run overhead-swing claire "Beach at sunset" "looks up into the lens with a small, curious smile and lowers her chin to follow the camera down, lips closed"
run tilt-up-reveal lena "Castle dungeon" "expression is still and unreadable until the camera reaches her face, then she gives a slow, knowing smile"
run pedestal-up mei "Rooftop at golden hour" "gazes out across the city, her expression easing from tension into calm" --image
run fpv-drone claire "Surface of Mars" "looks up toward the sound overhead, her expression moving from surprise to a wide grin as the camera arrives"
run walk-past-camera mei "Throne room" "walks with a calm, set expression that breaks into a small smile as she passes the lens, lips closed"
run dolly-zoom claire "Concert stage" "expression shifts from blank and neutral into dawning realization and slight shock, her eyes widening and her lips parting slightly, settling into a held, wide-eyed stillness by the end" --image
# Control: dolly zoom without the name, same scene and seed as the named take on Sofia.
run dolly-zoom-plain sofia "Rain-soaked city street" "expression shifts from blank and neutral into dawning realization and slight shock, her eyes widening and her lips parting slightly, settling into a held, wide-eyed stillness by the end" --slot "BACKGROUND=the glowing shopfronts, the street lamps and the parked cars" --seed 7
