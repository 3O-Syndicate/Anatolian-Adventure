"""
hero_sprite.py

Generates the bald hero's pixel art and animation frames (facing right) at
the game's native pixel density: TILESIZE is 32 and tiles are 32x32 art, so
one art pixel is one screen pixel. The hero is a small rig of shaded body
parts; each animation frame is a Pose, and arms follow the shotgun so the
hands always stay on it.

Run:  python art/hero/hero_sprite.py
Writes player/hero/<anim>/<n>.png, player/hero/anim.json,
effects/muzzle_flash/<n>.png and previews in art/hero/out/.
"""
import json
import math
import sys
from dataclasses import dataclass, replace
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pixelkit import Kit, RAMPS, neighbours, zoom  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).parent / "out"
W, H = 64, 64

K = Kit(W, H)
XX, YY = K.XX, K.YY
ellipse, capsule, box, poly_mask = K.ellipse, K.capsule, K.box, K.poly_mask
Canvas = K.canvas


# --------------------------------------------------------------------------
# Rig
# --------------------------------------------------------------------------

@dataclass
class Pose:
    body: tuple = (0, 0)          # torso, head, arms and gun
    hips: tuple = (0, 0)          # pants and hip joints
    head: tuple = (0, 0)          # extra head offset on top of body
    belly: tuple = (0.0, 0.0)     # belly radius change (rx, ry)
    face: str = "normal"          # normal, squint, shock
    near_foot: tuple = (1.0, 57.0, 0.0)   # ankle x offset from hip, ankle y, toe tilt
    far_foot: tuple = (0.0, 57.0, 0.0)
    gun: tuple = (0, 0)           # gun offset on top of body
    gun_angle: float = 0.0        # degrees, positive = muzzle down
    gun_open: float = 0.0         # break-open angle of the barrels, degrees
    near_hand: tuple = None       # free near hand position (reload), else on the grip
    far_hand: tuple = None        # free far hand position, else on the forend
    far_grip: tuple = None        # gun-local point the far hand holds, default forend
    show_gun: bool = True
    shell: str = None             # None, "hand" or "loading"


NEAR_HIP = (37.5, 48.0)
FAR_HIP = (26.0, 48.0)
THIGH, SHIN = 5.3, 5.1
NEAR_SHOULDER = (23.0, 25.0)
FAR_SHOULDER = (40.0, 26.0)
GUN_ORIGIN = (30.0, 39.0)
HINGE = (4.0, 2.0)                # barrel hinge, gun-local


def ik(root, target, l1, l2, prefer):
    """Two-bone joint position; prefer(a, b) picks one of the two solutions."""
    rx, ry = root
    tx, ty = target
    dx, dy = tx - rx, ty - ry
    d = math.hypot(dx, dy)
    d_clamped = min(max(d, abs(l1 - l2) + 0.5, 1.0), l1 + l2 - 0.01)
    ux, uy = (dx / d, dy / d) if d > 1e-6 else (0.0, 1.0)
    a = (l1 * l1 - l2 * l2 + d_clamped * d_clamped) / (2 * d_clamped)
    h = math.sqrt(max(l1 * l1 - a * a, 0.0))
    px, py = rx + a * ux, ry + a * uy
    j1 = (px - h * uy, py + h * ux)
    j2 = (px + h * uy, py - h * ux)
    return prefer(j1, j2)


def rot(p, deg, about=(0.0, 0.0)):
    a = math.radians(deg)
    x, y = p[0] - about[0], p[1] - about[1]
    return (about[0] + x * math.cos(a) - y * math.sin(a),
            about[1] + x * math.sin(a) + y * math.cos(a))


class Gun:
    """Double-barrelled 'cifte' shotgun in gun-local coordinates."""

    STOCK = [(-16, -1), (-2, -1), (-1, 0), (-1, 3), (-5, 3), (-16, 6)]
    RECEIVER = [(-2, -2), (4, -2), (4, 3), (-2, 3)]
    BARREL = [(3, -2), (30, -2), (30, 1), (3, 1)]
    FOREND = [(5, 1), (18, 1), (18, 3), (5, 3)]
    GRIP = (-2.0, 3.0)
    FOREND_HOLD = (15.5, 2.5)
    MUZZLE = (30.0, -0.5)
    BREECH = (3.5, -1.0)

    def __init__(self, pose):
        bx, by = pose.body
        gx, gy = pose.gun
        self.origin = (GUN_ORIGIN[0] + bx + gx, GUN_ORIGIN[1] + by + gy)
        self.angle = pose.gun_angle
        self.open = pose.gun_open
        self.far_grip = pose.far_grip or self.FOREND_HOLD

    def world(self, p, hinged=False):
        if hinged:
            p = rot(p, self.open, HINGE)
        x, y = rot(p, self.angle)
        return (self.origin[0] + x, self.origin[1] + y)

    def mask(self, points, hinged=False):
        return poly_mask([self.world(p, hinged) for p in points])

    def draw(self, c):
        c.flat(self.mask(self.STOCK), "wood", "gun")
        butt = self.world((-15.5, 2.5))
        butt_px = [(int(butt[0] + dx), int(butt[1] + dy)) for dx, dy in
                   [(0, -3), (0, -2), (0, -1), (0, 0), (0, 1), (0, 2), (0, 3)]]
        c.px(RAMPS["wood"][0], *[p for p in butt_px
                                  if 0 <= p[0] < W and 0 <= p[1] < H and c.alpha[p[1], p[0]]])
        c.flat(self.mask(self.BARREL, True), "metal", "gun", base=1)
        c.flat(self.mask(self.FOREND, True), "wood", "gun")
        c.flat(self.mask(self.RECEIVER), "metal", "gun", base=2)
        for p in [(0.5, 3.5), (0.5, 4.5), (1.5, 4.5), (2.5, 3.5)]:
            x, y = self.world(p)
            c.px(RAMPS["metal"][0], (int(x), int(y)))

    def point(self, name):
        return {
            "grip": self.world(self.GRIP),
            "forend": self.world(self.far_grip, True),
            "muzzle": self.world(self.MUZZLE, True),
            "breech": self.world(self.BREECH, True),
        }[name]


def draw_head(c, pose):
    hx = pose.body[0] + pose.head[0]
    hy = pose.body[1] + pose.head[1]

    def P(x, y):
        return (x + hx, y + hy)

    skull = ellipse(33 + hx, 13 + hy, 9.5, 9.5)
    jowls = ellipse(35 + hx, 18 + hy, 8.5, 5.5)
    c.draw(skull | jowls, "skin", "head")
    c.draw(ellipse(29 + hx, 14.5 + hy, 2.4, 3.4), "skin", "ear")
    c.px(RAMPS["skin"][0], P(29, 14), P(29, 15))
    c.draw(ellipse(43 + hx, 14.5 + hy, 2.7, 2.8), "skin", "head")
    c.px(RAMPS["skin"][0], P(42, 16))
    c.px((255, 236, 212), P(29, 6), P(30, 6), P(28, 7))  # bald shine

    dark, brow = RAMPS["hair"][0], RAMPS["hair"][1]
    if pose.face == "squint":
        c.px(dark, P(37, 11), P(38, 11), P(39, 11))
        c.px(brow, *[P(x, 9) for x in range(37, 41)], P(36, 10))
    elif pose.face == "shock":
        c.px((250, 250, 250), P(37, 9), P(38, 9), P(37, 10), P(38, 10), P(37, 11),
             P(38, 11), P(39, 9))
        c.px(dark, P(39, 10), P(39, 11))
        c.px(brow, *[P(x, 7) for x in range(37, 41)], P(36, 8))
    else:
        c.px((250, 250, 250), P(38, 10), P(38, 11))
        c.px(dark, P(39, 10), P(39, 11), P(38, 12), P(39, 12))
        c.px(brow, *[P(x, 8) for x in range(37, 41)], P(36, 9))

    stache = (ellipse(40.6 + hx, 18.5 + hy, 5.0, 2.1)
              | ellipse(36.2 + hx, 20.0 + hy, 1.7, 1.8)
              | ellipse(44.6 + hx, 19.0 + hy, 1.6, 1.7))
    c.draw(stache, "hair", "stache", thresh=(0.30, 0.62, 0.90))

    if pose.face == "shock":
        c.px((60, 18, 22), P(39, 21), P(40, 21), P(41, 21), P(40, 22), P(41, 22))
        c.px(RAMPS["skin"][0], P(39, 22), P(42, 22), P(40, 23), P(41, 23))
    else:
        c.px((128, 44, 48), P(39, 21), P(40, 21), P(41, 21), P(42, 21))
        c.px((240, 236, 228), P(40, 21), P(41, 21))
        c.px(RAMPS["skin"][0], P(38, 20), P(43, 21), P(39, 22), P(40, 22), P(41, 22),
             P(42, 22))


def draw_body(c, pose):
    """Torso in a ribbed white tank top over a big belly."""
    bx, by = pose.body
    erx, ery = pose.belly
    torso = ellipse(31 + bx, 28 + by, 13, 7) | ellipse(33 + bx, 37 + by, 14 + erx, 11 + ery)
    skin_bits = ellipse(37 + bx, 22 + by, 6, 6) | ellipse(21 + bx, 27 + by, 4.5, 7)
    c.draw(torso - skin_bits, "shirt", "shirt")
    c.draw(torso & skin_bits, "skin", "chest")
    hem = (torso - skin_bits).mask & neighbours((torso & skin_bits).mask)
    c.rgb[hem] = RAMPS["shirt"][1]
    shirt = (torso - skin_bits).mask & ~hem
    base = np.all(c.rgb == RAMPS["shirt"][2], axis=-1)
    rib = shirt & base & ((XX.astype(int) - bx) % 3 == 0)
    c.rgb[rib] = (224, 227, 236)


def leg(c, hip, foot, group, shoe_rx):
    """Thigh, shin and shoe; the knee bends forward."""
    dx, ankle_y, toe = foot
    ankle = (hip[0] + dx, ankle_y)
    knee = ik(hip, ankle, THIGH, SHIN, lambda a, b: a if a[0] > b[0] else b)
    c.draw(capsule(hip, knee, 4.7, 4.5) | capsule(knee, ankle, 4.5, 4.1), "pants", group)
    sx, sy = rot((1.0, 3.0), math.degrees(toe))
    shoe = ellipse(ankle[0] + sx, ankle[1] + sy, shoe_rx, 3.0, toe).where(YY < 63)
    c.draw(shoe, "shoe", group + "_shoe")


def draw_legs_and_hips(c, pose):
    hx, hy = pose.hips
    near_hip = (NEAR_HIP[0] + hx, NEAR_HIP[1] + hy)
    far_hip = (FAR_HIP[0] + hx, FAR_HIP[1] + hy)
    leg(c, far_hip, pose.far_foot, "leg_far", 5.6)
    hips = ellipse(32 + hx, 47 + hy, 12, 5) | box(21 + hx, 45 + hy, 43 + hx, 50 + hy)
    c.draw(hips, "pants", "hips")
    c.draw(hips.where((YY >= 43 + hy) & (YY < 45 + hy)), "belt", "belt", inner=False)
    leg(c, near_hip, pose.near_foot, "hips", 6.4)


def draw_shell(c, at, angle=0.0):
    x, y = at
    a = math.radians(angle)
    tip = (x + 1.8 * math.cos(a), y + 1.8 * math.sin(a))
    base = (x - 1.8 * math.cos(a), y - 1.8 * math.sin(a))
    c.draw(capsule(base, tip, 1.4), "shell", "shell", inner=False)
    c.draw(ellipse(base[0], base[1], 1.3, 1.6, a), "brass", "shell", inner=False)


def render(pose):
    c = Canvas()
    bx, by = pose.body
    gun = Gun(pose)
    far_shoulder = (FAR_SHOULDER[0] + bx, FAR_SHOULDER[1] + by)
    near_shoulder = (NEAR_SHOULDER[0] + bx, NEAR_SHOULDER[1] + by)
    far_hand = pose.far_hand or gun.point("forend")
    far_elbow = ik(far_shoulder, far_hand, 10.0, 8.5, lambda a, b: a if a[0] > b[0] else b)
    near_hand = pose.near_hand or gun.point("grip")
    near_elbow = ik(near_shoulder, near_hand, 10.2, 9.9, lambda a, b: a if a[0] < b[0] else b)

    c.draw(capsule(far_shoulder, far_elbow, 4.2, 3.8), "skin", "arm_far")
    draw_legs_and_hips(c, pose)
    draw_body(c, pose)
    draw_head(c, pose)
    if pose.show_gun:
        gun.draw(c)
    if pose.shell == "loading":
        breech = gun.point("breech")
        draw_shell(c, (breech[0] - 1, breech[1] - 1), -60)
    c.draw(capsule(far_elbow, far_hand, 3.8, 3.4), "skin", "arm_far2")
    c.draw(ellipse(far_hand[0], far_hand[1], 3.2, 2.8), "skin", "hand_far")
    c.draw(capsule(near_shoulder, near_elbow, 5.0, 4.4), "skin", "arm_near")
    c.draw(capsule(near_elbow, near_hand, 4.4, 3.9), "skin", "arm_near")
    c.draw(ellipse(near_hand[0], near_hand[1], 3.6, 3.4), "skin", "hand_near")
    if pose.shell == "hand":
        draw_shell(c, (near_hand[0] + 1, near_hand[1] - 3), -30)
    muzzle = gun.point("muzzle")
    return c.image(), (round(muzzle[0], 1), round(muzzle[1], 1))


# --------------------------------------------------------------------------
# Animations
# --------------------------------------------------------------------------

STAND = Pose()
CROUCH = Pose(body=(0, 11), hips=(0, 8), belly=(1.0, -0.5))


def run_frames():
    # near-leg cycle: (ankle x offset from hip, ankle y, toe tilt)
    cycle = [(4.5, 57, 0.0), (1.5, 57, 0.0), (-2.5, 57, 0.3),
             (-4.5, 55, 0.6), (-0.5, 53, 0.3), (3.5, 55, -0.2)]
    bob = [0, 1, -1, 0, 1, -1]
    frames = []
    for i in range(6):
        near = cycle[i]
        far = cycle[(i + 3) % 6]
        frames.append(Pose(body=(1, bob[i]), hips=(0, bob[i]), near_foot=near,
                           far_foot=(far[0] - 1, far[1], far[2]),
                           gun_angle=[0, 2, -1, 0, 2, -1][i]))
    return frames


def shoot_frames(base):
    return [replace(base, body=(base.body[0] - 1, base.body[1]), gun=(-3, 0),
                    gun_angle=-7, face="squint"),
            replace(base, gun=(-1, 0), gun_angle=-3, face="squint")]


def reload_frames():
    r0 = Pose(gun=(0, 1), gun_angle=10)
    r1 = Pose(gun=(0, 1), gun_angle=-4, gun_open=30, far_grip=(8.0, 2.5))
    breech = Gun(r1).point("breech")
    r2 = replace(r1, near_hand=(breech[0] - 3, breech[1] - 6), shell="hand")
    r3 = replace(r1, near_hand=(breech[0] - 2, breech[1] - 3), shell="loading")
    r4 = Pose(gun_angle=-6)
    return [r0, r1, r2, r3, r4]


ANIMS = {
    # name: (poses, durations in ms, loop)
    "idle": ([STAND,
              Pose(belly=(0.0, 0.6)),
              Pose(body=(0, 1), belly=(0.6, 0.3)),
              Pose(belly=(0.3, 0.3))], [260, 220, 260, 220], True),
    "run": (run_frames(), [70] * 6, True),
    "jump": ([Pose(body=(0, -1), hips=(0, -1), near_foot=(4.0, 53, -0.2),
                   far_foot=(-2.0, 57.5, 0.5), gun_angle=-8)], [100], False),
    "fall": ([Pose(near_foot=(2.0, 57.5, 0.3), far_foot=(-1.0, 58, 0.4), gun_angle=4),
              Pose(near_foot=(3.0, 57.0, 0.2), far_foot=(-2.0, 58.5, 0.5), gun_angle=2)],
             [120, 120], True),
    "land": ([Pose(body=(0, 2), hips=(0, 2), belly=(0.8, -0.6))], [90], False),
    "duck": ([Pose(body=(0, 5), hips=(0, 4), belly=(0.5, -0.3)), CROUCH], [50, 100], False),
    "shoot": (shoot_frames(STAND), [60, 90], False),
    "duck_shoot": (shoot_frames(CROUCH), [60, 90], False),
    "reload": (reload_frames(), [150, 250, 350, 350, 250], False),
    "hurt": ([Pose(body=(-2, 0), head=(-1, 0), gun=(-2, -3), gun_angle=-25, face="shock",
                   near_foot=(3.0, 55, -0.3))], [300], False),
    # the gun flies off; both arms flail above the head, Mario style
    "death": ([Pose(body=(0, -2), hips=(0, -2), face="shock", show_gun=False,
                    near_hand=(15, 9), far_hand=(51, 9),
                    near_foot=(4.0, 56, -0.4), far_foot=(-3.0, 58, 0.5)),
               Pose(body=(0, -2), hips=(0, -2), face="shock", show_gun=False,
                    near_hand=(14, 12), far_hand=(52, 6),
                    near_foot=(2.0, 58, 0.2), far_foot=(-4.0, 56, 0.6))], [110, 110], True),
}


def muzzle_flash_frames():
    """Three flash frames, anchored at the left-middle pixel (0, 6)."""
    frames = []
    shapes = [
        [(0, 3), (6, 1), (8, 4), (15, 6), (8, 8), (6, 11), (0, 9)],
        [(0, 4), (5, 3), (10, 6), (5, 9), (0, 8)],
        None,
    ]
    for pts in shapes:
        img = Image.new("RGBA", (16, 13), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        if pts:
            d.polygon(pts, fill=(255, 168, 40, 255))
            d.polygon([(x * 0.65, 6 + (y - 6) * 0.6) for x, y in pts], fill=(255, 226, 90, 255))
            d.polygon([(x * 0.35, 6 + (y - 6) * 0.35) for x, y in pts], fill=(255, 255, 236, 255))
        else:  # smoke puff
            for cx, cy, r, col in [(3, 6, 2.5, (190, 190, 196, 200)),
                                   (6, 5, 2, (220, 220, 226, 170))]:
                d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=col)
        frames.append(img)
    return frames


# --------------------------------------------------------------------------
# Export
# --------------------------------------------------------------------------

def export():
    frames_dir = ROOT / "player" / "hero"
    meta = {
        "frame_size": [W, H],
        "anchor": [32, 64],          # frame point placed on the hitbox's bottom centre
        "hitbox": {"stand": [24, 56], "duck": [24, 42]},
        "anims": {},
    }
    rendered = {}
    for name, (poses, durations, loop) in ANIMS.items():
        d = frames_dir / name
        d.mkdir(parents=True, exist_ok=True)
        for old in d.glob("*.png"):
            old.unlink()
        muzzles = []
        rendered[name] = []
        for i, pose in enumerate(poses):
            img, muzzle = render(pose)
            img.save(d / f"{i}.png")
            muzzles.append(list(muzzle))
            rendered[name].append(img)
        meta["anims"][name] = {"durations": durations, "loop": loop, "muzzle": muzzles}
    (frames_dir / "anim.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")

    fx_dir = ROOT / "effects" / "muzzle_flash"
    fx_dir.mkdir(parents=True, exist_ok=True)
    flashes = muzzle_flash_frames()
    for i, img in enumerate(flashes):
        img.save(fx_dir / f"{i}.png")
    return rendered, flashes, meta


def contact_sheet(rendered):
    """Every frame of every animation, one row per animation, 3x zoom."""
    font = ImageFont.truetype(str(ROOT / "font" / "PublicPixel.ttf"), 8)
    label_w = 80
    cols = max(len(f) for f in rendered.values())
    sheet = Image.new("RGBA", (label_w + cols * (W + 4), len(rendered) * (H + 4)),
                      (110, 175, 230, 255))
    d = ImageDraw.Draw(sheet)
    for row, (name, frames) in enumerate(rendered.items()):
        y = row * (H + 4)
        d.text((4, y + H // 2 - 4), name, font=font, fill=(20, 30, 50, 255))
        for col, img in enumerate(frames):
            sheet.alpha_composite(img, (label_w + col * (W + 4), y))
    return zoom(sheet, 3)


def preview_gif(rendered, meta, flashes):
    """All animations playing side by side at 3x."""
    font = ImageFont.truetype(str(ROOT / "font" / "PublicPixel.ttf"), 8)
    names = list(rendered)
    cols = 4
    cell_w, cell_h = 96, 84
    rows = math.ceil(len(names) / cols)
    tick = 30  # ms per GIF frame
    total = 2400
    out = []
    for t in range(0, total, tick):
        img = Image.new("RGBA", (cols * cell_w, rows * cell_h), (110, 175, 230, 255))
        d = ImageDraw.Draw(img)
        for i, name in enumerate(names):
            info = meta["anims"][name]
            durs = info["durations"]
            cycle = sum(durs)
            local = t % (cycle + (0 if info["loop"] else 600))
            k, acc = len(durs) - 1, 0
            for j, du in enumerate(durs):
                if local < acc + du:
                    k = j
                    break
                acc += du
            cx, cy = (i % cols) * cell_w, (i // cols) * cell_h
            d.rectangle([cx, cy + 74, cx + cell_w - 1, cy + cell_h - 1], fill=(92, 140, 52, 255))
            img.alpha_composite(rendered[name][k], (cx + 16, cy + 10))
            if name in ("shoot", "duck_shoot") and k < 2:
                mx, my = info["muzzle"][k]
                img.alpha_composite(flashes[k], (cx + 16 + int(mx), cy + 10 + int(my) - 6))
            d.text((cx + 4, cy + 2), name, font=font, fill=(20, 30, 50, 255))
        out.append(zoom(img, 3).convert("P", palette=Image.ADAPTIVE, colors=128))
    out[0].save(OUT / "animations.gif", save_all=True, append_images=out[1:],
                duration=tick, loop=0, disposal=2)


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    rendered, flashes, meta = export()
    contact_sheet(rendered).save(OUT / "all_frames.png")
    preview_gif(rendered, meta, flashes)
    print("frames:", sum(len(v) for v in rendered.values()), "->", ROOT / "player" / "hero")
