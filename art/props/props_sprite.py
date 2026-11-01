"""
props_sprite.py

Placeholder enemies, decor and level objects in the hero's style (same
palette, light and outline). Sizes follow the 32px tile grid.

Code names stay neutral so the lore can change without renaming files:
  walker = the walking enemy (drawn as an angry goose)
  turtle = the shell enemy (drawn as an Anatolian tortoise)

Run:  python art/props/props_sprite.py
Writes enemies/, decor/, objects/ and previews in art/props/out/.
"""
import math
import random
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pixelkit import Kit, RAMPS, zoom  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).parent / "out"


# --------------------------------------------------------------------------
# Enemies (32x32 walking frames, 32x16 shell frames, all facing right)
# --------------------------------------------------------------------------

def goose(step, bob, head):
    """step: leg offsets (back, front); bob: body y; head: neck/head x offset."""
    K = Kit(32, 32)
    c = K.canvas()
    (la, lift_a), (lb, lift_b) = step
    for x, dx, lift in ((11, la, lift_a), (16, lb, lift_b)):
        foot = (x + dx, 29 - lift)
        c.draw(K.capsule((x, 25 + bob), foot, 1.2, 1.0), "beak", f"leg{x}")
        c.draw(K.ellipse(foot[0] + 1.3, foot[1] + 0.8, 2.3, 1.1).where(K.YY < 31),
               "beak", f"leg{x}")
    c.draw(K.ellipse(5.5, 17 + bob, 3.4, 2.2, -0.5), "feather", "body")
    c.draw(K.ellipse(13, 20 + bob, 9.5, 6.2) | K.ellipse(19, 20 + bob, 5, 5.5),
           "feather", "body")
    c.draw(K.ellipse(11.5, 19 + bob, 6.5, 3.6, -0.15), "feather", "wing")
    hx, hy = 21.5 + head, 8 + bob
    c.draw(K.capsule((19, 17 + bob), (hx, hy), 2.9, 2.3) |
           K.ellipse(hx + 1, hy - 1.5, 3.6, 3.1), "feather", "neck")
    bx, by = hx + 3.5, hy - 2.5
    c.draw(K.poly([(bx, by), (bx + 5.5, by + 1.5), (bx + 4.5, by + 3.1), (bx, by + 3.5)]),
           "beak", "beak")
    ex, ey = int(hx + 1.5), int(hy - 2)
    c.px(RAMPS["hair"][0], (ex - 1, ey), (ex - 1, ey + 1))
    c.px(RAMPS["hair"][0], (ex - 2, ey - 2), (ex - 1, ey - 2), (ex, ey - 1))  # angry brow
    return c.image()


def tortoise(legs, head):
    """legs: x offsets (back far, front far, back near, front near); head: (dx, dy)."""
    K = Kit(32, 32)
    c = K.canvas()
    bf, ff, bn, fn = legs
    hx, hy = head
    c.draw(K.capsule((9, 25), (10 + bf, 30), 2.3), "scales", "leg_far")
    c.draw(K.capsule((20, 25), (21 + ff, 30), 2.3), "scales", "leg_far")
    c.draw(K.poly([(1.5, 25), (4.5, 22.5), (5, 25.5)]), "scales", "tail")
    c.draw(K.capsule((21, 22), (25.5 + hx, 17 + hy), 2.7, 2.3) |
           K.ellipse(27.5 + hx, 16 + hy, 3.8, 3.1), "scales", "head")
    ex, ey = int(28 + hx), int(15 + hy)
    c.px(RAMPS["hair"][0], (ex, ey), (ex, ey + 1))
    c.px(RAMPS["hair"][1], (ex - 1, ey - 1), (ex, ey - 2), (ex + 1, ey - 2))
    shell_dome(c, K, 14, 21, 12.5, 11, 25.5, 0)
    c.draw(K.capsule((10, 25), (9 + bn, 30), 2.4), "scales", "leg_near")
    c.draw(K.capsule((21, 25), (22 + fn, 30), 2.4), "scales", "leg_near2")
    for x in (9 + bn, 22 + fn):  # claws
        c.px(RAMPS["scute"][3], (int(x) + 1, 31 - 1), (int(x) + 2, 31 - 1))
    return c.image()


def shell_dome(c, K, cx, cy, rx, ry, flat_y, scroll):
    """Domed carapace with plate pattern; scroll slides the plates (spinning)."""
    dome = K.ellipse(cx, cy, rx, ry).where(K.YY < flat_y)
    c.draw(dome, "carapace", "shell")
    top = cy - ry
    plates = [(-5, 0.55, 3.0), (0.5, 0.35, 3.2), (6, 0.55, 3.0),
              (-8, 0.85, 2.6), (-2.5, 0.85, 2.6), (3, 0.85, 2.6), (8.5, 0.85, 2.4)]
    span = rx * 2 + 4
    for px_, fy, r in plates:
        x = cx + ((px_ + scroll + span / 2) % span) - span / 2
        y = top + (flat_y - top) * fy
        plate = (K.ellipse(x, y, r, r * 0.85) & dome)
        c.draw(plate, "scute", "plate%d" % px_)
    rim = K.ellipse(cx, flat_y - 1.2, rx + 0.6, 1.8) & K.ellipse(cx, cy, rx + 1, ry + 1)
    c.draw(rim, "scute", "rim", inner=False)


def turtle_shell(scroll=0, streaks=False):
    K = Kit(32, 16)
    c = K.canvas()
    shell_dome(c, K, 16, 14, 13.5, 11.5, 14.5, scroll)
    c.px(RAMPS["hair"][0], (28, 12), (28, 13), (27, 13))  # head opening
    img = c.image()
    if streaks:
        d = ImageDraw.Draw(img)
        for y, x0 in ((6, 0), (10, 1)):
            d.line([(x0, y), (x0 + 1, y)], fill=(236, 244, 252, 200))
    return img


ENEMIES = {
    "walker/walk": [goose(((-2, 0), (2, 0)), 0, 0),
                    goose(((0, 2), (0, 0)), -1, 1),
                    goose(((2, 0), (-2, 0)), 0, 0),
                    goose(((0, 0), (0, 2)), -1, 1)],
    "turtle/walk": [tortoise((1, -1, -1, 1), (0, 0)),
                    tortoise((0, 0, 0, 0), (0, 1)),
                    tortoise((-1, 1, 1, -1), (0, 0)),
                    tortoise((0, 0, 0, 0), (0, 1))],
    "turtle/shell": [turtle_shell()],
    "turtle/spin": [turtle_shell(s, streaks=True) for s in (0, 3, 6, 9)],
}


# --------------------------------------------------------------------------
# Decor (no collision; drawn behind or in front of the player)
# --------------------------------------------------------------------------

def speckle(c, K, mask, colour, count, seed):
    """Scatter single highlight pixels over the lit part of a mask."""
    rng = random.Random(seed)
    ys, xs = mask.nonzero()
    lit = [(x, y) for x, y in zip(xs, ys) if tuple(c.rgb[y, x]) in
           (RAMPS["leaf"][2], RAMPS["leaf"][3])]
    for x, y in rng.sample(lit, min(count, len(lit))):
        c.px(colour, (int(x), int(y)))


def bush():
    K = Kit(64, 32)
    c = K.canvas()
    leaves = (K.ellipse(13, 22, 11, 9.5) | K.ellipse(31, 17, 14, 13) |
              K.ellipse(50, 21, 12, 10.5) | K.ellipse(24, 25, 10, 7) |
              K.ellipse(41, 25, 10, 7)).where(K.YY < 31)
    c.draw(leaves, "leaf", "bush")
    speckle(c, K, leaves.mask, RAMPS["leaf"][3], 26, 1)
    for x, y in ((20, 14), (37, 11), (46, 19), (12, 20)):
        c.px(RAMPS["poppy"][2], (x, y))
    return c.image()


def tree():
    K = Kit(64, 96)
    c = K.canvas()
    c.draw(K.capsule((32, 92), (31, 56), 5.5, 4.2) | K.ellipse(26, 92, 4, 2.5) |
           K.ellipse(38, 92, 4, 2.5), "bark", "trunk")
    c.draw(K.capsule((31, 66), (22, 54), 2.2) | K.capsule((32, 62), (42, 52), 2.0),
           "bark", "branch")
    for x in (29, 33):
        for y in range(70, 90, 2):
            c.px(RAMPS["bark"][0], (x, y + (x % 3)))
    canopy = (K.ellipse(32, 30, 20, 17) | K.ellipse(17, 40, 13, 11) |
              K.ellipse(47, 40, 13, 11) | K.ellipse(25, 52, 12, 8) |
              K.ellipse(40, 52, 12, 8) | K.ellipse(32, 18, 13, 11))
    c.draw(canopy, "leaf", "canopy")
    speckle(c, K, canopy.mask, RAMPS["leaf"][3], 60, 2)
    return c.image()


def fence():
    """Tiles horizontally: rails run to both edges."""
    K = Kit(32, 32)
    c = K.canvas()
    c.flat(K.box(0, 13, 31, 15).mask, "wood", "rail")
    c.flat(K.box(0, 22, 31, 24).mask, "wood", "rail")
    for x in (5, 21):
        post = K.poly_mask([(x, 11), (x + 2.5, 7.5), (x + 5, 11), (x + 5, 32), (x, 32)])
        c.flat(post, "wood", f"post{x}")
        c.px(RAMPS["wood"][1], *[(x + 3, y) for y in range(12, 31, 3)])
    return c.image()


def rock():
    K = Kit(32, 32)
    c = K.canvas()
    c.draw(K.ellipse(14, 25, 12, 7.5).where(K.YY < 31), "stone", "rock")
    c.draw(K.ellipse(25, 27.5, 6.5, 4.5).where(K.YY < 31), "stone", "pebble")
    c.px(RAMPS["stone"][0], (12, 21), (13, 22), (13, 23), (14, 24))
    return c.image()


def grass_blades(c, K, seed, heights):
    rng = random.Random(seed)
    for x in range(1, 31, 3):
        h = rng.randint(*heights)
        lean = rng.uniform(-2.5, 2.5)
        blade = K.poly_mask([(x - 1.2, 31.9), (x + lean, 31.9 - h), (x + 1.4, 31.9)])
        c.flat(blade, "leaf", "grass", base=2)


def grass():
    K = Kit(32, 32)
    c = K.canvas()
    grass_blades(c, K, 3, (5, 11))
    return c.image()


def flowers():
    """Red poppies (gelincik) in a grass tuft."""
    K = Kit(32, 32)
    c = K.canvas()
    grass_blades(c, K, 4, (3, 7))
    for x, top in ((8, 14), (17, 9), (25, 16)):
        c.draw(K.capsule((x, 31), (x + 0.5, top + 2), 0.7), "leaf", f"stem{x}", inner=False)
        c.draw(K.ellipse(x + 0.5, top, 2.6, 2.2), "poppy", f"poppy{x}")
        c.px(RAMPS["hair"][0], (int(x + 0.5), int(top)))
    return c.image()


def sign():
    K = Kit(32, 32)
    c = K.canvas()
    c.flat(K.box(14, 16, 17, 31).mask, "wood", "post")
    c.flat(K.box(4, 6, 27, 17).mask, "wood", "board")
    dark = RAMPS["wood"][0]
    c.px(dark, *[(x, 11) for x in range(9, 21)], *[(x, 12) for x in range(9, 21)],
         (19, 9), (20, 10), (21, 11), (21, 12), (20, 13), (19, 14))
    return c.image()


def cloud():
    K = Kit(96, 48)
    c = K.canvas()
    puff = (K.ellipse(30, 30, 18, 13) | K.ellipse(50, 22, 20, 17) |
            K.ellipse(70, 30, 17, 12) | K.ellipse(46, 34, 30, 9)).where(K.YY < 42)
    c.draw(puff, "cloud", "cloud", thresh=(0.05, 0.30, 0.70))
    return c.image(outline=(150, 182, 224))


DECOR = {
    "bush": bush(), "tree": tree(), "fence": fence(), "rock": rock(),
    "grass": grass(), "flowers": flowers(), "sign": sign(), "cloud": cloud(),
}


# --------------------------------------------------------------------------
# Level objects
# --------------------------------------------------------------------------

def checkpoint(active):
    K = Kit(32, 64)
    c = K.canvas()
    c.flat(K.box(3, 58, 13, 62).mask, "stone", "base")
    c.draw(K.capsule((8, 58), (8, 9), 1.6), "metal", "pole")
    c.draw(K.ellipse(8, 7, 2.6, 2.6), "brass", "ball")
    if active:
        cloth = K.poly([(9.5, 10), (28, 13), (24.5, 16.5), (28, 21), (9.5, 23)])
        c.draw(cloth, "flag", "flag")
    else:
        cloth = K.poly([(9.5, 10), (15, 12), (14, 18), (16, 26), (9.5, 26)])
        c.draw(cloth, "cloth", "flag")
    return c.image()


def goal(frame):
    K = Kit(64, 128)
    c = K.canvas()
    c.flat(K.box(2, 118, 18, 126).mask, "stone", "base")
    c.flat(K.box(5, 113, 15, 117).mask, "stone", "base2")
    c.draw(K.capsule((10, 113), (10, 11), 2.2), "metal", "pole")
    c.draw(K.ellipse(10, 8, 3.6, 3.6), "brass", "ball")
    if frame == 0:
        pts = [(12.5, 12), (56, 16), (52, 26), (58, 36), (12.5, 40)]
    else:
        pts = [(12.5, 12), (54, 18), (59, 27), (53, 37), (12.5, 40)]
    c.draw(K.poly(pts), "flag", "flag")
    for x in (24, 38):  # cloth folds
        for y in range(16, 39):
            if c.alpha[y, x] and c.group[y, x] == c.group_ids["flag"]:
                c.px(RAMPS["flag"][1], (x + (y // 6 + frame) % 2 + 3 * frame, y))
    return c.image()


def chest(opened):
    """Treasure chest: wooden box, iron bands, brass lock."""
    K = Kit(32, 32)
    c = K.canvas()
    c.flat(K.box(4, 18, 27, 29).mask, "wood", "body")
    if opened:
        c.flat(K.box(5, 7, 26, 12).mask, "wood", "lid")
        c.flat(K.box(6, 13, 25, 17).mask, "shell", "inside", base=0)
    else:
        lid = K.ellipse(15.5, 18, 12, 7).where(K.YY < 18)
        c.draw(lid, "wood", "lid")
    for x in (8, 23):
        c.flat(K.box(x, 12 if not opened else 7, x + 1, 29).mask & c.alpha, "metal", f"band{x}")
    if not opened:
        c.draw(K.ellipse(15.5, 19.5, 2.4, 2.6), "brass", "lock")
        c.px(RAMPS["hair"][0], (15, 20), (15, 21))
    return c.image()


def wallet():
    """Leather wallet with a banknote sticking out."""
    K = Kit(32, 32)
    c = K.canvas()
    c.flat(K.box(12, 15, 21, 20).mask, "leaf", "note", base=3)
    c.px(RAMPS["leaf"][1], (15, 17), (16, 17), (17, 17))
    c.draw(K.ellipse(15.5, 23.5, 8.5, 6).where((K.YY > 18.5) & (K.YY < 29)), "belt", "wallet")
    c.px(RAMPS["belt"][0], *[(x, 22) for x in range(9, 23)])
    c.draw(K.ellipse(15.5, 25, 1.4, 1.4), "brass", "clasp")
    return c.image()


OBJECTS = {
    "checkpoint": [checkpoint(False), checkpoint(True)],
    "goal": [goal(0), goal(1)],
    "chest": [chest(False), chest(True)],
    "wallet": [wallet()],
}


# --------------------------------------------------------------------------
# Terrain tiles (tiles/<name>.png, 32x32, repeat without seams)
# --------------------------------------------------------------------------

def cloud_tile():
    """Cloud platform: puffy top that repeats every 32 px, flat shaded underside."""
    K = Kit(32, 32)
    c = K.canvas()
    body = K.box(0, 6, 31, 25)
    for cx in (0, 16, 32):
        body = body | K.ellipse(cx, 8, 9, 7.5)
    body = body | K.ellipse(8, 25, 9, 4.5) | K.ellipse(24, 25, 9, 4.5)
    c.draw(body.where((K.YY > 1) & (K.YY < 30)), "cloud", "cloud", thresh=(0.05, 0.30, 0.70))
    return c.image(outline=(150, 182, 224))


# shades of the old flat placeholder colour (175, 75, 50); the darkest is the mortar
BRICK = [(86, 36, 30), (138, 58, 42), (175, 75, 50), (204, 112, 80)]


def brick_tile():
    """Brick wall in running bond: four courses, joints shifted every other course.

    Drawn pixel by pixel so it repeats without seams in both directions.
    """
    img = Image.new("RGBA", (32, 32), BRICK[0])
    px = img.load()
    for course in range(4):
        top = course * 8
        for start in ((0, 16) if course % 2 == 0 else (8, 24)):
            for i in range(15):
                x = (start + 1 + i) % 32
                for y in range(top + 1, top + 8):
                    if y == top + 1 or i == 0:
                        px[x, y] = BRICK[3]
                    elif y == top + 7 or i == 14:
                        px[x, y] = BRICK[1]
                    else:
                        px[x, y] = BRICK[2]
    for x, y in ((5, 4), (21, 3), (12, 13), (28, 12), (4, 21), (19, 20), (10, 29), (26, 28)):
        px[x, y] = BRICK[1]
    return img


# file name in tiles/ -> image
TILES = {"4": cloud_tile(), "brick": brick_tile()}


# --------------------------------------------------------------------------
# Export
# --------------------------------------------------------------------------

def save_frames(folder, frames):
    folder.mkdir(parents=True, exist_ok=True)
    for old in folder.glob("*.png"):
        old.unlink()
    for i, img in enumerate(frames):
        img.save(folder / f"{i}.png")


def preview():
    """All props on a sky background with a ground strip, 3x."""
    font = ImageFont.truetype(str(ROOT / "font" / "PublicPixel.ttf"), 8)
    items = []
    for name, frames in ENEMIES.items():
        items += [(f"{name}/{i}", f) for i, f in enumerate(frames)]
    items += [(name, img) for name, img in DECOR.items()]
    for name, frames in OBJECTS.items():
        items += [(f"{name}/{i}", f) for i, f in enumerate(frames)]
    pad, row_h, width = 10, 150, 760
    x, y, rows = pad, pad, [[]]
    for label, img in items:
        if x + img.width + pad > width:
            rows.append([])
            x = pad
        rows[-1].append((label, img, x))
        x += max(img.width, 120) + pad
    sheet = Image.new("RGBA", (width, len(rows) * row_h), (110, 175, 230, 255))
    d = ImageDraw.Draw(sheet)
    for r, row in enumerate(rows):
        base = r * row_h + row_h - 18
        d.rectangle([0, base, width, base + 4], fill=(92, 140, 52, 255))
        for label, img, x in row:
            sheet.alpha_composite(img, (x, base - img.height))
            d.text((x, base + 7), label, font=font, fill=(20, 30, 50, 255))
    return zoom(sheet, 2)


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    for name, frames in ENEMIES.items():
        save_frames(ROOT / "enemies" / name, frames)
    decor_dir = ROOT / "decor"
    decor_dir.mkdir(exist_ok=True)
    for name, img in DECOR.items():
        img.save(decor_dir / f"{name}.png")
    for name, frames in OBJECTS.items():
        save_frames(ROOT / "objects" / name, frames)
    for name, img in TILES.items():
        img.save(ROOT / "tiles" / f"{name}.png")
    preview().save(OUT / "props_preview.png")
    print("enemies:", sum(len(f) for f in ENEMIES.values()), "frames; decor:", len(DECOR),
          "; objects:", sum(len(f) for f in OBJECTS.values()), "frames")
