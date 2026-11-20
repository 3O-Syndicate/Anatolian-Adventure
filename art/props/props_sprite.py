"""
props_sprite.py

Placeholder enemies, decor and level objects in the hero's style (same
palette, light and outline). Sizes follow the 32px tile grid.

Code names stay neutral so the lore can change without renaming files:
  walker = the walking enemy (drawn as an angry goose)
  turtle = the shell enemy (drawn as an Anatolian tortoise)

Run:  python art/props/props_sprite.py
Writes enemies/, decor/, objects/, items/bead/ and previews in art/props/out/.
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


def goblin(step, bob, lean, sway, arms):
    """Hunched goblin, 32x44, facing right: long yellow hair, long warty nose,
    pointed ear, ragged tunic, bare feet.

    step: ((back foot dx, lift), (front foot dx, lift)); bob: body y offset;
    lean: head/torso x offset (running leans forward); sway: hair tip x offset;
    arms: (back hand dx, front hand dx) relative to the hips.
    """
    K = Kit(32, 44)
    c = K.canvas()
    skin, dark = RAMPS["goblin"], RAMPS["goblin"][0]
    ink = RAMPS["hair"][0]
    (fa, lift_a), (fb, lift_b) = step
    hip_y = 32 + bob
    hx, hy = 15 + lean, 14 + bob          # head centre
    sx, sy = 15 + lean * 0.5, 24 + bob    # shoulders
    # back arm and back leg
    c.draw(K.capsule((sx - 1, sy), (16 + arms[0], sy + 6), 1.3), "goblin", "arm_back")
    c.draw(K.capsule((13, hip_y), (12 + fa, 41 - lift_a), 1.6, 1.3), "goblin", "leg_back")
    c.draw(K.ellipse(13.5 + fa, 42.2 - lift_a, 2.6, 1.3), "goblin", "leg_back")
    # long yellow hair falling down the back, behind head and body
    c.draw(K.capsule((hx - 3, hy - 4), (6 + sway, 30 + bob), 4.8, 2.6) |
           K.capsule((hx - 1, hy - 6), (9 + sway * 0.6, 27 + bob), 3.4, 1.8),
           "blond", "hair_back")
    # ragged tunic
    c.draw(K.ellipse(sx - 0.5, sy + 3, 5.8, 6.2) | K.ellipse(14.5, hip_y - 1.5, 5.4, 3.2),
           "bark", "tunic")
    for x in (10, 13, 16, 18):  # torn hem
        c.px(RAMPS["bark"][0], (x, hip_y + 1), (x + 1, hip_y + 2))
    # front leg
    c.draw(K.capsule((16, hip_y), (16 + fb, 41 - lift_b), 1.7, 1.4), "goblin", "leg_front")
    c.draw(K.ellipse(16.5 + fb, 42.2 - lift_b, 2.7, 1.3), "goblin", "leg_front")
    # big head; the hair only covers the crown and the back of the skull
    c.draw(K.ellipse(hx, hy, 7.8, 7.2), "goblin", "head")
    c.draw(K.ellipse(hx - 2, hy - 5, 7.0, 3.6).where(K.YY < hy - 3.5) |
           K.ellipse(hx - 6, hy - 1, 2.8, 5.5), "blond", "hair_cap")
    for x in (int(hx) - 4, int(hx) - 1, int(hx) + 2):  # strand lines
        c.px(RAMPS["blond"][1], (x, int(hy) - 6), (x + 1, int(hy) - 5))
    # long pointed ear, sticking out backwards over the hair
    c.draw(K.poly([(hx - 4, hy - 1.5), (hx - 13.5, hy - 5), (hx - 4, hy + 2.5)], tilt=-0.1),
           "goblin", "ear")
    c.px(dark, (int(hx) - 9, int(hy) - 3), (int(hx) - 8, int(hy) - 2))
    # long drooping nose with warts
    nose_tip = (min(29.5, hx + 12.5), hy + 4.5)
    c.draw(K.capsule((hx + 5.5, hy), nose_tip, 2.4, 1.2), "goblin", "nose")
    for x, y in ((hx + 9, hy + 1), (hx + 1.5, hy + 3)):
        c.px(dark, (int(x), int(y)), (int(x) + 1, int(y)))
        c.px(skin[3], (int(x), int(y) - 1))
    # mean yellow eye under a slanted brow
    ex, ey = int(hx + 3), int(hy - 2)
    c.px((250, 226, 90), (ex - 1, ey), (ex, ey))
    c.px(ink, (ex + 1, ey), (ex - 1, ey - 2), (ex, ey - 2), (ex + 1, ey - 1), (ex + 2, ey - 1))
    # grin with one tooth, under the nose
    my = int(hy + 4)
    c.px(ink, *[(int(hx) - 1 + i, my + (0 if i in (0, 5) else 1)) for i in range(6)])
    c.px((240, 236, 210), (int(hx) + 1, my))
    # front arm hanging forward, clawed hand
    hand = (20 + arms[1], sy + 7)
    c.draw(K.capsule((sx + 3, sy + 1), hand, 1.5, 1.3), "goblin", "arm_front")
    c.draw(K.ellipse(hand[0] + 0.5, hand[1] + 0.5, 1.9, 1.7), "goblin", "arm_front")
    c.px(dark, (int(hand[0]) + 2, int(hand[1]) + 2), (int(hand[0]), int(hand[1]) + 2))
    return c.image()


ENEMIES = {
    "goblin/walk": [goblin(((-3, 0), (3, 0)), 0, 0, 0, (2, -3)),
                    goblin(((-1, 1), (1, 0)), -1, 0, 1, (0, -1)),
                    goblin(((3, 0), (-3, 0)), 0, 0, 0, (-3, 2)),
                    goblin(((1, 0), (-1, 1)), -1, 0, 1, (-1, 0))],
    "goblin/run": [goblin(((-5, 0), (5, 1)), 0, 1, -2, (6, -2)),
                   goblin(((-2, 2), (2, 0)), -1, 1, -3, (7, 1)),
                   goblin(((5, 1), (-5, 0)), 0, 1, -2, (6, -2)),
                   goblin(((2, 0), (-2, 2)), -1, 1, -3, (7, 1))],
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


def awning(c, K, x0, x1, top, bottom, group):
    """Red and white striped awning that widens downwards, scalloped hem."""
    mask = K.poly_mask([(x0 + 2, top), (x1 - 1, top), (x1 + 1, bottom), (x0, bottom)])
    for cx in range(x0 + 2, x1, 4):
        mask |= K.ellipse(cx, bottom, 2.1, 2.2).mask & (K.YY > bottom)
    red = ((K.XX - x0) // 4) % 2 == 0
    c.flat(mask & red, "flag", group + "_red")
    c.flat(mask & ~red, "cloth", group + "_white", base=3)


# 5x7 capitals for shop signs, one string per row ('#' = ink)
SIGN_FONT = {
    "A": [".###.", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"],
    "B": ["####.", "#...#", "#...#", "####.", "#...#", "#...#", "####."],
    "D": ["####.", "#...#", "#...#", "#...#", "#...#", "#...#", "####."],
    "E": ["#####", "#....", "#....", "####.", "#....", "#....", "#####"],
    "K": ["#...#", "#..#.", "#.#..", "##...", "#.#..", "#..#.", "#...#"],
    "L": ["#....", "#....", "#....", "#....", "#....", "#....", "#####"],
    "R": ["####.", "#...#", "#...#", "####.", "#.#..", "#..#.", "#...#"],
}


def sign_text(c, text, x, y, colour, shadow):
    """Write text in SIGN_FONT with a one-pixel drop shadow; returns the width."""
    start = x
    for ch in text:
        if ch == " ":
            x += 4
            continue
        for dy, row in enumerate(SIGN_FONT[ch]):
            for dx, cell in enumerate(row):
                if cell == "#":
                    c.px(shadow, (x + dx + 1, y + dy + 1))
        for dy, row in enumerate(SIGN_FONT[ch]):
            for dx, cell in enumerate(row):
                if cell == "#":
                    c.px(colour, (x + dx, y + dy))
        x += 6
    return x - start - 1


def text_width(text):
    return sum(4 if ch == " " else 6 for ch in text) - 1


def shop():
    """Erdal Bakkal, 96x96 (3x3 tiles): a neighbourhood grocery with a clay-tile
    roof, a big ERDAL BAKKAL sign, a striped awning, display windows full of
    goods and crates of produce out front. The door fills the bottom-centre
    tile, the doorway where the game opens the shop."""
    K = Kit(96, 96)
    c = K.canvas()
    YY = K.YY
    stone, roof_r, wood, plaster = RAMPS["stone"], RAMPS["rooftile"], RAMPS["wood"], RAMPS["plaster"]

    # chimney behind the roof
    c.flat(K.box(67, 6, 75, 24).mask, "stone", "chimney")
    c.flat(K.box(65, 3, 77, 6).mask, "stone", "chimney_cap")
    c.px(stone[1], *[(x, 13) for x in range(68, 75)], *[(71, y) for y in range(7, 13)])

    # plastered walls with stone corner blocks
    c.flat(K.box(6, 38, 89, 95).mask, "plaster", "wall")
    for i, y in enumerate(range(56, 86, 7)):
        w = 5 if i % 2 == 0 else 3
        c.flat(K.box(6, y, 6 + w, y + 5).mask, "stone", f"quoin_l{i}")
        c.flat(K.box(89 - w, y, 89, y + 5).mask, "stone", f"quoin_r{i}")

    # stone footing, laid in courses
    c.flat(K.box(4, 86, 91, 95).mask, "stone", "footing")
    c.px(stone[1], *[(x, 90) for x in range(5, 91)])
    for row, y0 in enumerate((87, 91)):
        for x in range(8 + 5 * row, 91, 10):
            c.px(stone[1], *[(x, y) for y in range(y0, y0 + 3)])

    # clay-tile roof: rows of tiles with a ridge cap, eaves past the walls
    roof = K.poly_mask([(0, 38), (14, 10), (82, 10), (96, 38)])
    c.flat(roof, "rooftile", "roof")
    for r, y in enumerate(range(15, 38, 5)):
        c.px(roof_r[0], *[(x, y) for x in range(96) if roof[y, x]])
        c.px(roof_r[3], *[(x, y + 1) for x in range(96) if y + 1 < 38 and roof[y + 1, x]])
        for x in range(3 * (r % 2), 96, 6):
            c.px(roof_r[1], *[(x, yy) for yy in range(y - 4, y) if roof[yy, x]])
    c.flat(K.box(12, 8, 83, 11).mask, "rooftile", "ridge", base=1)
    c.flat(K.box(3, 38, 92, 40).mask, "wood", "beam")

    # the sign: red letters on a white board with a blue frame
    c.flat(K.box(7, 41, 88, 53).mask, "glass", "sign_frame", base=1)
    c.flat(K.box(9, 43, 86, 51).mask, "cloth", "sign", base=3)
    text = "ERDAL BAKKAL"
    sign_text(c, text, 48 - (text_width(text) + 1) // 2, 43, RAMPS["flag"][1], RAMPS["cloth"][1])

    # striped awning across the front
    awning(c, K, 7, 88, 54, 59, "awning")

    # display windows: shelves of bottles, jars and boxes behind the glass
    goods = [RAMPS[k][2] for k in ("flag", "brass", "leaf", "glass", "beak", "cloth", "shell")]
    for side, x0 in (("l", 10), ("r", 61)):
        c.flat(K.box(x0, 63, x0 + 24, 84).mask, "wood", f"wframe_{side}")
        c.flat(K.box(x0 + 2, 65, x0 + 22, 82).mask, "glass", f"glass_{side}", base=1)
        for s, shelf_y in enumerate((70, 76, 82)):
            c.px(wood[1], *[(x, shelf_y) for x in range(x0 + 2, x0 + 23)])
            for k, x in enumerate(range(x0 + 3, x0 + 22, 3)):
                col = goods[(k * 3 + s * 2 + (x0 // 10)) % len(goods)]
                h = 2 + (k + s) % 3
                c.px(col, *[(x, shelf_y - 1 - j) for j in range(h)], (x + 1, shelf_y - 1),
                     *[(x + 1, shelf_y - 1 - j) for j in range(h - 1)])
                c.px(RAMPS["cloth"][3], (x, shelf_y - h))
        c.px(RAMPS["glass"][3], (x0 + 3, 66), (x0 + 4, 66), (x0 + 3, 67), (x0 + 18, 66))

    # glazed shop door with a little "open" plate
    c.flat(K.box(37, 62, 58, 95).mask, "wood", "door_frame")
    c.flat(K.box(40, 64, 55, 95).mask, "wood", "door", base=3)
    c.flat(K.box(42, 66, 53, 80).mask, "glass", "door_glass", base=1)
    c.px(RAMPS["glass"][3], (43, 67), (44, 67), (43, 68))
    c.flat(K.box(44, 71, 51, 74).mask, "leaf", "open_plate", base=3)
    c.px(RAMPS["leaf"][0], *[(x, 72) for x in range(45, 51, 2)], *[(x, 73) for x in range(46, 51, 2)])
    c.px(RAMPS["metal"][1], (47, 66), (48, 66), (46, 67), (49, 67), (45, 68), (50, 68))
    c.draw(K.ellipse(53, 85, 1.3, 1.3), "brass", "handle")
    c.flat(K.box(36, 94, 59, 95).mask, "stone", "step", base=3)

    # produce out front: tomatoes and oranges on the left, bread on the right
    for name, x0, fruit in (("tomato", 8, "poppy"), ("orange", 22, "beak")):
        c.flat(K.box(x0, 87, x0 + 12, 95).mask, "wood", f"crate_{name}")
        c.px(wood[1], *[(x, 91) for x in range(x0, x0 + 13)])
        pile = K.ellipse(x0 + 4.5, 84, 2.4, 2.2) | K.ellipse(x0 + 8.5, 84, 2.4, 2.2)
        for ox in (x0 + 2.5, x0 + 6.5, x0 + 10.5):
            pile = pile | K.ellipse(ox, 86, 2.4, 2.2)
        c.draw(pile.where(K.YY < 87), fruit, name, inner=False)
    c.flat(K.box(63, 86, 87, 95).mask, "wood", "bread_crate")
    c.px(wood[1], *[(x, 90) for x in range(63, 88)])
    for i, bx in enumerate((68, 75.5, 83)):
        c.draw(K.ellipse(bx, 84.5, 3.6, 2.4).where(K.YY < 86), "scute", f"bread{i}")
        c.px(RAMPS["scute"][1], (int(bx) - 1, 84), (int(bx) + 1, 84))
    return c.image()


DECOR = {
    "bush": bush(), "tree": tree(), "fence": fence(), "rock": rock(),
    "grass": grass(), "flowers": flowers(), "sign": sign(), "cloud": cloud(),
    "shop": shop(),
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


def elder(swing):
    """Placeholder NPC (code name npc): an old man with a flat cap, white beard,
    waistcoat and walking stick, a tesbih hanging from his hand. 40x64; drawn
    facing right, saved facing left, towards a player arriving from the left.
    swing: x offset of the hanging tesbih loop."""
    K = Kit(40, 64)
    c = K.canvas()
    ink = RAMPS["hair"][0]
    # legs and shoes
    for x in (17, 23):
        c.draw(K.capsule((x, 45), (x, 59), 2.6, 2.3), "pants", f"leg{x}")
        c.draw(K.ellipse(x + 1.5, 61, 3.6, 1.8).where(K.YY < 63), "shoe", f"shoe{x}")
    # brown jacket over a white shirt that shows down the front
    c.draw(K.ellipse(20, 36, 7.5, 10.5) | K.ellipse(20, 45, 6.5, 3.5), "belt", "jacket")
    c.draw(K.poly([(22.5, 27), (26.5, 27), (25.5, 38), (23.5, 38)], tilt=0.0), "shirt", "shirt")
    for y in (31, 35):  # jacket buttons
        c.px(RAMPS["brass"][2], (22, y))
    # head, white beard and moustache, flat cap with its brim forward
    c.draw(K.ellipse(22, 18, 6.2, 6.6), "skin", "head")
    c.draw(K.ellipse(24.5, 24, 5.0, 5.6) | K.ellipse(26.5, 20.8, 3.2, 1.5), "cloth", "beard")
    c.draw(K.ellipse(21, 13, 7.2, 3.6).where(K.YY < 14.5) |
           K.poly([(24, 11.5), (31.5, 13), (31, 14.6), (24, 14.6)], tilt=0.2), "metal", "cap")
    c.px(ink, (25, 17))                                   # eye
    c.px(RAMPS["cloth"][3], (24, 15), (25, 15), (26, 15))  # bushy white brow
    c.px(RAMPS["skin"][1], (28, 18), (28, 19))           # nose
    c.draw(K.ellipse(17, 18, 1.6, 2.2), "skin", "ear")
    # back arm across the belly: the tesbih hangs from that hand, golden beads
    # in a loop with a red tassel
    hx, hy = 25, 42
    c.draw(K.capsule((17, 28), (hx - 1, hy - 1), 2.3, 2.0), "belt", "arm_back")
    c.draw(K.ellipse(hx, hy, 2.0, 1.8), "skin", "hand_back")
    loop = [(hx - 1, hy + 2), (hx - 2 + swing, hy + 4), (hx - 2 + swing, hy + 6),
            (hx - 1 + swing, hy + 8), (hx + 1 + swing, hy + 8), (hx + 2 + swing, hy + 6),
            (hx + 2 + swing, hy + 4), (hx + 1, hy + 2)]
    c.px(RAMPS["brass"][3], *loop)
    c.px(RAMPS["brass"][1], loop[3], loop[6])
    c.px(RAMPS["shell"][2], (hx + swing, hy + 9), (hx + swing, hy + 10), (hx + swing - 1, hy + 10))
    # front arm on the walking stick
    c.draw(K.capsule((31, 37), (33.5, 62), 1.2), "wood", "stick")
    c.draw(K.capsule((22, 28), (30, 37), 2.4, 2.0), "belt", "arm_front")
    c.draw(K.ellipse(30.5, 37.5, 2.2, 2.0), "skin", "hand")
    return c.image().transpose(Image.FLIP_LEFT_RIGHT)


OBJECTS = {
    "checkpoint": [checkpoint(False), checkpoint(True)],
    "goal": [goal(0), goal(1)],
    "chest": [chest(False), chest(True)],
    "wallet": [wallet()],
    "npc": [elder(0), elder(1)],
}


# --------------------------------------------------------------------------
# Pickups (items/<name>/<n>.png)
# --------------------------------------------------------------------------

def bead(turn):
    """Golden tesbih bead turning on its string: turn 0-3 moves the string hole
    across the front; a short string end sticks out on both sides."""
    K = Kit(16, 16)
    c = K.canvas()
    c.draw(K.box(1, 7, 14, 8), "belt", "string")
    c.draw(K.ellipse(8, 8, 5.6, 5.4), "brass", "bead")
    hole_x = (5, 7, 9, 11)[turn]
    c.px(RAMPS["brass"][0], (hole_x, 7), (hole_x, 8))
    if turn in (0, 2):  # glint
        c.px((255, 250, 220), (6, 4), (5, 5))
    else:
        c.px((255, 250, 220), (7, 4))
    return c.image()


def sparkle(c, x, y, size, colour):
    """Four-pointed twinkle: a centre pixel with arms of the given length."""
    pts = [(x, y)]
    for i in range(1, size + 1):
        pts += [(x - i, y), (x + i, y), (x, y - i), (x, y + i)]
    c.px(colour, *pts)


def kimiz(frame):
    """Power-up: a wooden bowl (tostagan) full of frothy kimiz with a ladle, 32x32.
    Frames 0-3 move a glint across the drink and twinkle two stars beside it."""
    K = Kit(32, 32)
    c = K.canvas()
    YY = K.YY
    c.draw(K.capsule((17, 14), (26, 4), 1.1), "wood", "ladle")          # ladle handle
    c.flat(K.box(12, 27, 19, 29).mask, "wood", "foot")
    bowl = K.ellipse(15.5, 15, 13, 12).where((YY > 15) & (YY < 28))
    c.draw(bowl, "wood", "bowl")
    for x in range(6, 26, 4):                                              # carved band
        c.px(RAMPS["brass"][2], (x, 20), (x + 1, 21), (x + 2, 20))
    c.flat(K.ellipse(15.5, 15, 13, 4.2).mask, "wood", "rim", base=3)
    milk = K.ellipse(15.5, 15.3, 11, 3)
    c.flat(milk.mask, "plaster", "kimiz", base=3)
    c.px(RAMPS["plaster"][2], *[(x, 17) for x in range(9, 23)])
    for x, y in ((8, 15), (10, 14), (12, 16), (21, 14), (23, 15), (19, 16)):  # froth
        c.px((255, 255, 255), (x, y))
    c.draw(K.capsule((17, 14), (19.5, 10.5), 1.1), "wood", "ladle_in")
    gx = (9, 13, 17, 21)[frame]
    c.px((255, 255, 255), (gx, 15), (gx + 1, 15), (gx + 1, 14))
    image = c.image()
    # twinkles outside the outline, so they read against the sky
    t = Kit(32, 32).canvas()
    big, small = (3, 1) if frame % 2 == 0 else (2, 2)
    sparkle(t, 4, 6, big, (255, 236, 150))
    sparkle(t, 29, 10, small, (255, 255, 255))
    stars = t.image(outline=None)
    stars.alpha_composite(image)
    return stars


ITEMS = {"bead": [bead(t) for t in range(4)], "kimiz": [kimiz(f) for f in range(4)]}


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
    for name, frames in {**OBJECTS, **ITEMS}.items():
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
    for name, frames in ITEMS.items():
        save_frames(ROOT / "items" / name, frames)
    for name, img in TILES.items():
        img.save(ROOT / "tiles" / f"{name}.png")
    preview().save(OUT / "props_preview.png")
    print("enemies:", sum(len(f) for f in ENEMIES.values()), "frames; decor:", len(DECOR),
          "; objects:", sum(len(f) for f in OBJECTS.values()), "frames; items:",
          sum(len(f) for f in ITEMS.values()), "frames")
