#!/usr/bin/env python3
"""Generate the hero timeline from tools/timeline.json.

    python3 tools/build_timeline.py            # rewrite index.html
    python3 tools/build_timeline.py --check    # print the maths, write nothing

Positions are computed from real dates, so a bar can never quietly drift out of
step with the engagement it points at. Everything between <!-- chart:start --> and
<!-- chart:end --> in index.html is generated; edit timeline.json instead.
"""

from __future__ import annotations

import argparse
import html
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SPEC = REPO / "tools" / "timeline.json"
INDEX = REPO / "index.html"

START = "<!-- chart:start -->"
END = "<!-- chart:end -->"


def months(ym: str) -> int:
    """'2019-03' -> absolute month index."""
    y, m = ym.split("-")
    return int(y) * 12 + (int(m) - 1)


def pct(v: float) -> str:
    return f"{v:.3f}".rstrip("0").rstrip(".")


class Scale:
    def __init__(self, spec: dict) -> None:
        self.zero = months(spec["axis"]["from"])
        self.span = months(spec["axis"]["to"]) - self.zero
        self.present = months(spec["present"])
        if self.span <= 0:
            sys.exit("axis.to must be after axis.from")

    def resolve(self, ym: str) -> int:
        return self.present if ym == "present" else months(ym)

    def place(self, frm: str, to: str) -> tuple[float, float]:
        """Return (x%, width%) for an inclusive [from, to] month range."""
        a = self.resolve(frm)
        b = self.resolve(to)
        if b < a:
            sys.exit(f"range ends before it starts: {frm} → {to}")
        x = (a - self.zero) / self.span * 100
        w = (b - a + 1) / self.span * 100
        return x, w


def esc(s: str) -> str:
    return html.escape(s, quote=True)


def build(spec: dict) -> str:
    sc = Scale(spec)
    axis = spec["axis"]
    step = axis.get("tickEvery", 12)
    ind = " " * 10
    L: list[str] = []

    n_eng = len(spec["engagements"])
    ibm = next((b for r in spec["spine"] for b in r["bars"]
                if b["label"] == "IBM"), None)
    ibm_months = (sc.resolve(ibm["to"]) - sc.resolve(ibm["from"]) + 1) if ibm else 0
    ibm_years = ibm_months // 12

    L.append(f'{ind}<figcaption class="chart__cap">')
    L.append(f'{ind}  <span class="eyebrow">Career timeline</span>')
    L.append(f'{ind}  <span class="chart__sub">{ibm_years} continuous years at IBM, {n_eng} assignments inside them.'
             f' Each bar in the lower band is a project — select one to read it.</span>')
    L.append(f"{ind}</figcaption>")
    L.append("")

    axis_from_y = sc.zero // 12
    axis_to_y = (sc.zero + sc.span) // 12
    L.append(f'{ind}<div class="chart__scroll" role="region" tabindex="0"')
    L.append(f'{ind}     aria-label="Career timeline, {axis_from_y} to {axis_to_y}, scrollable horizontally">')
    # --tick keeps the gridline pitch in lockstep with the axis length.
    tick = step / sc.span * 100
    L.append(f'{ind}  <div class="chart__plot" style="--tick:{pct(tick)}%">')

    # ---- axis -------------------------------------------------------------
    ticks = []
    for m in range(sc.zero, sc.zero + sc.span, step):
        x = (m - sc.zero) / sc.span * 100
        ticks.append(f'<span style="--x:{pct(x)}%">{m // 12}</span>')
    L.append(f'{ind}    <div class="chart__axis" aria-hidden="true">')
    for i in range(0, len(ticks), 5):
        L.append(f"{ind}      " + "".join(ticks[i:i + 5]))
    L.append(f"{ind}    </div>")
    L.append("")

    # ---- spine: where I actually was --------------------------------------
    # This band is the point of the whole chart: seventeen short bars below read
    # as seventeen short jobs unless something shows the continuous tenure above.
    L.append(f'{ind}    <p class="chart__grouphead" id="chart-where">Where</p>')
    L.append(f'{ind}    <ul class="spine" aria-labelledby="chart-where">')
    for row in spec["spine"]:
        L.append(f'{ind}      <li class="spine__row">')
        L.append(f'{ind}        <span class="vh">{esc(row["row"])}</span>')
        for bar in row["bars"]:
            x, w = sc.place(bar["from"], bar["to"])
            # The label sits above the band, so it is never clipped by a band
            # too narrow to hold it and needs no truncation.
            label = bar.get("labelLong", bar["label"])
            cls = f'tenure tenure--{bar["kind"]}' + (" tenure--current" if bar.get("current") else "")
            L.append(f'{ind}        <span class="{cls}" style="--x:{pct(x)}%;--w:{pct(w)}%">')
            L.append(f'{ind}          <span class="tenure__label" aria-hidden="true">{esc(label)}</span>')
            L.append(f'{ind}          <span class="vh">{esc(bar["sr"])}</span>')
            L.append(f"{ind}        </span>")
        L.append(f"{ind}      </li>")
    L.append(f"{ind}    </ul>")
    L.append("")

    # ---- engagements ------------------------------------------------------
    L.append(f'{ind}    <p class="chart__grouphead" id="chart-what">What</p>')
    L.append(f'{ind}    <ol class="chart__rows" aria-labelledby="chart-what">')
    for i, e in enumerate(spec["engagements"], start=1):
        x, w = sc.place(e["from"], e["to"])
        cls = f'bar bar--{e["family"]}' + (" bar--live" if e.get("live") else "")
        L.append(f'{ind}      <li><a class="{cls}" style="--x:{pct(x)}%;--w:{pct(w)}%"'
                 f' href="{e["href"]}" data-i="{i}"><span class="vh">{esc(e["label"])}</span></a></li>')
    L.append(f"{ind}    </ol>")
    L.append(f"{ind}  </div>")
    L.append(f"{ind}</div>")

    if spec.get("earlier"):
        L.append("")
        L.append(f'{ind}<p class="chart__earlier">{esc(spec["earlier"])}</p>')

    return "\n".join(L)


def splice(markup: str) -> bool:
    text = INDEX.read_text(encoding="utf-8")
    if START not in text or END not in text:
        sys.exit(f"index.html is missing the {START} / {END} markers")
    head, rest = text.split(START, 1)
    _, tail = rest.split(END, 1)
    updated = f"{head}{START}\n{markup}\n{' ' * 8}{END}{tail}"
    if updated == text:
        print("· index.html already up to date")
        return False
    INDEX.write_text(updated, encoding="utf-8")
    print("✓ rewrote timeline in index.html")
    return True


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true", help="print the maths, write nothing")
    args = ap.parse_args()

    spec = json.loads(SPEC.read_text(encoding="utf-8"))
    sc = Scale(spec)

    if args.check:
        print(f"axis {spec['axis']['from']} → {spec['axis']['to']}  "
              f"({sc.span} months)   present = {spec['present']}\n")
        for row in spec["spine"]:
            for b in row["bars"]:
                x, w = sc.place(b["from"], b["to"])
                dur = sc.resolve(b["to"]) - sc.resolve(b["from"]) + 1
                print(f"  {row['row']:<11} {b['label'][:34]:<34} "
                      f"{b['from']}→{b['to']:<8} {dur:>3}mo  x={x:7.3f}% w={w:6.3f}%")
        print()
        narrow = []
        for i, e in enumerate(spec["engagements"], 1):
            x, w = sc.place(e["from"], e["to"])
            dur = sc.resolve(e["to"]) - sc.resolve(e["from"]) + 1
            print(f"  {i:>2} {e['href']:<16} {e['from']}→{e['to']:<8} "
                  f"{dur:>3}mo  x={x:7.3f}% w={w:6.3f}%")
            if w < 1.5:
                narrow.append(e["href"])
        if narrow:
            print(f"\n! very narrow bars (<1.5% wide), check tap targets: {narrow}")
        return 0

    splice(build(spec))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
