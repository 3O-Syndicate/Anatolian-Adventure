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

Green 255 is reserved for white empty pixels, so terrain IDs range from 0 to 254.
Other colors have no behavior, including the existing yellow exit markers.

Optional textures are configured in `TERRAIN_TEXTURES` in `settings.py`.
Editable placeholders are provided in `tiles/ground.png`, `tiles/underground.png`,
and `tiles/brick.png`. Replace them with artwork and restart to reload textures.
Other IDs look for `tiles/<ID>.png`. Images are scaled to the tile size with
nearest-neighbor sampling. Missing textures use flat colored placeholders.
Type 0 never draws a texture. Terrain is rendered once into a transparent
surface when the level loads, then blitted over the background while scrolling.

The existing test map's magenta pixels are all type 0 and remain invisible.
Recolor chosen pixels to types 1 and above to make them visible. Save masks as
RGBA PNGs: indexed palettes may round small green-channel values to an existing
color and change the tile or spawn type.
