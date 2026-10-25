# POV shot

**Status:** verified (picked, 2026-10-25: pov-call_7_787b014efbc3)
**Effect:** the shot is the eyes of an unseen viewer; the camera moves as their head does, and only their hand ever appears. What happens in front of them is the user's action.
**Why it is here:** Hardcore Henry, Peep Show. One of MiniMax's twelve primitives (POV).

**Take 1** (pov_7_750d702e78d2, Sofia, Tokyo alley): a follow shot from behind her, not a POV. The
standard retention line holds her face "identical to <Picture 1> in every frame", which asks for her
face to be on screen and works against a first-person view when she is the viewer.

**Take 2** (pov_7_69e929bdcda1): with only her hands kept, a true first-person view, but two hands held out
in front read as a zombie POV. From take 3 the character is the person the viewer sees.

**Takes 3-5** (pov_7_094ffc7a0a3b, pov_7_15ba55af99f8, pov_7_8a21818889d4, pov_7_7b49e7f89c50,
pov_7_88a68b406b05, pov-call_7_787b014efbc3): the walk-up, tap and handshake written into the recipe.
Learned along the way: a passive task ("reading a menu", "unlocking a car") comes out as standing still;
the hand's beats need "first... then... only then" and the hand leaving the frame between them; a tap
lands in the air unless the camera comes within arm's reach.

**Take 6**: one POV move, not a set of scenes. The recipe now sets up only the first-person camera,
and the walk-up, the tap or the called name, and the handshake come from the user's action. The
preferred take is the called-by-name version (pov-call_7_787b014efbc3), so that is the test action.

**Take 6 result** (pov_7_7c94e06ff095): works with the scene only in the action. The action didn't say she
was in view at the start, so H3 opened on the empty road and found her halfway through. Where the
character is at the start belongs in the user's prompt, not the move.

## Machine-readable

```json
{
  "id": "F-06",
  "slug": "pov",
  "name": "POV shot",
  "group": "specialty",
  "status": "verified",
  "motion": "stationary",
  "length": 192,
  "framing": "A first-person POV shot {PLACE}",
  "framing_summary": "a first-person POV shot",
  "shot_intro": "custom",
  "shot_line": "A first-person POV shot {PLACE}, with {ENVIRONMENT_ELEMENTS} around: the camera is the eyes of an unseen viewer and moves exactly as the viewer's head does, swaying gently with each step when the viewer walks, and {SUBJECT} is seen through the viewer's eyes. Only the viewer's own hand ever appears, reaching in from the bottom of the frame when the viewer touches or takes something.",
  "app_note": "Describe what happens in front of the viewer: who they walk up to, what they say, what they reach for. The viewer's hand appears only when they touch something.",
  "extra_slots": {}
}
```
