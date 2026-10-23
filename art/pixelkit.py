"""
pixelkit.py

Shared pixel-art toolkit for the sprite generators in art/: shaded shapes,
a canvas that draws them with the game's colour ramps, and the automatic
dark outline. Every sprite uses the same palette and light so they match.

Usage:
    K = Kit(64, 64)
    c = K.canvas()
    c.draw(K.ellipse(32, 32, 10, 8), "skin", "head")
    image = c.image()
"""
import math

import numpy as np
from PIL import Image

# Light comes from the upper front so faces stay lit.
LIGHT = np.array([-0.30, -0.62, 0.72])
LIGHT /= np.linalg.norm(LIGHT)

# Each ramp: deep shadow, shadow, base, highlight.
RAMPS = {
    # hero
    "skin":    [(146, 82, 64), (198, 124, 88), (232, 164, 118), (250, 204, 164)],
    "shirt":   [(150, 158, 186), (202, 208, 224), (238, 240, 246), (255, 255, 255)],
    "pants":   [(36, 42, 66), (54, 64, 100), (76, 90, 134), (102, 118, 166)],
    "belt":    [(46, 28, 22), (74, 46, 32), (100, 66, 44), (128, 90, 58)],
    "shoe":    [(22, 20, 26), (38, 36, 44), (58, 56, 68), (92, 90, 104)],
    "hair":    [(24, 16, 16), (42, 30, 28), (66, 50, 46), (92, 74, 66)],
    "wood":    [(70, 36, 22), (110, 60, 32), (148, 88, 46), (182, 120, 66)],
    "metal":   [(34, 36, 44), (60, 64, 76), (96, 102, 118), (150, 158, 176)],
    "shell":   [(110, 20, 24), (170, 36, 36), (214, 64, 56), (240, 120, 100)],
    "brass":   [(120, 84, 24), (176, 132, 40), (222, 180, 70), (250, 226, 140)],
    # creatures
    "feather": [(130, 134, 156), (188, 192, 208), (230, 232, 240), (255, 255, 255)],
    "beak":    [(150, 60, 20), (210, 100, 30), (245, 150, 50), (255, 200, 110)],
    "carapace": [(58, 46, 22), (96, 78, 34), (136, 112, 50), (176, 150, 76)],
    "scales":  [(52, 66, 32), (82, 100, 46), (116, 136, 66), (156, 174, 96)],
    "scute":   [(112, 86, 34), (152, 120, 48), (188, 154, 70), (216, 192, 110)],
    # world
    "leaf":    [(28, 66, 40), (44, 100, 50), (70, 136, 62), (114, 178, 82)],
    "bark":    [(56, 34, 24), (88, 56, 36), (120, 82, 52), (152, 110, 72)],
    "stone":   [(68, 70, 84), (102, 106, 120), (138, 142, 156), (182, 186, 198)],
    "cloud":   [(176, 200, 232), (208, 226, 246), (236, 244, 252), (255, 255, 255)],
    "poppy":   [(120, 20, 36), (180, 36, 52), (228, 64, 70), (255, 132, 128)],
    "flag":    [(108, 16, 24), (168, 28, 36), (212, 44, 48), (240, 98, 90)],
    "cloth":   [(120, 120, 132), (176, 176, 186), (216, 216, 222), (244, 244, 248)],
}
OUTLINE = (40, 24, 28)
THRESH = (0.22, 0.48, 0.80)


class Shape:
    """A pixel mask plus a surface normal per pixel, used for shading."""

    def __init__(self, mask, normal):
        self.mask = mask
        self.n = normal

    def __or__(self, other):
        take_other = other.mask & (~self.mask | (other.n[2] > self.n[2]))
        n = np.where(take_other, other.n, self.n)
        return Shape(self.mask | other.mask, n)

    def __and__(self, other):
        return Shape(self.mask & other.mask, self.n)

    def __sub__(self, other):
        return Shape(self.mask & ~other.mask, self.n)

    def where(self, cond):
        return Shape(self.mask & cond, self.n)


def neighbours(a):
    """True where any 4-neighbour of a pixel is True."""
    out = np.zeros_like(a)
    out[1:, :] |= a[:-1, :]
    out[:-1, :] |= a[1:, :]
    out[:, 1:] |= a[:, :-1]
    out[:, :-1] |= a[:, 1:]
    return out


def shift(a, dx, dy):
    """a moved by (dx, dy) pixels, padding with False."""
    out = np.zeros_like(a)
    h, w = a.shape
    out[max(dy, 0):h + min(dy, 0), max(dx, 0):w + min(dx, 0)] = \
        a[max(-dy, 0):h + min(-dy, 0), max(-dx, 0):w + min(-dx, 0)]
    return out


class Kit:
    """Shape builders for a fixed image size (pixel centres sit at +0.5)."""

    def __init__(self, w, h):
        self.W, self.H = w, h
        self.YY, self.XX = np.mgrid[0:h, 0:w] + 0.5

    def ellipse(self, cx, cy, rx, ry, angle=0.0):
        XX, YY = self.XX, self.YY
        ca, sa = math.cos(angle), math.sin(angle)
        lx = (XX - cx) * ca + (YY - cy) * sa
        ly = -(XX - cx) * sa + (YY - cy) * ca
        dx, dy = lx / rx, ly / ry
        d2 = dx * dx + dy * dy
        nz = np.sqrt(np.clip(1 - d2, 0, 1))
        nx = dx * ca - dy * sa
        ny = dx * sa + dy * ca
        return Shape(d2 <= 1.0, np.stack([nx, ny, nz]))

    def capsule(self, p0, p1, r0, r1=None):
        """A limb segment with rounded ends, radius r0 at p0 and r1 at p1."""
        XX, YY = self.XX, self.YY
        (x0, y0), (x1, y1) = p0, p1
        r1 = r0 if r1 is None else r1
        vx, vy = x1 - x0, y1 - y0
        length2 = max(vx * vx + vy * vy, 1e-6)
        t = np.clip(((XX - x0) * vx + (YY - y0) * vy) / length2, 0, 1)
        r = r0 + (r1 - r0) * t
        ox = (XX - (x0 + t * vx)) / r
        oy = (YY - (y0 + t * vy)) / r
        d2 = ox * ox + oy * oy
        nz = np.sqrt(np.clip(1 - d2, 0, 1))
        return Shape(d2 <= 1.0, np.stack([ox, oy, nz]))

    def box(self, x0, y0, x1, y1):
        """Flat-facing rectangle, inclusive pixel bounds."""
        XX, YY = self.XX, self.YY
        mask = (XX >= x0) & (XX < x1 + 1) & (YY >= y0) & (YY < y1 + 1)
        n = np.stack([np.zeros_like(XX), np.zeros_like(XX), np.ones_like(XX)])
        return Shape(mask, n)

    def poly_mask(self, points):
        """Even-odd fill of a polygon given in continuous pixel coordinates."""
        XX, YY = self.XX, self.YY
        inside = np.zeros((self.H, self.W), bool)
        for i in range(len(points)):
            (x1, y1), (x2, y2) = points[i], points[(i + 1) % len(points)]
            crosses = (y1 > YY) != (y2 > YY)
            dy = (y2 - y1) if y2 != y1 else 1e-9
            x_at = (x2 - x1) * (YY - y1) / dy + x1
            inside ^= crosses & (XX < x_at)
        return inside

    def poly(self, points, tilt=-0.3):
        """Polygon as a Shape with a flat, slightly upward-facing normal."""
        XX = self.XX
        n = np.stack([np.zeros_like(XX), tilt * np.ones_like(XX), np.ones_like(XX)])
        return Shape(self.poly_mask(points), n)

    def canvas(self):
        return Canvas(self.W, self.H)


class Canvas:
    def __init__(self, w, h):
        self.W, self.H = w, h
        self.rgb = np.zeros((h, w, 3), np.uint8)
        self.alpha = np.zeros((h, w), bool)
        self.group = np.full((h, w), -1)
        self.group_ids = {}

    def draw(self, shape, ramp, group, inner=True, thresh=THRESH):
        """Shade a part with its colour ramp and draw it over what is there.

        inner=True darkens this part's edge where it overlaps a part from a
        different group, so overlapping limbs stay readable.
        """
        gid = self.group_ids.setdefault(group, len(self.group_ids))
        m = shape.mask
        n = shape.n
        light = (n[0] * LIGHT[0] + n[1] * LIGHT[1] + n[2] * LIGHT[2]) / (
            np.sqrt((n ** 2).sum(0)) + 1e-6)
        idx = np.digitize(light, thresh)
        colours = np.array(RAMPS[ramp], np.uint8)[idx]
        if inner:
            behind = self.alpha & (self.group != gid) & ~m
            edge = m & neighbours(behind)
        self.rgb[m] = colours[m]
        self.alpha |= m
        self.group[m] = gid
        if inner:
            self.rgb[edge] = RAMPS[ramp][0]

    def flat(self, mask, ramp, group, base=2):
        """Draw a hard-surface part: flat fill, lit top edge, dark bottom edge."""
        gid = self.group_ids.setdefault(group, len(self.group_ids))
        r = RAMPS[ramp]
        top = mask & ~shift(mask, 0, 1)
        bottom = mask & ~shift(mask, 0, -1)
        self.rgb[mask] = r[base]
        self.rgb[bottom] = r[0]
        self.rgb[top] = r[3]
        self.alpha |= mask
        self.group[mask] = gid

    def px(self, colour, *points):
        for x, y in points:
            if 0 <= x < self.W and 0 <= y < self.H:
                self.rgb[y, x] = colour
                self.alpha[y, x] = True

    def image(self, outline=OUTLINE):
        """The finished RGBA image; outline=None skips the silhouette outline."""
        rgb = self.rgb.copy()
        alpha = self.alpha
        if outline is not None:
            edge = ~self.alpha & neighbours(self.alpha)
            rgb[edge] = outline
            alpha = self.alpha | edge
        a = alpha.astype(np.uint8) * 255
        return Image.fromarray(np.dstack([rgb, a]), "RGBA")


def zoom(img, k):
    return img.resize((img.width * k, img.height * k), Image.NEAREST)
