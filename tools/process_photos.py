#!/usr/bin/env python3
"""Build the gallery: resize photos, strip every scrap of metadata, rewrite index.html.

Usage:
    python3 tools/process_photos.py            # build everything
    python3 tools/process_photos.py --check    # report only, write nothing

Reads tools/photos.json. Source photos live OUTSIDE the repo (default ../photo) so
originals are never committed. Output goes to assets/img/gallery/ as WebP + JPEG at
three widths, with all EXIF -- including GPS coordinates -- removed.

Requires: Pillow. HEIC input additionally requires ffmpeg on PATH (Pillow cannot
decode HEIC), or install pillow-heif to drop the ffmpeg dependency.
"""

from __future__ import annotations

import argparse
import html
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

try:
    from PIL import Image, ImageOps
except ImportError:  # pragma: no cover
    sys.exit("Pillow is required:  python3 -m pip install --upgrade Pillow")

REPO = Path(__file__).resolve().parent.parent
MANIFEST = REPO / "tools" / "photos.json"
OUT_DIR = REPO / "assets" / "img" / "gallery"
INDEX = REPO / "index.html"

WIDTHS = (400, 800, 1600)
THUMB_W = 400          # width used for the grid tile
JPEG_QUALITY = 82
WEBP_QUALITY = 80

START = "<!-- gallery:start -->"
END = "<!-- gallery:end -->"
P_START = "<!-- portrait:start -->"
P_END = "<!-- portrait:end -->"

PORTRAIT_WIDTHS = (160, 320)

# HEIC/HEIF extensions Pillow cannot open without a plugin.
NEEDS_FFMPEG = {".heic", ".heif"}


def load_manifest() -> dict:
    if not MANIFEST.exists():
        sys.exit(f"missing manifest: {MANIFEST}")
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def open_source(path: Path, scratch: Path) -> Image.Image:
    """Return an RGB image with orientation applied and no metadata attached."""
    if path.suffix.lower() in NEEDS_FFMPEG:
        if not shutil.which("ffmpeg"):
            sys.exit(
                f"{path.name} is HEIC and needs ffmpeg to decode.\n"
                "  brew install ffmpeg      (or: python3 -m pip install pillow-heif)"
            )
        decoded = scratch / (path.stem + ".png")
        # No -vf here: ffmpeg builds a complex filtergraph for tiled HEIF and
        # refuses to mix it with simple filters. Resize with Pillow instead.
        subprocess.run(
            ["ffmpeg", "-y", "-loglevel", "error", "-i", str(path),
             "-frames:v", "1", str(decoded)],
            check=True,
        )
        img = Image.open(decoded)
    else:
        img = Image.open(path)

    img = ImageOps.exif_transpose(img)      # bake rotation in, then drop EXIF
    return img.convert("RGB")


def render(img: Image.Image, stem: str, out_dir: Path) -> dict[int, tuple[int, int]]:
    """Write WebP + JPEG at each width. Returns {width: (w, h)} actually written."""
    written: dict[int, tuple[int, int]] = {}
    for width in WIDTHS:
        if width > img.width:
            # Never upscale; still emit the largest available so srcset stays valid.
            if written:
                continue
            resized = img.copy()
        else:
            height = round(img.height * width / img.width)
            resized = img.resize((width, height), Image.LANCZOS)

        # Saving without exif=/icc_profile= is what strips the metadata.
        resized.save(out_dir / f"{stem}-{width}.webp", "WEBP",
                     quality=WEBP_QUALITY, method=6)
        resized.save(out_dir / f"{stem}-{width}.jpg", "JPEG",
                     quality=JPEG_QUALITY, optimize=True, progressive=True)
        written[width] = resized.size
    return written


def srcset(stem: str, sizes: dict[int, tuple[int, int]], ext: str) -> str:
    return ", ".join(
        f"assets/img/gallery/{stem}-{w}.{ext} {w}w" for w in sorted(sizes)
    )


def build_markup(collections: list[dict]) -> str:
    """Static HTML for the gallery. Works with JavaScript disabled."""
    populated = [c for c in collections if c["items"]]
    lines: list[str] = []
    ind = " " * 8

    if not populated:
        return f"{ind}<p class=\"gallery__empty\">No photos yet.</p>"

    if len(populated) > 1:
        lines.append(f'{ind}<div class="gallery__filters" role="group" aria-label="Filter photos by album">')
        lines.append(f'{ind}  <button type="button" class="chip" data-album="all" aria-pressed="true">All</button>')
        for c in populated:
            lines.append(
                f'{ind}  <button type="button" class="chip" data-album="{html.escape(c["id"])}"'
                f' aria-pressed="false">{html.escape(c["label"])}</button>'
            )
        lines.append(f"{ind}</div>")

    lines.append(f'{ind}<ul class="gallery__grid" id="gallery-grid">')
    index = 0
    for c in populated:
        for item in c["items"]:
            stem, sizes, caption, alt = item["stem"], item["sizes"], item["caption"], item["alt"]
            tw, th = sizes.get(THUMB_W) or sizes[max(sizes)]
            largest = max(sizes)
            lines += [
                f'{ind}  <li class="gallery__item" data-album="{html.escape(c["id"])}">',
                f'{ind}    <button type="button" class="shot" data-index="{index}"',
                f'{ind}            data-full="assets/img/gallery/{stem}-{largest}.jpg"',
                f'{ind}            data-full-webp="assets/img/gallery/{stem}-{largest}.webp"',
                f'{ind}            data-caption="{html.escape(caption, quote=True)}"',
                f'{ind}            data-alt="{html.escape(alt, quote=True)}">',
                f"{ind}      <picture>",
                f'{ind}        <source type="image/webp" srcset="{srcset(stem, sizes, "webp")}" sizes="(min-width: 60rem) 21rem, (min-width: 34rem) 45vw, 92vw">',
                f'{ind}        <img src="assets/img/gallery/{stem}-{THUMB_W if THUMB_W in sizes else largest}.jpg"',
                f'{ind}             srcset="{srcset(stem, sizes, "jpg")}"',
                f'{ind}             sizes="(min-width: 60rem) 21rem, (min-width: 34rem) 45vw, 92vw"',
                f'{ind}             width="{tw}" height="{th}" loading="lazy" decoding="async"',
                f'{ind}             alt="{html.escape(alt, quote=True)}">',
                f"{ind}      </picture>",
                f'{ind}      <span class="shot__caption">{html.escape(caption)}</span>',
                f"{ind}    </button>",
                f"{ind}  </li>",
            ]
            index += 1
    lines.append(f"{ind}</ul>")
    lines.append(f'{ind}<p class="gallery__count" role="status" data-total="{index}">Showing all {index} photos.</p>')
    return "\n".join(lines)


def splice(text: str, start: str, end: str, markup: str, indent: int) -> str:
    if start not in text or end not in text:
        print(f"! {INDEX.name} has no {start} / {end} markers — skipped", file=sys.stderr)
        return text
    head, rest = text.split(start, 1)
    _, tail = rest.split(end, 1)
    return f"{head}{start}\n{markup}\n{' ' * indent}{end}{tail}"


def build_portrait(src_dir: Path, spec, scratch: Path) -> str:
    """Square-crop the headshot, strip its metadata, and return the markup.

    A phone headshot carries GPS just like any other photo, which is the reason
    this goes through the same pipeline instead of being dropped in by hand.

    `spec` is either a filename or an object with framing controls, because the
    source is often a wide scene rather than a head-and-shoulders shot:

        {"src": "IMG_1650.heic", "focusX": 0.58, "focusY": 0.72, "zoom": 2.6}

    focusX / focusY are fractions of the image (0 = left/top, 1 = right/bottom)
    marking the centre of the crop. zoom is how many times to tighten in from
    the largest possible square: 1 keeps the full square, 3 takes a third of it.
    Returns monogram-only markup when there is no headshot to use.
    """
    ind = " " * 10
    mono = (f'{ind}<span class="portrait">\n'
            f'{ind}  <span class="portrait__initials" aria-hidden="true">JZ</span>\n'
            f'{ind}</span>')
    if not spec:
        return mono

    if isinstance(spec, str):
        spec = {"src": spec}
    src = src_dir / spec["src"]
    if not src.exists():
        print(f"! portrait not found: {src} — keeping the monogram", file=sys.stderr)
        return mono

    img = open_source(src, scratch)
    zoom = max(1.0, float(spec.get("zoom", 1)))
    fx, fy = float(spec.get("focusX", 0.5)), float(spec.get("focusY", 0.5))

    side = int(min(img.size) / zoom)
    cx, cy = fx * img.width, fy * img.height
    left = round(min(max(cx - side / 2, 0), img.width - side))
    top = round(min(max(cy - side / 2, 0), img.height - side))
    img = img.crop((left, top, left + side, top + side))

    for w in PORTRAIT_WIDTHS:
        out = img if w > side else img.resize((w, w), Image.LANCZOS)
        out.save(OUT_DIR.parent / f"portrait-{w}.webp", "WEBP", quality=86, method=6)
        out.save(OUT_DIR.parent / f"portrait-{w}.jpg", "JPEG", quality=88, optimize=True)
    print(f"✓ portrait      {side}x{side} → {', '.join(map(str, PORTRAIT_WIDTHS))}")

    web = ", ".join(f"assets/img/portrait-{w}.webp {w}w" for w in PORTRAIT_WIDTHS)
    jpg = ", ".join(f"assets/img/portrait-{w}.jpg {w}w" for w in PORTRAIT_WIDTHS)
    big = PORTRAIT_WIDTHS[-1]
    return "\n".join([
        f'{ind}<span class="portrait">',
        f'{ind}  <span class="portrait__initials" aria-hidden="true">JZ</span>',
        f"{ind}  <picture>",
        f'{ind}    <source type="image/webp" srcset="{web}" sizes="5.2rem">',
        f'{ind}    <img src="assets/img/portrait-{big}.jpg" srcset="{jpg}" sizes="5.2rem"',
        f'{ind}         width="{big}" height="{big}" alt="Jin Zeng" decoding="async">',
        f"{ind}  </picture>",
        f"{ind}</span>",
    ])


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true", help="report only, write nothing")
    args = ap.parse_args()

    manifest = load_manifest()
    src_dir = (REPO / manifest.get("sourceDir", "../photo")).resolve()

    if not args.check:
        OUT_DIR.mkdir(parents=True, exist_ok=True)

    collections: list[dict] = []
    missing: list[str] = []
    total = 0

    with tempfile.TemporaryDirectory() as tmp:
        scratch = Path(tmp)
        for coll in manifest["collections"]:
            items = []
            for n, photo in enumerate(coll["photos"], start=1):
                src = src_dir / photo["src"]
                stem = f"{coll['id']}-{n:02d}"
                if not src.exists():
                    missing.append(str(src))
                    continue
                if args.check:
                    print(f"  would build {stem} from {photo['src']}")
                    continue
                img = open_source(src, scratch)
                sizes = render(img, stem, OUT_DIR)
                items.append({
                    "stem": stem,
                    "sizes": sizes,
                    "caption": photo["caption"],
                    "alt": photo["alt"],
                })
                total += 1
                print(f"✓ {stem:<12} {img.width}x{img.height} → {', '.join(map(str, sorted(sizes)))}")
            collections.append({"id": coll["id"], "label": coll["label"], "items": items})

    if missing:
        print("\n! source photos not found:", file=sys.stderr)
        for m in missing:
            print(f"    {m}", file=sys.stderr)

    if args.check:
        return 0

    print(f"\n{total} photo(s) → {OUT_DIR.relative_to(REPO)}  (all metadata stripped)")

    with tempfile.TemporaryDirectory() as tmp:
        portrait = build_portrait(src_dir, manifest.get("portrait"), Path(tmp))

    text = INDEX.read_text(encoding="utf-8")
    updated = splice(text, START, END, build_markup(collections), 8)
    updated = splice(updated, P_START, P_END, portrait, 10)
    if updated == text:
        print("· index.html already up to date")
    else:
        INDEX.write_text(updated, encoding="utf-8")
        print(f"✓ rewrote gallery and portrait blocks in {INDEX.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
