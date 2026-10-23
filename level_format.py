"""
level_format.py

Level files (levels/<n>.json), shared by the game and the map editor.

A level is a dict:
    version     format version (1)
    width       size in tiles
    height
    background  sky colour [r, g, b]
    terrain     one string per tile row; one character per tile:
                  "."      empty
                  "#"      invisible solid (terrain ID 0)
                  "1".."9", "A".."Z"   terrain IDs 1-35 (textures in tiles/)
    decor       [{"id": "tree", "x": 4, "y": 20, "layer": "back"}, ...]
                id is a file in decor/; (x, y) is the tile the image's bottom-left
                corner stands in; layer "back" is drawn behind the terrain,
                "front" in front of the player. Decor never collides.
    entities    [{"type": "walker", "x": 10, "y": 20, "dir": -1}, ...]
                one tile each, see ENTITY_TYPES. Extra keys per type:
                  walker/turtle  dir: -1 starts walking left, 1 right
                  tunnel         pair: two tunnels with the same pair connect

Old colour-mask levels (levels/<n>_mask.png) still load: they are converted
with mask_to_level(). Convert one for good with:
    python level_format.py import levels/0_mask.png levels/0.json
"""
import json
import os
import sys

from settings import MAP_BACKGROUND

FORMAT_VERSION = 1
EMPTY = "."
INVISIBLE = "#"
ID_CHARS = "123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"  # terrain IDs 1..35
DEFAULT_BACKGROUND = list(MAP_BACKGROUND)

ENTITY_TYPES = {
    # type: (default extra keys, how many a level should have)
    "player":     ({}, "one"),
    "walker":     ({"dir": -1}, "any"),
    "turtle":     ({"dir": -1}, "any"),
    "health":     ({}, "any"),
    "coin":       ({}, "any"),
    "tunnel":     ({"pair": 1}, "pairs"),
    "checkpoint": ({}, "any"),
    "goal":       ({}, "one"),
}
DECOR_LAYERS = ("back", "front")


# --- terrain characters ---------------------------------------------------

def tile_char(tile_id):
    """Terrain ID (None = empty) -> file character."""
    if tile_id is None:
        return EMPTY
    if tile_id == 0:
        return INVISIBLE
    if 1 <= tile_id <= len(ID_CHARS):
        return ID_CHARS[tile_id - 1]
    raise ValueError(f"terrain ID {tile_id} has no character (1-{len(ID_CHARS)} supported)")


def char_tile(ch):
    """File character -> terrain ID, None for empty."""
    if ch == EMPTY:
        return None
    if ch == INVISIBLE:
        return 0
    index = ID_CHARS.find(ch)
    if index < 0:
        raise ValueError(f"unknown terrain character {ch!r}")
    return index + 1


# --- levels -----------------------------------------------------------------

def new_level(width, height):
    return {
        "version": FORMAT_VERSION,
        "width": width,
        "height": height,
        "background": list(DEFAULT_BACKGROUND),
        "terrain": [EMPTY * width for _ in range(height)],
        "decor": [],
        "entities": [],
    }


def new_entity(entity_type, x, y):
    extra, _ = ENTITY_TYPES[entity_type]
    return {"type": entity_type, "x": x, "y": y, **extra}


def problems(level):
    """Human-readable issues; the game refuses levels with tunnel problems."""
    found = []
    counts = {}
    for entity in level["entities"]:
        counts[entity["type"]] = counts.get(entity["type"], 0) + 1
    for entity_type, (_, rule) in ENTITY_TYPES.items():
        n = counts.get(entity_type, 0)
        if rule == "one" and n != 1:
            found.append(f"{entity_type}: expected 1, found {n}")
    for pair, spots in tunnel_pairs(level).items():
        if len(spots) != 2:
            found.append(f"tunnel pair {pair}: expected 2 mouths, found {len(spots)} at {spots}")
    width, height = level["width"], level["height"]
    for item in level["entities"] + level["decor"]:
        if not (0 <= item["x"] < width and 0 <= item["y"] < height):
            found.append(f"{item.get('type') or item.get('id')} at ({item['x']}, {item['y']}) "
                         f"is outside the {width}x{height} map")
    return found


def tunnel_pairs(level):
    pairs = {}
    for entity in level["entities"]:
        if entity["type"] == "tunnel":
            pairs.setdefault(entity["pair"], []).append((entity["x"], entity["y"]))
    return pairs


def check_shape(level):
    """Raise ValueError if the dict is not a usable level."""
    for key in ("width", "height", "terrain", "decor", "entities"):
        if key not in level:
            raise ValueError(f"level is missing '{key}'")
    if len(level["terrain"]) != level["height"]:
        raise ValueError(f"terrain has {len(level['terrain'])} rows, height is {level['height']}")
    for row, line in enumerate(level["terrain"]):
        if len(line) != level["width"]:
            raise ValueError(f"terrain row {row} has {len(line)} tiles, width is {level['width']}")
        for ch in line:
            char_tile(ch)
    for entity in level["entities"]:
        if entity.get("type") not in ENTITY_TYPES:
            raise ValueError(f"unknown entity type {entity.get('type')!r}")


def load_level(path):
    with open(path, encoding="utf-8") as f:
        level = json.load(f)
    level.setdefault("background", list(DEFAULT_BACKGROUND))
    level.setdefault("decor", [])
    level.setdefault("entities", [])
    check_shape(level)
    return level


def save_level(level, path):
    """Write JSON with one terrain row / decor / entity per line, so git diffs stay readable."""
    def one_line(value):
        return json.dumps(value, ensure_ascii=False)

    lines = ["{"]
    for key in ("version", "width", "height", "background"):
        lines.append(f'  "{key}": {one_line(level[key])},')
    for key in ("terrain", "decor", "entities"):
        items = level[key]
        if items:
            lines.append(f'  "{key}": [')
            lines += [f"    {one_line(item)}," for item in items[:-1]]
            lines.append(f"    {one_line(items[-1])}")
            lines.append("  ]" + ("," if key != "entities" else ""))
        else:
            lines.append(f'  "{key}": []' + ("," if key != "entities" else ""))
    lines.append("}")
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines) + "\n")
    os.replace(tmp, path)


# --- old colour masks ---------------------------------------------------------

MASK_ENTITIES = {
    (0, 255, 255): "player",
    (0, 255, 0): "health",
    (255, 1, 0): "walker",
    (255, 2, 0): "turtle",
}


def mask_to_level(surface):
    """Convert a colour-mask pygame Surface (see levels/README.md) to a level."""
    from terrain import terrain_type
    width, height = surface.get_size()
    level = new_level(width, height)
    rows = []
    for row in range(height):
        chars = []
        for col in range(width):
            colour = tuple(surface.get_at((col, row)))[:3]
            chars.append(tile_char(terrain_type(colour)))
            if colour in MASK_ENTITIES:
                level["entities"].append(new_entity(MASK_ENTITIES[colour], col, row))
            elif colour[:2] == (255, 255) and 1 <= colour[2] <= 254:
                tunnel = new_entity("tunnel", col, row)
                tunnel["pair"] = colour[2]
                level["entities"].append(tunnel)
        rows.append("".join(chars))
    level["terrain"] = rows
    return level


def load_for_game(level_num, folder="levels"):
    """levels/<n>.json if it exists, otherwise the old levels/<n>_mask.png."""
    json_path = os.path.join(folder, f"{level_num}.json")
    if os.path.exists(json_path):
        return load_level(json_path)
    import pygame
    return mask_to_level(pygame.image.load(os.path.join(folder, f"{level_num}_mask.png")))


if __name__ == "__main__":
    if len(sys.argv) == 4 and sys.argv[1] == "import":
        import pygame
        level = mask_to_level(pygame.image.load(sys.argv[2]))
        save_level(level, sys.argv[3])
        print(f"wrote {sys.argv[3]}: {level['width']}x{level['height']}, "
              f"{len(level['entities'])} entities")
        for problem in problems(level):
            print("  note:", problem)
    else:
        print("usage: python level_format.py import <mask.png> <level.json>")
