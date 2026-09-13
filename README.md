# jjjzeng.github.io

Personal profile site for Jin Zeng — Manager, Data Science & AI Consulting.

**Live:** <https://jjjzeng.github.io>

Static HTML, CSS and vanilla JavaScript. No build step, no dependencies, no
framework, no analytics, no trackers, no cookies. Nothing is loaded from a third
party; the only outbound request in the whole site is the contact form posting to
Web3Forms, and only when a visitor presses send. GitHub Pages serves the repo root
as-is.

Reads in **English, 简体中文 or Français**, in a light or dark theme, and prints
cleanly as a résumé.

> The contact form is wired to a Web3Forms access key held in `index.html`.
> See [Contact form](#contact-form) if you ever need to rotate it.

---

## Before you push

If you edited `style.css`, `main.js` or `i18n.js`, re-stamp the asset URLs:

```bash
python3 tools/stamp_assets.py
```

**Why this matters.** GitHub Pages serves assets with `Cache-Control: max-age=600`.
Without a version in the URL, a returning visitor can be handed the new HTML while
still holding a ten-minute-old stylesheet from cache — which renders the page with
the wrong CSS and looks thoroughly broken. (This has happened once already: the
timeline bands collapsed to plain text and the spam honeypot became visible.)

The script hashes each file and writes `?v=<hash>` into every page that references
it, so a changed file gets a new URL and is fetched at once, while unchanged files
stay cached. It is idempotent — safe to run any time — and `--check` exits non-zero
if the stamps have drifted, which makes it usable as a pre-push guard:

```bash
python3 tools/stamp_assets.py --check
```

If a page ever *does* look wrong after a deploy, check this first: a hard reload
(`Cmd`/`Ctrl` + `Shift` + `R`) proving it fine means the stamps are stale, not the
code.

---

## Publish it

One-time setup, after the repo exists on GitHub:

1. Go to **Settings → Pages**.
2. Under **Build and deployment → Source**, choose **Deploy from a branch**.
3. Branch **`main`**, folder **`/ (root)`**. Save.
4. Wait a minute, then load <https://jjjzeng.github.io>.

Every later `git push` to `main` republishes automatically.

---

## What is deliberately *not* in this repo

| Excluded | Why |
| --- | --- |
| The résumé PDF | Contains a phone number, email address and home address. `.gitignore` blocks `*.pdf`, `*Resume*` and friends. |
| Original photos | Carry EXIF **GPS coordinates**, several of them recorded at home. Only processed, metadata-stripped copies are committed. |
| Email address, phone number, street address | Never in the markup. Contact goes through LinkedIn or the relay form, whose destination lives server-side at Web3Forms. |
| Client names | Every engagement is described by industry and outcome. Named platforms are either the employer's own products or public cloud services. |

Originals live one directory *up* from this repo (`../photo`, `../Resume*.pdf`),
outside the git working tree. The `.gitignore` rules are a second line of
defence, not the primary one.

---

## Add photos

The gallery is generated from a manifest, so photos never get hand-wired into
the HTML.

1. Drop the file into `../photo/` (outside the repo).
2. Add an entry to [`tools/photos.json`](tools/photos.json) under the album you
   want — `bakery`, `court` or `travel`. Write a real `alt` description; it is
   what a screen reader reads out.
3. Rebuild:

   ```bash
   python3 tools/process_photos.py
   ```

That resizes to 400 / 800 / 1600 px wide, writes WebP **and** JPEG, strips every
scrap of metadata including GPS, and rewrites the gallery block inside
`index.html` between the `<!-- gallery:start -->` and `<!-- gallery:end -->`
markers.

Dry run first, if you like:

```bash
python3 tools/process_photos.py --check
```

**Requirements:** Python 3 with Pillow. HEIC input also needs `ffmpeg` on PATH,
because Pillow cannot decode HEIC on its own:

```bash
python3 -m pip install --upgrade Pillow && brew install ffmpeg
```

To add a whole new album, add another object to the `collections` array in
`tools/photos.json`. Albums with no photos are skipped, and the filter chips
only appear once more than one album has content.

> **Edit the manifest, not the gallery block.** Everything between
> `<!-- gallery:start -->` and `<!-- gallery:end -->` in `index.html` is
> regenerated, so hand-edits there are lost on the next build. Editing a caption
> in place is also easy to get half-right: the tile shows `<span
> class="shot__caption">` but the lightbox reads the `data-caption` attribute, so
> changing one and not the other leaves them disagreeing. Change
> `tools/photos.json` and rebuild — that keeps both in step and the translation
> keys findable.

---

## Contact form

The **Send a message** form in the closing section posts to
[Web3Forms](https://web3forms.com), which relays to an inbox. The destination
address is held server-side against the access key, so **the email address never
appears in this repo or in the page source** — which is the whole reason for
using a relay instead of a `mailto:` link.

### The access key

It lives in one place — the hidden input in `index.html`:

```html
<input type="hidden" name="access_key" value="…">
```

**This key is public by design.** Web3Forms' own documentation says so, and it has
to be: a form on a static site has no server to hide anything behind, so the key
must reach the visitor's browser to work at all. It only names the destination
inbox — it cannot read past submissions, change settings, or reach the account.
Anyone can read it with View Source, which is expected and harmless.

The one thing it *can* attract is spam aimed at your inbox, which is what the
honeypot and Web3Forms' server-side filtering are for. To rotate it, get a new key
at <https://web3forms.com> and replace that one value.

If the value is ever missing or still reads `YOUR_…`, the form validates normally
but refuses to submit, saying *"This form is not connected yet"* rather than
pretending to send. A `console.warn` fires on load too.

### How it behaves

| | |
| --- | --- |
| **With JavaScript** | Validates in place, posts via `fetch`, answers in the same spot. Never navigates away. |
| **Without JavaScript** | A plain HTML POST. The browser's own `required` handling applies, and the hidden `redirect` field lands the visitor on `thanks.html`. |
| **Spam** | A `botcheck` honeypot (`display:none`, `aria-hidden`, `tabindex="-1"` — invisible to people and assistive tech alike) plus Web3Forms' own server-side filtering. If spam ever gets through, their free hCaptcha is a drop-in, at the cost of one third-party script. |
| **Validation** | Errors appear per field with an icon *and* wording, never colour alone; `aria-invalid` and `aria-describedby` are wired up; focus moves to the first bad field; a `role="status"` region announces the outcome. |

`redirect` is stripped from the `fetch` payload — it exists only for the no-JS
path. If you rename or move `thanks.html`, update that field to match.

---

## Languages

The switcher in the header offers **EN / 中文 / FR**. English is the default and
is the only copy that lives in `index.html`; the other two live in
[`assets/js/i18n.js`](assets/js/i18n.js), keyed by the exact English source
string.

That design has three consequences worth knowing:

- **No i18n markup in the HTML.** No `data-i18n` attributes to keep in sync —
  `main.js` walks the text nodes plus `aria-label`, `title`, `alt`,
  `data-caption` and `data-alt`, and swaps anything it finds a key for.
- **English is the no-JavaScript fallback.** With scripting off, a visitor reads
  the English page, which is the correct default rather than a blank one.
- **Anything without a key stays English on purpose.** Product and platform
  names (SageMaker, Elasticsearch, watsonx…) and certification titles should not
  be translated. For French, the *job titles* are also left in English: that is
  what French-speaking tech actually uses, and it avoids forcing a gendered form
  (`principal` / `principale`) onto a person.

### Editing or adding a translation

Edit `assets/js/i18n.js` directly — it is the source of truth, not generated.
After changing any English copy in `index.html`, run:

```bash
python3 tools/i18n_extract.py --missing
```

It lists every on-page string with no entry yet, and exits non-zero if any exist,
so it can gate a commit. Expect roughly 36 permanent entries in that list — the
product names above. Subtrees marked `data-no-i18n` (the switcher itself) are
skipped by both the tool and the runtime.

Keys containing `{braces}` are templates for the strings JavaScript builds at
runtime, such as `Showing {n} of {total} photos in {album}.`

The switcher also sets `<html lang>` and the page `<title>`, and re-renders the
theme-toggle label and both filter counters, so nothing is left in the previous
language. `style.css` carries a small block of per-language typography: CJK gets
neutral letter-spacing and looser leading, and French headings get a wider
measure, because French runs about 20% longer than English.

### The name

"Jin Zeng" stays in romanisation in all three languages. Guessing which
characters spell someone's name is not a decision to make on their behalf — add
them to the `zh` dictionary and to `meta.zh.title` if you want them.

---

## Add a headshot

Same pipeline as the gallery, and for the same reason — a headshot off a phone
carries GPS in its EXIF just like any other photo.

1. Put the file in `../photo/` (outside the repo).
2. Set `"portrait"` in [`tools/photos.json`](tools/photos.json) to its filename:

   ```json
   "portrait": "IMG_1234.HEIC",
   ```

3. Rebuild:

   ```bash
   python3 tools/process_photos.py
   ```

It crops to a square, writes `portrait-160` and `portrait-320` as WebP and JPEG,
strips all metadata, and splices the `<picture>` into the hero.

If the source is a wide scene rather than a head-and-shoulders shot, frame it:

```json
"portrait": { "src": "IMG_1650.heic", "focusX": 0.565, "focusY": 0.755, "zoom": 2.7 }
```

`focusX` / `focusY` place the centre of the crop as a fraction of the image;
`zoom` tightens in from the largest possible square. **Lower `zoom` = wider crop
= more background.** The avatar is a circle, so aim to land the face near the
centre.

Leave `"portrait"` as `null` and the hero shows a gradient `JZ` monogram instead.
The monogram is the *default*, not an error state — the page never requests a
file that might not be there, so there is no 404 either way.

---

## Regenerate the share card

The LinkedIn / Slack link preview image and the Apple touch icon are generated,
not hand-drawn:

```bash
python3 tools/make_images.py
```

Re-run it after changing the name, job title, or the engagement bars.

---

## Edit the content

Everything lives in `index.html` — there is no CMS and no data file to chase.

| What | Where |
| --- | --- |
| Roles and dates | `<ol class="roles">` in the **Work** section |
| Engagements | `<ol class="projects">` in the **Engagements** section |
| The timeline chart | `<ol class="chart__rows">` in the hero |
| Skills, education, languages, hobbies | their own sections, in order |
| Colours, type, spacing | the `:root` token block at the top of `assets/css/style.css` |
| Chinese and French copy | [`assets/js/i18n.js`](assets/js/i18n.js) |

Change any English string and its translations go stale silently, so run
`python3 tools/i18n_extract.py --missing` afterwards.

### The timeline is generated

`index.html`'s chart block is built from
[`tools/timeline.json`](tools/timeline.json) — do not hand-edit it:

```bash
python3 tools/build_timeline.py            # rewrite the block
python3 tools/build_timeline.py --check    # print the maths, write nothing
```

Give it real dates and it computes every position, the axis ticks, the gridline
pitch and the "N continuous years" figure in the caption. Adding an engagement is
three lines of JSON and a re-run.

The chart has two bands, and the split is the point of it:

- **Where** — a continuous `Employment` band. Seventeen short engagement bars on
  their own read as seventeen short *jobs*; this band carries the fact that all of
  them happened inside one unbroken IBM post. An arrow head marks it as ongoing.
  The UofT master's sits on the same axis because it genuinely overlaps, which
  shows it was done alongside full-time work. Degrees that predate the axis are
  named in a line underneath rather than squeezing the scale back to 2012.
- **What** — the engagement bars, unchanged.

`--check` warns about any bar under 1.5% of the axis width, since those get hard
to tap. If that fires, shorten the axis rather than shrinking the bars.

Each engagement `label` doubles as its screen-reader sentence **and** as an i18n
key, so rewording one means adding an entry in `assets/js/i18n.js`. Run
`python3 tools/i18n_extract.py --missing` after editing.

<details>
<summary>The underlying maths, if you ever need to place a bar by hand</summary>

Each bar carries two inline custom properties:

```html
<a class="bar bar--genai" style="--x:75%;--w:6.25%" href="#p-concierge" data-i="12">
```

The axis spans `axis.from → axis.to` from the spec, so for a date
`year + (month-1)/12`:

```
--x = (start - 2019) / 8 × 100%
--w = (end   - start) / 8 × 100%
```

Add a bar and you must also add the matching `<li class="row proj">` with the
same `id`, update the three counts in the filter chips, and update the
`Client engagements led` tally in the hero. The same numbers appear in
`tools/make_images.py` for the share card.

---

## Accessibility

Built to WCAG 2.2 AA and worth keeping that way:

- Every colour pair in both themes is contrast-checked — see
  [`tools/check_contrast.py`](tools/check_contrast.py) and run it after any
  palette change.
- Chart families are distinguished by **fill pattern as well as colour** — solid
  blue for generative AI, cyan diagonal stripes for ML, and a thick light-yellow
  ring for engagements that were both at once. That survives colour-blindness and
  greyscale printing, where a blue-vs-cyan distinction alone would not.
- Every timeline bar is a **24×24 px target** (SC 2.5.8): rows sit on a 24 px
  pitch and each bar carries an invisible `::before` hit area that fills its row
  exactly. Bar *lengths* stay truthful because they encode duration — the hit
  areas grow, the bars don't.
- Language proficiency shows a text label, never a bar length alone.
- Full keyboard operation: skip link, visible focus rings, a native `<dialog>`
  lightbox with arrow-key navigation, `<details>` disclosures.
- `prefers-reduced-motion` disables the chart animation and all reveals.
- `prefers-contrast: more` firms up the greys and outlines every bar.
- Reflows to 320 px with no horizontal scroll; the chart alone scrolls
  sideways, which WCAG 1.4.10 permits for data visualisations.
- Prints cleanly — navigation, chart and gallery drop out, disclosures open.
- The contact form labels every field, wires `aria-describedby` to its hint and
  error, sets `aria-invalid`, moves focus to the first bad field, and reports the
  outcome through a `role="status"` region. Errors carry an icon and wording as
  well as colour (SC 1.4.1), and native validation stays available with JavaScript
  off because `novalidate` is applied by script, not in the markup.
- Timeline bands are `<li>`s with a visually-hidden sentence each, so the spine
  reads as a list of dated facts rather than decoration.
- `<html lang>` tracks the chosen language, and the Chinese, Spanish and French
  fragments inside a page carry their own `lang` (SC 3.1.1 and 3.1.2).
- The dark closing band derives its greys with `color-mix()` from its own
  foreground and background, so it inverts with the theme. Hardcoding light greys
  there is what made the Connect text unreadable in dark mode once before.

```bash
python3 tools/check_contrast.py
```

---

## Licence

Code is free to reuse. **The photographs and biographical content are not** —
please don't lift them.
