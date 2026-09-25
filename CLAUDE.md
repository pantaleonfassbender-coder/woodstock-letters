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
- Keep the site dependency-free and the data files static. Search will move to
  Pagefind once more volumes are in, as a build step that adds files, not a framework.

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

## Conventions

- Citation form: `WL <vol> (<year>): <page>`. Article ids: `<vol>-<first page>`.
- `pages[].n` is the Internet Archive **viewer index**, not the scan leaf. The
  mapping comes from `*_page_numbers.json`. Links use `/page/n{n}`.
- Editorial prose on the site is in English, in the same register as Ignatiana.
