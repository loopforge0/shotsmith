#!/bin/sh
# The four untested group moves, one after another. Characters: Amber and Kate.
cd "$(dirname "$0")/.."
export COMFY_BASE_URL=http://127.0.0.1:8189
PY=.venv/Scripts/python.exe
$PY scripts/render_group.py aerial-pullback amber-main kate --seed 11 --action "<Subject 1> and <Subject 2> look out to sea, <Subject 2> resting her head on <Subject 1>'s shoulder"
$PY scripts/render_group.py dutch-angle amber-main kate --seed 11 --action "<Subject 1> whispers something to <Subject 2>, who turns to her in alarm"
$PY scripts/render_group.py handheld amber-main kate --scene "Autumn forest track" --seed 11 --action "<Subject 1> glances back over her shoulder while <Subject 2> keeps her eyes ahead"
$PY scripts/render_group.py crane-rise amber-main kate --scene "Autumn forest track" --seed 11 --action "the two of them run side by side, <Subject 2> half a step ahead"
