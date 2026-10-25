# Reverse dolly zoom (the world closes in)

**Status:** verified (2026-10-25: dolly-zoom-in_7_49dea3255f56, Kate, rain street, seed 7 at 1344x768; earlier failed on a waist-up framing)
**Effect:** the subject stays the same size in frame while the world behind them grows, flattens and
crowds in close behind them. The *Jaws* beach shot direction.
**Why it is here:** the library's telephoto direction (`dolly-zoom-telephoto`) was only measured
without an identity plate. This is the same sentence shape as `dolly-zoom.md`, reversed: pull out
plus zoom in, named, with the background listed object by object.

**Native take (2026-10-25, pod 00045):** at 1344x768 the zoom did not compensate: the camera simply pulled back and she shrank from waist-up to a small figure in the street, the background barely changing. Now a head-and-shoulders close-up, with the lock spelled out: the zoom cancels the pull, she fills the same part of the frame first to last and never gets smaller, only the background changes. That held (seed 7, pod 00049); a matching reaction was asked for, as on the forward dolly zoom, so it now carries the Jaws beat: calm to dawning dread to alarm.

## Machine-readable

```json
{
  "id": "K-06r",
  "slug": "dolly-zoom-in",
  "name": "reverse dolly zoom",
  "group": "specialty",
  "status": "verified",
  "motion": "stationary",
  "length": 124,
  "framing": "A head-and-shoulders close-up",
  "subject_action": "standing completely still {PLACE}, facing the camera",
  "shot_line": "The camera performs a reverse Hitchcock dolly zoom, the Jaws effect: it pulls out while simultaneously zooming in, the zoom exactly cancelling the pull, so that {SUBJECT}'s size and position in frame stay exactly constant throughout: {POSSESSIVE} head and shoulders fill the same part of the frame from the first frame to the last and {PRONOUN_SUBJ} never gets smaller. Only the background changes: {BACKGROUND} behind {PRONOUN} grow, flatten, and crowd in close behind {PRONOUN} as the lens's focal length changes. As the background crowds in, {POSSESSIVE} expression shifts from calm to dawning dread, then to alarm: {POSSESSIVE} eyes widen, {POSSESSIVE} brows lift and {POSSESSIVE} lips part.",
  "extra_slots": {
    "BACKGROUND": "three or four distinct things behind the person that will visibly loom closer, e.g. \"the shopfronts, the street lamps and the parked cars\""
  },
  "scene_warning": "Name solid, separate things behind the subject. A plain or low-texture background gives the move nothing to show.",
  "framing_note": "Open where it ends. Do NOT open wide."
}
```
