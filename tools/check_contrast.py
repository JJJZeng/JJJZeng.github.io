#!/usr/bin/env python3
"""Verify every meaningful colour pair against WCAG 2.2 contrast minimums.

    python3 tools/check_contrast.py

Exits non-zero if any pair fails, so it can gate a commit. Keep the token values
below in sync with the :root and [data-theme="dark"] blocks in
assets/css/style.css.
"""

from __future__ import annotations

import sys

LIGHT = {
    "paper": "#F7FAFD", "card": "#FFFFFF", "tint": "#EDF4FC",
    "ink": "#0C1F38", "slate": "#4A6280",
    "signal": "#0B4FD1", "signal-hi": "#08379A", "signal-wash": "#E4EEFC",
    "cyan": "#0F6E86", "cyan-wash": "#E2F1F5",
    "rule": "#D3E1F2", "rule-firm": "#6F8BAE",
    "warm": "#FFC933", "warm-fill": "#0B4FD1", "warm-wash": "#FFF3D1", "warm-ink": "#6B4A00",
    "white": "#FFFFFF",
}

DARK = {
    "paper": "#08131F", "card": "#0E2033", "tint": "#0B1A2A",
    "ink": "#E7F0FA", "slate": "#A6BFD9",
    "signal": "#86B6F2", "signal-hi": "#B0D0F8", "signal-wash": "#14304F",
    "cyan": "#5CC7E7", "cyan-wash": "#123642",
    "rule": "#21395A", "rule-firm": "#4A73A2",
    "warm": "#FFD75E", "warm-fill": "#3A70BC", "warm-wash": "#3D3218", "warm-ink": "#FFD75E",
    "near-black": "#06121E",
}

# (foreground, background, minimum, description)
#   4.5 = normal text            (WCAG 1.4.3 AA)
#   3.0 = large text >= 24px, and UI component / graphical boundaries (1.4.11)
PAIRS_LIGHT = [
    ("ink", "paper", 4.5, "body text on page"),
    ("ink", "card", 4.5, "body text on card"),
    ("ink", "tint", 4.5, "body text on tinted band"),
    ("slate", "paper", 4.5, "secondary text on page"),
    ("slate", "card", 4.5, "secondary text on card"),
    ("slate", "tint", 4.5, "secondary text on tinted band"),
    ("signal", "paper", 4.5, "link on page"),
    ("signal", "card", 4.5, "link on card"),
    ("signal", "tint", 4.5, "link on tinted band"),
    ("signal-hi", "paper", 4.5, "link hover on page"),
    ("signal-hi", "signal-wash", 4.5, "tag text on wash"),
    ("white", "signal", 4.5, "primary button label"),
    ("cyan", "paper", 4.5, "role label on page"),
    ("cyan", "tint", 4.5, "role label on tinted band"),
    ("cyan", "cyan-wash", 4.5, "ML tag text on wash"),
    ("signal", "paper", 3.0, "chart bar vs page"),
    ("cyan", "paper", 3.0, "chart bar vs page"),
    ("rule-firm", "paper", 3.0, "input / chip border"),
    ("rule-firm", "card", 3.0, "tag border on card"),
    ("warm", "warm-fill", 3.0, "both-marker ring vs its bar"),
    ("warm-fill", "paper", 3.0, "both-marker bar vs page"),
    ("warm-ink", "warm-wash", 4.5, "both-families tag text"),
    ("paper", "ink", 4.5, "connect band body text"),
    ("on-invert-soft", "ink", 4.5, "connect band lede"),
    ("on-invert-dim", "ink", 4.5, "connect band eyebrow"),
    ("ink", "paper", 4.5, "connect band button label"),
    ("on-invert-edge", "ink", 3.0, "connect band ghost button edge"),
    ("rule-firm", "tint", 3.0, "chip border on band"),
]

PAIRS_DARK = [
    ("ink", "paper", 4.5, "body text on page"),
    ("ink", "card", 4.5, "body text on card"),
    ("ink", "tint", 4.5, "body text on tinted band"),
    ("slate", "paper", 4.5, "secondary text on page"),
    ("slate", "card", 4.5, "secondary text on card"),
    ("slate", "tint", 4.5, "secondary text on tinted band"),
    ("signal", "paper", 4.5, "link on page"),
    ("signal", "card", 4.5, "link on card"),
    ("signal", "tint", 4.5, "link on tinted band"),
    ("signal-hi", "paper", 4.5, "link hover on page"),
    ("signal-hi", "signal-wash", 4.5, "tag text on wash"),
    ("near-black", "signal", 4.5, "primary button label"),
    ("cyan", "paper", 4.5, "role label on page"),
    ("cyan", "tint", 4.5, "role label on tinted band"),
    ("cyan", "cyan-wash", 4.5, "ML tag text on wash"),
    ("signal", "paper", 3.0, "chart bar vs page"),
    ("cyan", "paper", 3.0, "chart bar vs page"),
    ("rule-firm", "paper", 3.0, "border vs page"),
    ("rule-firm", "card", 3.0, "border vs card"),
    ("warm", "warm-fill", 3.0, "both-marker ring vs its bar"),
    ("warm-fill", "paper", 3.0, "both-marker bar vs page"),
    ("warm-ink", "warm-wash", 4.5, "both-families tag text"),
    ("paper", "ink", 4.5, "connect band body text"),
    ("on-invert-soft", "ink", 4.5, "connect band lede"),
    ("on-invert-dim", "ink", 4.5, "connect band eyebrow"),
    ("ink", "paper", 4.5, "connect band button label"),
    ("on-invert-edge", "ink", 3.0, "connect band ghost button edge"),
    ("rule-firm", "tint", 3.0, "border vs band"),
]


def mix(a: str, b: str, pct: float) -> str:
    """sRGB mix of pct% a into b — mirrors CSS color-mix(in srgb, a pct%, b)."""
    ha, hb = a.lstrip("#"), b.lstrip("#")
    out = []
    for i in (0, 2, 4):
        ca, cb = int(ha[i:i + 2], 16), int(hb[i:i + 2], 16)
        out.append(round(ca * pct + cb * (1 - pct)))
    return "#" + "".join(f"{c:02X}" for c in out)


def add_invert_tokens(tok: dict) -> dict:
    """The connect band paints --paper on --ink, so its greys are mixes of the two."""
    tok = dict(tok)
    tok["on-invert-soft"] = mix(tok["paper"], tok["ink"], 0.84)
    tok["on-invert-dim"] = mix(tok["paper"], tok["ink"], 0.70)
    tok["on-invert-edge"] = mix(tok["paper"], tok["ink"], 0.50)
    return tok


def channel(v: float) -> float:
    v /= 255
    return v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4


def luminance(hex_colour: str) -> float:
    h = hex_colour.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return 0.2126 * channel(r) + 0.7152 * channel(g) + 0.0722 * channel(b)


def ratio(a: str, b: str) -> float:
    la, lb = luminance(a), luminance(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


def run(name: str, tokens: dict, pairs: list) -> int:
    print(f"\n  {name}")
    print(f"  {'':<38} {'ratio':>7}  {'min':>5}")
    print("  " + "─" * 60)
    fails = 0
    for fg, bg, need, what in pairs:
        r = ratio(tokens[fg], tokens[bg])
        ok = r >= need
        if not ok:
            fails += 1
        print(f"  {'✓' if ok else '✗'} {fg:>11} on {bg:<12} {what:<24}"[:52]
              + f" {r:>6.2f}:1 {need:>5.1f}")
    return fails


def main() -> int:
    print("WCAG 2.2 contrast check — 4.5:1 for text, 3:1 for large text and UI bounds")
    fails = run("LIGHT THEME", add_invert_tokens(LIGHT), PAIRS_LIGHT)
    fails += run("DARK THEME", add_invert_tokens(DARK), PAIRS_DARK)

    total = len(PAIRS_LIGHT) + len(PAIRS_DARK)
    print()
    if fails:
        print(f"✗ {fails} of {total} pairs below the minimum")
        return 1
    print(f"✓ all {total} pairs pass")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
