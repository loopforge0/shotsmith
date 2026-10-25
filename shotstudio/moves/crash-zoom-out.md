# Crash zoom out

**Status:** verified (one render, seed 7, Mei, Tokyo alley)
**Effect:** a held close-up on the face, then one violent zoom out to a wide shot.
**Why it is here:** Higgsfield's "Crash Zoom Out". The reverse of the library's crash zoom in.

## Takes (Mei, Tokyo alley, seed 7)

| Wording | Zoom as H3 rendered it | After the speed ramp |
|---|---|---|
| "a Zoom Out with large amplitude at fast speed ... in about 200 milliseconds" | 2.2 s, with parallax, read like a dolly | 4 frames; clip 3.2 s |
| "between one frame and the next ... two or three frames, as abrupt as a cut ... nothing shifts against anything else" | 1.75 s | 3 frames; clip 3.6 s |

H3 picks its own pace for the snap (the library's crash zoom notes say the same), so the app speeds the
zoom up after rendering (`shotstudio/snap.py`). The second wording is kept because it leaves less to cut.

## Shot line

> The camera is locked off and completely motionless, and the framing does not change at all for the first two seconds. At the two-second mark the camera performs a Zoom Out with large amplitude at fast speed: a single violent crash zoom that travels the whole distance from the tight close-up out to a wide shot, with {SUBJECT} small and complete in frame {PLACE}, in about 200 milliseconds, in one continuous snap. The instant the zoom lands the camera is locked off again and the wide framing does not change for the rest of the shot.

**Native-resolution take (2026-10-25):** at 1344x768 the same prompt and seed started the zoom about a second later and ran it to near the end (out: 3.0-4.8 s of 5.2 s), so after the speed ramp the landed framing held only 0.5-1 s. The hold before the zoom is now one second and the landed framing is asked to hold for the last two.

## Machine-readable

```json
{
  "id": "B-01",
  "slug": "crash-zoom-out",
  "name": "crash zoom out",
  "group": "zoom",
  "status": "verified",
  "motion": "stationary",
  "length": 124,
  "framing": "{TIGHT_FRAMING} fills the frame with {SUBJECT}'s face",
  "framing_summary": "a tight close-up",
  "shot_intro": "sentence",
  "shot_line": "The camera is locked off on a tripod and holds the tight close-up completely still for the first second only; only the zoom lens changes and the camera body never moves. Between one frame and the next the lens crash zooms out to a wide shot with {SUBJECT} small and complete in frame {PLACE}: the whole change takes only two or three frames, as abrupt as a cut, with a streak of zoom blur on those few frames only, and nothing shifts against anything else, the background simply shrinks flat together with {PRONOUN}. After it lands, the wide framing is locked for the whole rest of the shot, at least the last two seconds, and does not change.",
  "extra_slots": {},
  "snap": true,
  "app_note": "The zoom is sped up after rendering so it lands in a few frames; H3 alone takes a second or two. The clip comes out shorter by about that much, and the render as H3 made it is kept as _raw.mp4."
}
```
