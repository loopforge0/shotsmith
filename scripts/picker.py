"""A local page for choosing the best take of every move: each move's renders side by side, grouped as
in the app, with the prompt's summary under each. Clicking a take marks it as that move's pick, and the
picks save to outputs/picks.json, which is the list to re-render at native resolution for the app's
previews and the demo video.

    python scripts/picker.py        then open http://127.0.0.1:7870
"""

import json
import re
import sys
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from shotstudio import shots  # noqa: E402

OUT = ROOT / "outputs"
PICKS = OUT / "picks.json"
PORT = 7870

# Renders that are not takes of a move: A/B copies, reference-video experiments, motion templates.
SKIP = re.compile(r"(_raw|-match_)")
STEM = re.compile(r"^(.*?)_(\d+)_([0-9a-f]{12})$")
# Renamed or merged moves: the takes of these prefixes belong to the move on the right.
ALIAS = {"pov-call": "pov", "dolly-zoom-large": "dolly-zoom", "dolly-zoom-plain": "dolly-zoom",
         "crash-zoom-in-snap": "crash-zoom-in", "crash-zoom-out-snap": "crash-zoom-out"}


def _cast_looks() -> dict[str, str]:
    samples = json.loads((ROOT / "shotstudio" / "samples.json").read_text(encoding="utf-8"))
    return {c["look"]: key for key, c in samples["cast"].items() if c.get("look")}


def takes() -> list[dict]:
    looks = _cast_looks()
    found: dict[str, list[dict]] = {}
    for video in OUT.glob("*.mp4"):
        m = STEM.match(video.stem)
        if not m or SKIP.search(video.name):
            continue
        prefix = ALIAS.get(m.group(1), m.group(1))
        slug = prefix if prefix in shots.RECIPES else next(
            (s for s in sorted(shots.RECIPES, key=len, reverse=True) if prefix.startswith(s)), None)
        if not slug:
            continue
        summary, cast, size = "", [], ""
        wf = video.with_name(video.stem + ".workflow.json")
        if wf.exists():
            h3 = json.loads(wf.read_text(encoding="utf-8"))["6"]["inputs"]
            line = re.search(r"^\[[a-z +]+\] (.*)$", h3.get("prompt", ""), re.M)
            summary = line.group(1) if line else ""
            cast = [name for look, name in looks.items() if look in h3.get("prompt", "")]
            size = f"{h3.get('width')}x{h3.get('height')}"
        found.setdefault(slug, []).append({"file": video.name, "variant": m.group(1), "seed": m.group(2),
                                           "summary": summary, "cast": cast, "size": size,
                                           "mtime": video.stat().st_mtime})
    groups = {c["slug"]: c["group"] for c in shots.catalog()}
    moves = []
    for slug, shot in shots.RECIPES.items():
        if slug not in found:
            continue
        moves.append({"slug": slug, "name": shot.get("label", shot["name"]),
                      "group": groups.get(slug) or shot.get("group", "") or "other", "status": shot.get("status", ""),
                      "takes": sorted(found[slug], key=lambda t: -t["mtime"])})
    order = ["zoom", "tracking", "angle", "pan and roll", "specialty", "effects"]
    return sorted(moves, key=lambda m: (order.index(m["group"]) if m["group"] in order else 99, m["name"]))


PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Take Picker</title>
<style>
:root{--bg:#111214;--panel:#1b1d21;--line:#2c2f35;--text:#e8e8ea;--dim:#9a9ca3;--pick:#f5b301;--ok:#4caf7a}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--text);font:14px/1.4 system-ui,sans-serif}
header{position:sticky;top:0;z-index:2;background:var(--bg);border-bottom:1px solid var(--line);padding:12px 16px;display:flex;gap:16px;align-items:center;flex-wrap:wrap}
h1{font-size:17px;margin:0}#count{color:var(--dim)}#saved{color:var(--ok);font-size:13px}
nav{display:flex;gap:6px;flex-wrap:wrap}nav a{color:var(--dim);text-decoration:none;border:1px solid var(--line);border-radius:12px;padding:2px 9px;font-size:12px}
nav a.done{border-color:var(--pick);color:var(--pick)}
label{color:var(--dim);font-size:13px}
h2{font-size:13px;text-transform:uppercase;letter-spacing:.08em;color:var(--dim);margin:28px 16px 4px}
section{margin:0 16px 22px;padding:12px;background:var(--panel);border:1px solid var(--line);border-radius:10px}
section h3{margin:0 0 10px;font-size:15px;display:flex;gap:10px;align-items:baseline}
.status{font-size:11px;color:var(--dim);border:1px solid var(--line);border-radius:8px;padding:0 6px}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:12px}
.take{border:2px solid transparent;border-radius:8px;overflow:hidden;background:#000;cursor:pointer}
.take.picked{border-color:var(--pick)}
.take video{width:100%;display:block;aspect-ratio:16/9;background:#000}
.meta{padding:6px 8px;background:var(--panel);font-size:12px;color:var(--dim)}
.meta b{color:var(--text);font-weight:600}.meta .sum{margin-top:3px;display:-webkit-box;-webkit-line-clamp:3;-webkit-box-orient:vertical;overflow:hidden}
.pickbtn{float:right;font-size:12px;color:var(--pick)}
</style></head><body>
<header><h1>Take Picker</h1><span id="count"></span><span id="saved"></span>
<label><input type="checkbox" id="sound"> sound</label><nav id="nav"></nav></header>
<main id="main"></main>
<script>
const MOVES = __MOVES__;
let picks = __PICKS__;
const main = document.getElementById("main"), nav = document.getElementById("nav");
function render() {
  main.innerHTML = ""; nav.innerHTML = ""; let group = null;
  for (const m of MOVES) {
    if (m.group !== group) { group = m.group; const h = document.createElement("h2"); h.textContent = group; main.append(h); }
    const sec = document.createElement("section"); sec.id = m.slug;
    sec.innerHTML = `<h3>${m.name}<span class="status">${m.status}</span><span class="status">${m.takes.length} take${m.takes.length > 1 ? "s" : ""}</span></h3><div class="grid"></div>`;
    const grid = sec.querySelector(".grid");
    for (const t of m.takes) {
      const d = document.createElement("div"); d.className = "take" + (picks[m.slug] === t.file ? " picked" : "");
      d.innerHTML = `<video src="/files/${t.file}" preload="metadata" muted loop playsinline controls></video>
        <div class="meta"><span class="pickbtn">${picks[m.slug] === t.file ? "&#9733; picked" : "click to pick"}</span>
        <b>${t.cast.join(", ") || t.variant}</b> &middot; seed ${t.seed} &middot; ${t.size}<div class="sum">${t.summary}</div>
        <div>${t.file}</div></div>`;
      const v = d.querySelector("video");
      d.addEventListener("mouseenter", () => { v.muted = !document.getElementById("sound").checked; v.play().catch(() => {}); });
      d.addEventListener("mouseleave", () => v.pause());
      d.querySelector(".meta").addEventListener("click", () => pick(m.slug, t.file));
      grid.append(d);
    }
    main.append(sec);
    const a = document.createElement("a"); a.href = "#" + m.slug; a.textContent = m.name; if (picks[m.slug]) a.className = "done"; nav.append(a);
  }
  document.getElementById("count").textContent = `${Object.keys(picks).length} / ${MOVES.length} picked`;
}
async function pick(slug, file) {
  if (picks[slug] === file) delete picks[slug]; else picks[slug] = file;
  const y = window.scrollY; render(); window.scrollTo(0, y);
  const r = await fetch("/picks", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(picks) });
  document.getElementById("saved").textContent = r.ok ? "saved" : "save failed";
}
render();
</script></body></html>"""


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(OUT), **kwargs)

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            picks = json.loads(PICKS.read_text(encoding="utf-8")) if PICKS.exists() else {}
            body = PAGE.replace("__MOVES__", json.dumps(takes())).replace("__PICKS__", json.dumps(picks)).encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if self.path.startswith("/files/"):
            self._send_video(OUT / Path(self.path[len("/files/"):]).name)
            return
        self.send_error(404)

    def _send_video(self, path: Path):
        # Range requests, so the browser can seek inside a take.
        if not path.exists() or path.suffix != ".mp4":
            self.send_error(404)
            return
        size = path.stat().st_size
        start, end = 0, size - 1
        m = re.match(r"bytes=(\d*)-(\d*)", self.headers.get("Range", ""))
        if m:
            start = int(m.group(1)) if m.group(1) else size - int(m.group(2))
            end = int(m.group(2)) if m.group(1) and m.group(2) else end
            self.send_response(206)
            self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
        else:
            self.send_response(200)
        self.send_header("Content-Type", "video/mp4")
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Content-Length", str(end - start + 1))
        self.end_headers()
        with path.open("rb") as f:
            f.seek(start)
            left = end - start + 1
            while left > 0:
                chunk = f.read(min(1 << 16, left))
                if not chunk:
                    break
                try:
                    self.wfile.write(chunk)
                except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
                    return
                left -= len(chunk)

    def do_POST(self):
        if self.path != "/picks":
            self.send_error(404)
            return
        picks = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        PICKS.write_text(json.dumps(picks, indent=2) + "\n", encoding="utf-8")
        self.send_response(204)
        self.end_headers()

    def log_message(self, *args):
        pass


if __name__ == "__main__":
    print(f"take picker on http://127.0.0.1:{PORT}", flush=True)
    ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
