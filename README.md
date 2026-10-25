# H3 Shot Studio

Pick a named camera move, cast it with a character photo, describe the scene, and render it with
MiniMax H3, on your own GPU or on Comfy Cloud.

MiniMax H3 has twelve camera primitives (pan, tilt, zoom, arc and so on) and no named compound
shots. There is no "dolly zoom" or "crash zoom" button. Each film shot has to be written as a
sentence built from the primitives, and most ways of writing it do not work. This app wraps a
library of shots that did work, with what each one needs: frame count, opening framing,
how many characters, and the ways it still fails.

An open rebuild of the "direct your shot like a film set" idea behind paid camera-preset tools,
built on the [Comfy SDK](https://docs.comfy.org/development/api-development/sdks) and open weights.

## The shots

From the shot library: crash zoom in, yo-yo zoom, snorricam, rack focus, three-panel split screen,
whip pan, dutch angle, super dolly in, eyes in, aerial pullback, handheld tracking, 360 orbit and
crane rise.

Added here, in the library's recipe format (`shotstudio/moves/`), from viewer requests and the
camera presets of paid tools: low-angle hero shot, swing down from overhead, tilt up reveal,
pedestal up, racing-drone dive, walk-past shot, fisheye close-up, crash zoom out, super dolly out,
quarter-circle arc, crane down, lateral tracking shot, static shot, jib up, hero spin, slow pan reveal,
tilt down reveal, a reverse dolly zoom, a POV shot and a cut-away montage (a face, four
quick inserts of the hands at work, and the face again, ready). Each held up in a test render on one of
the bundled characters and locations. Each tile's still and hover preview come from the chosen take rendered at
1344x768 (`scripts/make_previews.py`).

**Effects**, from a side-by-side test of paid-tool effects against H3, made reusable for any character
and location: set on fire, disintegration, vanish, levitation, thunder god, melting, giant, incline, architecture wave, time-lapse and a rooftop swing between buildings.

**Crash zooms are sped up after rendering.** H3 paces a "snap" zoom over one to two seconds whatever the
prompt asks (the shot library found the same). The app finds the zoom by comparing every frame with the
opening and closing framings at thumbnail size, and plays that stretch fast enough to land in three frames (an eighth of a second),
with the audio sped up to match (`shotstudio/snap.py`). The clip comes out shorter by the time removed,
and the render as H3 made it is kept as `_raw.mp4`.

A shot is in the app only if its recipe holds up. Two exceptions are marked:

- **Dolly zoom (experimental).** The subject's size holds in most takes, but the background
  recedes clearly only in some scenes, and sometimes moves the opposite way. It works best with a
  bundled location, which names three or four solid things behind the subject for it. Its test
  takes described the place in words, and with the picture in place of the words the move shrank to
  a fraction of its size, so try **Words only** if the background holds still. The test log is in `shotstudio/moves/dolly-zoom.md`.
- Left out: bullet time (it could not be done), and the
  battle knight and split diopter (their recipes stay in `shotstudio/moves/`, marked removed).

The dolly zoom and reverse dolly zoom open on a head-and-shoulders close-up and carry a reaction
(calm to shock as the world stretches away, calm to dread as it closes in): a waist-up framing let H3
pull back instead of holding the subject's size.

Each move takes a set number of characters:

| Characters | Moves |
|---|---|
| 1 | crash zoom, yo-yo zoom, snorricam, eyes in, super dolly in, split screen, and all the added moves and the dolly zoom. The camera locks onto or lands on one face. Objects the character holds are fine. |
| 2 | whip pan (it lands on the second character) |
| 3 | rack focus (one near, two far) |
| 1 or 2 | 360 orbit, aerial pullback, crane rise, handheld, dutch angle |

The library's recipes are written around one person. With two characters, the last five
moves switch to a group version (`shotstudio/group_moves.json`) that aims the camera at the whole
group and puts the action inside the move: the orbit circles both people while they act, instead of
circling one and leaving the action for afterwards. Each group version is offered only after a
group render of it held up; all five were rendered once with two characters. Three is not offered until a three-person render of it has been checked.

## Using it

**Every move starts from a take that worked.** Picking a move loads the approved example: its
characters, location, action text, seed and size. Generate it unchanged and the prompt behind the
example runs again, with one addition: every character's look (hair and clothing, set on the
character) is named where the prompt says who each person is and what stays the same. From photos
alone H3 lets clothing pass between people, worst when a reference is a head-and-shoulders portrait
(an orbit with Allie and Lena put both in Allie's dress), so a character you upload should have its
look filled in, and a photo that shows the outfit helps. Click a character (in the text or under it) to swap in another, or one you
upload: the prompt stays word for word, with that character's name, description and pronouns changed.
With two or three people, each "her" or "his" follows the person last named before it, so only the
swapped person's change. Picking another bundled place swaps the location's own words the same way,
including the words a move takes from its location: what recedes behind a dolly zoom, the wider place
an aerial pullback opens onto, the corridor a super dolly charges down, what tumbles past in the
incline. Each bundled location carries its own, and a described or uploaded location gets plain
stand-ins. If the action refers to the old place (a car at the roadside), edit that line. Any other
change builds the prompt from the move's recipe.

**The main box is the shot.** It shows the shot lines of that prompt, the part that says what the
camera and the people do, with `@Name` tags for the characters and objects, `@Location` for a location
image, and a bundled location's own words marked. Edit it like any text. **Advanced prompt** shows
the whole prompt in its parts (who is in it, the summary, each shot, the sound) and edits the same
prompt: a change in either shows in the other. Your edits stay through a character swap, a new
location (its words are swapped in your text too) and adding or removing someone (the parts that
list who is in it are rewritten; the shot lines are yours to adjust). **Go back to the tested prompt**
undoes them. The examples are in `shotstudio/presets.json`, made from the approved takes by
`scripts/make_presets.py`.

**Effects** (set on fire, vanish, levitation and the rest) run their tested prompt as it is: choose who
is in it and where, and nothing else.

The app has two places to work and a library:

- **Create**: the shot you are making (the chips for its cast, camera move, location and sound, the
  shot text, Generate) and your renders below it. A render in progress can be **Cancel**led, which
  stops it on ComfyUI. Open a finished render to watch it, **Download** it, **Delete** it (its video,
  prompt and workflow), or **Recreate** it: its move, cast, location, sound, size, seed and exact
  prompt come back, ready to change and render again.
- **Shots**: every camera move, and the effects on their own tab, each shown by a take that worked.
  Pick one and it loads into Create with that take's cast and location.
- **Cast**, **Props** and **Locations**: what you have, edited there. A character's photo, name,
  pronoun, look and voice; a prop's photo and name; a place's picture and words. These are plain
  lists with no shot in view. Who and what goes into a shot is chosen on Create, from the chips or by
  clicking a name in the shot text, where a swap keeps the take's prompt with the new name, look and
  pronouns.

Bring people and things into the shot with `@`:

> @Amber hands the @Lantern to @Kate, who lifts it to her face and smiles.

Typing `@` lists every character and object; each one you mention is sent to H3 as a reference
image and numbered in the prompt (characters first, in the order you mention them, then objects).
Moves that need two or three characters, like the whip pan and rack focus, use them in that order.

- **Cast** (the chip): who and what is in this shot, each a photo and a one-word name. Upload your own.
  A character's pronoun is they unless you choose she or he. With they, the prompt names the character
  instead ("the person" when they are alone in the shot, their `<Subject N>` label when others are in
  it), since H3 can read "they" as several people.
  H3 takes at most 9 reference images, a location image included; the chip shows the count.
  **Fill in from the photo** (recommended) writes a new character's look, hair and clothing, the way
  the bundled characters have theirs, in about 10 seconds; check it before saving. The pronoun is
  yours to set; it is not read from the photo.
- **Camera move** (or type `#`): pick another move without leaving Create.
- **Location**: pick one of the twenty-three that come with the app (a desert highway to a dungeon,
  Mars and a space station) or one you added. A place is a picture and the words that describe it,
  and H3 gets both, the way a character comes with a photo and a look: the tested prompt describes
  the place in words, and the picture is added as a reference, defined by those words and held to.
  **Words only** leaves the picture out, as the approved takes were rendered. For a new place,
  describe it and either **Use these words** or **Make an image** (Qwen Image 2.1 turbo on the same
  ComfyUI, about 20 seconds once loaded, with progress on the button; it waits for a render in
  progress), or upload a photo of it with nobody in it. **Describe it from the image** (recommended)
  then writes the place's words the way the bundled ones have them, in about 20 seconds: the place,
  what is around, its sound, and what the camera moves take from a location (what recedes behind a
  dolly zoom, the corridor a super dolly charges down). Until then it is used as a picture alone.
  Where the characters are in it, if it matters, goes in the main text.

  Both describe buttons use Qwen3-VL 8B, the text encoder Qwen Image 2.1 already needs
  (`qwen3vl_8b_int8_convrot`). H3's own 32B encoder cannot: it is cut down to the layers H3 reads,
  without the part that writes text. They run on ComfyUI through the Comfy SDK like a render, with core
  nodes only (TextGenerate, then SaveText, whose file carries the text back).
- **Sound**: ambience and music, each either described or given as an audio clip that H3 reuses
  as that layer (MiniMax's `partially_copy`: the clip plays under the shot, with the action and
  dialogue added over it). Both are optional: no ambience means the natural sound of the location,
  no music means none. Clips count toward H3's 3 audio inputs.
- **Voices** live with each character, on the Cast page: a description ("a low, calm voice") or a
  few seconds of someone speaking for H3 to copy, plus the language they speak. A character keeps their
  voice in every shot. H3 takes at most 3 voice clips per shot.

Dialogue goes in the shot in quotes, where it is spoken; the app writes it in H3's form (`<d>[English] …</d>`, each speaker marked `(S1)`, `(S2)`), which only the advanced prompt shows. The speaker of a new line is the person named last before it:

> @Amber turns to @Kate and holds out the @Lantern. @Amber says "This was my grandfather's." @Kate takes it and asks "Does it still work?"

A line already in the example keeps its speaker. For a new one, name the speaker before the quote
("@Kate asks"); objects never speak. A different language goes after the quote: "Bonjour" (in French).

- **Off screen**: say so in the shot's words ("@Amber says off screen, her lips closed, "I knew this
  place.""); the editable shot does not add MiniMax's off-screen wording for you yet.
- **Recordings** (a line already recorded, under the Cast chip › Recordings) are not yet carried into
  the editable shot.
- Bottom bar: aspect ratio (16:9, 9:16), resolution (480p, 768p), duration (5, 8, 10 s; a move's
  own length is its minimum), seed, and **Advanced prompt** to see exactly what H3 receives.

Hover over any control for what it does. Finished renders fill the grid below. Each opens with its
seed, timing, and downloads for the MP4, the prompt and the ComfyUI workflow.

## The prompt H3 receives

Every render uses MiniMax's full-reference format, in its six sections and order:
`subject_definitions`, `summary`, `retention_analysis`, `detailed_description`,
`overall_soundscape`, `non_diegetic_music`. Characters, objects and a location image are
`<Subject N>` bound to `<Picture N>`; voice clips are `<Audio N>`, defined as a timbre reference (voice samples) or as reused dialogue (recordings).
Spoken lines follow the guide's speaker rules: a stable `(S1)`, `(S2)` in the order people first
speak, the voice given outside the `<d>` tag on their first line, and only the language tag and the
words, verbatim, inside it:

> <Subject 1> (S1), with a soft, warm voice, says: <d>[English] This was my grandfather's</d>.
**Advanced prompt** in the app shows the whole thing before you render.

## How it works

```
browser  ->  shotstudio.server (FastAPI)
               |- shots.py   scene + cast + shot -> full Ref2VA prompt (the shot library's build_prompt)
               '- render.py  Comfy SDK: upload plates, submit workflow, stream progress, download MP4
                                  |
                 COMFY_BASE_URL   |-- unset:  Comfy Cloud (needs COMFY_API_KEY)
                                  '-- http://127.0.0.1:8189: your ComfyUI behind comfy-api-proxy
```

The workflow (`shotstudio/workflows/h3_ref2va_shot.json`) is native ComfyUI nodes only:
`MiniMaxH3ReferenceToVideo`, 20 steps of `res_multistep`, and video plus audio out. Every render
saves the exact prompt and API-format workflow next to the MP4, so any result can be reproduced
in ComfyUI. Renders go to `outputs/app/`, which is also the history list: the app rebuilds it from
that folder when it starts. Uploads (characters, objects, locations, voices) go to `uploads/`. Both sit
under `SHOTSTUDIO_DATA` (the repository folder by default), and both are per install: the history is
whoever uses that copy of the app.

Settings that are fixed on purpose, from the shot library's tests:

- **20 steps, no turbo LoRA.** A 4-step turbo render suppresses the camera move almost entirely.
- **124 frames minimum, 192 for three-phase shots.** That is H3's trained range.
- **A place is its words, with its picture added.** Every tested prompt describes the place in
  words. An early A/B, with the picture given in place of the words, halved the camera move. Given
  with its words (the default), the super dolly in kept its whole move in a one-seed A/B. **Words
  only** in the Location panel leaves the picture out.

## Run it on your own GPU

You need:

- **ComfyUI 0.41.0 or later**, which has the native MiniMax H3, Qwen Image 2.1, TextGenerate and
  SaveText nodes this app uses. It was developed on 0.41.0. No custom nodes.
- **Python 3.12** for the app (3.12.9 was tested).
- **ffmpeg and ffprobe** on your PATH. The crash zooms use them to speed up the zoom after rendering.
- These model files in ComfyUI's `models` folders:

| Folder | File | Used for |
|---|---|---|
| `diffusion_models` | `minimax_h3_ref2va_pruned_int8_convrot.safetensors` | rendering |
| `text_encoders` | `qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors` | rendering |
| `vae` | `minimax_h3_video_vae_fp16.safetensors`, `minimax_h3_audio_vae_fp32.safetensors` | rendering |
| `text_encoders` | `qwen3vl_8b_int8_convrot.safetensors` | **Fill in from the photo**, **Describe it from the image**, **Make an image** |
| `diffusion_models` | `qwen_image_2.1_turbo_int8_convrot.safetensors` | **Make an image** |
| `vae` | `qwen_image_2.1_vae_bf16.safetensors` | **Make an image** |

The first four are all a render needs. Without the Qwen files, rendering still works, and the
describe and Make image buttons report the missing file.

Different file names for the H3 files? Put them in `shotstudio/models.json`:

```json
{"unet": "...", "clip": "...", "video_vae": "...", "audio_vae": "..."}
```

Then, with ComfyUI running on port 8188 (on Linux and macOS, `.venv/bin/` in place of
`.venv/Scripts/`):

```bash
python -m venv .venv
.venv/Scripts/pip install -r requirements.txt
.venv/Scripts/comfy-api-proxy start --state-dir outputs/proxy-state   # the Comfy API v2 on 127.0.0.1:8189
COMFY_BASE_URL=http://127.0.0.1:8189 .venv/Scripts/python -m shotstudio.server
```

Open http://127.0.0.1:7860. On Windows, `run_local.bat` does the last two steps. ComfyUI on another
port: add `--comfyui http://127.0.0.1:PORT` to the proxy. The app on another port: set `PORT`.

I developed this on an RTX 3060 12 GB with 32 GB of RAM. At that spec a draft shot (864x480,
124 frames) took 6 min 4 s and 10 min 43 s in two runs, from the click to the MP4. The sampler ran
at 15.3 s and 26.6 s a step, and the cause of the difference was not found. A better card should be
faster.

## Run it on Comfy Cloud

Create an API key at [platform.comfy.org](https://platform.comfy.org) (API access needs a paid
Cloud plan), then:

```bash
COMFY_API_KEY=comfyui-... python -m shotstudio.server
```

## Credits and licence

MIT. The shot library in `shotstudio/vendor/h3shots` is
[minimaxh3-shots-skills](https://github.com/loopforge0/minimaxh3-shots-skills), also MIT, and
builds on MiniMax's own H3 prompt guide. Every bundled image is generated: the sample characters
(which include the plates the library was developed on), the props (`scripts/make_object_plates.py`)
and the locations (`scripts/gen_locations.py`, `scripts/make_location_plates.py`). None is a photo
of a real person or place.
