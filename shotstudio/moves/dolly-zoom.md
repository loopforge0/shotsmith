# Dolly zoom (the Vertigo effect)

**Status:** experimental (offered with a label; see the test log)
**Effect:** the subject stays the same size in frame while the world behind them recedes, shrinks and
spreads apart into much greater depth.
**Why it is here:** the library's version (`vendor/h3shots/.../shots/dolly-zoom.md`) is left out of the
app for an unreliable subject lock. This one goes back to what its one clean take (K-06n, the concert
stage: subject 1.27x, background 0.47x) actually said, instead of the locked variant (X-01b) that
stacked every invariant clause.

**Closer, with a reaction (2026-10-25):** the native take (00033) worked but read flat: waist-up, a neutral face. The move now opens on a head-and-shoulders close-up and carries the classic Vertigo beat, calm to dawning realisation to shock, over the stretch. Test: --redo --seed=7 dolly-zoom.

## What changed from the library recipe

- **One sentence for the move**, worded as K-06n ran it. X-01b's stacked "stays exactly constant,
  neither closer nor further away, rooted, faces the camera" clauses did not fix the lock.
- **The named compound goes in as well** ("a Hitchcock dolly zoom, the Vertigo effect"). On its own it
  gave the library's best lock (1.00x) and no background recession; the composed sentence gives the
  recession. This asks for both.
- **The background is named, object by object** (`{BACKGROUND}`). K-06n listed curtains, a drum kit,
  keyboards and a microphone stand, and those are what visibly receded. The library's own warning: a
  low-texture background makes the shot unreadable. The app's location text alone would give "the
  rest of the setting", which has nothing in it to recede.

## Test log

All 480p, 5 s, 20 steps. "Lock" is the subject's size and position in frame; "background" is what it did.

| Take | Wording | Scene | Lock | Background |
|---|---|---|---|---|
| Sofia, seed 7 | named ("Hitchcock dolly zoom, the Vertigo effect") | rain street, text | held | loomed closer (the reverse direction) |
| Amber, seed 7 | named | pine forest, text | grew a little | no clear change |
| Claire, seed 11 | named | concert stage, image | held | barely moved (an image plate shrinks the move) |
| Sofia, seed 7 | unnamed, K-06n's sentence | rain street, text | held | loomed closer, the same as the named take |
| Claire, seed 11 | unnamed, `with large amplitude` on both halves | concert stage, image | held | recedes a little more than without it, still small |
| Claire, seed 11 | unnamed, `with large amplitude` on both halves | concert stage, text | held, grows very slightly | **recedes and spreads apart clearly, the right direction.** The stage's look drifts (red curtains to a blue-lit backdrop) |

The name made no difference on the same seed and scene, so it was dropped. `with large amplitude`
on both halves gave the first clean Vertigo-direction take since K-06n, with the location described
rather than given as an image, so the recipe is K-06n's sentence with both modifiers. The subject lock, the library version's failure, held in three of four. The background is
the unreliable half: it moved clearly on the textured street, in the reverse direction to the
wording, and barely anywhere else. Offered as experimental because it is the shot people ask for.

## Machine-readable

```json
{
  "id": "K-06n",
  "slug": "dolly-zoom",
  "name": "dolly zoom",
  "group": "specialty",
  "status": "experimental",
  "motion": "stationary",
  "length": 124,
  "framing": "A head-and-shoulders close-up",
  "subject_action": "standing completely still {PLACE}, facing the camera",
  "shot_line": "The camera pushes in with large amplitude while simultaneously zooming out with large amplitude, so that {SUBJECT}'s size and position in frame stay exactly constant throughout, while {BACKGROUND} behind {PRONOUN} recede, shrink, and spread apart into much greater depth as the lens's focal length changes. As the background stretches away, {POSSESSIVE} expression shifts from calm to dawning realisation, then to shock: {POSSESSIVE} eyes widen, {POSSESSIVE} brows lift and {POSSESSIVE} lips part.",
  "extra_slots": {
    "BACKGROUND": "three or four distinct things behind the person that will visibly recede, e.g. \"the red curtains, the drum kit and the keyboards\", \"the shopfronts, the street lamps and the parked cars\""
  },
  "scene_warning": "Works best with the location described, not an image: an image held the move to a fraction of its size. Name solid, separate things behind the subject.",
  "framing_note": "Open where it ends. Do NOT open wide.",
  "label": "dolly zoom (experimental)",
  "app_note": "Experimental. The subject usually holds its size; the background does not always recede. Describe the location rather than choosing an image of it: with an image the move is much smaller."
}
```
