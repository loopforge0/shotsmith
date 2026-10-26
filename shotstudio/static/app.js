"use strict";

// The location fills the recipes' location slots, and a move's own location fields (what recedes behind
// a dolly zoom, the corridor a super dolly charges down: shots.LOCATION_FIELDS) on the server; anything
// else a move needs (a montage's inserts) shows under the text.
const LOCATION_FIELDS = ["LOCATION", "BACKGROUND", "PLACE_2", "THE_SPACE", "NEAR_OBJECTS", "FURTHER_OBJECTS", "GROUND", "LOOSE_THINGS"];
const BASE = ["ENVIRONMENT", "PLACE", "ENVIRONMENT_ELEMENTS", "LIGHTING", "PALETTE", "GEAR", "PERFORMANCE", "SOUNDSCAPE", "MUSIC",
  ...LOCATION_FIELDS];
const MAX_IMAGES = 9;   // H3: 9 reference images, 3 audio clips
const MAX_AUDIO = 3;

const FIELD = {
  SETTING: ["Location", "a snow-covered arctic shore at night, an old sailing ship anchored offshore", true],
  WHERE_IT_ENDS: ["Where it ends", "in the driver's seat of the car, the dark sunglasses on", true],
  ACTION: ["The action every panel shows", "seated at a desk typing", true],
  ACTION_SHORT: ["Action in a word or two", "typing"],
  PANEL_1_ANGLE: ["Left panel", "the person from the side in profile"],
  PANEL_2_ANGLE: ["Middle panel", "the front"],
  PANEL_3_ANGLE: ["Right panel", "the person from behind"],
};

const VOICES = {
  describe: ["Describe it", "Write how the voice sounds. H3 makes up a voice to match."],
  sample: ["Use a voice sample", "Upload a few seconds of this person speaking. H3 copies the sound of the voice and says the lines in it."],
};
const LANGUAGES = ["English", "Spanish", "French", "German", "Italian", "Portuguese", "Chinese", "Japanese", "Korean"];

const $ = (s, root = document) => root.querySelector(s);
const S = {
  config: null, elements: [], shot: null, scene: {},
  cast: [],   // refs of the characters and objects in the shot, in the order they were added
  location: { mode: "text", image: null },
  sound: { ambience: { mode: "text", audio: null, name: "" }, music: { mode: "text", audio: null, name: "" } },
  aspect: "16:9", resolution: "480p", duration: "5s", group: "all", query: "", refTab: "character",
  override: null,   // the whole H3 prompt as edited by hand in the Prompt panel; any other change drops it
};

// ---------- presets: every move starts from its approved take ----------

// ---------- the prompt model ----------
// One prompt is the shot: S.prompt, what H3 receives. The main text shows its shot lines with @tags
// for the references; the advanced prompt shows all of it. Both edit S.prompt. S.base is what the
// server gives for the current inputs (the move's tested take, swapped and moved to the location),
// so "edited" means S.prompt differs from it. A change of inputs edits S.prompt in place: a character
// swap swaps name, look and pronouns, a new location swaps the location's words, a change of who or
// what is in it rewrites only the sections that list them.

/** Where a location is, as the server's /api/relocate takes it. */
function locSpec() {
  if (S.location.mode === "image") return { image: S.location.image || "" };
  return sceneName() ? { scene: sceneName() } : { setting: S.scene.SETTING?.trim() || "" };
}

const platePos = () => (S.location.mode !== "text" ? mentioned().length + 1 : 0);
/** Does this place have words (bundled, or described from its image)? */
const hasWords = e => !!e && (e.sample || !!e.scene?.ENVIRONMENT);
const soundKey = () => JSON.stringify([S.sound, S.scene.SOUNDSCAPE || "", S.scene.MUSIC || ""]);
const inputsNow = () => ({ cast: mentioned().map(e => e.ref), loc: locSpec(), plate: platePos(), sound: soundKey() });

/** The shot lines inside detailed_description: [start, end) in the prompt. */
function shotSpan(prompt) {
  const m = /^detailed_description:\n/m.exec(prompt || "");
  if (!m) return null;
  const from = m.index + m[0].length;
  const next = /\n\n[a-z_]+:[ \n]/g;
  next.lastIndex = from;
  const n = next.exec(prompt);
  const end = n ? n.index : prompt.replace(/\n+$/, "").length;
  const first = prompt.slice(from, end).search(/\[Shot \d+\]/);
  return [from + Math.max(first, 0), end];
}

/** The prompt's labels as the main text's @tags, and back. */
function toTags(text, order, plate) {
  return text.replace(/<Subject (\d+)>/g, (all, n) => order[n - 1] ? "@" + order[n - 1].name : all)
    .replace(/<Picture (\d+)>/g, (all, n) => (Number(n) === plate ? "@Location" : all));
}

function fromTags(text, order, plate) {
  return text.replace(MENTION, (all, name) => {
    if (plate && name.toLowerCase() === "location") return `<Picture ${plate}>`;
    const i = order.findIndex(e => e.name.toLowerCase() === name.toLowerCase());
    return i < 0 ? all : `<Subject ${i + 1}>`;
  });
}

/** What the main text shows: the shot lines, tagged. A single shot drops its "[Shot 1]". */
function shotView(prompt) {
  const span = shotSpan(prompt);
  if (!span) return "";
  let text = prompt.slice(...span);
  if ((text.match(/\[Shot \d+\]/g) || []).length === 1) text = text.replace(/^\[Shot 1\] ?/, "");
  return toTags(speechToQuotes(text), mentioned(), platePos());
}

/** Write the main text back into the prompt's shot lines. */
function applyShotView(text) {
  const span = shotSpan(S.prompt);
  if (!span) return;
  let body = quotesToSpeech(fromTags(text, mentioned(), platePos()));
  if (!/\[Shot \d+\]/.test(body)) body = "[Shot 1] " + body;
  S.prompt = S.prompt.slice(0, span[0]) + body + S.prompt.slice(span[1]);
}

// Speech. H3 takes a line as <d>[English] the words</d>, its speaker marked with a stable (S1), (S2)
// after their name; the main text shows a plain quote. Where each (Sx) sat is remembered (S.speakers:
// the words just before it), so writing the text back puts them where they were. A new quote's
// speaker is the person named last before it.
const SPEECH = /:? <d>\[([^\]]+)\] ([\s\S]*?)<\/d>/g;
const SPOKEN = /"([^"\n]+)"(?: \(in ([A-Z][a-z]+)\))?|“([^”\n]+)”(?: \(in ([A-Z][a-z]+)\))?/g;

function speechToQuotes(text) {
  S.speakers = [];
  text = text.replace(/ \((S\d+)\)/g, (all, id, at, whole) => {
    S.speakers.push({ id, anchor: whole.slice(Math.max(0, at - 24), at) });
    return "";
  });
  return text.replace(SPEECH, (all, lang, words) => ` "${words}"` + (lang === "English" ? "" : ` (in ${lang})`));
}

function quotesToSpeech(text) {
  const known = S.speakers || [];
  const idOf = new Map(known.map(s => [s.anchor.match(/<Subject \d+>$/)?.[0], s.id]).filter(([k]) => k));
  let next = Math.max(0, ...known.map(s => Number(s.id.slice(1)))) + 1;
  let out = "", from = 0, line = 0;
  for (const m of text.matchAll(SPOKEN)) {
    let before = text.slice(from, m.index).replace(/ $/, "");
    const words = m[1] ?? m[3], lang = m[2] ?? m[4] ?? "English";
    // Put the speaker's (Sx) back: where it was, or after the person named last.
    const rec = known[line];
    const anchorAt = rec ? before.lastIndexOf(rec.anchor.slice(-14)) : -1;
    if (anchorAt >= 0) {
      const at = anchorAt + rec.anchor.slice(-14).length;
      before = before.slice(0, at) + ` (${rec.id})` + before.slice(at);
    } else {
      // People speak, objects do not.
      const tags = [...before.matchAll(/<Subject (\d+)>/g)].filter(x => Number(x[1]) <= castChars().length);
      const last = tags[tags.length - 1];
      if (last) {
        if (!idOf.has(last[0])) idOf.set(last[0], `S${next++}`);
        const at = last.index + last[0].length;
        before = before.slice(0, at) + ` (${idOf.get(last[0])})` + before.slice(at);
      }
    }
    // "says: <d>"; after a full stop or at the start, the line stands alone.
    out += before + (/(^|[.!?])$/.test(before) ? (before ? " " : "") : ": ") + `<d>[${lang}] ${words}</d>`;
    from = m.index + m[0].length;
    line++;
  }
  return out + text.slice(from);
}

/** The prompt with its labels renumbered for a new cast order (people who left keep their name). */
function renumber(prompt, oldRefs, oldPlate) {
  const old = oldRefs.map(element);
  const tagged = toTags(prompt, old.map(e => e || { name: "someone" }), oldPlate);
  return fromTags(tagged, mentioned(), platePos());
}

const isEdited = () => S.prompt != null && S.base != null && S.prompt !== S.base;

function showModel() {
  const ta = $("#text");
  if (document.activeElement !== ta) ta.value = shotView(S.prompt);
  paintHighlight();
}

let refreshing = null;

/** Bring S.prompt in line with the inputs, keeping any edits (see the top of this section). */
function refreshModel() {
  refreshing = (async () => {
    if (blocked()) { S.blockedKey = JSON.stringify(inputsNow()); return; }  // nothing to build until the shot is valid
    const now = inputsNow(), was = S.inputs, gen = S.gen;
    const base = (await api("/api/prompt", { ...request(), prompt_override: null })).prompt;
    if (gen !== S.gen) return;  // another move was picked meanwhile
    if (!isEdited() || !was || S.shot.group === "effects") {
      S.prompt = base;
    } else {
      let prompt = S.prompt;
      const castChanged = JSON.stringify(was.cast) !== JSON.stringify(now.cast);
      if (castChanged || was.plate !== now.plate) prompt = renumber(prompt, was.cast, was.plate);
      if (JSON.stringify(was.loc) !== JSON.stringify(now.loc) || was.plate !== now.plate) {
        prompt = (await api("/api/relocate", { prompt, old: was.loc, new: now.loc, old_plate: was.plate, new_plate: now.plate, shot: S.shot.slug })).prompt;
      }
      const sections = [];
      const sizes = l => [l.cast.length, l.plate];
      if (JSON.stringify(sizes(was)) !== JSON.stringify(sizes(now)) || castChanged) sections.push("subject_definitions", "retention_analysis", "summary");
      if (was.sound !== now.sound) sections.push("subject_definitions", "retention_analysis", "overall_soundscape", "non_diegetic_music");
      if (sections.length) prompt = (await api("/api/refit", { prompt, shot: { ...request(), prompt_override: null }, sections })).prompt;
      if (gen !== S.gen) return;
      S.prompt = prompt;
    }
    S.base = base;
    S.inputs = now;
    showModel();
  })().catch(e => explain(e)).finally(() => { refreshing = null; refreshIfChanged(); });
  return refreshing;
}

/** Refresh when an input the prompt depends on has changed since the last refresh. */
function refreshIfChanged() {
  const key = JSON.stringify(inputsNow());
  if (!refreshing && key !== JSON.stringify(S.inputs) && key !== S.blockedKey) refreshModel();
}

/** Pre-load a move with its approved take: characters, location, text, fields, seed and size. */
function loadPreset(slug) {
  const p = S.config.presets?.[slug];
  if (!p) return false;
  S.cast = [...p.cast.map(k => `sample:${k}`), ...(p.objects || []).map(k => `object:${k}`)].filter(element);
  const place = p.location.image || p.location.scene;
  S.location.mode = "both";
  S.location.image = `location:${place}`;
  S.scene = { SCENE: place };
  Object.assign(S.scene, p.extras);
  S.takeText = p.text;
  $("#seed").value = p.seed;
  S.aspect = p.width >= p.height ? "16:9" : "9:16";
  S.resolution = Object.entries(S.config.sizes[S.aspect]).find(([, wh]) => wh[0] === p.width)?.[0] || S.resolution;
  S.duration = Object.entries(S.config.durations).find(([, n]) => n === p.length)?.[0] || S.duration;
  for (const [id, key] of [["#aspect", "aspect"], ["#res", "resolution"], ["#dur", "duration"]]) paintSeg(id, S[key]);
  return true;
}

/** Put `next` in the shot where `prev` was. The server swaps them in the text, and in an advanced prompt
 * if there is one, the way it swaps them in the move's tested prompt: name, look and pronouns only. */
async function swapCast(prev, next) {
  if (prev.ref === next.ref) return;
  if (S.cast.includes(next.ref)) return toast(`${next.name} is already in the shot.`);
  // Characters and objects, in the prompt's numbering; an object is "it" either way.
  const who = e => ({ name: e.name, ref: e.ref, pronoun: e.kind === "object" ? "it" : e.pronoun || "they", look: e.look || "" });
  const before = mentioned().map(who);
  S.cast[S.cast.indexOf(prev.ref)] = next.ref;
  const after = mentioned().map(who);
  const swap = async (text, kind) => (await api("/api/swap", { text, old: before, new: after, kind })).text;
  try {
    S.takeText = await swap(S.takeText || "", "text");
    if (isEdited()) [S.prompt, S.base] = [await swap(S.prompt, "prompt"), await swap(S.base, "prompt")];
    S.inputs = { ...S.inputs, cast: inputsNow().cast };
  } catch (e) { toast(e.message); }
  await refreshModel();
}

/** A small list of characters to swap `prev` for, under the element clicked. */
function swapMenu(prev, anchor) {
  const pop = $("#mention-pop");
  const items = S.elements.filter(e => e.kind === prev.kind && e.ref !== prev.ref);
  pop.replaceChildren(h("div", { class: "pm-head" }, `Swap ${prev.name} for`), ...items.map(e => h("button", {
    type: "button", class: "pm", onmousedown: ev => { ev.preventDefault(); pop.hidden = true; swapCast(prev, e); },
  }, h("img", { src: e.img, alt: "" }), h("span", {}, e.name), h("small", {}, S.cast.includes(e.ref) ? "in shot" : e.kind))),
  h("button", { type: "button", class: "pm", onmousedown: ev => { ev.preventDefault(); pop.hidden = true; openPanel("references", { tab: prev.kind }); } },
    h("i", { class: "pm-line" }, "+"), h("span", {}, "Upload a new one…"), h("small", {}, "")));
  pop.items = null;
  pop.hidden = false;
  anchor?.focus?.();
}

// ---------- helpers ----------

function h(tag, attrs = {}, ...kids) {
  const n = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (v === undefined || v === null || v === false) continue;
    if (k === "class") n.className = v;
    else if (k === "style") n.style.cssText = v;
    else if (k.startsWith("on")) n.addEventListener(k.slice(2), v);
    else n.setAttribute(k, v === true ? "" : v);
  }
  for (const kid of kids.flat()) if (kid !== null && kid !== undefined && kid !== false) n.append(kid);
  return n;
}

async function api(path, body) {
  const res = await fetch(path, body === undefined ? {} : {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const d = data.detail;
    const err = new Error(typeof d === "string" ? d : d?.message || res.statusText);
    err.missing = d?.missing || [];
    throw err;
  }
  return data;
}

/** Run a background job (describing a photo, making an image) and show how it is going on the
 * button: the stage, a bar filling as it counts steps, and the seconds left once that rate is known. */
async function followTask(btn, path, body) {
  const label = btn.textContent;
  let job = await api(path, body);
  btn.classList.add("working");
  btn.disabled = true;
  try {
    for (;;) {
      const pct = Math.round(job.progress * 100);
      const left = job.seconds_left != null ? ` · about ${Math.max(1, job.seconds_left)} s left` : "";
      btn.textContent = `${cap(job.stage)}… ${pct ? pct + "%" : job.elapsed + " s"}${pct ? left : ""}`;
      btn.style.setProperty("--done", `${pct}%`);
      if (job.status === "succeeded") return job.result;
      if (job.status === "failed") throw new Error(job.error);
      await new Promise(r => setTimeout(r, 400));
      job = await api(`${path}/${job.id}`);
    }
  } finally {
    btn.classList.remove("working");
    btn.style.removeProperty("--done");
    btn.textContent = label;
    btn.disabled = false;
  }
}

const describeImage = (btn, ref, kind) => followTask(btn, "/api/describe", { ref, kind });

async function uploadFile(f) {
  const body = new FormData();
  body.append("file", f);
  const res = await fetch("/api/upload", { method: "POST", body });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || res.statusText);
  return data;
}

function toast(msg) {
  const t = $("#toast");
  t.hidden = !msg;
  t.textContent = msg || "";
  clearTimeout(toast.timer);
  if (msg) toast.timer = setTimeout(() => { t.hidden = true; }, 7000);
}

const cap = s => s[0].toUpperCase() + s.slice(1);
const fmt = s => (s >= 60 ? `${Math.floor(s / 60)}m ${String(s % 60).padStart(2, "0")}s` : `${s}s`);
const esc = s => s.replace(/[&<>]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;" })[c]);
const element = ref => S.elements.find(e => e.ref === ref);
const byName = name => S.elements.find(e => e.kind !== "location" && e.name.toLowerCase() === name.toLowerCase());
const shotBySlug = slug => S.config.shots.find(s => s.slug === slug);
const extraSlots = () => S.shot.slots.filter(s => !BASE.includes(s));
const short = (s, n = 28) => (s.length > n ? s.slice(0, n).trimEnd() + "…" : s);

// ---------- mentions ----------

const MENTION = /@([A-Za-z0-9_-]+)/g;
const QUOTE = /"[^"\n]+"|“[^”\n]+”/g;   // what characters say, written in quotes

/** The cast, in the order H3 will number it: characters first, then objects. */
function mentioned() {
  const all = S.cast.map(element).filter(Boolean);
  return [...all.filter(e => e.kind === "character"), ...all.filter(e => e.kind === "object")];
}

const castChars = () => mentioned().filter(e => e.kind === "character");

function addToCast(e) {
  if (S.cast.includes(e.ref)) return true;
  if (e.kind === "character" && castChars().length >= 3) {
    toast("A shot takes at most 3 characters.");
    return false;
  }
  S.cast.push(e.ref);
  return true;
}

function removeFromCast(e) {
  const ta = $("#text");
  ta.value = ta.value.replace(new RegExp(`@${e.name}\\b`, "gi"), e.name);
  applyShotView(ta.value);
  S.cast = S.cast.filter(r => r !== e.ref);
}

/** Anything typed as @Name joins the cast. */
function syncCastFromText() {
  for (const m of $("#text").value.matchAll(MENTION)) {
    const e = byName(m[1]);
    if (e && e.kind !== "recording" && !S.cast.includes(e.ref)) addToCast(e);
  }
}

function unknownMentions() {
  return [...$("#text").value.matchAll(MENTION)].map(m => m[1])
    .filter(n => !byName(n) && !(n.toLowerCase() === "location" && platePos()));
}

/** The location's own words in the shot text, marked like a tag. */
function placeWords() {
  const sc = S.location.mode !== "image" && S.config.samples.scenes[sceneName()];
  if (!sc) return [];
  const keys = ["ENVIRONMENT", "PLACE", "ENVIRONMENT_ELEMENTS", ...LOCATION_FIELDS];
  return [...new Set(keys.map(k => sc[k]).filter(v => v && v.length > 3))].sort((a, b) => b.length - a.length);
}

function paintHighlight() {
  const ta = $("#text");
  syncCastFromText();
  const order = mentioned();
  let marked = esc(ta.value)
    .replace(QUOTE, said => `<mark class="said">${said}</mark>`)
    .replace(MENTION, (all, name) => `<mark class="${byName(name)?.kind || (name.toLowerCase() === "location" && platePos() ? "place" : "bad")}">${all}</mark>`);
  // The location's own words last, so the quote and tag marks never see this mark's attribute quotes.
  const place = placeWords().map(esc);
  if (place.length) {
    const re = new RegExp(place.map(w => w.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")).join("|"), "g");
    marked = marked.replace(re, w => `<mark class="place">${w}</mark>`);
  }
  $("#hl").innerHTML = marked + "\n";
  $("#hl").scrollTop = ta.scrollTop;
  $("#refs").replaceChildren(...order.map((e, i) => h("span", {
    class: "ref " + e.kind, title: `${e.name} is <Picture ${i + 1}> in the prompt. Click to swap in someone else.`,
    onclick: ev => { if (!ev.target.closest(".rm")) swapMenu(e, ev.currentTarget); },
  }, h("img", { src: e.img, alt: "" }), e.name,
    h("button", { type: "button", class: "rm", title: `Take ${e.name} out of the shot`,
      onclick: () => { removeFromCast(e); paintHighlight(); } }, "✕"))));
  $("#refs").hidden = !order.length;
  renderChips();
  refreshIfChanged();
}

function caretWord() {
  const ta = $("#text");
  const before = ta.value.slice(0, ta.selectionStart);
  const m = before.match(/@([A-Za-z0-9_-]*)$/);
  return m ? { start: before.length - m[0].length, query: m[1] } : null;
}

let popupIndex = 0;

function paintPopup() {
  const pop = $("#mention-pop");
  const w = caretWord();
  if (!w) { pop.hidden = true; return; }
  const q = w.query.toLowerCase();
  const items = S.elements.filter(e => e.kind !== "location" && e.name.toLowerCase().startsWith(q));
  if (!items.length) { pop.hidden = true; return; }
  popupIndex = Math.min(popupIndex, items.length - 1);
  pop.replaceChildren(...items.map((e, i) => h("button", {
    type: "button", class: "pm" + (i === popupIndex ? " on" : ""),
    onmousedown: ev => { ev.preventDefault(); insertMention(e.name, w); },
  }, e.img ? h("img", { src: e.img, alt: "" }) : h("i", { class: "pm-line" }, "♪"),
    h("span", {}, e.name, e.words ? h("em", {}, `“${e.words.slice(0, 28)}${e.words.length > 28 ? "…" : ""}”`) : null),
    h("small", {}, e.kind))));
  pop.hidden = false;
  pop.items = items;
}

function insertMention(name, w = caretWord()) {
  const ta = $("#text");
  const pos = w ? ta.selectionStart : (document.activeElement === ta ? ta.selectionStart : ta.value.length);
  const start = w ? w.start : pos;
  const needsSpace = !w && start > 0 && !/\s/.test(ta.value[start - 1]);
  const insert = (needsSpace ? " " : "") + "@" + name + " ";
  ta.value = ta.value.slice(0, start) + insert + ta.value.slice(pos);
  const caret = start + insert.length;
  ta.focus();
  ta.setSelectionRange(caret, caret);
  $("#mention-pop").hidden = true;
  paintHighlight();
}

function onTextKey(e) {
  const pop = $("#mention-pop");
  if (pop.hidden || !pop.items) return false;
  if (e.key === "ArrowDown" || e.key === "ArrowUp") {
    e.preventDefault();
    popupIndex = (popupIndex + (e.key === "ArrowDown" ? 1 : -1) + pop.items.length) % pop.items.length;
    paintPopup();
  } else if (e.key === "Enter" || e.key === "Tab") {
    e.preventDefault();
    insertMention(pop.items[popupIndex].name);
  } else if (e.key === "Escape") {
    pop.hidden = true;
  } else return false;
  return true;
}

// ---------- composer ----------

function chip(key, label, value, sw, need, tip) {
  return h("button", { type: "button", class: "chip" + (need ? " need" : ""), title: tip, onclick: () => openPanel(key) },
    h("span", { class: "sw", style: sw?.style }, sw?.text || ""),
    h("span", {}, h("span", { class: "t" }, label), h("span", { class: "v" }, value)));
}

function imageCount() {
  return mentioned().length + (S.location.mode !== "text" && S.location.image ? 1 : 0);
}

function renderChips() {
  const s = S.shot;
  const chars = castChars();
  const locImg = S.location.mode !== "text" ? element(S.location.image) : null;
  const n = imageCount();
  const [lo, hi] = s.cast;
  $("#chips").replaceChildren(
    chip("references", "Cast", chars.length ? mentioned().map(e => e.name).join(", ") : "Add a character",
      chars[0] ? { style: `background-image:url(${chars[0].img})` } : { text: "@" },
      chars.length < lo || chars.length > hi || n > MAX_IMAGES,
      `Who and what is in the shot (${n} of H3's ${MAX_IMAGES} reference images used). ${cap(s.name)} takes ${castText(s)}.`),
    chip("camera", "Camera move", cap(s.name), s.still ? { style: `background-image:url(${s.still})` } : { text: "✥" },
      extraSlots().some(k => !S.scene[k]?.trim()), "The named camera move. Type # in the text to change it."),
    chip("location", S.location.mode === "text" ? "Location · words only" : "Location", S.location.mode !== "text" ? (locImg?.name || "Choose a place") : short(sceneName() || S.scene.SETTING?.trim() || "Describe it"),
      locImg ? { style: `background-image:url(${locImg.img})` } : sceneName() && element(`location:${sceneName()}`)
        ? { style: `background-image:url(${element(`location:${sceneName()}`).img})` } : { text: "⌖" },
      S.location.mode !== "text" ? !locImg : !(sceneName() || S.scene.SETTING?.trim()),
      "Where the shot happens: an image, or a description."),
    chip("sound", "Sound", soundText(), { text: "♪" }, false,
      "Background sound and music. Optional."));

  const min = s.length;
  for (const b of $("#dur").children) {
    const too = S.config.durations[b.dataset.v] < min;
    b.disabled = too;
    b.title = too ? `${cap(s.name)} needs at least ${Math.round(min / 24)}s` : "Length of the clip";
    if (too && S.duration === b.dataset.v) S.duration = b.nextElementSibling?.dataset.v || S.duration;
  }
  paintSeg("#dur", S.duration);
  $("#prompt-btn").textContent = isEdited() ? "Advanced prompt · edited" : "Advanced prompt";
  $("#prompt-btn").classList.toggle("edited", isEdited());
}

function soundText() {
  const layer = (key, slot) => {
    const L = S.sound[key];
    return L.mode === "audio" ? (L.audio ? L.name : "") : S.scene[slot]?.trim() || "";
  };
  return short([layer("ambience", "SOUNDSCAPE"), layer("music", "MUSIC")].filter(Boolean).join(" · ") || "Natural sound");
}

function castText(s) {
  const [lo, hi] = s.cast;
  return lo === hi ? `${lo} character${lo > 1 ? "s" : ""}` : `${lo} to ${hi} characters`;
}

function seg(id, values, key, tips) {
  $(id).replaceChildren(...values.map(v => h("button", {
    type: "button", "data-v": v, title: tips?.[v], onclick: () => { S[key] = v; paintSeg(id, v); },
  }, v)));
  paintSeg(id, S[key]);
}

function paintSeg(id, v) {
  for (const b of $(id).children) b.classList.toggle("on", b.dataset.v === v);
}

function modeSeg(current, modes, onPick) {
  return h("div", { class: "seg mode" }, ...modes.map(([m, label, tip]) => h("button", {
    type: "button", class: m === current ? "on" : "", title: tip, onclick: () => onPick(m),
  }, label)));
}

function selectShot(slug, { preset = true } = {}) {
  S.shot = shotBySlug(slug);
  const loaded = preset && loadPreset(slug);
  const effect = S.shot.group === "effects";
  // An effect runs its approved prompt: only who is in it and where can change.
  $("#text").hidden = effect;
  $("#hl").hidden = effect;
  $("#effect-note").hidden = !effect;
  $("#effect-note").textContent = effect ? `${cap(S.shot.name)} runs its tested prompt. Choose who is in it and where.` : "";
  if (!loaded) S.takeText = "";
  S.prompt = S.base = S.inputs = null;
  S.gen = (S.gen || 0) + 1;
  S.blockedKey = null;
  $("#text").value = "";
  paintHighlight();  // which builds the new move's prompt (refreshIfChanged)
  if (loaded) toast("");
}

/** Pick a bundled scene. A move field still holding the old scene's own words (a split screen's action
 * and angles) takes the new scene's, where it has them. */
function switchScene(name) {
  const scenes = S.config.samples.scenes, old = scenes[S.scene.SCENE] || {}, now = scenes[name] || {};
  for (const k of extraSlots()) if (old[k] && S.scene[k] === old[k] && now[k]) S.scene[k] = now[k];
  S.scene.SCENE = name;
}

/** Locations people added and had described join the bundled scenes, as text-mode places too. */
function addedScenes() {
  for (const e of S.elements) {
    if (e.kind === "location" && !e.sample && e.scene?.ENVIRONMENT) S.config.samples.scenes[e.name] = { ...e.scene, image: e.img };
  }
}

/** Is the text-mode location set, as a description or a bundled scene? */
const sceneName = () => S.scene.SCENE && S.config.samples.scenes[S.scene.SCENE] ? S.scene.SCENE : "";

// ---------- panels ----------

function openPanel(name, opts = {}) {
  const panels = { references, camera, location: locationPanel, sound, voices, prompt: promptPanel, viewer };
  $("#modal").className = "modal" + (["camera", "viewer", "references", "location"].includes(name) ? " wide" : "");
  panels[name](opts);
  $("#scrim").hidden = false;
}

function closePanel() {
  $("#scrim").hidden = true;
  $("#modal-body").replaceChildren();
  paintHighlight();
}

function setPanel(title, ...content) {
  $("#modal-title").textContent = title;
  $("#modal-body").replaceChildren(h("div", { class: "pane" }, ...content));
}

function fieldFor(slot, onChange) {
  const [label, ph, full] = FIELD[slot] || [cap(slot.toLowerCase().replace(/_/g, " ")), ""];
  const ta = h("textarea", { rows: full ? 2 : 1, placeholder: ph, oninput: e => { S.scene[slot] = e.target.value; onChange?.(); } });
  ta.value = S.scene[slot] || "";
  return h("div", { class: "field" + (full ? " full" : "") }, h("label", {}, label), ta);
}

// A tile with a preview plays it, silent and looping, while the pointer is over it.
function tile({ img, name, sub, on, order, onclick, wide, tip, preview }) {
  const video = preview ? h("video", { src: preview, muted: true, loop: true, playsinline: true, preload: "none" }) : null;
  if (video) video.muted = true;
  const hover = video ? {
    onmouseenter: () => { video.play().then(() => video.classList.add("playing")).catch(() => {}); },
    onmouseleave: () => { video.pause(); video.currentTime = 0; video.classList.remove("playing"); },
  } : {};
  return h("button", { type: "button", class: "tile" + (wide ? " wide" : "") + (on ? " on" : ""), onclick, title: tip, ...hover },
    h("span", { class: "img" + (img ? "" : " none"), style: img ? `background-image:url(${img})` : "" },
      video, order ? h("span", { class: "order" }, order) : null),
    h("span", { class: "name" }, name), sub ? h("span", { class: "sub" }, sub) : null);
}

function uploadTile(accept, onFile, wide = false, tip = "Upload an image") {
  const file = h("input", { type: "file", accept, hidden: true, onclick: e => e.stopPropagation(), onchange: e => onFile(e.target.files[0]) });
  return h("button", { type: "button", class: "tile" + (wide ? " wide" : ""), title: tip, onclick: () => file.click() },
    h("span", { class: "img add" }, "+"), h("span", { class: "name" }, "Upload"), file);
}

function references({ tab } = {}) {
  if (tab) S.refTab = tab;
  const pane = h("div", { class: "pane" });
  let draft = null;

  const save = async () => {
    try {
      if (S.refTab === "recording" && !draft.words.trim()) return toast("Type the words that are in the recording.");
      await api("/api/elements", { ref: draft.ref, name: draft.name.trim(), kind: S.refTab, pronoun: draft.pronoun, type: draft.type || "person", look: draft.look || "",
        words: draft.words.trim(), language: draft.language });
      S.elements = await api("/api/elements");
      const name = draft.name.trim();
      draft = null;
      const saved = S.elements.find(e => e.name === name);
      if (saved && saved.kind !== "recording") addToCast(saved);
      paint();
    } catch (e) { toast(e.message); }
  };

  const editor = () => {
    if (!draft) return "";
    const name = h("input", { type: "text", placeholder: { character: "Mara", object: "Teapot", recording: "Toast" }[S.refTab], maxlength: 32,
      title: "One word. You will type @ and this name to use it.",
      oninput: e => { draft.name = e.target.value.replace(/[^A-Za-z0-9_-]/g, ""); e.target.value = draft.name; } });
    const pron = h("select", { title: "Used when the prompt refers back to this character", onchange: e => { draft.pronoun = e.target.value; } },
      ...["they", "she", "he"].map(p => h("option", { value: p }, p)));
    const look = h("input", { type: "text", maxlength: 300, placeholder: "short red hair, a green bomber jacket",
      title: "Hair and clothing in a few words. With two or three characters, this keeps each person's outfit their own.",
      oninput: e => { draft.look = e.target.value; } });
    look.value = draft.look || "";
    name.value = draft.name || "";
    pron.value = draft.pronoun || "they";
    const fill = h("button", { type: "button", class: "btn",
      title: "Qwen3-VL reads the photo and writes the look the way the bundled characters have it. About 10 seconds; check it before saving.",
      onclick: async e => {
        const btn = e.currentTarget;
        btn.disabled = true;
        try {
          const got = await describeImage(btn, draft.ref, "character");
          Object.assign(draft, { look: got.look || draft.look, type: got.type || draft.type });
          paint();
        } catch (err) { toast(err.message); btn.disabled = false; btn.textContent = "Fill in from the photo"; }
      } }, "Fill in from the photo");
    const rec = S.refTab === "recording";
    const words = h("textarea", { rows: 2, placeholder: "The words in the recording, exactly", oninput: e => { draft.words = e.target.value; } });
    const lang = h("select", { onchange: e => { draft.language = e.target.value; } }, ...LANGUAGES.map(x => h("option", { value: x }, x)));
    return h("div", { class: "newchar" },
      rec ? h("audio", { class: "plate", src: draft.img, controls: true }) : h("div", { class: "plate", style: `background-image:url(${draft.img})` }),
      h("div", { class: "form tight" },
        h("div", { class: "field" }, h("label", {}, "Name"), name),
        S.refTab === "character" ? h("div", { class: "field" }, h("label", {}, "Pronoun"), pron) : "",
        S.refTab === "character" ? h("div", { class: "field full" }, h("label", {}, "Look ", h("small", { class: "hint" }, "recommended"), ), look) : "",
        S.refTab === "character" ? h("div", { class: "field full" }, fill) : "",
        rec ? h("div", { class: "field" }, h("label", {}, "Language"), lang) : "",
        rec ? h("div", { class: "field full" }, h("label", {}, "Words"), words) : "",
        h("div", { class: "field full row-end" },
          h("button", { type: "button", class: "btn", onclick: () => { draft = null; paint(); } }, "Cancel"),
          h("button", { type: "button", class: "btn primary", onclick: save }, "Save"))));
  };

  const paint = () => {
    const order = mentioned();
    pane.replaceChildren(
      modeSeg(S.refTab, [["character", "Characters", "People who appear in the shot"], ["object", "Objects", "Things that must appear in the shot"],
        ["recording", "Recordings", "A line already recorded. H3 reuses the audio and lip-syncs the speaker to it."]],
        m => { S.refTab = m; draft = null; paint(); }),
      h("div", { class: "tiles" },
        ...S.elements.filter(e => e.kind === S.refTab).map(e => {
          if (e.kind === "recording") return tile({ name: e.name, sub: `“${e.words}”`,
            tip: `Type @${e.name} in the text where it is spoken, after who says it. Click to put it at the cursor.`,
            onclick: () => { closePanel(); insertMention(e.name, null); } });
          const idx = order.indexOf(e);
          return tile({
            img: e.img, name: e.name, on: idx >= 0, order: idx >= 0 ? idx + 1 : null,
            tip: idx >= 0 ? `In the shot as <Picture ${idx + 1}>. Click to take it out.` : `Put ${e.name} in the shot. Type @${e.name} to refer to it in the text.`,
            onclick: () => { if (idx >= 0) removeFromCast(e); else addToCast(e); paint(); paintHighlight(); },
          });
        }),
        uploadTile(S.refTab === "recording" ? "audio/*" : "image/png,image/jpeg,image/webp", async f => {
          try {
            const up = await uploadFile(f);
            draft = { ref: up.ref, img: up.url, name: "", pronoun: "they", type: "person", look: "", words: "", language: "English" };
            paint();
          } catch (e) { toast(e.message); }
        }, false, { character: "Upload a photo of a person", object: "Upload a photo of an object",
          recording: "Upload a recording of the line" }[S.refTab])),
      editor());
  };
  paint();
  $("#modal-title").textContent = `Cast in this shot · ${cap(S.shot.name)} takes ${castText(S.shot)}`;
  $("#modal-body").replaceChildren(pane);
}

function camera() {
  const pane = h("div", { class: "pane" });
  const paint = () => {
    const groups = ["all", ...new Set(S.config.shots.map(s => s.group))];
    const q = S.query.toLowerCase();
    const list = S.config.shots.filter(s =>
      (S.group === "all" || s.group === S.group) && (!q || s.name.toLowerCase().includes(q)));
    const search = h("input", {
      class: "search", type: "search", placeholder: "Search", value: S.query,
      oninput: e => { S.query = e.target.value; paint(); $(".search", pane).focus(); },
    });
    pane.replaceChildren(
      h("div", { class: "toolbar" },
        h("div", { class: "filters" }, ...groups.map(g => h("button", {
          type: "button", class: "f" + (g === S.group ? " on" : ""), onclick: () => { S.group = g; paint(); },
        }, g))), search),
      h("div", { class: "tiles" }, ...list.map(s => tile({
        img: s.still, preview: s.preview, name: cap(s.name), wide: true, on: s.slug === S.shot.slug,
        sub: castText(s),
        tip: s.cast[1] === 1 ? "A one-person move: the camera locks onto one face. Objects they hold are fine." : s.cast[0] > 1 ? `Needs exactly ${s.cast[0]} characters, in cast order` : "Works with one character, or with a group of two or three",
        onclick: () => { selectShot(s.slug); paint(); },
      }))),
      S.shot.note ? h("div", { class: "section" }, h("h3", {}, cap(S.shot.name)), h("p", { class: "note" }, S.shot.note)) : "");
  };
  paint();
  $("#modal-title").textContent = "Camera move";
  $("#modal-body").replaceChildren(pane);
}

function locationPanel() {
  const pane = h("div", { class: "pane" });
  const L = S.location;
  let draft = null;   // a new image (uploaded or made) being named and described
  let words = sceneName() ? "" : S.scene.SETTING || "";

  // Every location: the bundled ones and the ones added. Each has a picture; most also have words.
  const places = () => S.elements.filter(e => e.kind === "location")
    .map(e => ({ ...e, words: e.sample || !!e.scene?.ENVIRONMENT }));
  const chosen = () => L.mode !== "text" ? places().find(e => e.ref === L.image)
    : places().find(e => e.words && e.name === sceneName());

  const pick = (e, mode = L.mode) => {
    L.image = e.ref;
    L.mode = !e.words ? "image" : mode === "text" ? "text" : "both";
    if (e.words) { switchScene(e.name); S.scene.SETTING = ""; }
    paint();
  };

  const save = async () => {
    if (!draft.name.trim()) return toast("Give the location a name.");
    try {
      await api("/api/elements", { ref: draft.ref, name: draft.name.trim(), kind: "location", scene: draft.scene || {} });
      S.elements = await api("/api/elements");
      addedScenes();
      const saved = places().find(e => e.ref === draft.ref);
      draft = null;
      if (saved) pick(saved, saved.words ? "text" : "image");
      else paint();
    } catch (e) { toast(e.message); }
  };

  const describeBtn = target => h("button", { type: "button", class: "btn",
    title: "Qwen3-VL reads the image and writes the place the way the bundled locations have it: what is around, its sound, what a camera move passes. Then the place can be used as words, which keeps the full camera move. About 20 seconds.",
    onclick: async e => {
      try {
        target.scene = await describeImage(e.currentTarget, target.ref, "location");
        if (!draft) {  // a saved location: keep its words
          await api("/api/elements", { ref: target.ref, name: target.name, kind: "location", scene: target.scene });
          S.elements = await api("/api/elements");
          addedScenes();
        }
        paint();
      } catch (err) { toast(err.message); }
    } }, "Describe it from the image (recommended)");

  const how = () => {
    const c = chosen();
    if (!c && L.mode === "text" && S.scene.SETTING?.trim()) return h("p", { class: "note" }, "Using your own words, below.");
    if (!c) return "";
    return h("div", { class: "how" },
      c.words ? modeSeg(L.mode, [
        ["both", "Picture and words", "H3 gets the place's picture, described by its words, as a character gets a photo and a look."],
        ["text", "Words only", "H3 imagines the place from its words alone, without the picture."],
      ], m => pick(c, m)) : h("span", { class: "hint" }, "Picture only, until it is described."),
      h("span", { class: "hint" }, L.mode === "text" ? `${cap(S.config.samples.scenes[c.name]?.ENVIRONMENT || c.name)}.`
        : L.mode === "both" ? "The picture, and its words." : "The picture alone."),
      c.words ? "" : describeBtn(c));
  };

  const make = async btn => {
    if (!words.trim()) return toast("Describe the place first.");
    try {
      const up = await followTask(btn, "/api/locations/generate", { description: words });
      draft = { ref: up.ref, img: up.url, name: "" };
      paint();
    } catch (e) { toast(e.message); }
  };

  const newPlace = () => draft
    ? h("div", { class: "newloc" }, h("img", { src: draft.img, alt: "" }),
      h("div", { class: "field" }, h("label", {}, "Name"),
        h("input", { type: "text", value: draft.name, placeholder: "Harbour", oninput: e => { draft.name = e.target.value; } })),
      draft.scene ? h("p", { class: "note scene-words" },
        `${cap(draft.scene.ENVIRONMENT || "")}. Around: ${draft.scene.ENVIRONMENT_ELEMENTS || "?"}. Sound: ${draft.scene.SOUNDSCAPE || "?"}.`)
        : describeBtn(draft),
      h("button", { type: "button", class: "btn", onclick: () => { draft = null; paint(); } }, "Cancel"),
      h("button", { type: "button", class: "btn primary", onclick: save }, "Save"))
    : h("div", { class: "section" }, h("h3", {}, "A new place"),
      h("div", { class: "makeloc" },
        h("textarea", { rows: 2, placeholder: "a 1950s diner at night, neon in the windows, rain on the glass",
          oninput: e => { words = e.target.value; } }, words),
        h("div", { class: "makeloc-btns" },
          h("button", { type: "button", class: "btn", title: "Use the description as it is. Keeps the full camera move.",
            onclick: () => {
              if (!words.trim()) return toast("Describe the place first.");
              L.mode = "text"; delete S.scene.SCENE; S.scene.SETTING = words.trim(); paint();
            } }, "Use these words"),
          h("button", { type: "button", class: "btn", title: "Make a picture of it with Qwen Image 2.1 turbo on the same ComfyUI (about 20 seconds once loaded), then name it and keep it with your locations.",
            onclick: e => make(e.currentTarget) }, "Make an image"))),
      h("p", { class: "note" }, "Or upload a photo of a place, with nobody in it, from the + tile above. Where the characters are in the place, if it matters, goes in the main text."));

  const paint = () => {
    const c = chosen();
    pane.replaceChildren(
      h("div", { class: "tiles" },
        ...places().map(e => tile({
          img: e.img, name: e.name, wide: true, on: c?.ref === e.ref && !draft,
          sub: e.words ? "" : "picture only",
          onclick: () => { draft = null; pick(e); },
        })),
        uploadTile("image/png,image/jpeg,image/webp", async f => {
          try {
            const up = await uploadFile(f);
            draft = { ref: up.ref, img: up.url, name: "" };
            paint();
          } catch (e) { toast(e.message); }
        }, true, "Upload a photo of a place, with nobody in it")),
      how(),
      newPlace());
  };
  paint();
  $("#modal-title").textContent = "Location";
  $("#modal-body").replaceChildren(pane);
}

function sound() {
  const pane = h("div", { class: "pane" });
  const layer = (key, slot, title, placeholder, emptyTip, audioTip) => {
    const L = S.sound[key];
    let body;
    if (L.mode === "text") {
      const ta = h("textarea", { rows: 2, placeholder, title: emptyTip, oninput: e => { S.scene[slot] = e.target.value; } });
      ta.value = S.scene[slot] || "";
      body = h("div", { class: "form one" }, h("div", { class: "field full" }, ta));
    } else if (L.audio) {
      body = h("div", { class: "clip" }, h("audio", { src: `/uploads/${L.audio}`, controls: true }), h("span", {}, L.name),
        h("button", { type: "button", class: "btn", onclick: () => { Object.assign(L, { audio: null, name: "" }); paint(); } }, "Remove"));
    } else {
      const file = h("input", { type: "file", accept: "audio/*", hidden: true, onclick: e => e.stopPropagation(), onchange: async e => {
        try {
          const up = await uploadFile(e.target.files[0]);
          Object.assign(L, { audio: up.ref, name: e.target.files[0].name });
          paint();
        } catch (err) { toast(err.message); }
      } });
      body = h("button", { type: "button", class: "btn", title: audioTip, onclick: () => file.click() }, "Choose a clip…", file);
    }
    return [h("h3", { class: "sec" }, title),
      modeSeg(L.mode, [["text", "Describe it", emptyTip], ["audio", "Use a clip", audioTip]], m => { L.mode = m; paint(); }),
      body];
  };
  const paint = () => pane.replaceChildren(
    ...layer("ambience", "SOUNDSCAPE", "Ambience", "Wind through the pines, distant birdsong",
      "Leave empty for the natural sound of the location", "H3 reuses the clip's background sound under the shot"),
    h("div", { style: "height:18px" }),
    ...layer("music", "MUSIC", "Music", "A slow solo piano melody",
      "Leave empty for no music", "H3 reuses the clip as the shot's music"),
    h("p", { class: "note" }, `Clips here count toward H3's ${MAX_AUDIO} audio clips, with voice samples and recordings.`));
  paint();
  $("#modal-title").textContent = "Sound";
  $("#modal-body").replaceChildren(pane);
}

function voices() {
  const pane = h("div", { class: "pane" });
  const chars = castChars();
  const save = async c => {
    try {
      await api("/api/voices", { ref: c.ref, voice: c.voice, voice_audio: c.voice_audio, language: c.language });
    } catch (err) { toast(err.message); }
  };

  const card = c => {
    c.voiceMode ??= c.voice_audio ? "sample" : "describe";
    const lang = h("select", { title: "The language this character speaks in", onchange: e => { c.language = e.target.value; save(c); } },
      ...LANGUAGES.map(x => h("option", { value: x }, x)));
    lang.value = c.language || "English";
    const file = h("input", { type: "file", accept: "audio/*", hidden: true, onclick: e => e.stopPropagation(), onchange: async e => {
      try {
        const up = await uploadFile(e.target.files[0]);
        Object.assign(c, { voice_audio: up.ref, voice: "" });
        await save(c);
        paint();
      } catch (err) { toast(err.message); }
    } });
    let how;
    if (c.voiceMode === "describe") {
      how = h("input", { type: "text", placeholder: "a low, calm, slightly husky voice",
        title: "Leave empty and H3 picks a voice", onchange: e => { c.voice = e.target.value.trim(); c.voice_audio = null; save(c); } });
      how.value = c.voice || "";
    } else if (c.voice_audio) {
      how = h("div", { class: "clip" }, h("audio", { src: `/uploads/${c.voice_audio}`, controls: true }),
        h("button", { type: "button", class: "btn", onclick: () => { c.voice_audio = null; save(c); paint(); } }, "Remove"));
    } else {
      how = h("button", { type: "button", class: "btn", title: VOICES.sample[1], onclick: () => file.click() }, "Choose a voice sample…", file);
    }
    return h("div", { class: "line voice" },
      h("div", { class: "line-top" }, h("img", { class: "face", src: c.img, alt: "" }), h("b", {}, c.name),
        h("div", { class: "field" }, lang)),
      modeSeg(c.voiceMode, Object.entries(VOICES).map(([k, [label, tip]]) => [k, label, tip]), m => { c.voiceMode = m; paint(); }),
      how);
  };

  const paint = () => pane.replaceChildren(
    ...(chars.length ? chars.map(card) : [h("p", { class: "note" }, "Add a character to the shot first.")]),
    h("p", { class: "note" }, 'Write what characters say in the text, in quotes: @Amber turns to @Kate and says "This was my grandfather\'s." ' +
      'Say "off screen" or "in a voiceover" and their lips stay closed. To use a line already recorded, add it under References › Recordings. ' +
      "Each character keeps their voice in every shot."));
  paint();
  $("#modal-title").textContent = "Voices";
  $("#modal-body").replaceChildren(pane);
}

function request() {
  return {
    shot: S.shot.slug,
    text: (S.takeText || "").match(MENTION)?.every(m => byName(m.slice(1)) && S.cast.includes(byName(m.slice(1)).ref)) === false ? "" : S.takeText || "",
    mentions: mentioned().map(e => ({ name: e.name, ref: e.ref, kind: e.kind, pronoun: e.pronoun || "they", type: e.type || "person", look: e.look || "",
      voice: e.voiceMode === "sample" ? "" : e.voice || "", voice_audio: e.voiceMode === "describe" ? null : e.voice_audio || null,
      language: e.language || "English" })).concat(S.elements
      .filter(e => e.kind === "recording" && new RegExp(`@${e.name}\\b`, "i").test(S.takeText || ""))
      .map(e => ({ name: e.name, ref: e.ref, kind: "recording", words: e.words, language: e.language || "English" }))),
    scene: S.scene,
    location: { ref: S.location.mode !== "text" ? S.location.image : null },
    ambience_audio: S.sound.ambience.mode === "audio" ? S.sound.ambience.audio : null,
    music_audio: S.sound.music.mode === "audio" ? S.sound.music.audio : null,
    aspect: S.aspect, resolution: S.resolution, duration: S.duration,
    seed: $("#seed").value === "" ? null : Number($("#seed").value),
    prompt_override: S.shot.group === "effects" ? null : S.prompt,
  };
}

function blocked() {
  const bad = unknownMentions();
  if (bad.length) return `@${bad[0]} is not a character or object you have. Add it under References, or fix the name.`;
  const chars = castChars().length;
  const [lo, hi] = S.shot.cast;
  if (chars < lo || chars > hi) return `${cap(S.shot.name)} takes ${castText(S.shot)}; the shot has ${chars}.`;
  if (imageCount() > MAX_IMAGES) return `H3 takes at most ${MAX_IMAGES} reference images.`;
  if (S.location.mode !== "text" && !S.location.image) return "Choose a location, or describe one.";
  if (S.location.mode === "text" && !sceneName() && !S.scene.SETTING?.trim()) return "Describe the location, or choose an image of it.";
  for (const [key, L] of Object.entries(S.sound)) if (L.mode === "audio" && !L.audio) return `Choose the ${key} clip, or describe it instead.`;
  return "";
}

// What each part of an H3 prompt is, for the advanced prompt's labels.
const PROMPT_PARTS = {
  subject_definitions: "Who is in it", summary: "Summary", retention_analysis: "What stays the same",
  detailed_description: "Style", overall_soundscape: "Sound", non_diegetic_music: "Music",
};

/** The prompt cut into its parts: its section headings and [Shot N] markers stay fixed, the words between
 * them are editable. Joining every part's `head` and `body` gives the prompt back exactly. */
function promptParts(prompt) {
  const parts = [];
  // A shot marker starts a line or a sentence; "(appears in [Shot 1] to [Shot 7])" is not one.
  const marks = [...prompt.matchAll(/^([a-z_]+):[ \n]|(?<=^|[.!?"'>)]\s)\[Shot (\d+)\] ?/gm)];
  if (!marks.length || marks[0].index > 0) parts.push({ label: "Prompt", head: "", body: prompt.slice(0, marks[0]?.index ?? prompt.length) });
  marks.forEach((m, i) => {
    const end = i + 1 < marks.length ? marks[i + 1].index : prompt.length;
    const raw = prompt.slice(m.index + m[0].length, end);
    const body = raw.replace(/\n*$/, ""), tail = raw.slice(body.length);
    parts.push({ label: m[2] ? `Shot ${m[2]}` : PROMPT_PARTS[m[1]] || m[1].replace(/_/g, " "), head: m[0], body, tail });
  });
  return parts;
}

function partBox(part, editable) {
  const ta = h("textarea", { class: "part-text", spellcheck: "false", readonly: !editable,
    oninput: () => { part.body = ta.value; fit(); } });
  ta.value = part.body;
  const fit = () => { ta.style.height = "auto"; ta.style.height = ta.scrollHeight + 2 + "px"; };
  requestAnimationFrame(fit);
  return h("div", { class: "part" }, h("label", {}, part.label), ta);
}

async function promptPanel() {
  if (blocked()) { closePanel(); toast(blocked()); return; }
  try {
    if (!S.prompt) await (refreshing || refreshModel());
    const effect = S.shot.group === "effects";
    const prompt = S.prompt;
    const parts = promptParts(prompt);
    const boxes = parts.filter(x => x.body.trim()).map(x => partBox(x, !effect));
    if (effect) {
      setPanel("Advanced prompt", h("p", { class: "note" },
        "An effect runs its tested prompt as it is. Change who is in it and where; the words stay."),
        h("div", { class: "parts" }, ...boxes));
      return;
    }
    setPanel("Advanced prompt",
      h("p", { class: "note" }, (isEdited() ? "Your edited prompt is in use. " : "This is the tested prompt for this move, as H3 will receive it. ") +
        "The shot lines are the text in the main box; editing either changes both. Swapping a character, the location or " +
        "who is in the shot keeps your edits."),
      h("div", { class: "parts" }, ...boxes),
      h("div", { class: "row-end" },
        isEdited() ? h("button", { type: "button", class: "btn", onclick: () => { S.prompt = S.base; closePanel(); showModel(); } }, "Go back to the tested prompt") : "",
        h("button", { type: "button", class: "btn primary", onclick: () => {
          S.prompt = parts.map(x => x.head + x.body + (x.tail || "")).join("");
          closePanel();
          showModel();
        } }, "Use this prompt")));
  } catch (e) { closePanel(); explain(e); }
}

function explain(e) {
  if (e.missing?.length) {
    toast("Still to fill in: " + e.missing.map(k => FIELD[k]?.[0] || k.toLowerCase().replace(/_/g, " ")).join(", "));
  } else toast(e.message);
}

// ---------- renders ----------

const cards = new Map();
const DONE = ["succeeded", "failed", "canceled"];

/** A button that acts on its second click, so one stray click cannot stop or delete a render. */
function twoStep(label, sure, act, cls = "btn") {
  const b = h("button", { type: "button", class: cls, onclick: async ev => {
    ev.stopPropagation();
    if (!b.dataset.armed) {
      b.dataset.armed = "1";
      b.textContent = sure;
      b.classList.add("danger");
      setTimeout(() => { delete b.dataset.armed; b.textContent = label; b.classList.remove("danger"); }, 3000);
      return;
    }
    b.disabled = true;
    try { await act(); } catch (err) { toast(err.message); b.disabled = false; }
  } }, label);
  return b;
}

/** Delete a finished render: its card goes, and its files. */
async function deleteJob(job) {
  await api(`/api/jobs/${job.id}/delete`, {});
  cards.get(job.id)?.remove();
  cards.delete(job.id);
  if (!cards.size) $("#hero").hidden = false;
}

function trackJob(job) {
  $("#hero").hidden = true;
  let card = cards.get(job.id);
  if (!card) {
    card = h("div", { class: "card", onclick: () => card.job.status === "succeeded" && openPanel("viewer", { job: card.job }) });
    cards.set(job.id, card);
    $("#grid").prepend(card);
  }
  paintCard(card, job);
  if (!DONE.includes(job.status)) followJobs();
}

/** One poll for every render still going. A stream per render would hold a connection each, and a
 * browser allows six per server: with six renders queued the page could no longer reach it. */
let following = null;
function followJobs() {
  following ??= setInterval(async () => {
    try {
      for (const j of await api("/api/jobs")) {
        const card = cards.get(j.id);
        if (card && !DONE.includes(card.job.status)) paintCard(card, j);
      }
    } catch { return; }   // the server is restarting: try again on the next tick
    if ([...cards.values()].every(c => DONE.includes(c.job.status))) { clearInterval(following); following = null; }
  }, 1500);
}

function paintCard(card, j) {
  const prev = card.job;
  card.job = j;
  const s = shotBySlug(j.shot) || { name: j.shot };
  const capEl = h("div", { class: "cap" }, h("span", {}, cap(s.name)), h("small", {}, j.elapsed ? fmt(j.elapsed) : ""));
  if (j.status === "succeeded") {
    if (prev?.status === "succeeded" && card.querySelector("video")) return;
    card.className = "card" + (j.height > j.width ? " tall" : "");
    const v = h("video", { src: `/outputs/${j.video}`, loop: true, playsinline: true, preload: "metadata" });
    v.muted = true;
    card.onmouseenter = () => v.play().catch(() => {});
    card.onmouseleave = () => v.pause();
    card.replaceChildren(v, capEl);
    return;
  }
  const over = DONE.includes(j.status);
  if (prev && !DONE.includes(prev.status) && !over && card.querySelector(".track")) {
    // Still running: move the bar and the message, and leave the Cancel button as it is.
    card.querySelector(".track i").style.width = `${Math.round(j.progress * 100)}%`;
    card.querySelector(".run small").textContent = j.elapsed ? `${j.message || j.status} · ${fmt(j.elapsed)}` : j.message || j.status;
    card.querySelector(".cap").replaceWith(capEl);
    return;
  }
  card.className = "card running" + (j.status === "failed" ? " failed" : "");
  card.replaceChildren(
    s.still ? h("img", { src: s.still, alt: "" }) : h("div", {}),
    h("div", { class: "run" },
      over ? h("span", {}, j.status === "failed" ? "Failed" : "Canceled") : h("span", { class: "track" }, h("i", { style: `width:${Math.round(j.progress * 100)}%` })),
      h("small", {}, j.status === "failed" ? j.error : over ? "" : j.elapsed ? `${j.message || j.status} · ${fmt(j.elapsed)}` : j.message || j.status),
      over ? h("button", { type: "button", class: "btn", onclick: ev => { ev.stopPropagation(); deleteJob(j).catch(err => toast(err.message)); } }, "Remove")
        : twoStep("Cancel", "Cancel this render?", () => api(`/api/jobs/${j.id}/cancel`, {}).then(x => paintCard(card, x)))),
    capEl);
}

async function viewer({ job }) {
  const s = shotBySlug(job.shot) || { name: job.shot };
  const base = "/outputs/" + job.video.replace(/\.mp4$/, "");
  const { prompt } = await api(`/api/jobs/${job.id}/prompt`);
  $("#modal-title").textContent = cap(s.name);
  $("#modal-body").replaceChildren(h("div", { class: "viewer" },
    h("video", { src: base + ".mp4", controls: true, autoplay: true, loop: true, playsinline: true }),
    h("aside", {},
      h("dl", {},
        h("dt", {}, "Size"), h("dd", {}, `${job.width}×${job.height} · ${(job.length / 24).toFixed(1)}s`),
        h("dt", {}, "Seed"), h("dd", {}, String(job.seed)),
        job.elapsed ? h("dt", {}, "Took") : null, job.elapsed ? h("dd", {}, fmt(job.elapsed)) : null),
      h("div", { class: "row-end left" },
        job.inputs ? h("button", { type: "button", class: "btn primary", title: "Load this shot again: its move, cast, location, sound, size, seed and its exact prompt",
          onclick: () => recreate(job) }, "Recreate")
          : h("button", { type: "button", class: "btn", title: "Use this seed and move for the next render (made before Recreate existed)",
            onclick: () => { selectShot(job.shot, { preset: false }); $("#seed").value = job.seed; closePanel(); showPage("create"); } }, "Reuse seed"),
        h("a", { class: "btn", href: base + ".mp4", download: `${s.name.replace(/\W+/g, "-")}-${job.seed}.mp4` }, "Download"),
        twoStep("Delete", "Delete for good?", async () => { await deleteJob(job); closePanel(); })),
      h("div", { class: "links" },
        h("a", { href: base + ".workflow.json", download: true, title: "Open in ComfyUI to re-run it" }, "Workflow"),
        h("a", { href: base + ".txt", download: true }, "Prompt")),
      h("details", {}, h("summary", {}, "Prompt"), h("pre", {}, prompt)))));
}

async function generate() {
  if (blocked()) return toast(blocked());
  const btn = $("#go");
  btn.disabled = true;
  try {
    await refreshing;
    trackJob(await api("/api/render", request()));
    toast("");
  } catch (e) { explain(e); }
  btn.disabled = false;
}

// ---------- pages ----------
// Create is the composer and the renders; Shots is the move library; Cast, Props and Locations are
// libraries of what you have, edited there. A library page changes the shot only when asked
// ("Use in this shot"); the composer's chips are where the shot itself is changed.

function showPage(name) {
  S.page = name;
  document.querySelectorAll(".nav[data-page]").forEach(b => b.classList.toggle("on", b.dataset.page === name));
  const create = name === "create";
  $("#feed").hidden = !create;
  $(".dock").hidden = !create;
  $("#page").hidden = create;
  if (!create) ({ shots: shotsPage, cast: () => libraryPage("character"), props: () => libraryPage("object"), locations: () => libraryPage("location") })[name]();
}

function shotsPage() {
  const page = $("#page");
  S.shotsTab ??= "moves";
  const paint = () => {
    const effects = S.shotsTab === "effects";
    const q = S.query.toLowerCase();
    const list = S.config.shots.filter(s => (s.group === "effects") === effects && (!q || s.name.toLowerCase().includes(q)));
    const groups = [...new Set(list.map(s => s.group))];
    page.replaceChildren(
      h("header", { class: "page-head" },
        h("div", {}, h("h1", {}, "Shots"),
          h("p", {}, effects ? "Effects run their tested prompt as it is: choose who is in it and where."
            : "Each move starts from a take that worked. Pick one, then swap in your cast and location.")),
        h("input", { class: "search", type: "search", placeholder: "Search", value: S.query,
          oninput: e => { S.query = e.target.value; paint(); $(".page-head .search").focus(); } })),
      modeSeg(S.shotsTab, [["moves", "Camera moves", "Named camera moves"], ["effects", "Effects", "Fire, vanishing, levitation and more"]],
        m => { S.shotsTab = m; paint(); }),
      ...groups.map(g => h("section", { class: "shelf" },
        effects ? "" : h("h2", {}, cap(g)),
        h("div", { class: "tiles" }, ...list.filter(s => s.group === g).map(s => tile({
          img: s.still, preview: s.preview, name: cap(s.name), wide: true, on: s.slug === S.shot.slug, sub: castText(s),
          tip: "Load this shot with its example cast and location",
          onclick: () => { selectShot(s.slug); showPage("create"); },
        }))))));
  };
  paint();
}

function libraryPage(kind) {
  const page = $("#page");
  const title = { character: "Cast", object: "Props", location: "Locations" }[kind];
  const blurb = {
    character: "Your people: a photo, a one-word name to @mention, their look (hair and clothing) and their voice. Put them in a shot from Create.",
    object: "Things that can appear in a shot, each a photo and a one-word name. Put them in a shot from Create.",
    location: "Places, each a picture and the words that describe it. Choose one for a shot from Create's Location chip.",
  }[kind];
  let sel = null;     // the item open in the editor
  let draft = null;   // a new one, not saved yet

  const items = () => S.elements.filter(e => e.kind === kind);
  const inShot = e => S.cast.includes(e.ref);

  const saveNew = async () => {
    if (!draft.name.trim()) return toast("Give it a name.");
    try {
      await api("/api/elements", { ref: draft.ref, name: draft.name.trim(), kind, pronoun: draft.pronoun || "they", type: draft.type || "person",
        look: draft.look || "", scene: draft.scene || {} });
      S.elements = await api("/api/elements");
      addedScenes();
      sel = S.elements.find(e => e.ref === draft.ref) || null;
      draft = null;
      paint();
    } catch (e) { toast(e.message); }
  };

  const saveEdit = async e => {
    try {
      await api("/api/elements", { ref: e.ref, name: e.name.trim(), kind, pronoun: e.pronoun || "they", type: e.type || "person",
        look: e.look || "", scene: e.scene || {} });
      S.elements = await api("/api/elements");
      addedScenes();
      sel = S.elements.find(x => x.ref === e.ref) || null;
      toast("");
      paint();
    } catch (err) { toast(err.message); }
  };

  const remove = async e => {
    try {
      await api("/api/elements/delete", { ref: e.ref });
      if (inShot(e)) removeFromCast(e);
      S.elements = await api("/api/elements");
      sel = null;
      paint();
      paintHighlight();
    } catch (err) { toast(err.message); }
  };

  const voiceBox = c => {
    c.voiceMode ??= c.voice_audio ? "sample" : "describe";
    const save = () => api("/api/voices", { ref: c.ref, voice: c.voice || "", voice_audio: c.voice_audio || null, language: c.language || "English" })
      .then(() => api("/api/elements").then(els => { S.elements = els; })).catch(err => toast(err.message));
    const lang = h("select", { onchange: e => { c.language = e.target.value; save(); } }, ...LANGUAGES.map(x => h("option", { value: x }, x)));
    lang.value = c.language || "English";
    const file = h("input", { type: "file", accept: "audio/*", hidden: true, onchange: async e => {
      try { const up = await uploadFile(e.target.files[0]); Object.assign(c, { voice_audio: up.ref, voice: "" }); await save(); paint(); }
      catch (err) { toast(err.message); }
    } });
    let how;
    if (c.voiceMode === "describe") {
      how = h("input", { type: "text", placeholder: "a low, calm, slightly husky voice", title: "Leave empty and H3 picks a voice",
        onchange: e => { c.voice = e.target.value.trim(); c.voice_audio = null; save(); } });
      how.value = c.voice || "";
    } else if (c.voice_audio) {
      how = h("div", { class: "clip" }, h("audio", { src: `/uploads/${c.voice_audio}`, controls: true }),
        h("button", { type: "button", class: "btn", onclick: () => { c.voice_audio = null; save(); paint(); } }, "Remove"));
    } else {
      how = h("button", { type: "button", class: "btn", title: VOICES.sample[1], onclick: () => file.click() }, "Choose a voice sample…", file);
    }
    return h("div", { class: "field full" }, h("label", {}, "Voice"),
      h("div", { class: "voice-row" }, modeSeg(c.voiceMode, Object.entries(VOICES).map(([k, [label, tip]]) => [k, label, tip]), m => { c.voiceMode = m; paint(); }), lang),
      how, h("small", { class: "hint" }, 'Used whenever they speak: write their lines in the shot in quotes, @' + (c.name || "Name") + ' says "Hello."'));
  };

  const editor = () => {
    const e = draft || sel;
    if (!e) return h("aside", { class: "lib-edit empty" }, h("p", { class: "note" },
      kind === "location" ? "Pick a place to see its words, or add a new one." : `Pick one to edit it, or upload a photo to add one.`));
    const mine = !e.sample;
    const fields = [];
    if (mine) {
      const name = h("input", { type: "text", value: e.name || "", maxlength: kind === "location" ? 60 : 32,
        placeholder: { character: "Mara", object: "Teapot", location: "Harbour" }[kind],
        oninput: ev => { e.name = kind === "location" ? ev.target.value : ev.target.value.replace(/[^A-Za-z0-9_-]/g, ""); ev.target.value = e.name; } });
      fields.push(h("div", { class: "field" }, h("label", {}, "Name"), name));
    }
    if (kind === "character") {
      if (mine) {
        const pron = h("select", { onchange: ev => { e.pronoun = ev.target.value; } }, ...["they", "she", "he"].map(x => h("option", { value: x }, x)));
        pron.value = e.pronoun || "they";
        const look = h("textarea", { rows: 3, placeholder: "short red hair, a green bomber jacket", oninput: ev => { e.look = ev.target.value; } });
        look.value = e.look || "";
        fields.push(h("div", { class: "field" }, h("label", {}, "Pronoun"), pron),
          h("div", { class: "field full" }, h("label", {}, "Look ", h("small", { class: "hint" }, "hair and clothing, recommended")), look,
            h("button", { type: "button", class: "btn", onclick: async ev => {
              try { const got = await describeImage(ev.currentTarget, e.ref, "character"); Object.assign(e, { look: got.look || e.look, type: got.type || e.type }); paint(); }
              catch (err) { toast(err.message); }
            } }, "Fill in from the photo")));
      } else {
        fields.push(h("div", { class: "field full" }, h("label", {}, "Look"), h("p", { class: "ro" }, e.look || "—")));
      }
      if (!draft) fields.push(voiceBox(e));
    }
    if (kind === "location") {
      const sc = e.sample ? S.config.samples.scenes[e.name] : e.scene;
      fields.push(h("div", { class: "field full" }, h("label", {}, "Its words"),
        sc?.ENVIRONMENT ? h("p", { class: "ro" }, `${cap(sc.ENVIRONMENT)}. Around: ${sc.ENVIRONMENT_ELEMENTS}. Sound: ${sc.SOUNDSCAPE}.`)
          : h("button", { type: "button", class: "btn", onclick: async ev => {
            try { e.scene = await describeImage(ev.currentTarget, e.ref, "location"); if (!draft) await saveEdit(e); else paint(); }
            catch (err) { toast(err.message); }
          } }, "Describe it from the image (recommended)")));
    }
    const actions = [];
    if (draft) {
      actions.push(h("button", { type: "button", class: "btn", onclick: () => { draft = null; paint(); } }, "Cancel"),
        h("button", { type: "button", class: "btn primary", onclick: saveNew }, "Save"));
    } else {
      if (mine) actions.push(h("button", { type: "button", class: "btn", onclick: () => saveEdit(e) }, "Save changes"),
        h("button", { type: "button", class: "btn danger", onclick: () => remove(e) }, "Delete"));
    }
    return h("aside", { class: "lib-edit" },
      h("div", { class: "lib-photo", style: `background-image:url(${e.img})` }),
      h("h2", {}, e.name || "New"), e.sample ? h("small", { class: "hint" }, "Comes with the app") : "",
      h("div", { class: "form tight" }, ...fields),
      h("div", { class: "row-end left" }, ...actions));
  };

  const makePlace = () => {
    let words = "";
    return h("section", { class: "section" }, h("h3", {}, "Make a place from words"),
      h("div", { class: "makeloc" },
        h("textarea", { rows: 2, placeholder: "a 1950s diner at night, neon in the windows, rain on the glass", oninput: ev => { words = ev.target.value; } }),
        h("div", { class: "makeloc-btns" },
          h("button", { type: "button", class: "btn", title: "Make a picture of it with Qwen Image 2.1 turbo, then name it and keep it here.",
            onclick: async ev => {
              if (!words.trim()) return toast("Describe the place first.");
              try { const up = await followTask(ev.currentTarget, "/api/locations/generate", { description: words }); draft = { ref: up.ref, img: up.url, name: "" }; sel = null; paint(); }
              catch (err) { toast(err.message); }
            } }, "Make an image"))));
  };

  const makePerson = () => {
    let words = "";
    return h("section", { class: "section" }, h("h3", {}, "Make a character from words"),
      h("div", { class: "makeloc" },
        h("textarea", { rows: 2, placeholder: "a woman in her thirties with a short silver bob, a mustard raincoat over a black turtleneck", oninput: ev => { words = ev.target.value; } }),
        h("div", { class: "makeloc-btns" },
          h("button", { type: "button", class: "btn", title: "Make a picture of them with Qwen Image 2.1 turbo, then name them and fill in their look from it.",
            onclick: async ev => {
              if (!words.trim()) return toast("Describe the person first.");
              try {
                const up = await followTask(ev.currentTarget, "/api/characters/generate", { description: words });
                draft = { ref: up.ref, img: up.url, name: "", pronoun: "they", type: "person", look: "" };
                sel = null;
                paint();
              } catch (err) { toast(err.message); }
            } }, "Make an image"))));
  };

  const paint = () => page.replaceChildren(
    h("header", { class: "page-head" }, h("div", {}, h("h1", {}, title), h("p", {}, blurb))),
    h("div", { class: "lib" },
      h("div", {},
        h("div", { class: "tiles" },
          ...items().map(e => tile({
            img: e.img, name: e.name, wide: kind === "location", on: (sel?.ref === e.ref) && !draft,
            sub: [e.sample ? "" : "yours",
              kind === "location" && !e.sample && !e.scene?.ENVIRONMENT ? "picture only" : ""].filter(Boolean).join(" · "),
            onclick: () => { draft = null; sel = e; paint(); },
          })),
          uploadTile("image/png,image/jpeg,image/webp", async f => {
            try {
              const up = await uploadFile(f);
              draft = { ref: up.ref, img: up.url, name: "", pronoun: "they", type: "person", look: "" };
              sel = null;
              paint();
            } catch (err) { toast(err.message); }
          }, kind === "location", { character: "Upload a photo of a person", object: "Upload a photo of an object", location: "Upload a photo of a place, with nobody in it" }[kind])),
        kind === "location" ? makePlace() : kind === "character" ? makePerson() : ""),
      editor()));
  paint();
}

/** Load a render's whole setup back into Create: move, cast, location, sound, size, seed, and the
 * prompt exactly as it ran. */
async function recreate(job) {
  const i = job.inputs;
  closePanel();
  showPage("create");
  selectShot(job.shot, { preset: false });
  S.cast = (i.mentions || []).filter(m => m.kind !== "recording").map(m => m.ref).filter(element);
  S.location.mode = !i.location?.ref ? "text" : hasWords(element(i.location.ref)) ? "both" : "image";
  if (i.location?.ref) S.location.image = i.location.ref;
  S.scene = { ...(i.scene || {}) };
  for (const [key, clip] of [["ambience", i.ambience_audio], ["music", i.music_audio]]) {
    S.sound[key] = clip ? { mode: "audio", audio: clip, name: "the clip" } : { mode: "text", audio: null, name: "" };
  }
  Object.assign(S, { aspect: i.aspect || S.aspect, resolution: i.resolution || S.resolution, duration: i.duration || S.duration });
  for (const [id, key] of [["#aspect", "aspect"], ["#res", "resolution"], ["#dur", "duration"]]) paintSeg(id, S[key]);
  $("#seed").value = job.seed;
  S.takeText = i.text || "";
  const { prompt } = await api(`/api/jobs/${job.id}/prompt`);   // the job list leaves prompts out
  await refreshing;
  await refreshModel();
  if (prompt) S.prompt = prompt;
  showModel();
}

// ---------- boot ----------

async function boot() {
  [S.config, S.elements] = await Promise.all([api("/api/config"), api("/api/elements")]);
  addedScenes();

  const t = S.config.target;
  $("#target").replaceChildren(
    h("b", {}, t.includes("cloud.comfy.org") ? "Comfy Cloud" : "Your ComfyUI"), t.replace(/^https?:\/\//, ""));
  $("#target").title = "Renders run here, through the Comfy SDK";

  const pick = ["crane-rise", "dutch-angle", "orbit-360", "snorricam", "aerial-pullback"].map(shotBySlug).filter(s => s?.still);
  $("#fan").replaceChildren(...pick.map(s => h("img", { src: s.still, alt: "" })));

  seg("#aspect", Object.keys(S.config.sizes), "aspect", { "16:9": "Landscape", "9:16": "Portrait" });
  seg("#res", Object.keys(S.config.sizes["16:9"]), "resolution",
    { "480p": "Quick draft, to check the move", "768p": "H3's native size. Slower." });
  seg("#dur", Object.keys(S.config.durations), "duration");

  S.shot = shotBySlug("orbit-360") || S.config.shots[0];
  S.location.image = S.elements.find(e => e.kind === "location")?.ref || null;
  S.cast = [S.elements.find(e => e.kind === "character").ref];
  selectShot(S.shot.slug);
  toast("");

  const ta = $("#text");
  ta.addEventListener("input", () => { popupIndex = 0; applyShotView(ta.value); paintHighlight(); paintPopup(); });
  // The swap menu closes on any click outside it.
  document.addEventListener("mousedown", e => { if (!e.target.closest("#mention-pop, .ref")) $("#mention-pop").hidden = true; });
  ta.addEventListener("keydown", e => {
    if (onTextKey(e)) return;
    if (e.key === "#") { e.preventDefault(); openPanel("camera"); }
  });
  ta.addEventListener("click", paintPopup);
  ta.addEventListener("scroll", () => { $("#hl").scrollTop = ta.scrollTop; });
  ta.addEventListener("blur", () => setTimeout(() => { $("#mention-pop").hidden = true; }, 150));

  document.querySelectorAll(".nav[data-page]").forEach(b => { b.onclick = () => showPage(b.dataset.page); });
  $("#go").onclick = generate;
  $("#prompt-btn").onclick = () => openPanel("prompt");
  $("#modal-close").onclick = closePanel;
  $("#scrim").addEventListener("click", e => { if (e.target.id === "scrim") closePanel(); });
  document.addEventListener("keydown", e => { if (e.key === "Escape" && !$("#scrim").hidden) closePanel(); });

  (await api("/api/jobs")).reverse().forEach(trackJob);
}

boot().catch(e => toast(e.message));
