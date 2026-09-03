#!/usr/bin/env python3
"""List every translatable string in index.html, in document order.

    python3 tools/i18n_extract.py            # human-readable list
    python3 tools/i18n_extract.py --json     # JSON array, ready to paste
    python3 tools/i18n_extract.py --missing  # only strings absent from i18n.js

Translation is keyed by the English source string itself, so index.html needs no
markup for it and stays readable. That also means English is what a visitor with
JavaScript disabled sees — the correct default rather than a broken page.

Run --missing after editing copy in index.html to find what still needs a zh/fr
entry in assets/js/i18n.js.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from html.parser import HTMLParser
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
INDEX = REPO / "index.html"
I18N = REPO / "assets" / "js" / "i18n.js"

SKIP_ELEMENTS = {"script", "style", "title"}
# Attributes whose values are read by a human or a screen reader.
ATTRS = ("aria-label", "title", "alt", "data-caption", "data-alt")
# Strings that are the same in every language, or are data rather than prose.
IGNORE = re.compile(
    r"""^(
        [\d\s.,:/–—\-•+%()]*            # pure numbers, dates, ranges
        |JZ|EN|FR|IBM|Citi|中文|Español|Français
        |[A-Z]{2,5}                      # bare acronyms
        |\d{4}\.\d{2}.*                  # 2026.01 — present
    )$""",
    re.X,
)


class Walk(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.stack: list[str] = []
        self.found: list[tuple[str, str]] = []   # (kind, string)
        self.seen: set[str] = set()
        self.no_i18n_depth = 0   # inside a data-no-i18n subtree

    def _add(self, kind: str, raw: str) -> None:
        s = re.sub(r"\s+", " ", raw).strip()
        if not s or IGNORE.match(s) or s in self.seen:
            return
        self.seen.add(s)
        self.found.append((kind, s))

    def handle_starttag(self, tag, attrs):
        names = {k for k, _ in attrs}
        opening = tag not in ("area", "base", "br", "col", "embed", "hr", "img", "input",
                              "link", "meta", "param", "source", "track", "wbr")
        # Subtrees marked data-no-i18n are excluded here for the same reason the
        # runtime skips them: the language switcher's own labels must each stay in
        # their own language.
        if "data-no-i18n" in names:
            if opening:
                self.stack.append(("__noi18n__", tag))
                self.no_i18n_depth += 1
                return
            return
        if opening:
            self.stack.append(tag)
        if self.no_i18n_depth:
            return
        for k, v in attrs:
            if k in ATTRS and v:
                self._add(f"@{k}", v)

    def handle_endtag(self, tag):
        while self.stack:
            top = self.stack.pop()
            if isinstance(top, tuple):
                if top[1] == tag:
                    self.no_i18n_depth -= 1
                    return
                continue
            if top == tag:
                return

    def handle_data(self, data):
        if self.no_i18n_depth:
            return
        if any(t in SKIP_ELEMENTS for t in self.stack if isinstance(t, str)):
            return
        self._add("text", data)


def existing_keys() -> set[str]:
    if not I18N.exists():
        return set()
    src = I18N.read_text(encoding="utf-8")
    # Keys are JSON-style double-quoted strings on the left of a colon.
    return set(re.findall(r'^\s*"((?:[^"\\]|\\.)*)"\s*:', src, re.M))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--missing", action="store_true")
    args = ap.parse_args()

    w = Walk()
    w.feed(INDEX.read_text(encoding="utf-8"))
    strings = [s for _, s in w.found]

    if args.missing:
        have = {k.replace('\\"', '"') for k in existing_keys()}
        missing = [s for s in strings if s not in have]
        if args.json:
            print(json.dumps(missing, ensure_ascii=False, indent=2))
        else:
            print(f"{len(missing)} of {len(strings)} strings have no translation entry\n")
            for s in missing:
                print(f"  {s}")
        return 1 if missing else 0

    if args.json:
        print(json.dumps(strings, ensure_ascii=False, indent=2))
        return 0

    kinds: dict[str, int] = {}
    for kind, s in w.found:
        kinds[kind] = kinds.get(kind, 0) + 1
    print(f"{len(strings)} unique translatable strings")
    for k, n in sorted(kinds.items(), key=lambda kv: -kv[1]):
        print(f"  {k:<16}{n}")
    print()
    for kind, s in w.found:
        print(f"[{kind}] {s}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
