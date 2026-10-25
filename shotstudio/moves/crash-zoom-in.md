# Crash zoom in

**Status:** verified (Amber, arctic shore, seed 7: H3 zoomed over 0.9 s; ramped to 4 frames, clip 4.5 s)
**What it is:** the mirror of `crash-zoom-out.md`: holds the wide shot, snaps to a tight close-up of the face in a few frames, holds the close-up. It replaces the library's crash zoom in (`vendor/.../shots/crash-zoom-in.md`), which asked for the same snap but, like every H3 crash zoom, came back over a second or more. Same wording as the crash zoom out, and the same speed ramp after rendering (`snap`).

**Native-resolution take (2026-10-25):** at 1344x768 the same prompt and seed started the zoom about a second later and ran it to near the end (out: 3.0-4.8 s of 5.2 s), so after the speed ramp the landed framing held only 0.5-1 s. The hold before the zoom is now one second and the landed framing is asked to hold for the last two.

## Machine-readable

```json
{
  "id": "C-01b",
  "slug": "crash-zoom-in",
  "name": "crash zoom in",
  "status": "verified",
  "motion": "stationary",
  "length": 124,
  "framing": "{WIDE_FRAMING} places {SUBJECT} small and complete in frame {PLACE}",
  "framing_summary": "a wide shot",
  "shot_intro": "comma",
  "shot_line": "The camera is locked off on a tripod and holds the wide shot completely still for the first second only; only the zoom lens changes and the camera body never moves. Between one frame and the next the lens crash zooms in to a tight close-up of {FACE}: the whole change takes only two or three frames, as abrupt as a cut, with a streak of zoom blur on those few frames only, and nothing shifts against anything else, the background simply magnifies flat together with {PRONOUN}. After it lands, the close-up is locked for the whole rest of the shot, at least the last two seconds, and does not change.",
  "extra_slots": {},
  "snap": true,
  "app_note": "The zoom is sped up after rendering so it lands in a few frames; H3 alone takes a second or two. The clip comes out shorter by about that much, and the render as H3 made it is kept as _raw.mp4.",
  "group": "zoom"
}
```
