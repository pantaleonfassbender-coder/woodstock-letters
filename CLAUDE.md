# Woodstock Letters research edition: working notes for Claude

Static site (vanilla JS, no build step) plus a Python pipeline in `tools/`.
Read README.md for the layout and RIGHTS.md before touching any volume after 1930.

## Hard rules

- **Never build full text past the public-domain cutoff.** `build_volume.py`
  refuses volumes after `current year − 96`. Do not weaken or bypass the guard.
  Volumes 60–98 stay catalogue-only until RIGHTS.md says otherwise.
- **Never commit `data/raw/`.** It is re-fetched from archive.org and is git-ignored.
- **No archive links (ZIP, torrent, bulk downloads) in README.md.** A previous
  repository was flagged by GitHub for this.
- **Regex patches go through the Edit tool, never through Bash heredocs.**
  Backslashes (`\1`, `\b`, `\d`) are silently mangled in heredocs. This has
  already broken the year repair once.
- Keep the site dependency-free and the data files static. Search and the
  concordance use Pagefind, built by `tools/build_search.py` into `pagefind/`:
  a build step that adds files, not a framework. Netlify runs it on deploy; never
  commit `pagefind/`. Run it locally before previewing search.

## Processing a batch of volumes

```bash
pip install -r requirements.txt
python tools/fetch_ia.py --from 30 --to 34
python tools/build_volume.py 30 31 32 33 34
python tools/build_atlas.py        # rebuild the atlas network over all full-text volumes
python tools/build_people.py       # rebuild the people network
```

Then review each `docs/qa/volNNN.md` before committing:

1. **Pagination.** The report must show no "pagination gaps", and the
   cross-check with the IA page labels must show 100 % agreement. If either
   fails, investigate. Do not commit a volume with wrong page numbers.
2. **Articles.** Scan the list for obvious false splits (a title repeated on
   consecutive pages, garbage titles such as "Var La"), and check the
   "index entries without a detected article start" section. Fix the heuristics
   in `build_volume.py` when a pattern recurs. Leave one-offs.
3. **Repairs.** Skim the repair list for wrong corrections. A wrong rule must be
   narrowed, never left in place.

Commit per batch with the volume numbers in the message, for example
`Add vols. 30–34 (1901–1905)`. Record a summary in `docs/PROGRESS.md`:
volumes, articles, pages, repairs, and open issues.

## Before every commit

Run `python tools/check_edition.py`. It must print `OK`. A warning is worth a
look; a failure is not to be committed around.

## Reading paths

`data/paths.json` is the editor's curation. Stations must be article ids of the
edition (the check script verifies them). Notes with `"status": "draft"` on the
path were drafted by the model; only the editor removes the mark. Do not add
paths or rewrite notes unasked.

## Register and tables

- `data/general_index.json` comes from the printed index of 1960 (in copyright):
  headings and references only, never the compiler's phrases. `build_volume.py`
  reads its "(auth.)" marks to fill missing authors (`authorFrom: "general index"`).
- `data/tables/` is built by `tools/extract_tables.py` from the raw OCR of all
  volumes; it needs `python tools/fetch_ia.py --from 1 --to 59` first. Nothing in
  it is corrected by hand; if a table is wrong, the scan is the source.

## Plates, essay, legal notice

- Plates live in `assets/plates/` (JPEG, 1600 px wide, with `_t` thumbnails) and are
  registered in `data/plates.json` with caption, credit and source leaf. Only images
  from issues published before 1931 or from other public-domain sources; each must
  name its source. Never take an image from vols. 60–98.
- The introductory essay is `data/introduction.json`; the site renders it at
  `#/introduction` and `tools/build_introduction_docx.js` builds the manuscript in
  `docs/`. Change the JSON, then rebuild the .docx, never the other way round.
  The essay follows APA Style: the author is P. Fassbender alone; the AI system is
  never listed as an author but disclosed in the author note and the closing section
  (Anthropic, 2026; Floridi, in press; McAdoo, 2024). Keep it that way.
- The legal notice at `#/imprint` (in `app.js`, `viewImprint`) describes the site's
  actual behaviour: no cookies, one localStorage key (`wlTheme`), no third-party
  requests, Netlify's injected RUM script. Anything that changes that behaviour
  must change the notice in the same commit.

## Conventions

- Citation form: `WL <vol> (<year>): <page>`. Article ids: `<vol>-<first page>`.
- `pages[].n` is the Internet Archive **viewer index**, not the scan leaf. The
  mapping comes from `*_page_numbers.json`. Links use `/page/n{n}`.
- Editorial prose on the site is in English, in the same register as Ignatiana.
