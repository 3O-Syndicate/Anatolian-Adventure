# Map masks

Only `<level>_mask.png` is needed. Each pixel becomes a 32×32 world tile.
The full-size `<level>.png` artwork is no longer loaded.

Colors are RGBA (`0xRRGGBBAA`). Alpha is reserved and currently ignored.

| Mask color | Meaning |
| --- | --- |
| `(255, 0, 255, A)` / `0xFF00FFAA` | Invisible solid collision |
| `(255, 1, 255, A)` | Ground, solid |
| `(255, 2, 255, A)` | Underground, solid |
| `(255, 3, 255, A)` | Brick, solid |
| `(255, 4..254, 255, A)` | Additional solid tile types |
| White or black | Empty space |
| `(0, 255, 255, A)` | Player spawn |
| `(0, 255, 0, A)` | Health pickup |
| `(255, 1, 0, A)` | Walking enemy |
| `(255, 2, 0, A)` | Turtle |
| `(255, 255, 1..254, A)` | Tunnel mouth; blue is the pair ID |
| `(255, 255, 0, A)` | Inactive legacy yellow marker |

Green 255 is reserved for white empty pixels, so terrain IDs range from 0 to 254.
Other colors have no behavior.

## Tunnels

Place exactly two pixels with the same `(255, 255, ID)` color for each tunnel
pair, using IDs 1–254. For example, `(255, 255, 1)` / `0xFFFF01FF` connects the
two ID-1 mouths. White (blue 255) is empty; pure yellow (blue 0) stays inactive.
Invalid pairs stop level loading with their IDs and pixel coordinates.

Place each marker in an empty tile immediately above a solid floor or pipe top.
Markers do not create collisions or visible artwork: build the surrounding pipe
with terrain tiles. Stand with the player's center over the marker and press S
to teleport. The player's feet arrive at the destination marker's bottom edge,
just above its supporting floor. Leave room for the entire player above and
around the destination; blocked or out-of-map exits cannot be entered.

Teleporting clears velocity and snaps the camera to the destination. Hold S
without returning immediately; release and press it again to go back. An S
press while airborne does not queue entry for landing. Pairs are within one level.

Optional textures are configured in `TERRAIN_TEXTURES` in `settings.py`.
Editable placeholders are provided in `tiles/ground.png`, `tiles/underground.png`,
and `tiles/brick.png`. Replace them with artwork and restart to reload textures.
Other IDs look for `tiles/<ID>.png`. Images are scaled to the tile size with
nearest-neighbor sampling. Missing textures use flat colored placeholders.
Type 0 never draws a texture. Terrain is rendered once into a transparent
surface when the level loads, then blitted over the background while scrolling.

Type-0 magenta pixels remain invisible; recolor chosen pixels to types 1 and
above to make them visible. Save masks as
RGBA PNGs: indexed palettes may round small green-channel values to an existing
color and change the tile or spawn type.
