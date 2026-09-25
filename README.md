# Woodstock Letters: A Research Edition

A searchable, citable edition of the *Woodstock Letters*, the private house journal of
the Jesuits in North America, printed at Woodstock College, Maryland. It is a companion to
[Ignatiana](https://ignatian-research.netlify.app/).

The journal ran to 98 volumes, from 1872 to 1969. The edition gives the full text of the
volumes in the public domain, vols. 1–59 (1872–1930): 172 issues, 24,248 pages, 2,671 articles and some
10 million words, each page linked to its scan at the Internet Archive. The later volumes are
outside the public domain or not yet cleared, and are not part of the edition (see
[RIGHTS.md](RIGHTS.md)).

An [introductory essay](https://woodstock-letters.netlify.app/#/introduction) describes the journal,
the source, the method and the apparatus, and discloses, as APA Style asks, how the edition and the
essay were made with a generative AI system (Claude), as an experiment in what Floridi calls distant
writing; its manuscript (APA 7) is in `docs/` and is built from `data/introduction.json` by
`tools/build_introduction_docx.js`.

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
  For the Jesuits it matches, it gives the dates and places of birth, entry and death from the
  [Jesuit Online Necrology](https://jesuitonlinenecrology.bc.edu/) (Boston College Libraries),
  with a link to the record.
- **Discourse.** Year-by-year measures of voice (*we*, *I*), certainty, motives and feeling,
  with the open word lists of P. Fassbender's study of U.S. Jesuit discourse, 1890–1944
  ([replication package](https://doi.org/10.5281/zenodo.22697014), CC BY 4.0). Articles are classed
  into registers, so that essays can be read apart from letters, Varia and obituaries, and
  commemorative pieces apart from ordinary ones. The study's texts, scored from the edition,
  give its values: [validation report](docs/discourse_validation.md).
- **Citation forms.** `WL 29 (1900): 46` for a page, `WL 54 (1925): 104*` for an asterisked
  folio, `WL 30 (1901): Suppl. vii` for a Supplement, `WL 30 (1901): insert after p. 332`
  for an unnumbered insert.
- **Reading paths.** Seven curated routes through the edition (`data/paths.json`): the farms
  and the slaves of Maryland, the Jesuits and the American university, Woodstock itself, the
  jubilee effect (with the discourse measures beside each station), the Indian missions, the
  Jesuits as scientists, the chaplains. A question per path, a note per station.
- **Register.** The headings and references of the printed general index to vols. 1–80
  (Zorn, 1960), with the compiler's marks for obituaries, authors, reviews and pictures;
  references to vols. 1–59 open the page, to vols. 60–80 the scan. The index is not in the
  public domain, so only its facts are taken (see [RIGHTS.md](RIGHTS.md)); its author marks
  fill authors of unsigned pieces.
- **Tables.** The fold-out statistics (*Ministeria spiritualia*, students in the colleges,
  the list of the dead) as OCR text and best-effort CSV in `data/tables/`, each linked to its scan.
- **Plates.** The college as drawn in 1871 and photographed about 1920, the makers of Woodstock
  from Dooley's history of 1927, and the place on the Patapsco from the county atlas of 1877
  (Library of Congress): `assets/plates/`, registered with caption, credit and source leaf in
  `data/plates.json`.
- **Rights.** See [RIGHTS.md](RIGHTS.md). Legal notice and privacy: on the site under `#/imprint`.

## Layout

```
index.html, app.js, style.css   the static site (no build step, no framework)
net.js                          the atlas network renderer (canvas, no library)
data/general_index.json         the register: headings and references of the 1960 index
data/tables.json, data/tables/  the fold-out statistics as OCR text and CSV
data/introduction.json          the introductory essay; docs/*.docx is built from it
data/plates.json, assets/       plates cut from public-domain page images, with credits
CITATION.cff, .zenodo.json      citation metadata for the release and its archiving
data/atlas.json                 term co-occurrence network for the atlas
data/people.json                person-to-person network
data/necrology.json             biodata from the Jesuit Online Necrology, by person
data/discourse.json             word-list measures and register of every article
data/discourse_study.json       the study's corpus means, as reference points
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
python tools/fetch_necrology.py          # match its Jesuits to the Jesuit Online Necrology (cached, 2 s apart)
python tools/build_discourse.py          # score every article with the study's word lists
python tools/validate_discourse.py PKG   # compare with the study's replication package, unzipped at PKG
python tools/build_general_index.py      # register from the printed index of 1960 (data/general_index.json)
python tools/extract_tables.py           # the fold-out statistics into data/tables/ (needs the raw OCR of all volumes)
python tools/check_edition.py            # consistency checks; run before every commit
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
   One-off faults (a split the running heads misled, a title the OCR spoiled, a misread
   index page) are corrected by eye in `tools/article_overrides.json`, and each is listed
   in the QA report.
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
