#!/bin/sh
# Test renders for the new moves in shotstudio/moves, one after another.
cd "$(dirname "$0")/.."
export COMFY_BASE_URL=http://127.0.0.1:8189
PY=.venv/Scripts/python.exe
run() { echo "== $1 $2" ; $PY scripts/render_shot.py "$@" --seed 7 | grep -E '"(status|video|error|elapsed)"'; }
run low-angle-hero kate "Arctic shore" "expression moves from calm watchfulness to quiet, steely resolve, chin lifting slightly, lips closed"
run overhead-swing allie "Autumn forest track" "looks up into the lens with a small, curious smile and lowers her chin to follow the camera down, lips closed"
run tilt-up-reveal sofia "Rain-soaked city street" "expression is still and unreadable until the camera reaches her face, then she gives a slow, knowing smile"
run pedestal-up amber-main "Arctic shore" "gazes out to sea, her expression easing from tension into calm"
run fisheye sofia "Rain-soaked city street" "leans into the lens with a slow, mischievous grin that breaks into a laugh"
run fpv-drone amber-main "Arctic shore" "looks up toward the sound overhead, her expression moving from surprise to a wide grin as the camera arrives"
run walk-past-camera kate "Autumn forest track" "walks with a calm, set expression that breaks into a small smile as she passes the lens, lips closed"
