# Cut-away montage (effect)

**Status:** verified (picked, 2026-10-25: cutaway-montage_7_a0d781db0401)
**Effect:** a close-up of the character, then four lightning-fast inserts of their hands getting ready, each a fraction of a second, then a snap back to their face. The prep montage of Guy Ritchie's and Edgar Wright's films.
**Take 1** (cutaway-montage_7_8deccfbd8998, Lena, concert stage): the seven cuts land on time, but the cable
jack went into the guitar strap from the insert before, and the tuning peg became a knob on the amp from
the insert before. Each insert under half a second picks up the last thing shown, so inserts must name
the object and where on it the hands work.

**Take 1, Claire** (cutaway-montage_7_02e5fe0de109, desert highway): all four inserts right, but the
seatbelt and the gear stick were both done two-handed, because the template put "her hands" before every
insert. The template now leaves the hands out ("as she reaches to ...") and each insert says one hand or both.

**Why it is here:** it was asked for. MiniMax's guide documents timed cuts inside one clip; this packs seven into five seconds.

**Where the montage ends (2026-10-25, native 00031):** the closing eyes and face close-ups said "cuts back to the tight close-up", which points at Shot 1, so H3 put her back on the highway; and the sunglasses insert, unlike the seatbelt and gear stick, did not imply the car. Shots 6 and 7 now stay "in the same place as the last insert", and the app note asks for the place when the object does not give it. That was not enough (native 00038): the last insert, a gear stick in extreme close-up, shows almost nothing of the car, so the closing close-ups came out on a neutral background. They now take WHERE_IT_ENDS, where the montage ends up with what is around, named in both. Review also caught continuity: having put the sunglasses on, she should end wearing them, which an eyes close-up cannot show. Shot 6 is now a close-up on the face as the gaze snaps up, and WHERE_IT_ENDS also carries anything the inserts put on. Result (seed 7, cutaway-montage_7_304523c26fc8): every beat right, keys one-handed, seatbelt once, sunglasses on in the car, gear stick, then both closing close-ups in the driver's seat with the sunglasses on. The seatbelt insert was then simplified by hand (pod 00050, now the native clip): "as she pulls the seatbelt and clicks it into place" instead of "close on the action as she reaches to pull the seatbelt across and click its metal tongue into the buckle at the hip with the right hand". The long, over-specified insert was the weak one; a short, plain action reads better.

## Machine-readable

```json
{
  "id": "F-10",
  "slug": "cutaway-montage",
  "name": "cut-away montage",
  "group": "specialty",
  "kind": "effect",
  "status": "verified",
  "motion": "stationary",
  "length": 124,
  "framing": "{MEDIUM_FRAMING}",
  "summary": "getting ready in a rapid, rhythmic cut-away montage of quick inserts",
  "retention": "{POSSESSIVE} face, identity and clothing are held identical to {PLATE} in every shot, and the hands in the inserts are {POSSESSIVE} own.",
  "shot_line": "A tight close-up frames {FACE} {PLACE}, with {ENVIRONMENT_ELEMENTS} soft behind {PRONOUN}; {POSSESSIVE} eyes narrow with focus as {PRONOUN_SUBJ} decides. [Shot 2] At 00:01.300, the shot cuts to an extreme close-up insert, close on the action as {PRONOUN_SUBJ} reaches to {INSERT_1}. [Shot 3] At 00:01.700, the shot cuts to an extreme close-up insert, close on the action as {PRONOUN_SUBJ} reaches to {INSERT_2}. [Shot 4] At 00:02.100, the shot cuts to an extreme close-up insert, close on the action as {PRONOUN_SUBJ} reaches to {INSERT_3}. [Shot 5] At 00:02.500, the shot cuts to an extreme close-up insert, close on the action as {PRONOUN_SUBJ} reaches to {INSERT_4}. [Shot 6] At 00:02.900, the shot cuts to an extreme close-up on {POSSESSIVE} face, now {WHERE_IT_ENDS}, as {POSSESSIVE} gaze snaps up, sharp and ready. [Shot 7] At 00:03.300, the shot cuts to a tight close-up of {FACE}, still {WHERE_IT_ENDS}, now still and ready, and {PRONOUN_SUBJ} looks up into the lens with a small, sure smile.",
  "sound": "{SOUNDSCAPE}, cut into a tight rhythm: a sharp click, snap, whoosh or thud on every insert, then a beat of quiet",
  "music": "N/A",
  "app_note": "Name each object and exactly where the hands work on it: \"push the cable's plug into the socket on the guitar's body\", not \"plug in the guitar\", and say one hand or both: \"with the right hand\". Each insert is a fraction of a second, so H3 reuses whatever was in the insert before unless told otherwise. Say where an insert happens when the object does not make it obvious: \"slide on dark sunglasses in the driver's seat\". Then say where the montage ends up, with what is around, and anything the inserts put on (sunglasses, a jacket), so the closing close-ups match.",
  "extra_slots": {"INSERT_1": "the first insert", "INSERT_2": "the second insert", "INSERT_3": "the third insert", "INSERT_4": "the fourth insert",
    "WHERE_IT_ENDS": "where the montage ends up, with what is around, and anything the inserts put on, e.g. \"in the driver's seat of the car, with the steering wheel, dashboard and windscreen all around, the dark sunglasses on\""}
}
```
