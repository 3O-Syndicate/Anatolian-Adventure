# Levels

Each level is `levels/<n>.json`. Edit them with the map editor:

```
python editor.py 1
```

`levels/0.json` is the old test map converted from `0_mask.png`.
`levels/1.json` is a sample level that shows every feature (decor on both
layers, coins, a tunnel pair, enemies facing both ways, checkpoint, goal);
rework or replace it freely. Play a level directly with
`python main.py --level 1`, or press F5 in the editor.

## Map editor

The editor draws the level with the game's own tiles, decor and sprites.
The right panel has three tabs: **Zemin** (terrain), **Dekor** (decor) and
**Nesne** (objects).

| Input | Action |
| --- | --- |
| Left drag | Paint the selected tile / decor / object |
| Right drag | Erase on the current tab |
| Middle drag, or Space + left drag | Move the view |
| Wheel | Zoom (0.5x, 1x, 2x) |
| `1` `2` `3` | Terrain / decor / object tab |
| `B` / `R` | Brush / rectangle (rectangle fills terrain) |
| `L` | Decor layer: back (behind terrain) or front (over the player) |
| `G` | Grid on/off |
| Alt + click, or `I` | Pick what is under the cursor |
| `F` | Turn the enemy under the cursor around |
| `+` / `-` | Change the pair number of the tunnel, or the item of the chest, under the cursor |
| `T` | Type the text of the hint sign under the cursor (`Enter` saves, `Esc` cancels); a new sign asks for it right away |
| `Ctrl+Z` / `Ctrl+Y` | Undo / redo |
| `Ctrl` + arrows | Resize: columns at the right edge, rows at the top |
| `PgUp` / `PgDn` | Previous / next level; a new number starts an empty level |
| `F5` | Save and play this level |
| `Ctrl+S` | Save; problems are listed in the panel |
| `Esc` | Quit (press twice to drop unsaved changes) |

Placement rules: one object per tile; the player and the goal move instead
of duplicating; a new tunnel mouth joins a mouth that has no partner yet,
otherwise it starts a new pair. Wide decor goes down one per click, 1-tile
decor (fence, grass, ...) and coins can be dragged.

Saving warns about a missing player or goal, tunnel pairs without exactly
two mouths, and anything outside the map. F5 refuses to start the game while
a tunnel has no partner, because the game rejects such levels.

## File format

The format lives in `level_format.py`, shared by the game and the editor.
Files keep one terrain row, decor or object per line so git diffs stay
readable.

```json
{
  "version": 1,
  "width": 120,
  "height": 20,
  "background": [110, 175, 230],
  "terrain": [
    "......",
    "111111",
    "222222"
  ],
  "decor": [
    {"id": "tree", "x": 8, "y": 16, "layer": "back"}
  ],
  "entities": [
    {"type": "player", "x": 3, "y": 16},
    {"type": "walker", "x": 25, "y": 16, "dir": -1},
    {"type": "tunnel", "x": 20, "y": 16, "pair": 1}
  ]
}
```

Coordinates are tile columns (`x`) and rows (`y`), counted from the top left.

**Terrain** is one character per tile:

| Character | Tile |
| --- | --- |
| `.` | Empty |
| `#` | Invisible solid (terrain ID 0) |
| `1` | Ground (`tiles/ground.png`) |
| `2` | Underground (`tiles/underground.png`) |
| `3` | Brick (`tiles/brick.png`) |
| `4` | Cloud platform (`tiles/4.png`) |
| `5`-`9`, `A`-`Z` | Terrain IDs 5-35, texture `tiles/<ID>.png` |

Textures are configured in `TERRAIN_TEXTURES` in `settings.py`; other IDs
look for `tiles/<ID>.png`, and missing textures use flat coloured
placeholders. All terrain is solid.

**Decor** never collides. `id` is a file in `decor/` (without `.png`).
`x, y` is the tile the image's bottom-left corner stands in. Layer `back`
is drawn behind the terrain, `front` in front of the player.

**Entities** take one tile each:

| Type | Meaning | Extra keys |
| --- | --- | --- |
| `player` | Start position; the player's feet stand in this tile | |
| `walker` | Walking enemy (goose art) | `dir`: -1 starts left, 1 right |
| `turtle` | Shell enemy (tortoise art) | `dir` |
| `health` | Health pickup | |
| `coin` | Coin | |
| `tunnel` | Tunnel mouth, in an empty tile right above a floor | `pair`: mouths with the same pair connect |
| `checkpoint` | Checkpoint flag; after touching it the player respawns there instead of losing | |
| `goal` | Goal flag; touching it finishes the level | |
| `chest` | Treasure chest, opens on touch: `shotgun` +30 ammo, `armor` stops one enemy hit, `acid` 3 flasks (Q pours a puddle that dissolves enemies for 4 s) | `item`: `acid`, `shotgun` or `armor` |
| `wallet` | Dropped wallet: +5 coins | |
| `hint` | Sign whose text pops up in a bubble while the player is near | `text` |

## Old colour masks

Before the JSON files, levels were `<level>_mask.png` images where each
pixel is one 32x32 tile. When `<level>.json` exists the mask is ignored;
without a JSON file the mask still loads. Convert one for good with:

```
python level_format.py import levels/0_mask.png levels/0.json
```

| Mask colour | Meaning |
| --- | --- |
| `(255, 0, 255)` | Invisible solid collision |
| `(255, 1..35, 255)` | Terrain ID 1-35 (1 ground, 2 underground, 3 brick) |
| White or black | Empty space |
| `(0, 255, 255)` | Player spawn |
| `(0, 255, 0)` | Health pickup |
| `(255, 1, 0)` | Walking enemy |
| `(255, 2, 0)` | Turtle |
| `(255, 255, 1..254)` | Tunnel mouth; blue is the pair number |

Masks can hold terrain IDs up to 254, but the JSON format has characters
for IDs 0-35 only; the importer stops on higher IDs. Save masks as RGBA
PNGs: indexed palettes may round small channel values and change a type.
