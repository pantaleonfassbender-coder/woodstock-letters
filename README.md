# Woodstock Letters: A Research Edition

A searchable, citable edition of the *Woodstock Letters* (1872–1969), the private
house journal of the Jesuits in North America, printed at Woodstock College,
Maryland. It is a companion to [Ignatiana](https://ignatian-research.netlify.app/).

**Status: pilot.** The catalogue covers the full run (316 issues, 98 volumes).
Volumes 24–59 (1895–1930) are in full text.

## What it offers

- **Page-exact citation.** Every paragraph sits on its printed page (`WL 29 (1900): 46`)
  and links to the scan of that page in the Internet Archive viewer.
- **Article catalogue.** Articles are delimited from the running heads and the
  volume index, and authors are taken from the index.
- **Full text for the public-domain volumes**, repaired conservatively. Every
  repair is logged in a QA report.
- **Concordance.** Keyword in context across the full-text volumes, every line cited
  to its page, with its distribution by volume and its collocates.
- **Atlas.** A network of the journal's own vocabulary: terms joined when they share
  sentences more often than chance, coloured by the section they belong to.
- **People.** A person-to-person network: Jesuits, prelates and others named in the
  same paragraphs, with each person's spread over the volumes, obituary and writings.
- **Rights tiers.** See [RIGHTS.md](RIGHTS.md).

## Layout

```
index.html, app.js, style.css   the static site (no build step, no framework)
net.js                          the atlas network renderer (canvas, no library)
data/atlas.json                 term co-occurrence network for the atlas
data/people.json                person-to-person network
pagefind/                       search index, built on deploy (git-ignored)
data/catalogue.json             every issue 1872–1969 (metadata only)
data/manifest.json              volumes built with full text
data/vol/NNN.json               one volume: articles, pages, paragraphs, index
docs/qa/volNNN.md               QA report per volume
tools/                          the pipeline (Python 3.11+)
data/raw/                       downloaded OCR, git-ignored
```

## Pipeline

```bash
pip install -r requirements.txt
python tools/fetch_catalogue.py          # refresh the catalogue (rarely needed)
python tools/fetch_ia.py --vol 29        # fetch OCR for one volume (or --from 1 --to 59)
python tools/build_volume.py 29          # build data/vol/029.json + docs/qa/vol029.md
python tools/build_atlas.py              # rebuild data/atlas.json over all full-text volumes
python tools/build_people.py             # rebuild data/people.json
python tools/build_search.py             # build the search index into pagefind/ (git-ignored)
python -m http.server 8765               # preview at http://localhost:8765
```

The site has no build step of its own. Netlify runs `tools/build_search.py` as its
build command (see `netlify.toml`), so the search index is rebuilt on every deploy and
never committed.

How the build works, briefly:

1. **Pages.** The build reads the IA hOCR page by page. Running heads are
   stripped, and printed page numbers are recomputed by consensus over
   neighbouring pages. They are cross-checked against the Internet Archive's own
   page labels (vol. 29: 534 of 534 agree). Pages the OCR cannot settle are read
   on the scan and recorded in `tools/page_overrides.json`, with pages missing
   from a scan. Each entry is listed in the QA report.
2. **Articles.** An article starts at a title page, at a mid-page heading that the
   following running heads repeat, or at a start page named in the volume index.
3. **Repair.** Line-end hyphenation is resolved, and recurrent misreadings are
   fixed: the *ct* ligature read as `6l`/`dl`, `é` read as `6`, years such as
   `i898`. Other repairs are gated by an English frequency list (`wordfreq`).
   Every change is listed in the QA report.

## Scanning the whole run

The pipeline is written to run unattended in Claude Code cloud sessions. See
[docs/CLOUD.md](docs/CLOUD.md).

## Licences

Code: MIT ([LICENSE](LICENSE)). Editorial texts: CC BY 4.0 ([LICENSE-CONTENT](LICENSE-CONTENT)).
Derived data: CC0 1.0 ([LICENSE-DATA](LICENSE-DATA)). The public-domain text is not claimed.

## Sources

Scans and OCR: Boston College Libraries, Internet Archive collection `woodstockletters`
(scanned 2015, sponsor: Boston Library Consortium).
