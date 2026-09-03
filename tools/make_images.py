#!/usr/bin/env python3
"""Generate the social share card and the Apple touch icon.

    python3 tools/make_images.py

Writes assets/img/og-cover.png (1200x630) and assets/img/apple-touch-icon.png (180x180).
Re-run after changing the name, title, or the engagement bars below.
"""

from __future__ import annotations

import sys
from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    sys.exit("Pillow is required:  python3 -m pip install --upgrade Pillow")

REPO = Path(__file__).resolve().parent.parent
OUT = REPO / "assets" / "img"

INK = (12, 31, 56)
DEEP = (7, 20, 38)
SIGNAL = (75, 143, 240)
SIGNAL_SOLID = (11, 79, 209)
CYAN = (92, 199, 231)
WARM = (255, 201, 51)      # marks the both-families engagements
WARM_FILL = (58, 112, 188)
PAPER = (247, 250, 253)
SLATE = (150, 178, 210)

# (x%, width%, family) — mirrors the chart in index.html
BARS = [
    (2.083, 42.708, "ml"), (9.375, 2.083, "ml"), (11.458, 2.083, "ml"),
    (27.083, 2.083, "ml"), (39.583, 6.25, "ml"), (53.125, 2.083, "ml"),
    (56.25, 6.25, "genai"), (63.542, 4.167, "both"), (66.667, 2.083, "genai"),
    (68.75, 2.083, "genai"), (69.792, 5.208, "genai"), (75.0, 6.25, "genai"),
    (80.208, 7.292, "genai"), (87.5, 3.125, "genai"), (89.583, 3.125, "both"),
    (91.667, 3.125, "genai"), (92.708, 4.167, "genai"),
]

FONT_DIRS = ["/System/Library/Fonts/Supplemental", "/System/Library/Fonts", "/Library/Fonts"]
SERIF = ["Georgia Bold.ttf", "Georgia.ttf", "Charter.ttc", "Iowan Old Style.ttc", "DejaVuSerif-Bold.ttf"]
SANS = ["HelveticaNeue.ttc", "Helvetica.ttc", "SFNS.ttf", "Arial.ttf", "DejaVuSans.ttf"]
MONO = ["SFNSMono.ttf", "Menlo.ttc", "Courier New Bold.ttf", "DejaVuSansMono.ttf"]


def font(candidates: list[str], size: int) -> ImageFont.FreeTypeFont:
    for name in candidates:
        for d in FONT_DIRS:
            p = Path(d) / name
            if p.exists():
                try:
                    return ImageFont.truetype(str(p), size)
                except OSError:
                    continue
    print(f"! no font found among {candidates}; falling back to bitmap default", file=sys.stderr)
    return ImageFont.load_default()


def vgradient(size, top, bottom):
    """Vertical gradient with a soft diagonal blue bloom in the corner."""
    w, h = size
    base = Image.new("RGB", (1, h))
    px = base.load()
    for y in range(h):
        t = y / max(h - 1, 1)
        px[0, y] = tuple(round(top[i] + (bottom[i] - top[i]) * t) for i in range(3))
    img = base.resize((w, h))

    bloom = Image.new("L", (w, h), 0)
    bd = ImageDraw.Draw(bloom)
    bd.ellipse([-w * 0.30, -h * 0.75, w * 0.72, h * 0.85], fill=64)
    from PIL import ImageFilter
    bloom = bloom.filter(ImageFilter.GaussianBlur(150))
    img.paste(Image.new("RGB", (w, h), SIGNAL_SOLID), (0, 0), bloom)
    return img


def og_cover() -> None:
    W, H = 1200, 630
    img = vgradient((W, H), DEEP, INK)
    d = ImageDraw.Draw(img)

    pad = 82
    f_eyebrow = font(MONO, 21)
    f_name = font(SERIF, 104)
    f_role = font(SANS, 37)
    f_stats = font(MONO, 23)

    # eyebrow
    d.text((pad, pad - 6), "T O R O N T O ,   C A N A D A", font=f_eyebrow, fill=SLATE)

    # name
    d.text((pad - 4, pad + 42), "Jin Zeng", font=f_name, fill=PAPER)

    # role
    d.text((pad, pad + 186), "Manager, Data Science & AI Consulting", font=f_role, fill=(200, 221, 246))

    # accent rule
    d.rounded_rectangle([pad, pad + 258, pad + 96, pad + 263], radius=3, fill=SIGNAL)

    # stats
    d.text((pad, pad + 292), "7+ YEARS   ·   17 ENGAGEMENTS   ·   11 INDUSTRIES", font=f_stats, fill=SLATE)

    # miniature engagement chart — the site's signature, at card scale
    cx, cy = pad, H - 178
    cw, rh, gap = W - pad * 2, 6, 3
    for i, (x, w, fam) in enumerate(BARS):
        x0 = cx + cw * x / 100
        x1 = max(x0 + 7, cx + cw * (x + w) / 100)
        y0 = cy + i * (rh + gap)
        colour = CYAN if fam == "ml" else (WARM_FILL if fam == "both" else SIGNAL)
        d.rounded_rectangle([x0, y0, x1, y0 + rh], radius=rh / 2, fill=colour)
        if fam == "both":
            d.rounded_rectangle([x0, y0, x1, y0 + rh], radius=rh / 2, outline=WARM, width=2)

    # axis end labels
    f_tick = font(MONO, 18)
    d.text((cx, cy - 30), "2019", font=f_tick, fill=(108, 138, 176))
    r = d.textbbox((0, 0), "2026", font=f_tick)
    d.text((cx + cw - (r[2] - r[0]), cy - 30), "2026", font=f_tick, fill=(108, 138, 176))

    OUT.mkdir(parents=True, exist_ok=True)
    img.save(OUT / "og-cover.png", "PNG", optimize=True)
    print(f"✓ og-cover.png        {W}x{H}")


def touch_icon() -> None:
    S = 180
    img = Image.new("RGB", (S, S), SIGNAL_SOLID)
    d = ImageDraw.Draw(img)
    for y in range(S):  # diagonal blue → cyan wash
        t = y / (S - 1)
        d.line([(0, y), (S, y)],
               fill=tuple(round(SIGNAL_SOLID[i] + (15, 110, 134)[i] * t - SIGNAL_SOLID[i] * t) for i in range(3)))
    f = font(SERIF, 92)
    box = d.textbbox((0, 0), "JZ", font=f)
    d.text(((S - (box[2] - box[0])) / 2 - box[0], (S - (box[3] - box[1])) / 2 - box[1]),
           "JZ", font=f, fill=(255, 255, 255))
    img.save(OUT / "apple-touch-icon.png", "PNG", optimize=True)
    print(f"✓ apple-touch-icon.png {S}x{S}")


if __name__ == "__main__":
    og_cover()
    touch_icon()
