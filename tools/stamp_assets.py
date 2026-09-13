#!/usr/bin/env python3
"""Stamp CSS/JS URLs with a content hash so a stale cache can never break the page.

    python3 tools/stamp_assets.py            # update the stamps
    python3 tools/stamp_assets.py --check    # report drift, write nothing (exit 1)

GitHub Pages serves assets with `Cache-Control: max-age=600`. Without a version in
the URL, a returning visitor can hold a cached stylesheet for ten minutes after a
deploy while getting the new HTML — which renders the page with the old CSS and
looks badly broken. Appending ?v=<hash of the file> gives a changed file a new URL,
so it is fetched immediately, while unchanged files stay cached.

Run this after editing style.css or either JS file, and before committing. It is
idempotent: nothing changes if the hashes already match.
"""

from __future__ import annotations

import argparse
import hashlib
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

# Files whose URLs get a version stamp, and the pages that reference them.
ASSETS = [
    "assets/css/style.css",
    "assets/js/i18n.js",
    "assets/js/main.js",
]
PAGES = ["index.html", "404.html", "thanks.html"]


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()[:8]


def pattern(asset: str) -> re.Pattern[str]:
    """Match href/src for this asset, with or without a leading slash or ?v=."""
    esc = re.escape(asset)
    return re.compile(
        r'((?:href|src)=")(/?)' + esc + r'(?:\?v=[0-9a-f]+)?(")'
    )


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true",
                    help="report drift and exit 1, without writing")
    args = ap.parse_args()

    hashes: dict[str, str] = {}
    for asset in ASSETS:
        p = REPO / asset
        if not p.exists():
            print(f"! missing asset: {asset}", file=sys.stderr)
            return 1
        hashes[asset] = digest(p)
        print(f"  {asset:<26} {hashes[asset]}")

    drift: list[str] = []
    edits = 0
    print()

    for page in PAGES:
        p = REPO / page
        if not p.exists():
            continue
        text = original = p.read_text(encoding="utf-8")
        touched: list[str] = []

        for asset, h in hashes.items():
            rx = pattern(asset)
            found = rx.search(text)
            if not found:
                continue                      # that page does not use this asset

            def repl(m: re.Match[str], _a=asset, _h=h) -> str:
                return f"{m.group(1)}{m.group(2)}{_a}?v={_h}{m.group(3)}"

            text, n = rx.subn(repl, text)
            if n and text != original:
                touched.append(asset.rsplit("/", 1)[-1])

        if text != original:
            uniq = sorted(set(touched))
            if args.check:
                drift.append(f"{page}: {', '.join(uniq)}")
            else:
                p.write_text(text, encoding="utf-8")
                print(f"  ✓ {page:<12} stamped {', '.join(uniq)}")
                edits += 1
        else:
            print(f"  · {page:<12} already current")

    if args.check:
        if drift:
            print("\n✗ asset stamps are out of date:", file=sys.stderr)
            for d in drift:
                print(f"    {d}", file=sys.stderr)
            print("\n  Fix with:  python3 tools/stamp_assets.py", file=sys.stderr)
            return 1
        print("\n✓ all asset stamps current")
        return 0

    print(f"\n{'✓ ' + str(edits) + ' page(s) updated' if edits else '· nothing to do'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
