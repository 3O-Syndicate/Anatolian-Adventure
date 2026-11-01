# Art generators

The hero, enemies, decor and level objects are drawn by Python scripts at
the game's pixel density (32x32 tiles, one art pixel = one screen pixel).
Change a script and run it again to rebuild every frame.

| Script | Writes |
| --- | --- |
| `art/hero/hero_sprite.py` | `player/hero/<animation>/<n>.png`, `player/hero/anim.json`, `effects/muzzle_flash/` |
| `art/props/props_sprite.py` | `enemies/`, `decor/`, `objects/`, `tiles/4.png` (cloud) |

```
python art/hero/hero_sprite.py
python art/props/props_sprite.py
```

Both need Pillow and numpy. Previews go to `art/hero/out/` and
`art/props/out/` (not committed).

`art/pixelkit.py` holds what they share: the colour ramps, the light
direction, shaded shapes (ellipse, capsule, polygon) and the dark outline.
Using it for new sprites keeps them in the same style.

## Hero

The hero is a rig of shaded body parts. Each animation frame is a `Pose`
(body, hips and head offsets, belly size, face, foot positions, gun angle);
the arms follow the shotgun automatically. Animations, frame durations and
looping are listed in `ANIMS`. `anim.json` also stores the gun muzzle
position of every frame (bullets and the muzzle flash start there), the
frame anchor and the standing/ducking hitbox sizes read by `player.py`.

## Placeholders

Enemies keep neutral code names so the lore can change without renaming
files: `walker` is drawn as a goose, `turtle` as a tortoise (walk, shell and
spinning shell). Decor images in `decor/` show up in the map editor's
Dekor tab automatically; a new `decor/<name>.png` needs no code change.
