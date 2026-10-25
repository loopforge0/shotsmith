"""Write outputs/prompt-review.html: every move the app offers, with the full prompt H3 receives when
someone brings the usual inputs (a character photo, a location photo and one action sentence), so the
wording can be reviewed in one place. What came from the person's inputs is highlighted; everything
else is the move's recipe in shotstudio/moves/ (or the shot library's, for the moves it supplies).

    python scripts/prompt_review.py
"""

import html
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from shotstudio import shots  # noqa: E402

OUT = ROOT / "outputs" / "prompt-review.html"
SAMPLES = json.loads((ROOT / "shotstudio" / "samples.json").read_text(encoding="utf-8"))
SCENE = "Rooftop at golden hour"
CAST = ["sofia", "mei", "lena"]
ACTION = {1: "<Subject 1> looks out over the city, then turns to the camera and smiles.",
          2: "<Subject 1> and <Subject 2> talk quietly, then <Subject 2> laughs.",
          3: "<Subject 1>, <Subject 2> and <Subject 3> stand together, talking and laughing."}
# Inputs the person typed, to highlight in the prompt.
USER_MARK = re.compile(r"(&lt;Subject \d+&gt;|&lt;Picture \d+&gt;|\[[A-Z_0-9]+: [^\]]+\])")


def build(entry: dict) -> str:
    n = max(entry["cast"][0], entry.get("subjects", 1))
    chars = [{"pronoun": "they", "look": ""} for c in CAST[:n]]   # what an uploaded character gets by default
    scene = {k: v for k, v in SAMPLES["scenes"][SCENE].items()}
    for slot in entry["slots"]:
        if slot in entry["hints"]:
            scene[slot] = f"[{slot}: {entry['hints'][slot]}]"
    try:
        return shots.build(entry["slug"], scene, chars, ACTION[n], location_plate=True)
    except shots.PromptError as exc:
        return f"(could not build with the sample inputs: {exc})"


def page() -> str:
    groups: dict[str, list[dict]] = {}
    for entry in shots.catalog():
        groups.setdefault(entry["group"] or "other", []).append(entry)
    nav, body = [], []
    for group, entries in groups.items():
        body.append(f"<h2 id='g-{html.escape(group)}'>{html.escape(group)}</h2>")
        nav.append(f"<a href='#g-{html.escape(group)}'>{html.escape(group)} ({len(entries)})</a>")
        for e in entries:
            recipe = shots.RECIPES.get(e["slug"], {})
            prompt = html.escape(build(e))
            action = html.escape(ACTION[max(e["cast"][0], e.get("subjects", 1))])
            prompt = prompt.replace(action, f"<mark class='act'>{action}</mark>")
            prompt = USER_MARK.sub(r"<mark>\1</mark>", prompt)
            source = f"shotstudio/moves/{e['slug']}.md" if (ROOT / "shotstudio" / "moves" / f"{e['slug']}.md").exists() \
                else "shot library (vendor)"
            note = f"<p class='note'>{html.escape(e['note'])}</p>" if e.get("note") else ""
            body.append(f"""<section id="{e['slug']}"><h3>{html.escape(e['name'])}
<span class="tag">{html.escape(recipe.get('status', ''))}</span><span class="tag">{e['cast'][0]}-{e['cast'][1]} people</span>
<span class="tag">{round(e['length'] / 24, 1)} s</span></h3>
<p class="src">{source}</p>{note}<pre>{prompt}</pre></section>""")
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Prompt Review</title><style>
:root{{--bg:#111214;--panel:#1b1d21;--line:#2c2f35;--text:#e8e8ea;--dim:#9a9ca3;--mark:#3a3216;--markt:#f5d36b;--act:#16303a;--actt:#7fd3f0}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--text);font:14px/1.5 system-ui,sans-serif}}
header{{position:sticky;top:0;background:var(--bg);border-bottom:1px solid var(--line);padding:12px 16px;z-index:1}}
h1{{font-size:17px;margin:0 0 6px}}header p{{margin:0 0 8px;color:var(--dim);font-size:13px}}
nav{{display:flex;flex-wrap:wrap;gap:6px}}nav a{{color:var(--dim);text-decoration:none;border:1px solid var(--line);border-radius:12px;padding:1px 9px;font-size:12px}}
h2{{font-size:13px;text-transform:uppercase;letter-spacing:.08em;color:var(--dim);margin:28px 16px 6px}}
section{{margin:0 16px 16px;padding:12px;background:var(--panel);border:1px solid var(--line);border-radius:10px}}
h3{{margin:0 0 4px;font-size:15px;display:flex;gap:8px;align-items:baseline;flex-wrap:wrap}}
.tag{{font-size:11px;color:var(--dim);border:1px solid var(--line);border-radius:8px;padding:0 6px;font-weight:400}}
.src{{margin:0;color:var(--dim);font-size:12px}}.note{{margin:6px 0;font-size:13px;color:#c9cbd1}}
pre{{white-space:pre-wrap;word-break:break-word;font:12.5px/1.5 ui-monospace,Consolas,monospace;margin:8px 0 0;color:#d6d7db}}
mark{{background:var(--mark);color:var(--markt);border-radius:3px;padding:0 2px}}mark.act{{background:var(--act);color:var(--actt)}}
</style></head><body><header><h1>Prompt Review</h1>
<p>Every move in the app, built from the same inputs: one to three character photos (Sofia, Mei, Lena), a location
photo (rooftop at golden hour) and one action sentence. <mark class="act">Blue</mark> is the action sentence the person
types; <mark>yellow</mark> is where their photos and extra fields land. Everything else is the move's recipe.</p>
<nav>{''.join(nav)}</nav></header>{''.join(body)}</body></html>"""


if __name__ == "__main__":
    OUT.write_text(page(), encoding="utf-8")
    print(f"{OUT} ({len(shots.catalog())} moves)")
