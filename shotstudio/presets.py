"""Each camera move starts from an approved take (presets.json, made by scripts/make_presets.py).

If the inputs are the take's, its exact prompt runs again. A swapped character or bundled location is
an edit of that exact prompt, not a rebuild, so what made the take work stays word for word: the
character's look, name and pronouns change, or the location's own words do. Anything else (objects,
dialogue, sound clips, a location image or description, a different cast size) builds from the recipe.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from . import shots

ROOT = Path(__file__).resolve().parent
PRESETS: dict[str, dict] = json.loads((ROOT / "presets.json").read_text(encoding="utf-8")) \
    if (ROOT / "presets.json").exists() else {}
SAMPLES = json.loads((ROOT / "samples.json").read_text(encoding="utf-8"))

# Locations people added and had described (describe.py): name -> their words, with "ref" (the
# image). The server sets this; they work wherever a bundled location does.
extra_scenes = lambda: {}


def scenes() -> dict[str, dict]:
    """Every location with words: the bundled ones, then the ones people added."""
    return {**SAMPLES["scenes"], **extra_scenes()}


def image_scene(ref: str | None) -> dict:
    """The words of the location whose image this is, bundled ("location:Name") or added."""
    ref = ref or ""
    bundled = SAMPLES["scenes"].get(ref.removeprefix("location:"), {}) if ref.startswith("location:") else {}
    return bundled or next((sc for sc in extra_scenes().values() if sc.get("ref") == ref), {})


def image_place(ref: str | None) -> str | None:
    """The name of the place with words whose picture this is, so the picture can go with its words."""
    ref = ref or ""
    if ref.startswith("location:") and ref.removeprefix("location:") in SAMPLES["scenes"]:
        return ref.removeprefix("location:")
    return next((name for name, sc in extra_scenes().items() if sc.get("ref") == ref and sc.get("ENVIRONMENT")), None)


def add_plate(prompt: str, n: int, sc: dict) -> str:
    """A prompt that describes its place in words, with the place's picture as <Picture n> too: the
    picture defined by those words, as a character is defined by their look, and held to."""
    label, plate = f"<Subject {n}>", f"<Picture {n}>"
    if f"{label} is the environment in {plate}" in prompt:
        return prompt
    around = f", with {sc['ENVIRONMENT_ELEMENTS']}" if sc.get("ENVIRONMENT_ELEMENTS") else ""
    prompt = shots._insert_after_section(prompt, "subject_definitions", [f"{label} is the environment in {plate}: {sc['ENVIRONMENT']}{around}."])
    return shots._insert_after_section(prompt, "retention_analysis", [
        f"{label} (appears in [Shot 1]): fully_preserved - the environment's layout, materials and look are held to {plate} throughout."])


# The location's own words in a prompt, with the moves' location fields (shots.LOCATION_FIELDS).
_SCENE_WORDS = ("ENVIRONMENT_ELEMENTS", "PLACE", "ENVIRONMENT", "SOUNDSCAPE")
# After "her", these mean it is the object ("behind her."), not the possessive ("her face").
_AFTER_OBJECT = {"and", "as", "to", "with", "in", "on", "at", "from", "up", "down", "behind", "into",
                 "while", "the", "a", "an", "so", "until", "before", "after", "around", "over", "through",
                 "toward", "towards", "now", "again", "for", "off", "out", "away", "is", "was", "who", "that",
                 "by", "but", "or", "then", "when", "if", "close", "closer", "go", "free"}
# Before "the person", these make it the object ("behind the person" -> "behind him").
_BEFORE_OBJECT = {"behind", "at", "to", "with", "toward", "towards", "from", "on", "into", "around", "over", "past",
                  "beside", "near", "of", "for", "by", "under", "above", "onto", "facing", "follows", "frames",
                  "circles", "orbits", "passes", "reaches", "keeps", "holds"}


def labelled(text: str, names: list[str]) -> str:
    """The app's @Name text in the prompt's <Subject N> form."""
    index = {n.lower(): i + 1 for i, n in enumerate(names)}
    return re.sub(r"@([A-Za-z0-9_-]+)", lambda m: f"<Subject {index[m[1].lower()]}>" if m[1].lower() in index else m[0], text)


def _pronoun_words(pronoun: str) -> dict[str, str]:
    """Words for one character: she and he as chosen, anyone else named "the person"."""
    if pronoun == "he":
        return {"subj": "he", "obj": "him", "poss": "his", "poss_alone": "his", "self": "himself"}
    if pronoun == "she":
        return {"subj": "she", "obj": "her", "poss": "her", "poss_alone": "hers", "self": "herself"}
    return {"subj": "the person", "obj": "the person", "poss": "the person's", "poss_alone": "the person's",
            "self": "themselves"}


def swap_pronouns(text: str, old: str, new: str) -> str:
    """Rewrite one character's pronouns, telling possessive "her face" from object "behind her"."""
    if old == new:
        return text
    a, b = _pronoun_words(old), _pronoun_words(new)

    def cap(word: str, like: str) -> str:
        return word[:1].upper() + word[1:] if like[:1].isupper() else word

    if old not in ("she", "he"):  # "the person" forms: possessive first, so its "the person" is not split
        text = re.sub(r"\b(the person's|The person's)", lambda m: cap(b["poss"], m[1]), text)
        text = re.sub(r"\b(themselves)\b", lambda m: b["self"], text)
        # After a preposition or verb object slot it is "him"/"her"; elsewhere the subject.
        def person(m: re.Match) -> str:
            before = m.group(1) or ""
            word = b["obj"] if before.strip().lower() in _BEFORE_OBJECT else b["subj"]
            return before + cap(word, m.group(2))
        return re.sub(r"(\b[A-Za-z]+\s+)?\b(the person|The person)\b(?! in <Picture)", person, text)

    def fix(m: re.Match) -> str:
        word, rest = m.group(1), m.group(2) or ""
        low = word.lower()
        if low == a["self"]:
            out = b["self"]
        elif low == a["subj"]:
            out = b["subj"]
        elif low == a["obj"] and a["obj"] != a["poss"]:  # him
            out = b["obj"]
        elif low == a["poss_alone"] and a["poss_alone"] != a["poss"]:  # hers
            out = b["poss_alone"]
        else:  # her or his: possessive when a word follows that is not a preposition or conjunction
            follows = re.match(r"\s+([A-Za-z'-]+)", rest)
            possessive = bool(follows) and follows.group(1).lower() not in _AFTER_OBJECT
            if old == "he":
                out = b["poss"] if possessive else b["poss_alone"]
            else:
                out = b["poss"] if possessive else b["obj"]
        return cap(out, word) + rest

    words = sorted({a["subj"], a["obj"], a["poss"], a["poss_alone"], a["self"]}, key=len, reverse=True)
    pattern = r"\b(" + "|".join(map(re.escape, words)) + r")\b(\s+[A-Za-z'-]+|[.,;:!?)])?"
    return re.sub(pattern, fix, text, flags=re.I)


# A pair or group named together ("<Subject 2> and <Subject 3> peer past her shoulders") is not who a
# following "her" means; a single subject, or its picture, is.
_GROUP = r"<Subject \d+>(?:,? <Subject \d+>)*,? and <Subject \d+>"


def _pronoun_pattern(pronoun: str) -> str:
    w = _pronoun_words(pronoun)
    words = sorted({w["subj"], w["obj"], w["poss"], w["poss_alone"], w["self"]}, key=len, reverse=True)
    return r"\b(?:" + "|".join(map(re.escape, words)) + r")\b(?! in <Picture)"


def swap_cast(text: str, old: list[dict], new: list[dict]) -> str:
    """Swap characters in a prompt (or @mention text in its <Subject N> form): each changed character's
    look, name and pronouns, the rest of the words kept. With several characters, a pronoun belongs to
    the subject last named on its own before it.

    `old` and `new` are {"name", "pronoun", "look"} in cast order."""
    n = len(old)
    changed = [i for i in range(n) if (old[i]["name"], old[i].get("pronoun"), old[i].get("look")) !=
               (new[i]["name"], new[i].get("pronoun"), new[i].get("look"))]
    if not changed:
        return text
    # Looks first, as placeholders, so a pronoun inside one ("a tattoo on her neck") is left alone.
    looks = sorted(((i, (old[i].get("look") or "").strip().rstrip(".")) for i in range(n)), key=lambda x: -len(x[1]))
    for i, look in looks:
        if look:
            text = text.replace(look, f"\x02{i}\x02")
    for i in changed:
        a, b = old[i].get("pronoun") or "they", new[i].get("pronoun") or "they"
        if a == b:
            continue
        spans, last = [], 1
        token = re.compile(rf"({_GROUP})|<(?:Subject|Picture) (\d+)>|({_pronoun_pattern(a)})", re.I)
        for m in token.finditer(text):
            if m[2] and int(m[2]) <= n:
                last = int(m[2])
            elif m[3] and (n == 1 or last == i + 1):
                spans.append(m.span())
        for s, e in reversed(spans):  # each with its neighbouring words, which tell "her face" from "behind her"
            prev = re.search(r"[A-Za-z']+[ \t]+$", text[:s])
            ws = prev.start() if prev else s
            nxt = re.match(r"[ \t]+[A-Za-z'-]+|[.,;:!?)]", text[e:])
            we = e + (nxt.end() if nxt else 0)
            text = text[:ws] + swap_pronouns(text[ws:we], a, b) + text[we:]
    for i, look in looks:
        if not look:
            continue
        new_look = (new[i].get("look") or "").strip().rstrip(".") if i in changed else look
        if new_look:
            text = text.replace(f"\x02{i}\x02", new_look)
        else:
            text = text.replace(f", with \x02{i}\x02.", ".").replace(f" (\x02{i}\x02)", "").replace(f"\x02{i}\x02", "")
    for i in changed:  # names, through placeholders so swapping two names round works
        text = re.sub(rf"\b{re.escape(old[i]['name'])}\b", f"\x03{i}\x03", text)
    for i in changed:
        text = text.replace(f"\x03{i}\x03", new[i]["name"])
    return text


def swap_text(text: str, old: list[dict], new: list[dict]) -> str:
    """swap_cast for the page's @Name action text."""
    swapped = swap_cast(labelled(text, [c["name"] for c in old]), old, new)
    return re.sub(r"<Subject (\d+)>", lambda m: "@" + new[int(m[1]) - 1]["name"] if int(m[1]) <= len(new) else m[0], swapped)


def derive(slug: str, characters: list[dict], scene_name: str | None, location_ref: str | None,
           text: str, extras: dict[str, str], simple: bool, objects: list[dict] = ()) -> str | None:
    """The prompt for these inputs, as an edit of the move's approved take; None to build from the recipe.

    `characters` are {"ref", "name", "pronoun", "look"} in cast order, `objects` {"ref", "name"};
    `text` is the @Name action; `simple` is False when the shot has recordings or sound clips.
    Dialogue is fine: it is in the text, which has to be the take's. An object can be swapped for
    another like a character: the prompt names it only by its picture."""
    p = PRESETS.get(slug)
    if not p or not simple or len(characters) != len(p["cast"]) or len(objects) != len(p["objects"]):
        return None
    take_loc = p["location"]
    if "image" in take_loc:
        if location_ref != f"location:{take_loc['image']}":
            return None
    elif location_ref or not scene_name or scene_name not in scenes():
        return None
    # An edited extra field (a montage insert, the background) is replaced where the take's value is
    # in the prompt word for word; a field the take's prompt words differently builds from the recipe.
    edited = {k: (v, extras[k].strip()) for k, v in p["extras"].items() if extras.get(k, v).strip() != v}
    if any(not new or v not in p["prompt"] for v, new in edited.values()):
        return None
    old = [{k: SAMPLES["cast"][c].get(k, "") for k in ("name", "pronoun", "look")} for c in p["cast"]]
    new = [o if c["ref"] == f"sample:{key}" else {k: c.get(k) or "" for k in ("name", "pronoun", "look")}
           for o, c, key in zip(old, characters, p["cast"])]
    old += [{"name": SAMPLES["objects"][o]["name"], "pronoun": "it", "look": ""} for o in p["objects"]]
    new += [{"name": o["name"], "pronoun": "it", "look": ""} for o in objects]
    # The text is the take's, with the swap made in it (the page does) or not.
    take_text = labelled(p["text"], [c["name"] for c in old])
    if labelled(text, [c["name"] for c in new]).strip() not in (swap_cast(take_text, old, new).strip(), take_text.strip()):
        return None
    prompt = p["prompt"]
    for old_value, new_value in edited.values():
        prompt = prompt.replace(old_value, new_value)
    prompt = swap_cast(prompt, old, new)
    # Every character's look in their definition and retention line, also in a take written before
    # looks were: from photos alone H3 lets clothing pass between people (an orbit with Allie and Lena
    # put both in Allie's dress, Lena's portrait showing little of her sweater).
    prompt = shots._with_looks(prompt, new[:len(characters)])
    if "scene" in take_loc and scene_name != take_loc["scene"]:
        prompt = relocate(prompt, SAMPLES["scenes"][take_loc["scene"]], scenes()[scene_name], p.get("place_words"))
    return prompt


def scene_words(spec: dict, plate_n: int) -> dict[str, str]:
    """A location's own words, as a prompt has them: {"scene": bundled name}, {"setting": a description}
    or {"image": a location ref}, whose picture is <Picture plate_n>."""
    if spec.get("scene") in scenes():
        own = scenes()[spec["scene"]]
        words = {k: v for k, v in own.items() if k in _SCENE_WORDS + ("ENVIRONMENT_PREP",)}
    elif spec.get("setting"):
        own, words = {}, shots.describe_location(spec["setting"])
        words["SOUNDSCAPE"] = "The natural ambient sound of the location"
        the_place = re.sub(r"^(a|an)\s+", "the ", words["ENVIRONMENT"], flags=re.I)
        own = {"LOCATION": the_place, "THE_SPACE": the_place}
    else:
        own = image_scene(spec.get("image"))
        words = {k: v.replace("{PLATE}", f"<Picture {plate_n}>") for k, v in shots.IMAGE_LOCATION.items()}
        words["SOUNDSCAPE"] = own.get("SOUNDSCAPE", "The natural ambient sound of the location")
    words.update({k: own.get(k) or v for k, v in shots.LOCATION_FIELDS.items()})
    return words


def relocate(prompt: str, old_sc: dict, new_sc: dict, take_words: dict[str, str] | None = None) -> str:
    """Swap one location's own words in a prompt for another's, leaving every other word alone.

    `take_words` are a take's own phrases for its location, outside the location's words (the montage
    ends with "the desert highway beyond"), each with the field it stands for (LOCATION)."""
    pairs = [(f"{old_sc.get('ENVIRONMENT_PREP', 'in')} {old_sc['ENVIRONMENT']}",
              f"{new_sc.get('ENVIRONMENT_PREP', 'in')} {new_sc['ENVIRONMENT']}")]
    pairs += [(phrase, new_sc[field]) for phrase, field in (take_words or {}).items() if new_sc.get(field)]
    # A take's style line can carry its location's light and palette ("low golden afternoon sunlight
    # cutting through the trees in shafts"): the new place's, or none for a place without them. The
    # lens stays; it belongs to the move.
    light = [k for k in ("LIGHTING", "PALETTE") if old_sc.get(k) and old_sc[k] in prompt]
    if light and all(new_sc.get(k) for k in light):
        pairs += [(old_sc[k], new_sc[k]) for k in light]
    elif light:
        prompt = prompt.replace("".join(f", {old_sc[k]}" for k in light), "")
    pairs += [(old_sc[k], new_sc[k]) for k in _SCENE_WORDS + tuple(shots.LOCATION_FIELDS)
              if old_sc.get(k) and new_sc.get(k) and old_sc[k] != new_sc[k]]
    # Longest first, through placeholders, so a short value ("the snow") is never replaced inside a
    # longer one or inside a value already swapped in.
    pairs.sort(key=lambda kv: -len(kv[0]))
    for i, (old, _) in enumerate(pairs):
        prompt = re.sub(rf"(?<![\w-]){re.escape(old)}(?![\w-])", f"\x00{i}\x00", prompt)
    for i, (_, new) in enumerate(pairs):
        prompt = prompt.replace(f"\x00{i}\x00", new)
    return prompt


_SECTION = re.compile(r"^([a-z_]+):[ \n]", re.M)


def sections(prompt: str) -> dict[str, tuple[int, int]]:
    """Where each section's words are: name -> (start, end), the heading and the blank line excluded."""
    marks = list(_SECTION.finditer(prompt))
    out = {}
    for m, nxt in zip(marks, marks[1:] + [None]):
        end = nxt.start() if nxt else len(prompt)
        out[m[1]] = (m.end(), m.end() + len(prompt[m.end():end].rstrip("\n")))
    return out


def replace_sections(prompt: str, source: str, names: list[str]) -> str:
    """`prompt` with the named sections' words taken from `source`."""
    src = sections(source)
    for name in names:
        where = sections(prompt)
        if name in where and name in src:
            s, e = where[name]
            prompt = prompt[:s] + source[src[name][0]:src[name][1]] + prompt[e:]
    return prompt


def public() -> dict:
    """What the page needs to pre-load a move: the take's inputs, not its prompt."""
    return {slug: {k: p.get(k, []) for k in ("cast", "objects", "location", "text", "extras", "seed", "width", "height",
                                            "length", "take")}
            for slug, p in PRESETS.items()}
