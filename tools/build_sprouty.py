"""Build the Sprouty Codex pet (sprite v2: 8x11 grid of 192x208 cells, 1536x2288 RGBA).

Usage: python3 build_sprouty.py [output_dir]
Writes <output_dir>/sprouty/{pet.json,spritesheet.png} and <output_dir>/previews/*.gif
"""
import json
import math
import os
import sys

from PIL import Image, ImageDraw, ImageFilter, ImageOps

S = 4                       # supersampling factor
CW, CH = 192, 208           # cell size
COLS, ROWS = 8, 11
FRAMES = [6, 8, 8, 4, 5, 8, 6, 6, 6, 8, 8]
STATES = ["idle", "running-right", "running-left", "waving", "jumping",
          "failed", "waiting", "running", "review", "look-a", "look-b"]

# ---- palette -------------------------------------------------------------
OUT = (46, 56, 50, 255)
OW = 3
MINT = (139, 211, 160, 255)
MINT_D = (104, 182, 130, 255)
BELLY = (246, 242, 214, 255)
BLUSH = (244, 168, 178, 255)
LEAF = (98, 190, 98, 255)
LEAF_D = (62, 140, 72, 255)
EYE = (30, 36, 32, 255)
WHITE = (255, 255, 255, 255)
MOUTH = (204, 78, 88, 255)
SWEAT = (150, 212, 250, 255)
WOOD = (214, 176, 122, 255)
WOOD_D = (170, 128, 80, 255)

G_BODY = (79, 163, 122, 255)
G_CAPE = (44, 104, 76, 255)
G_BELLY = (232, 236, 200, 255)
CRYSTAL = (188, 166, 242, 255)
CRYSTAL_L = (230, 220, 255, 255)
GOLD = (255, 222, 110, 255)
AMBER = (255, 190, 80, 255)
ORB = (214, 255, 168, 255)


class Pen:
    """Draws in cell coordinates on a supersampled canvas."""

    def __init__(self):
        self.im = Image.new("RGBA", (CW * S, CH * S), (0, 0, 0, 0))
        self.d = ImageDraw.Draw(self.im)

    def ell(self, cx, cy, rx, ry, fill, ol=True, ow=OW):
        if ol:
            self.d.ellipse([(cx - rx - ow) * S, (cy - ry - ow) * S,
                            (cx + rx + ow) * S, (cy + ry + ow) * S], fill=OUT)
        self.d.ellipse([(cx - rx) * S, (cy - ry) * S, (cx + rx) * S, (cy + ry) * S], fill=fill)

    def _cap(self, p1, p2, r, fill):
        (x1, y1), (x2, y2) = p1, p2
        self.d.line([x1 * S, y1 * S, x2 * S, y2 * S], fill=fill, width=int(2 * r * S))
        for x, y in (p1, p2):
            self.d.ellipse([(x - r) * S, (y - r) * S, (x + r) * S, (y + r) * S], fill=fill)

    def cap(self, p1, p2, r, fill, ol=True):
        if ol:
            self._cap(p1, p2, r + OW, OUT)
        self._cap(p1, p2, r, fill)

    def poly(self, pts, fill, ol=True, ow=OW):
        sp = [(x * S, y * S) for x, y in pts]
        self.d.polygon(sp, fill=fill)
        if ol:
            self.d.line(sp + [sp[0]], fill=OUT, width=ow * S, joint="curve")

    def line(self, pts, fill=OUT, w=2.2):
        sp = [(x * S, y * S) for x, y in pts]
        self.d.line(sp, fill=fill, width=int(w * S), joint="curve")
        r = w / 2
        for x, y in (pts[0], pts[-1]):
            self.d.ellipse([(x - r) * S, (y - r) * S, (x + r) * S, (y + r) * S], fill=fill)

    def arc(self, cx, cy, rx, ry, a0, a1, w=2.4, fill=OUT):
        self.d.arc([(cx - rx) * S, (cy - ry) * S, (cx + rx) * S, (cy + ry) * S],
                   a0, a1, fill=fill, width=int(w * S))

    def leaf(self, x, y, length, width, ang, fill=LEAF):
        """Leaf from (x,y) pointing at angle ang (deg, 0 = up, clockwise)."""
        a = math.radians(ang)
        ux, uy = math.sin(a), -math.cos(a)
        nx, ny = -uy, ux
        n = 14
        left, right = [], []
        for i in range(n + 1):
            t = i / n
            w = width * math.sin(math.pi * t) ** 0.8
            px, py = x + ux * length * t, y + uy * length * t
            left.append((px + nx * w, py + ny * w))
            right.append((px - nx * w, py - ny * w))
        self.poly(left + right[::-1], fill, ow=2)
        self.line([(x + ux * 2, y + uy * 2), (x + ux * length * 0.75, y + uy * length * 0.75)],
                  fill=LEAF_D, w=1.4)

    def star(self, x, y, r, fill=GOLD):
        pts = []
        for i in range(8):
            rr = r if i % 2 == 0 else r * 0.35
            a = math.radians(i * 45)
            pts.append((x + math.sin(a) * rr, y - math.cos(a) * rr))
        self.poly(pts, fill, ol=False)

    def drop(self, x, y, r, fill=SWEAT):
        self.poly([(x, y - r * 2.1), (x + r * 0.9, y - r * 0.4), (x - r * 0.9, y - r * 0.4)],
                  fill, ol=False)
        self.ell(x, y, r, r, fill, ol=True, ow=1.5)
        self.d.ellipse([(x - r) * S, (y - r) * S, (x + r) * S, (y + r) * S], fill=fill)
        self.ell(x - r * 0.35, y - r * 0.3, r * 0.28, r * 0.28, WHITE, ol=False)

    def done(self, tilt=0.0, pivot=(96, 200)):
        im = self.im
        if tilt:
            im = im.rotate(-tilt, resample=Image.BICUBIC, center=(pivot[0] * S, pivot[1] * S))
        return im.resize((CW, CH), Image.LANCZOS)


# ---- base form -----------------------------------------------------------
def sprouty(p=None, **kw):
    o = dict(x=0, y=0, sq=0.0, look=(0, 0), face=0, eyes="open", mouth="smile",
             armL=18, armR=18, liftL=0, liftR=0, sway=0, droop=False, tail=1,
             tilt=0, blush=True, extras=None)
    o.update(kw)
    p = p or Pen()
    cx, gy = 96 + o["x"], 200 + o["y"]
    rw, rh = 50 * (1 + o["sq"]), 48 * (1 - o["sq"])
    cy = gy - 10 - rh
    lx, ly = o["look"]
    fx, fy = o["face"] + lx * 6, ly * 5

    # tail
    ts = o["tail"]
    p.ell(cx + ts * rw * 0.82, gy - 22, 15, 10, MINT)
    p.ell(cx + ts * (rw + 9), gy - 33, 7, 7, MINT)
    # feet
    p.ell(cx - 22, gy - 7 - o["liftL"], 13, 8, MINT)
    p.ell(cx + 22, gy - 7 - o["liftR"], 13, 8, MINT)
    # body
    p.ell(cx, cy, rw, rh, MINT)
    p.ell(cx + fx * 0.4, cy + rh * 0.36, rw * 0.62, rh * 0.55, BELLY, ol=False)
    for dx, dy, r in ((-22, -0.62, 5), (-8, -0.8, 4), (24, -0.55, 4)):
        p.ell(cx + dx - fx * 0.5, cy + rh * dy, r, r * 0.7, MINT_D, ol=False)
    # sprout
    base = (cx + fx * 0.3, cy - rh + 3)
    ang = o["sway"] + (35 if o["droop"] else 0)
    a = math.radians(ang)
    top = (base[0] + math.sin(a) * 15, base[1] - math.cos(a) * 15)
    p.cap(base, top, 2.2, LEAF_D)
    spread = 100 if o["droop"] else 52
    p.leaf(top[0], top[1], 17, 7, ang - spread)
    p.leaf(top[0], top[1], 17, 7, ang + spread)

    # face
    ey = cy - 6 + fy
    eye_x = [cx + fx - 17, cx + fx + 17]
    if o["blush"]:
        for i, ex in enumerate(eye_x):
            p.ell(ex + (-11 if i == 0 else 11), ey + 12, 8, 4.5, BLUSH, ol=False)
    for i, ex in enumerate(eye_x):
        side = -1 if i == 0 else 1
        e = o["eyes"]
        if e in ("open", "wide", "sad", "up"):
            rx, ry = (8, 11) if e == "wide" else (7, 9.5)
            p.ell(ex, ey, rx, ry, EYE, ol=False)
            hx, hy = ex - 2 + lx * 1.8, ey - 3 + ly * 1.8
            p.ell(hx, hy, 2.7, 3.1, WHITE, ol=False)
            p.ell(ex + 2.5 + lx, ey + 3.5 + ly, 1.3, 1.3, WHITE, ol=False)
            if e == "sad":
                p.line([(ex - side * 8, ey - 12), (ex + side * 6, ey - 17)], w=2.4)
        elif e == "blink":
            p.arc(ex, ey + 1, 7, 4, 10, 170, w=2.6)
        elif e == "happy":
            p.arc(ex, ey + 3, 7, 6, 200, 340, w=2.8)
        elif e == "focus":
            p.ell(ex, ey + 1, 7, 4, EYE, ol=False)
            p.line([(ex - side * 8, ey - 9), (ex + side * 6, ey - 6)], w=2.4)
        elif e == "squeeze":
            p.line([(ex - 6 * side, ey - 5), (ex + 5 * side, ey), (ex - 6 * side, ey + 5)], w=2.6)

    mx, my = cx + fx, ey + 15
    m = o["mouth"]
    if m == "smile":
        p.arc(mx - 3.5, my - 1, 3.5, 3.2, 10, 170, w=2)
        p.arc(mx + 3.5, my - 1, 3.5, 3.2, 10, 170, w=2)
    elif m == "open":
        p.ell(mx, my + 2, 5.5, 6, MOUTH, ow=2)
        p.ell(mx, my + 5, 3.2, 2.2, (240, 140, 150, 255), ol=False)
    elif m == "o":
        p.ell(mx, my + 2, 3, 3.6, MOUTH, ow=2)
    elif m == "sad":
        p.arc(mx, my + 4, 5, 4, 200, 340, w=2.2)
    elif m == "flat":
        p.line([(mx - 4, my + 1), (mx + 4, my + 1)], w=2)

    # arms
    for side, a_deg in ((-1, o["armL"]), (1, o["armR"])):
        sx, sy = cx + side * rw * 0.8, cy + rh * 0.22
        a = math.radians(a_deg)
        hx, hy = sx + side * math.sin(a) * 16, sy + math.cos(a) * 16
        p.cap((sx, sy), (hx, hy), 6, MINT)

    for fn in (o["extras"] or []):
        fn(p, cx, cy, gy, rw, rh)
    return p, cx, gy


# ---- evolved form --------------------------------------------------------
def shard(p, bx, by, tx, ty, w):
    a = math.atan2(ty - by, tx - bx)
    nx, ny = -math.sin(a) * w / 2, math.cos(a) * w / 2
    mx, my = bx + (tx - bx) * 0.55, by + (ty - by) * 0.55
    p.poly([(bx + nx, by + ny), (mx + nx * 1.25, my + ny * 1.25), (tx, ty),
            (mx - nx * 1.25, my - ny * 1.25), (bx - nx, by - ny)], CRYSTAL, ow=2)
    p.line([(bx + nx * 0.3, by + ny * 0.3), (tx, ty)], fill=CRYSTAL_L, w=1.6)


def grove(p=None, y=0, orb_r=10, extras=None):
    p = p or Pen()
    cx, gy = 96, 202 + y
    # cape (behind)
    pts = [(cx - 30, gy - 110), (cx + 30, gy - 110)]
    xs = list(range(60, -61, -15))
    for i, dx in enumerate(xs):
        pts.append((cx + dx, gy - 6 - (0 if i % 2 == 0 else 10)))
    p.poly(pts, G_CAPE)
    # tail
    p.cap((cx + 18, gy - 22), (cx + 52, gy - 34), 7, G_BODY)
    p.leaf(cx + 56, gy - 36, 20, 7, 55)
    # legs
    p.cap((cx - 16, gy - 44), (cx - 18, gy - 10), 11, G_BODY)
    p.cap((cx + 16, gy - 44), (cx + 18, gy - 10), 11, G_BODY)
    p.ell(cx - 21, gy - 5, 15, 7, G_BODY)
    p.ell(cx + 21, gy - 5, 15, 7, G_BODY)
    # torso
    p.ell(cx, gy - 74, 36, 46, G_BODY)
    p.ell(cx, gy - 64, 22, 32, G_BELLY, ol=False)
    for k in range(3):
        p.arc(cx, gy - 78 + k * 13, 16, 5, 20, 160, w=1.4, fill=(190, 200, 160, 255))
    # chest gem
    gx, gyy = cx, gy - 92
    p.poly([(gx, gyy - 8), (gx + 6, gyy), (gx, gyy + 8), (gx - 6, gyy)], AMBER, ow=2)
    p.ell(gx - 1.5, gyy - 2.5, 1.6, 1.6, WHITE, ol=False)
    # left arm down, right arm raised with orb
    p.leaf(cx - 30, gy - 106, 24, 9, -120)
    p.cap((cx - 34, gy - 100), (cx - 46, gy - 58), 8, G_BODY)
    p.leaf(cx + 30, gy - 106, 24, 9, 120)
    p.cap((cx + 34, gy - 100), (cx + 50, gy - 136), 8, G_BODY)
    if orb_r:
        p.ell(cx + 54, gy - 152, orb_r, orb_r, ORB, ow=2)
        p.ell(cx + 51, gy - 155, orb_r * 0.3, orb_r * 0.3, WHITE, ol=False)
    # crystal antlers (behind head)
    for s in (-1, 1):
        shard(p, cx + s * 16, gy - 150, cx + s * 34, gy - 194, 11)
        shard(p, cx + s * 25, gy - 160, cx + s * 52, gy - 176, 7)
    # head
    hy = gy - 136
    p.ell(cx, hy, 30, 27, G_BODY)
    p.ell(cx - 18, hy - 14, 4, 3, (60, 135, 100, 255), ol=False)
    p.ell(cx + 18, hy - 14, 4, 3, (60, 135, 100, 255), ol=False)
    for s in (-1, 1):
        ex = cx + s * 12
        p.ell(ex, hy + 1, 6.5, 4.8, GOLD, ow=2)
        p.ell(ex - 1.5, hy - 0.5, 1.6, 1.6, WHITE, ol=False)
        p.line([(ex + s * 8, hy - 10), (ex - s * 6, hy - 6)], w=2.4)
    p.arc(cx, hy + 11, 6, 3, 20, 160, w=2)
    for fn in (extras or []):
        fn(p, cx, gy)
    return p


# ---- post effects --------------------------------------------------------
def silhouette(img, color):
    out = Image.new("RGBA", img.size, color)
    out.putalpha(img.getchannel("A"))
    return out


def glow(img, color, radius, strength):
    a = img.getchannel("A").filter(ImageFilter.GaussianBlur(radius))
    a = a.point(lambda v: min(255, int(v * strength)))
    g = Image.new("RGBA", img.size, color)
    g.putalpha(a)
    return g


def rays(n, alpha, center=(96, 118), length=74, phase=0):
    im = Image.new("RGBA", (CW * S, CH * S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    for i in range(n):
        a = math.radians(phase + i * 360 / n)
        x1 = center[0] + math.sin(a) * 30
        y1 = center[1] - math.cos(a) * 30
        x2 = center[0] + math.sin(a) * length
        y2 = center[1] - math.cos(a) * length
        d.line([x1 * S, y1 * S, x2 * S, y2 * S], fill=(255, 245, 190, alpha), width=5 * S)
    return im.resize((CW, CH), Image.LANCZOS).filter(ImageFilter.GaussianBlur(2))


def stack(*layers):
    out = Image.new("RGBA", (CW, CH), (0, 0, 0, 0))
    for l in layers:
        out = Image.alpha_composite(out, l)
    return out


def sparkles(points, r=5, fill=GOLD):
    def fn(p, *a):
        for x, y, *rr in points:
            p.star(x, y, rr[0] if rr else r, fill)
    return fn


# ---- extras used by states ----------------------------------------------
def dust(side):
    def fn(p, cx, cy, gy, rw, rh):
        for dx, dy, r in ((0, 0, 6), (-9, -5, 4), (-15, 2, 3)):
            p.ell(cx + side * (52 - dx), gy - 6 + dy, r, r, (226, 226, 218, 255), ow=1.5)
    return fn


def sweat_drop(p, cx, cy, gy, rw, rh):
    p.drop(cx + rw * 0.72, cy - rh * 0.45, 5)


def tears(t):
    def fn(p, cx, cy, gy, rw, rh):
        for s in (-1, 1):
            p.drop(cx + s * 22, cy + 10 + t * 9, 3.6)
    return fn


def cloud(dx):
    def fn(p, cx, cy, gy, rw, rh):
        c = (170, 176, 186, 255)
        x, y = 50 + dx, 40
        p.ell(x, y, 16, 10, c, ow=2)
        p.ell(x + 14, y - 4, 12, 10, c, ow=2)
        p.ell(x + 26, y + 2, 11, 8, c, ow=2)
        p.d.ellipse([(x - 16) * S, (y - 4) * S, (x + 36) * S, (y + 9) * S], fill=c)
        for k in range(3):
            p.line([(x + k * 11, y + 15), (x - 3 + k * 11, y + 22)], fill=SWEAT, w=2)
    return fn


def bubble(n):
    def fn(p, cx, cy, gy, rw, rh):
        p.ell(132, 84, 4, 4, WHITE, ow=2)
        p.ell(142, 70, 6, 6, WHITE, ow=2)
        p.ell(158, 46, 26, 18, WHITE, ow=2)
        for k in range(n):
            p.ell(146 + k * 12, 46, 3, 3, EYE, ol=False)
    return fn


def tablet(p, cx, cy, gy, rw, rh):
    gy -= 5
    p.d.rounded_rectangle([(cx - 44 - OW) * S, (gy - 32 - OW) * S, (cx + 44 + OW) * S, (gy + 2 + OW) * S],
                          radius=7 * S, fill=OUT)
    p.d.rounded_rectangle([(cx - 44) * S, (gy - 32) * S, (cx + 44) * S, (gy + 2) * S],
                          radius=6 * S, fill=WOOD)
    for k in range(3):
        p.line([(cx - 32, gy - 22 + k * 9), (cx + 20 - k * 12, gy - 22 + k * 9)], fill=WOOD_D, w=2)


# ---- state rows ----------------------------------------------------------
def row_idle():
    sq = [0, 0.02, 0.035, 0.02, 0, -0.012]
    sway = [0, 3, 6, 3, 0, -3]
    return [sprouty(sq=sq[i], sway=sway[i], eyes="blink" if i == 4 else "open")[0].done()
            for i in range(6)]


def row_run_right():
    out = []
    for i in range(8):
        ph = i / 8 * 2 * math.pi
        out.append(sprouty(
            y=-abs(math.sin(ph)) * 7, face=8, tail=-1, sway=-12,
            liftL=max(0, math.sin(ph)) * 8, liftR=max(0, -math.sin(ph)) * 8,
            armL=30 + 28 * math.sin(ph), armR=30 - 28 * math.sin(ph),
            mouth="open" if i % 4 < 2 else "smile",
            extras=[dust(-1)] if i in (0, 4) else None)[0].done(tilt=6))
    return out


def row_wave():
    ang = [140, 168, 140, 112]
    return [sprouty(armR=ang[i], armL=12, sway=-4 + 4 * i % 8,
                    eyes="happy" if i in (1, 2) else "open", mouth="open")[0].done()
            for i in range(4)]


def row_jump():
    spec = [(0, 0.13, 20, "open", "smile", 0), (-24, -0.1, 150, "open", "open", -6),
            (-42, -0.06, 168, "happy", "open", 6), (-22, -0.05, 120, "open", "open", 3),
            (0, 0.1, 40, "happy", "smile", -4)]
    out = []
    for y, sq, arm, e, m, sw in spec:
        cell = sprouty(y=y, sq=sq, armL=arm, armR=arm, eyes=e, mouth=m, sway=sw,
                       liftL=4 if y else 0, liftR=4 if y else 0)[0].done()
        sh = Image.new("RGBA", (CW, CH), (0, 0, 0, 0))
        k = 1 + y / 80
        ImageDraw.Draw(sh).ellipse([96 - 40 * k, 198, 96 + 40 * k, 206], fill=(0, 0, 0, 40))
        out.append(stack(sh, cell))
    return out


def row_failed():
    out = [sprouty(y=-4, eyes="wide", mouth="o", armL=60, armR=60, extras=[sweat_drop])[0].done(),
           sprouty(eyes="wide", mouth="o", armL=45, armR=45, extras=[sweat_drop])[0].done()]
    for i in range(6):
        ex = [cloud(i * 2)] if i >= 2 else []
        if i >= 1:
            ex.append(tears(i % 3))
        out.append(sprouty(x=(1.5 if i % 2 else -1.5), sq=0.06, eyes="sad" if i % 3 else "squeeze",
                           mouth="sad", droop=True, armL=8, armR=8, extras=ex)[0].done())
    return out


def row_waiting():
    dots = [1, 2, 3, 3, 2, 1]
    tap = [0, 5, 0, 5, 0, 0]
    return [sprouty(look=(0.5, -0.6), mouth="flat", armL=10, armR=10, liftR=tap[i],
                    sway=4 if i % 2 else 0, extras=[bubble(dots[i])])[0].done()
            for i in range(6)]


def row_working():
    spots = [(48, 120), (148, 100), (60, 88), (140, 128), (44, 104), (150, 84)]
    out = []
    for i in range(6):
        a, b = (-22, -6) if i % 2 == 0 else (-6, -22)
        out.append(sprouty(look=(0, 0.5), eyes="focus", mouth="flat", armL=a, armR=b,
                           sway=-3 if i % 2 else 3,
                           extras=[tablet, sparkles([(*spots[i], 6)])])[0].done())
    return out


def row_review_evolve():
    """Sprouty evolves into the Grove Warden."""
    base_happy = sprouty(eyes="happy", mouth="open", armL=150, armR=150,
                         extras=[sparkles([(40, 90, 5), (152, 76, 6), (60, 50, 4)])])[0].done()
    base = sprouty(eyes="happy", mouth="open", armL=160, armR=160)[0].done()

    def fit(cell, k=0.88):
        """Shrink toward the feet so glows keep a margin inside the cell."""
        small = cell.resize((int(CW * k), int(CH * k)), Image.LANCZOS)
        out = Image.new("RGBA", (CW, CH), (0, 0, 0, 0))
        out.paste(small, ((CW - small.width) // 2, CH - small.height - 3), small)
        return out

    g = fit(grove().done())
    warm = (255, 238, 170, 255)

    f0 = base_happy
    f1 = stack(glow(base, warm, 7, 2.2), Image.blend(base, silhouette(base, (255, 250, 225, 255)), 0.45))
    f2 = stack(rays(10, 150), glow(base, warm, 10, 3.0), silhouette(base, (255, 252, 236, 255)))
    mid = fit(grove().done(), 0.74)
    f3 = stack(rays(10, 180, phase=18), glow(mid, warm, 9, 3.0), silhouette(mid, (255, 252, 236, 255)))
    f4 = stack(glow(g, warm, 7, 2.0), Image.blend(g, silhouette(g, (255, 250, 225, 255)), 0.4))
    f5 = stack(glow(g, (214, 255, 168, 255), 5, 0.9),
               fit(grove(Pen(), extras=[sparkles([(30, 60, 6), (170, 108, 5), (40, 150, 4)])]).done()))
    return [f0, f1, f2, f3, f4, f5]


def row_look():
    out = []
    for i in range(16):
        a = math.radians(i * 22.5)  # clockwise from 12 o'clock
        lx, ly = math.sin(a), -math.cos(a)
        out.append(sprouty(look=(lx, ly), sway=-lx * 6, tilt=lx * 3)[0].done())
    return out


def build(out_dir):
    rows = [row_idle(), row_run_right(), None, row_wave(), row_jump(), row_failed(),
            row_waiting(), row_working(), row_review_evolve()]
    rows[2] = [ImageOps.mirror(c) for c in rows[1]]
    look = row_look()
    rows += [look[:8], look[8:]]

    sheet = Image.new("RGBA", (CW * COLS, CH * ROWS), (0, 0, 0, 0))
    for r, cells in enumerate(rows):
        assert len(cells) == FRAMES[r], (r, len(cells))
        for c, cell in enumerate(cells):
            sheet.paste(cell, (c * CW, r * CH))

    pet_dir = os.path.join(out_dir, "sprouty")
    os.makedirs(pet_dir, exist_ok=True)
    sheet.save(os.path.join(pet_dir, "spritesheet.png"), optimize=True)
    with open(os.path.join(pet_dir, "pet.json"), "w", encoding="utf-8") as f:
        json.dump({
            "id": "sprouty",
            "displayName": "Sprouty",
            "description": "A sprout gecko that evolves into the Grove Warden when work is done.",
            "spriteVersionNumber": 2,
            "spritesheetPath": "spritesheet.png",
        }, f, indent=2)
        f.write("\n")

    # previews (on a light background, 2x)
    prev = os.path.join(out_dir, "previews")
    os.makedirs(prev, exist_ok=True)
    timing = {
        "idle": [280, 110, 110, 140, 140, 320], "running-right": [120] * 8,
        "running-left": [120] * 8, "waving": [160] * 4, "jumping": [140, 110, 160, 110, 200],
        "failed": [160] * 8, "waiting": [220] * 6, "running": [150] * 6,
        "review": [300, 180, 180, 200, 240, 700],
    }
    bg = (246, 245, 238, 255)

    def flat(cell):
        b = Image.new("RGBA", (CW, CH), bg)
        return Image.alpha_composite(b, cell).convert("RGB").resize((CW * 2, CH * 2), Image.LANCZOS)

    for r, name in enumerate(STATES[:9]):
        frames = [flat(c) for c in rows[r]]
        frames[0].save(os.path.join(prev, f"{name}.gif"), save_all=True,
                       append_images=frames[1:], duration=timing[name], loop=0, disposal=2)
    frames = [flat(c) for c in look]
    frames[0].save(os.path.join(prev, "look.gif"), save_all=True, append_images=frames[1:],
                   duration=350, loop=0, disposal=2)
    b = Image.new("RGBA", sheet.size, bg)
    Image.alpha_composite(b, sheet).convert("RGB").save(os.path.join(prev, "sheet-preview.png"))
    return sheet


if __name__ == "__main__":
    build(sys.argv[1] if len(sys.argv) > 1 else ".")
