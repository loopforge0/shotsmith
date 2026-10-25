# Overhead swing to eye level

**Status:** verified (two renders: seed 7, and seed 11 on Claire, beach)
**Effect:** the camera starts a few metres straight above, looking down at the person head to toe as they look up, then swings down in front of them in a quarter-circle arc at the same distance, ending face-on at eye level.
**Why it is here:** A viewer's request on the 14-techniques video; they found "swing" works in H3.

## Shot line

> The camera swings down in front of {PRONOUN} in a smooth quarter-circle arc at slow speed, keeping the same distance from {PRONOUN} the whole way: it travels from straight above {POSSESSIVE} head down to {POSSESSIVE} eye level on the side {PRONOUN_SUBJ} is facing, tilting from pointing straight down to pointing level as it goes so {FACE} stays centred, and ends face-on to {PRONOUN} in a medium shot with the horizon level behind {PRONOUN}. It never passes behind {PRONOUN}, and it does not dive, fly forward or drop straight down.

**Not a drone (2026-10-25, pod 00035):** "high" and "like a drone" turned it into a drone dive (overhead-swing_7_553616ac45b4, much like the FPV drone move): an oblique aerial descending onto her. The move is a swing: now a few metres straight above, lens pointing down, then a quarter-circle arc at constant distance down to eye level, and it says it does not dive, fly forward or drop straight down. Result: seed 7 (overhead-swing_7_19b343ffd693) starts top-down with her small on the sand looking up and comes down in front of her to face-on, a little higher at the start and wider at the end than asked; seed 11 (overhead-swing_11_c7afe47bd721) is the truest arc but starts on the top of her head and swings round her back before reaching the front.

**Start high (2026-10-25):** the close-up start (overhead-swing_7_cbea1f0b49c8) worked, but it was meant to begin higher up, like a drone, not at a close-up. The framing now starts high with the person small on the ground, and the swing draws in to a medium close-up instead of holding the face at one size. Result (beach, seed 7, overhead-swing_7_553616ac45b4): a high drone view with her tiny on the sand between the groynes, descending and swinging round in front of her to end face-on at eye level, waist-up. The forest at native size failed on the 3060 too (overhead-swing_7_bcdda67e38a0, the exact prompt): the resolution, not the GPU, moves the composition.

**Native-resolution take (2026-10-25, overhead-swing_7_4862efe94d0c):** at 1344x768 seed 7 started high above her with the pines warped into a fisheye tunnel and swung round to end behind her head. The recipe said where the swing ends but not which side it comes down on. Now: down in front of her on the side she faces, never passing behind her. (An "arm's length directly above" was tried too and dropped: on the beach it read as a selfie, her arms reaching up as if holding the camera, where the original reads as a drone shot.) The tightened wording alone did not help: seed 7 again and seed 11 in the forest both swung behind her. On a beach at sunset (seed 7, overhead-swing_7_c58b29400285) it came down in front and ended face-on, so the forest was the cause.

## Machine-readable

```json
{
  "id": "N-02",
  "slug": "overhead-swing",
  "name": "swing down from overhead",
  "group": "angle",
  "status": "verified",
  "motion": "stationary",
  "length": 124,
  "framing": "A top-down overhead shot, the camera a few metres directly above {SUBJECT} with its lens pointing straight down, a bird's-eye view of {SUBJECT} from head to toe with the ground around and looking up into the lens",
  "framing_summary": "a top-down overhead shot",
  "shot_intro": "comma",
  "shot_line": "The camera swings down in front of {PRONOUN} in a smooth quarter-circle arc at slow speed, keeping the same distance from {PRONOUN} the whole way: it travels from straight above {POSSESSIVE} head down to {POSSESSIVE} eye level on the side {PRONOUN_SUBJ} is facing, tilting from pointing straight down to pointing level as it goes so {FACE} stays centred, and ends face-on to {PRONOUN} in a medium shot with the horizon level behind {PRONOUN}. It never passes behind {PRONOUN}, and it does not dive, fly forward or drop straight down.",
  "extra_slots": {},
  "app_note": "Works best in an open place such as a beach, field or plaza. Tall trees or buildings around the person can bend into a tunnel from overhead and send the swing round behind them.",
  "performance_note": "Start looking up into the lens and let the chin come down with the camera, e.g. \"looks up into the lens with a small, curious smile and lowers her chin to follow the camera down\"."
}
```
