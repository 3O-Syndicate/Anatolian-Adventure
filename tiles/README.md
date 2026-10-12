# Terrain textures

These editable PNG placeholders are loaded directly by the game:

| File | Green-channel terrain ID |
| --- | --- |
| `ground.png` | 1 |
| `underground.png` | 2 |
| `brick.png` | 3 |

Replace or edit these files in any image editor and restart the game to reload
them. Use 32×32 RGBA PNGs for pixel-perfect tiles; other dimensions are scaled
to 32×32 using nearest-neighbor sampling. Texture transparency is supported.

For additional types, add `<ID>.png` here or configure a filename in
`TERRAIN_TEXTURES` in `settings.py`. ID 0 always stays invisible.

Tests read the existing ground texture and do not create, overwrite, or delete
artwork. The placeholders are ordinary project assets, not temporary test files.
