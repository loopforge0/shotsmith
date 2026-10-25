"""Generate bundled location plates with Qwen Image 2.1 turbo and add them to samples.json.

Each location is also a full text scene, so the same place can be tested as a description or as an
image. Every location has separate, solid things in it (posts, lamps, shelves) that a camera move
can be read against.

    COMFY_BASE_URL=http://127.0.0.1:8189 python scripts/gen_locations.py [slug ...]
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from shotstudio import render  # noqa: E402

SAMPLES = ROOT / "shotstudio" / "samples.json"
OUT = ROOT / "shotstudio" / "static" / "locations"

STYLE = ("A wide cinematic photograph, eye level, natural perspective, no people, empty of any person or "
         "figure, realistic film still with fine detail and soft depth.")

# name, slug, image prompt, then the scene slots.
LOCATIONS = [
    ("Desert highway", "desert-highway",
     "A straight two-lane desert highway running to the horizon at golden hour, red sandstone mesas on both "
     "sides, a row of wooden telephone poles along the right shoulder, a faded road sign, cracked asphalt "
     "with a dashed yellow centre line, long low shadows.",
     {"ENVIRONMENT": "an empty desert highway at golden hour", "ENVIRONMENT_PREP": "on",
      "PLACE": "on the centre line of the highway",
      "ENVIRONMENT_ELEMENTS": "red sandstone mesas, wooden telephone poles along the shoulder, a faded road sign and the road running to the horizon",
      "LIGHTING": "low warm golden-hour sun from the side, long shadows", "PALETTE": "a warm orange and dusty blue palette",
      "SOUNDSCAPE": "A dry desert wind continues throughout, with the faint hum of the telephone wires",
      "BACKGROUND": "the telephone poles, the road sign and the mesas"}),
    ("Tokyo alley", "tokyo-alley",
     "A narrow Tokyo side alley at night, rows of glowing red paper lanterns hanging overhead, small izakaya "
     "fronts with noren curtains, two lit vending machines on the left, bicycles leaning on a wall, wet "
     "paving stones reflecting the light, tangled power lines above.",
     {"ENVIRONMENT": "a narrow Tokyo alley at night", "ENVIRONMENT_PREP": "in",
      "PLACE": "in the middle of the lantern-lit alley",
      "ENVIRONMENT_ELEMENTS": "red paper lanterns, izakaya fronts, lit vending machines, parked bicycles and wet paving stones",
      "LIGHTING": "warm lantern glow mixed with the cold light of the vending machines", "PALETTE": "a red and teal palette",
      "SOUNDSCAPE": "Muffled chatter and clinking glasses from the bars, the hum of the vending machines and a light drizzle",
      "BACKGROUND": "the hanging lanterns, the vending machines and the bar fronts"}),
    ("Old library", "old-library",
     "A grand old library hall, two storeys of tall dark wooden bookshelves packed with books, a rolling "
     "ladder, brass reading lamps with green shades on long oak tables, tall arched windows letting in "
     "dusty shafts of daylight, a polished wooden floor.",
     {"ENVIRONMENT": "a grand old library hall", "ENVIRONMENT_PREP": "in",
      "PLACE": "between the long reading tables",
      "ENVIRONMENT_ELEMENTS": "tall wooden bookshelves, a rolling ladder, green-shaded brass lamps and arched windows",
      "LIGHTING": "dusty shafts of daylight from tall windows, warm lamp light", "PALETTE": "a warm brown and amber palette",
      "SOUNDSCAPE": "The hush of a large quiet room, a clock ticking somewhere and a page turning far away",
      "BACKGROUND": "the bookshelves, the rolling ladder and the arched windows"}),
    ("Concert stage", "concert-stage",
     "An empty concert stage, tall deep-red velvet curtains, a single warm spotlight beam falling from high "
     "above onto centre stage, a chrome microphone on a tall stand, a drum kit on a riser behind, stacked "
     "keyboards to the left, monitor wedges, a polished wooden stage floor reflecting the warm light.",
     {"ENVIRONMENT": "a concert stage", "ENVIRONMENT_PREP": "on", "PLACE": "centre stage under the spotlight",
      "ENVIRONMENT_ELEMENTS": "red velvet curtains, a microphone stand, a drum kit on a riser, stacked keyboards and monitor wedges",
      "LIGHTING": "warm amber stage lighting with a hard spotlight from above and deep shadow beyond it",
      "PALETTE": "rich saturated reds",
      "SOUNDSCAPE": "The quiet room tone of a large empty auditorium, with faint distant creaks",
      "BACKGROUND": "the red curtains, the drum kit and the keyboards"}),
    ("Rooftop at golden hour", "rooftop",
     "A city rooftop terrace at golden hour, strings of warm festoon lights overhead, potted olive trees and "
     "wooden planters, a low glass railing, distant glass towers and water towers across the skyline, the "
     "low sun flaring between buildings.",
     {"ENVIRONMENT": "a city rooftop terrace at golden hour", "ENVIRONMENT_PREP": "on",
      "PLACE": "on the rooftop deck",
      "ENVIRONMENT_ELEMENTS": "string lights, potted olive trees, a glass railing and distant towers",
      "LIGHTING": "warm golden-hour sunlight with lens flare", "PALETTE": "a rich saturated golden palette",
      "SOUNDSCAPE": "City traffic far below and wind moving through the string lights",
      "BACKGROUND": "the string lights, the water towers and the glass towers"}),
    ("Subway platform", "subway-platform",
     "An empty underground subway platform at night, white tiled walls, a row of steel pillars receding "
     "into the distance, flickering fluorescent tube lights, a yellow safety line along the platform edge, "
     "station name signs, the dark mouth of the tunnel at the far end.",
     {"ENVIRONMENT": "an empty subway platform", "ENVIRONMENT_PREP": "on", "PLACE": "on the platform",
      "ENVIRONMENT_ELEMENTS": "tiled walls, a row of steel pillars, fluorescent lights and the dark tunnel mouth",
      "LIGHTING": "cold flickering fluorescent light", "PALETTE": "a sickly green and grey palette",
      "SOUNDSCAPE": "The buzz of fluorescent tubes and a distant train rumbling in the tunnel",
      "BACKGROUND": "the steel pillars, the light tubes and the tunnel mouth"}),
    ("Beach at sunset", "beach-sunset",
     "A wide sandy beach at sunset, a wooden lifeguard tower on stilts, a line of weathered wooden groynes "
     "running into the sea, gentle waves, wet sand reflecting a pink and orange sky, a distant pier with "
     "lights.",
     {"ENVIRONMENT": "a wide beach at sunset", "ENVIRONMENT_PREP": "on", "PLACE": "on the wet sand",
      "ENVIRONMENT_ELEMENTS": "a lifeguard tower, wooden groynes, gentle waves and a distant pier",
      "LIGHTING": "soft warm sunset light from low on the horizon", "PALETTE": "a pink and orange palette",
      "SOUNDSCAPE": "Gentle waves breaking and gulls calling in the distance",
      "BACKGROUND": "the lifeguard tower, the groynes and the pier"}),
    ("Glass greenhouse", "greenhouse",
     "The inside of a tall Victorian glass greenhouse, white painted iron arches and glass panes, giant "
     "palms and tree ferns, hanging baskets, a tiled path down the middle, misty humid air with soft "
     "daylight through the glass.",
     {"ENVIRONMENT": "a Victorian glass greenhouse", "ENVIRONMENT_PREP": "in", "PLACE": "on the tiled path",
      "ENVIRONMENT_ELEMENTS": "white iron arches, giant palms, tree ferns and hanging baskets",
      "LIGHTING": "soft diffused daylight through misty glass", "PALETTE": "a lush green and white palette",
      "SOUNDSCAPE": "Water dripping from leaves and the soft hiss of misters",
      "BACKGROUND": "the iron arches, the palms and the hanging baskets"}),
    ("Fifties diner", "diner",
     "The inside of a 1950s American diner at night, a long chrome counter with red vinyl stools, red "
     "booth seats, a black and white checkered floor, a jukebox, pie cases, neon signs glowing in the "
     "windows, rain outside.",
     {"ENVIRONMENT": "a 1950s diner at night", "ENVIRONMENT_PREP": "in", "PLACE": "beside the counter",
      "ENVIRONMENT_ELEMENTS": "a chrome counter with red stools, red booths, a jukebox and neon signs in the windows",
      "LIGHTING": "warm overhead light mixed with neon from the windows", "PALETTE": "a red, chrome and pastel palette",
      "SOUNDSCAPE": "A quiet diner hum, a coffee machine gurgling and rain against the windows",
      "BACKGROUND": "the red stools, the jukebox and the neon signs"}),
    ("Mountain lake", "mountain-lake",
     "A still alpine lake at dawn, a wooden jetty running out into the water, a red rowing boat tied to it, "
     "pine trees along the shore, jagged snow-capped peaks reflected in the glassy water, thin mist on the "
     "surface.",
     {"ENVIRONMENT": "an alpine lake at dawn", "ENVIRONMENT_PREP": "on", "PLACE": "at the end of the jetty",
      "ENVIRONMENT_ELEMENTS": "a wooden jetty, a red rowing boat, shoreline pines and snow-capped peaks",
      "LIGHTING": "cool soft dawn light with the first warm sun on the peaks", "PALETTE": "a cool blue and pale gold palette",
      "SOUNDSCAPE": "Still morning air, water lapping at the jetty and a bird calling across the lake",
      "BACKGROUND": "the pines, the rowing boat and the mountain peaks"}),
]

LOCATIONS += [
    ("Castle dungeon", "dungeon",
     "A medieval castle dungeon, rough stone walls and a low vaulted ceiling, a row of rusted iron cell "
     "bars along the right, flaming torches in iron brackets, heavy chains hanging from the wall, wet "
     "flagstones with puddles, a narrow stone staircase leading up into darkness at the back.",
     {"ENVIRONMENT": "a medieval castle dungeon", "ENVIRONMENT_PREP": "in", "PLACE": "in the torchlit passage",
      "ENVIRONMENT_ELEMENTS": "rough stone walls, rusted iron cell bars, flaming torches and hanging chains",
      "LIGHTING": "flickering orange torchlight with deep black shadows", "PALETTE": "a dark amber and black palette",
      "SOUNDSCAPE": "Water dripping on stone, torches crackling and a chain creaking somewhere in the dark",
      "BACKGROUND": "the cell bars, the torches and the stone staircase"}),
    ("Space station", "space-station",
     "The observation deck of a space station in orbit, a huge curved window looking down on the blue "
     "Earth and the black starfield, white panelled walls with handrails and status lights, a row of "
     "consoles with glowing screens, cables and ducts along the ceiling.",
     {"ENVIRONMENT": "the observation deck of a space station", "ENVIRONMENT_PREP": "on",
      "PLACE": "in front of the great window",
      "ENVIRONMENT_ELEMENTS": "a huge curved window onto the Earth and the stars, white panelled walls, handrails and glowing consoles",
      "LIGHTING": "cool blue earthlight through the window and small coloured status lights",
      "PALETTE": "a clean white, black and blue palette",
      "SOUNDSCAPE": "The low hum of life support, soft electronic beeps and the hiss of air vents",
      "BACKGROUND": "the consoles, the handrails and the Earth beyond the window"}),
    ("Surface of Mars", "mars",
     "The surface of Mars, a rust-red rocky plain strewn with boulders, a ridge of jagged red cliffs, a "
     "small white landing module with solar panels on the left, tyre tracks in the dust, a butterscotch "
     "sky with a small pale sun low over the horizon.",
     {"ENVIRONMENT": "the surface of Mars", "ENVIRONMENT_PREP": "on", "PLACE": "on the red rocky plain",
      "ENVIRONMENT_ELEMENTS": "rust-red boulders, jagged cliffs, a white landing module and a butterscotch sky",
      "LIGHTING": "thin pale sunlight from low on the horizon", "PALETTE": "a rust red and butterscotch palette",
      "SOUNDSCAPE": "A thin, faint wind and fine dust hissing over the rocks",
      "BACKGROUND": "the boulders, the landing module and the cliffs"}),
    ("Underwater reef", "underwater-reef",
     "An underwater coral reef in clear tropical water, towering coral heads and sea fans, a school of "
     "silver fish, sunbeams slanting down from the bright surface above, white sand on the sea floor, a "
     "sunken anchor half covered in coral.",
     {"ENVIRONMENT": "a coral reef underwater", "ENVIRONMENT_PREP": "on", "PLACE": "above the white sand of the reef",
      "ENVIRONMENT_ELEMENTS": "towering coral heads, sea fans, a school of silver fish and a sunken anchor",
      "LIGHTING": "rippling sunbeams from the surface above", "PALETTE": "a turquoise and coral palette",
      "SOUNDSCAPE": "Muffled underwater ambience, rising bubbles and the faint crackle of the reef",
      "BACKGROUND": "the coral heads, the sea fans and the anchor"}),
    ("Ice cave", "ice-cave",
     "The inside of a glacier ice cave, walls and ceiling of translucent blue ice with ripples and "
     "trapped bubbles, long icicles hanging from above, a frozen stream along the floor, a bright opening "
     "at the far end letting in white daylight.",
     {"ENVIRONMENT": "a glacier ice cave", "ENVIRONMENT_PREP": "in", "PLACE": "in the middle of the ice cave",
      "ENVIRONMENT_ELEMENTS": "translucent blue ice walls, hanging icicles, a frozen stream and the bright opening",
      "LIGHTING": "cold blue light glowing through the ice", "PALETTE": "an icy blue and white palette",
      "SOUNDSCAPE": "Water dripping from the icicles and the deep creak of the glacier",
      "BACKGROUND": "the icicles, the ice ripples and the cave mouth"}),
    ("Jungle temple ruins", "temple-ruins",
     "Ancient stone temple ruins deep in a jungle, a stepped stone pyramid covered in moss and vines, "
     "carved stone pillars, giant tree roots breaking through the steps, a broken stone idol, mist and "
     "green light filtering through the canopy.",
     {"ENVIRONMENT": "ancient temple ruins in the jungle", "ENVIRONMENT_PREP": "among",
      "PLACE": "on the mossy temple steps",
      "ENVIRONMENT_ELEMENTS": "a mossy stepped pyramid, carved pillars, giant tree roots and a broken stone idol",
      "LIGHTING": "soft green light filtering through the canopy, drifting mist", "PALETTE": "a deep green and grey stone palette",
      "SOUNDSCAPE": "Dense jungle sound, birds calling, insects buzzing and water trickling over stone",
      "BACKGROUND": "the carved pillars, the tree roots and the pyramid"}),
    ("Throne room", "throne-room",
     "A vast gothic castle throne room, a tall carved stone throne on a raised dais at the far end, "
     "towering stone columns in two rows, long red banners hanging from the vaulted ceiling, tall stained "
     "glass windows, iron chandeliers with candles, a long red carpet down the middle.",
     {"ENVIRONMENT": "a vast gothic throne room", "ENVIRONMENT_PREP": "in", "PLACE": "on the long red carpet",
      "ENVIRONMENT_ELEMENTS": "towering stone columns, red banners, stained glass windows and a carved throne",
      "LIGHTING": "coloured light through stained glass and warm candlelight", "PALETTE": "a deep red and gold palette",
      "SOUNDSCAPE": "The echoing hush of a vast stone hall and candles guttering",
      "BACKGROUND": "the stone columns, the banners and the throne"}),
    ("Neon megacity", "neon-megacity",
     "A futuristic cyberpunk megacity street at night, enormous towers covered in glowing holographic "
     "advertisements, an elevated train track overhead, flying cars streaking between buildings, steam "
     "vents, crowded stalls with neon kanji signs, rain-slicked pavement.",
     {"ENVIRONMENT": "a cyberpunk megacity street at night", "ENVIRONMENT_PREP": "on", "PLACE": "on the rain-slicked street",
      "ENVIRONMENT_ELEMENTS": "towers covered in holographic adverts, an elevated train track, flying cars and neon stalls",
      "LIGHTING": "saturated neon and holographic light", "PALETTE": "an electric pink, cyan and violet palette",
      "SOUNDSCAPE": "A dense city hum, an overhead train rattling past and distant electronic announcements",
      "BACKGROUND": "the holographic adverts, the train track and the towers"}),
    ("Wild West town", "wild-west",
     "The dusty main street of an old Wild West frontier town at noon, wooden false-front buildings with "
     "a saloon, a general store and a sheriff's office, hitching posts with horses, a water trough, a "
     "wooden boardwalk, tumbleweed, desert hills beyond.",
     {"ENVIRONMENT": "a Wild West frontier town", "ENVIRONMENT_PREP": "in", "PLACE": "in the middle of the dusty main street",
      "ENVIRONMENT_ELEMENTS": "a saloon, a general store, hitching posts with horses and a wooden boardwalk",
      "LIGHTING": "hard bright noon sun with short shadows", "PALETTE": "a sun-bleached tan and brown palette",
      "SOUNDSCAPE": "A hot dry wind, a horse snorting and a saloon door creaking",
      "BACKGROUND": "the saloon, the hitching posts and the water tower"}),
    ("Glowing forest", "glowing-forest",
     "A fantasy forest at night lit by bioluminescence, giant mushrooms glowing soft blue and violet, "
     "ferns with glowing tips, twisted ancient trees, floating motes of light, a small stream reflecting "
     "the glow, mist between the trunks.",
     {"ENVIRONMENT": "a glowing fantasy forest at night", "ENVIRONMENT_PREP": "in", "PLACE": "beside the glowing stream",
      "ENVIRONMENT_ELEMENTS": "giant glowing mushrooms, ferns with glowing tips, twisted trees and floating motes of light",
      "LIGHTING": "soft blue and violet bioluminescent glow", "PALETTE": "a deep blue, violet and teal palette",
      "SOUNDSCAPE": "A hushed night forest, a trickling stream and a soft high shimmering hum",
      "BACKGROUND": "the glowing mushrooms, the twisted trees and the stream"}),
]

COMMON = {"GEAR": "an ARRI Alexa", "MUSIC": "N/A", "PERFORMANCE": "expression shifts slowly from calm into quiet wonder"}

samples = json.loads(SAMPLES.read_text(encoding="utf-8"))
only = set(sys.argv[1:])
for name, slug, prompt, scene in LOCATIONS:
    if only and slug not in only:
        continue
    path = OUT / f"{slug}.png"
    if not path.exists():
        render.generate_image(f"{prompt} {STYLE}", path, seed=7)
        print("generated", path.name, flush=True)
    samples["scenes"][name] = {**COMMON, **scene, "LOCATION": scene["ENVIRONMENT"].split(" at ")[0].replace("an ", "the ", 1).replace("a ", "the ", 1),
                               "image": f"locations/{slug}.png"}
SAMPLES.write_text(json.dumps(samples, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
print("samples.json:", len(samples["scenes"]), "scenes")
