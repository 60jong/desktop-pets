"""Build the Minkyung praise pet (sprite v2: 8x11 grid of 192x208 cells, 1536x2288 RGBA).

Floating, sparkly letters that praise 김민경 differently in every Codex state.

Usage: python3 build_minkyung.py [output_dir]
Writes <output_dir>/minkyung/{pet.json,spritesheet.png} and <output_dir>/previews/*.gif
Default output_dir is the repo root, so the pet lands in pets/minkyung and the
previews in assets/motions/minkyung.
"""
import json
import math
import os
import sys

from PIL import Image, ImageDraw, ImageFilter, ImageFont

S = 3                       # supersampling factor
CW, CH = 192, 208           # cell size
COLS, ROWS = 8, 11
ROW_SPEC = [("idle", 6), ("running-right", 8), ("running-left", 8), ("waving", 4),
            ("jumping", 5), ("failed", 8), ("waiting", 6), ("running", 6), ("review", 6)]
LOOK = 16

HERE = os.path.dirname(os.path.abspath(__file__))
FONT = os.path.join(HERE, "fonts", "Jua-Regular.ttf")

# ---- palette -------------------------------------------------------------
WHITE = (255, 255, 255, 255)
PINK = ((255, 150, 196), (176, 128, 255))        # top -> bottom gradient
PEACH = ((255, 184, 140), (255, 120, 170))
MINT = ((120, 226, 200), (110, 160, 255))
GOLD = ((255, 228, 120), (255, 160, 70))
BLUE = ((170, 196, 235), (130, 150, 205))
SHADOW = (150, 90, 170, 90)
HEART = (255, 102, 150, 255)
STAR = (255, 236, 140, 255)
STAR_W = (255, 255, 255, 255)

_fonts = {}


def font(px):
    key = round(px * S)
    if key not in _fonts:
        _fonts[key] = ImageFont.truetype(FONT, key)
    return _fonts[key]


def ease(x):
    return 0.5 - 0.5 * math.cos(math.pi * max(0.0, min(1.0, x)))


# ---- primitives (all coordinates in cell pixels, drawn at S x) -------------
def glyph(ch, size, grad, alpha=1.0):
    f = font(size)
    l, t, r, b = f.getbbox(ch, stroke_width=round(2.4 * S))
    pad = 6 * S
    w, h = r - l + pad * 2, b - t + pad * 2
    org = (pad - l, pad - t)
    tile = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(tile)
    d.text((org[0] + 2 * S, org[1] + 3 * S), ch, font=f, fill=SHADOW,
           stroke_width=round(2.4 * S), stroke_fill=SHADOW)
    tile = tile.filter(ImageFilter.GaussianBlur(1.5 * S))
    d = ImageDraw.Draw(tile)
    d.text(org, ch, font=f, fill=WHITE, stroke_width=round(2.4 * S), stroke_fill=WHITE)
    mask = Image.new("L", (w, h), 0)
    ImageDraw.Draw(mask).text(org, ch, font=f, fill=255)
    top, bot = grad
    g = Image.new("RGBA", (1, h))
    gb = mask.getbbox() or (0, 0, w, h)
    for y in range(h):
        k = min(1, max(0, (y - gb[1]) / max(1, gb[3] - gb[1])))
        g.putpixel((0, y), tuple(round(top[i] + (bot[i] - top[i]) * k) for i in range(3)) + (255,))
    g = g.resize((w, h))
    tile.paste(g, (0, 0), mask)
    # glossy highlight on the upper part of the letter
    hl = Image.new("L", (w, h), 0)
    ImageDraw.Draw(hl).rectangle((0, 0, w, gb[1] + (gb[3] - gb[1]) * 0.38), fill=70)
    hl = Image.composite(hl, Image.new("L", (w, h), 0), mask)
    tile.paste(Image.new("RGBA", (w, h), WHITE), (0, 0), hl)
    if alpha < 1:
        a = tile.getchannel("A").point(lambda v: round(v * alpha))
        tile.putalpha(a)
    return tile


def put(img, tile, cx, cy, rot=0.0, sx=1.0, sy=1.0):
    if sx != 1 or sy != 1:
        tile = tile.resize((max(1, round(tile.width * sx)), max(1, round(tile.height * sy))), Image.LANCZOS)
    if rot:
        tile = tile.rotate(rot, resample=Image.BICUBIC, expand=True)
    img.alpha_composite(tile, (round(cx * S - tile.width / 2), round(cy * S - tile.height / 2)))


def word(img, text, cx, cy, size, grad, per=None, spacing=0.92, alpha=1.0):
    """Draw text centred at (cx, cy); per(i) -> (dx, dy, rot, sx, sy) animates each letter."""
    f = font(size)
    adv = [f.getlength(c) / S * spacing for c in text]
    total = sum(adv)
    x = cx - total / 2
    for i, c in enumerate(text):
        if c != " ":
            dx, dy, rot, sx, sy = per(i) if per else (0, 0, 0, 1, 1)
            put(img, glyph(c, size, grad, alpha), x + adv[i] / 2 + dx, cy + dy, rot, sx, sy)
        x += adv[i]


def sparkle(img, cx, cy, r, color=STAR, rot=0.0):
    if r <= 0.3:
        return
    d = ImageDraw.Draw(img)
    pts = []
    for k in range(8):
        a = math.radians(rot + k * 45)
        rr = r if k % 2 == 0 else r * 0.32
        pts.append(((cx + math.sin(a) * rr) * S, (cy - math.cos(a) * rr) * S))
    d.polygon(pts, fill=WHITE)
    inner = [((cx + (x / S - cx) * 0.7) * S, (cy + (y / S - cy) * 0.7) * S) for x, y in pts]
    d.polygon(inner, fill=color)


def heart(img, cx, cy, r, color=HEART, rot=0.0):
    if r <= 0.3:
        return
    t = Image.new("RGBA", (round(r * 4.4 * S), round(r * 4.4 * S)), (0, 0, 0, 0))
    d = ImageDraw.Draw(t)
    c = t.width / 2
    rr = r * S

    def shape(scale, fill):
        q = rr * scale
        d.ellipse((c - q * 1.0 - q * 0.05, c - q * 0.9, c + q * 0.05, c + q * 0.1), fill=fill)
        d.ellipse((c - q * 0.05, c - q * 0.9, c + q * 1.0 + q * 0.05, c + q * 0.1), fill=fill)
        d.polygon([(c - q * 1.02, c - q * 0.3), (c + q * 1.02, c - q * 0.3), (c, c + q * 1.15)], fill=fill)

    shape(1.25, WHITE)
    shape(1.0, color)
    d.ellipse((c - rr * 0.62, c - rr * 0.62, c - rr * 0.32, c - rr * 0.32), fill=(255, 255, 255, 200))
    put(img, t, cx, cy, rot)


def lines(img, x0, y, n, length, color=(255, 170, 210, 200), direction=1):
    d = ImageDraw.Draw(img)
    for k in range(n):
        yy = y + k * 14
        x1 = x0 - direction * (k % 2) * 8
        xa, xb = sorted((x1, x1 - direction * length))
        d.rounded_rectangle((xa * S, (yy - 1.6) * S, xb * S, (yy + 1.6) * S), radius=1.6 * S, fill=color)


def canvas():
    return Image.new("RGBA", (CW * S, CH * S), (0, 0, 0, 0))


def finish(img):
    return img.resize((CW, CH), Image.LANCZOS)


# ---- states ----------------------------------------------------------------
TAU = 2 * math.pi


def idle(i, n):
    """김민경 / 최고 — letters bob in a wave, sparkles twinkle."""
    p = i / n
    img = canvas()
    for k, (x, y, ph) in enumerate([(26, 58, 0), (168, 72, 0.33), (150, 186, 0.66), (34, 168, 0.5)]):
        sparkle(img, x, y, 5 + 4 * math.sin(TAU * (p + ph)) ** 2, STAR if k % 2 else STAR_W, 20 * p)
    word(img, "김민경", 96, 92, 46, PINK, lambda j: (0, -5 * math.sin(TAU * (p - j * 0.16)), 0, 1, 1))
    word(img, "최고", 96, 150, 58, PEACH, lambda j: (0, -6 * math.sin(TAU * (p - 0.4 - j * 0.2)),
                                                    4 * math.sin(TAU * (p + j * 0.5)), 1, 1))
    heart(img, 158, 128 - 4 * math.sin(TAU * p), 7, rot=-12)
    return finish(img)


def run(i, n, direction):
    """민경 / 출동! — letters lean forward and hop one after another, speed lines trail."""
    p = i / n
    img = canvas()
    tail = 18 if direction > 0 else 174
    for k in range(3):
        off = ((p * 3 + k * 0.33) % 1) * 14
        lines(img, tail - direction * off, 84 + k * 30, 1, 22 - k * 4, direction=direction)
    lean = -10 * direction
    word(img, "민경", 100 if direction > 0 else 92, 82, 50, MINT,
         lambda j: (0, -9 * abs(math.sin(math.pi * (p * 2 + j * 0.5))), lean, 1, 1))
    word(img, "출동!", 100 if direction > 0 else 92, 146, 50, PINK,
         lambda j: (0, -9 * abs(math.sin(math.pi * (p * 2 + 0.25 + j * 0.33))), lean, 1, 1))
    for k in range(2):
        q = (p + k * 0.5) % 1
        sparkle(img, tail - direction * (6 + 30 * q), 176 - 20 * q, 6 * (1 - q), STAR, 90 * q)
    return finish(img)


def waving(i, n):
    """민경 / 안녕~ — 안녕~ swings like a waving hand, hearts pop."""
    p = i / n
    sw = math.sin(TAU * p)
    img = canvas()
    word(img, "민경", 96, 82, 50, PINK, lambda j: (0, -3 * math.sin(TAU * (p + j * 0.3)), 0, 1, 1))
    word(img, "안녕~", 96, 146, 50, PEACH, lambda j: (sw * 6 * (j - 1), -3 * abs(sw) * (2 - abs(j - 1)), -14 * sw, 1, 1))
    for k, (x, y) in enumerate([(30, 50), (164, 44), (164, 110)]):
        q = (p + k / 3) % 1
        heart(img, x, y - 14 * q, 9 * math.sin(math.pi * q), rot=(-1) ** k * 14)
    return finish(img)


def jumping(i, n):
    """민경 / 짱!! — squash, launch, stretch, land."""
    p = i / n
    img = canvas()
    h = math.sin(math.pi * p)
    sq = 1 - 0.18 * (1 - h) if i in (0, n - 1) else 1
    lift = -34 * h
    sx, sy = 1 + (1 - sq) * 0.9, sq + 0.12 * h
    word(img, "민경", 96, 84 + lift, 50, MINT, lambda j: (0, 0, 0, sx, sy))
    word(img, "짱!!", 96, 150 + lift + (1 - sq) * 20, 60, GOLD, lambda j: (0, 0, (-1) ** j * 6 * h, sx, sy))
    for k in range(5):
        a = math.radians(-70 + k * 35)
        r = 30 + 60 * h
        sparkle(img, 96 + math.sin(a) * r, 120 - math.cos(a) * r * 0.9 + lift * 0.3, 7 * h, STAR if k % 2 else STAR_W)
    d = ImageDraw.Draw(img)
    w = 40 - 16 * h
    d.ellipse(((96 - w) * S, 192 * S, (96 + w) * S, 199 * S), fill=(170, 120, 200, 60))
    return finish(img)


def failed(i, n):
    """괜찮아 (droops in blue) → 그래도 / 최고 (springs back in pink)."""
    img = canvas()
    if i < 4:
        p = i / 3
        word(img, "괜찮아", 96, 96 + 10 * ease(p), 44, BLUE,
             lambda j: (0, 6 * ease(p) * (1 + j % 2), (-1) ** j * 8 * ease(p), 1, 1))
        d = ImageDraw.Draw(img)
        for k, x in enumerate((40, 150)):
            y = 70 + 30 * ((p + k * 0.5) % 1)
            d.ellipse(((x - 3) * S, (y - 5) * S, (x + 3) * S, (y + 3) * S), fill=(150, 205, 250, 200))
        heart(img, 96, 156, 4 + 6 * ease(p), color=(255, 150, 185, 255))
    else:
        p = (i - 4) / 3
        b = math.sin(math.pi * p)
        word(img, "그래도", 96, 84 - 6 * b, 40, PINK, lambda j: (0, -4 * math.sin(math.pi * (p + j * 0.3)), 0, 1, 1))
        word(img, "최고", 96, 146 - 8 * b, 60, PEACH, lambda j: (0, 0, (-1) ** j * 5 * b, 1 + 0.08 * b, 1 + 0.08 * b))
        for k, (x, y) in enumerate([(28, 120), (166, 120), (96, 40)]):
            sparkle(img, x, y, 4 + 5 * abs(math.sin(math.pi * (p + k * 0.33))), STAR)
    return finish(img)


def waiting(i, n):
    """기다릴게 / 민경 · · · — slow sway, dots fill in one by one."""
    p = i / n
    img = canvas()
    word(img, "기다릴게", 96, 84, 40, MINT, lambda j: (0, -3 * math.sin(TAU * (p - j * 0.12)), 0, 1, 1), alpha=0.95)
    word(img, "민경", 80, 146, 50, PINK, lambda j: (0, -2 * math.sin(TAU * p), 0, 1, 1))
    d = ImageDraw.Draw(img)
    shown = i % 3 + 1 if i < 3 else 3 - (i - 3) % 3
    for k in range(3):
        x, y = 128 + k * 14, 156
        c = (255, 150, 196, 255) if k < shown else (230, 210, 240, 160)
        d.ellipse(((x - 4) * S, (y - 4) * S, (x + 4) * S, (y + 4) * S), fill=WHITE)
        d.ellipse(((x - 3) * S, (y - 3) * S, (x + 3) * S, (y + 3) * S), fill=c)
    heart(img, 164, 56 - 3 * math.sin(TAU * p), 6, rot=10)
    return finish(img)


def working(i, n):
    """열일하는 / 김민경 — letters buzz busily, sparks fly off."""
    p = i / n
    img = canvas()
    word(img, "열일하는", 96, 84, 40, PEACH,
         lambda j: (1.6 * math.sin(TAU * (p * 3 + j * 0.4)), -3 * abs(math.sin(TAU * (p * 2 + j * 0.25))), 0, 1, 1))
    word(img, "김민경", 96, 146, 50, PINK,
         lambda j: (0, -5 * abs(math.sin(math.pi * (p * 2 + j * 0.33))), 3 * math.sin(TAU * (p * 2 + j * 0.5)), 1, 1))
    for k in range(4):
        q = (p * 2 + k * 0.25) % 1
        a = math.radians(-60 + k * 40)
        sparkle(img, 96 + math.sin(a) * (60 + 30 * q), 118 - math.cos(a) * (50 + 30 * q), 6 * (1 - q), STAR, 45 * q)
    return finish(img)


def review(i, n):
    """역시 / 김민경 + crown & golden burst — the big finale."""
    p = i / (n - 1)
    img = canvas()
    d = ImageDraw.Draw(img)
    burst = ease(min(1, p * 1.6))
    for k in range(12):
        a = math.radians(k * 30 + 25 * p)
        r0, r1 = 30, 30 + 64 * burst
        w = math.radians(5)
        d.polygon([((96 + math.sin(a) * r0) * S, (122 - math.cos(a) * r0) * S),
                   ((96 + math.sin(a - w) * r1) * S, (122 - math.cos(a - w) * r1) * S),
                   ((96 + math.sin(a + w) * r1) * S, (122 - math.cos(a + w) * r1) * S)],
                  fill=(255, 226, 140, round(110 * burst)))
    pop = ease(min(1, p * 2))
    word(img, "역시", 96, 80, 40 * (0.6 + 0.4 * pop), GOLD, lambda j: (0, -4 * math.sin(math.pi * p + j), 0, 1, 1))
    grow = ease(min(1, max(0, p * 1.6 - 0.2)))
    word(img, "김민경", 96, 140, 44 + 10 * grow, PINK, lambda j: (0, -4 * math.sin(math.pi * (p + j * 0.2)), 0, 1, 1))
    cy = 40 - 18 * (1 - grow)
    if grow > 0:
        cw = 20 * grow
        d.polygon([((96 - cw) * S, (cy + 8) * S), ((96 - cw) * S, (cy - 6) * S), ((96 - cw / 2) * S, (cy + 1) * S),
                   (96 * S, (cy - 10) * S), ((96 + cw / 2) * S, (cy + 1) * S), ((96 + cw) * S, (cy - 6) * S),
                   ((96 + cw) * S, (cy + 8) * S)], fill=(255, 200, 70, 255), outline=WHITE, width=2 * S)
    for k, (x, y) in enumerate([(30, 70), (162, 70), (26, 176), (166, 176)]):
        sparkle(img, x, y, 8 * burst * (0.6 + 0.4 * math.sin(math.pi * (p * 2 + k * 0.5)) ** 2), STAR if k % 2 else STAR_W)
    return finish(img)


def look(i):
    """김민경 / 최고 leaning toward the 16 directions, a heart orbits on that side."""
    a = TAU * i / LOOK                       # 0 = 12 o'clock, clockwise
    dx, dy = math.sin(a), -math.cos(a)
    img = canvas()
    word(img, "김민경", 96 + 6 * dx, 92 + 4 * dy, 46, PINK, lambda j: (0, 0, -6 * dx, 1, 1))
    word(img, "최고", 96 + 6 * dx, 150 + 4 * dy, 58, PEACH, lambda j: (0, 0, -6 * dx, 1, 1))
    heart(img, 96 + 76 * dx, 118 + 70 * dy, 8, rot=-math.degrees(a) * 0.3)
    return finish(img)


DRAW = {
    "idle": idle,
    "running-right": lambda i, n: run(i, n, 1),
    "running-left": lambda i, n: run(i, n, -1),
    "waving": waving,
    "jumping": jumping,
    "failed": failed,
    "waiting": waiting,
    "running": working,
    "review": review,
}


def build(out_root):
    sheet = Image.new("RGBA", (CW * COLS, CH * ROWS), (0, 0, 0, 0))
    frames = {}
    for row, (name, n) in enumerate(ROW_SPEC):
        frames[name] = [DRAW[name](i, n) for i in range(n)]
        for col, f in enumerate(frames[name]):
            sheet.alpha_composite(f, (col * CW, row * CH))
    frames["look"] = [look(i) for i in range(LOOK)]
    for i, f in enumerate(frames["look"]):
        sheet.alpha_composite(f, ((i % 8) * CW, (9 + i // 8) * CH))

    pet_dir = os.path.join(out_root, "pets", "minkyung")
    os.makedirs(pet_dir, exist_ok=True)
    sheet.save(os.path.join(pet_dir, "spritesheet.png"), optimize=True)
    meta = {"id": "minkyung", "displayName": "김민경 최고",
            "description": "Floating sparkly letters that praise 김민경 in every Codex state.",
            "spriteVersionNumber": 2, "spritesheetPath": "spritesheet.png"}
    with open(os.path.join(pet_dir, "pet.json"), "w", encoding="utf-8") as fp:
        json.dump(meta, fp, ensure_ascii=False, indent=2)
        fp.write("\n")

    prev = os.path.join(out_root, "assets", "motions", "minkyung")
    os.makedirs(prev, exist_ok=True)
    for name, fs in frames.items():
        bg = [Image.alpha_composite(Image.new("RGBA", f.size, (250, 246, 252, 255)), f).convert("RGB") for f in fs]
        bg[0].save(os.path.join(prev, f"{name}.gif"), save_all=True, append_images=bg[1:],
                   duration=120 if name == "look" else 150, loop=0)
    return pet_dir, prev


if __name__ == "__main__":
    root = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(HERE)
    print("\n".join(build(root)))
