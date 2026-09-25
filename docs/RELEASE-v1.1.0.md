# Release text for v1.1.0

Use as the GitHub release title and body. Zenodo files it as a new version
under the concept DOI of v1.0.0 (10.5281/zenodo.22967521). After the release,
put the version DOI into `CITATION.cff` and bump `version` there and in the
JSON-LD of `index.html`.

## Title

Woodstock Letters: A Research Edition, v1.1.0 — register, tables, checks

## Body

Second release. The text of vols. 1–59 is unchanged; the edition gains the
journal's own finding aids and a consistency check.

**Register.** The headings and volume-and-page references of the printed
*Woodstock Letters Index, Volumes 1–80, 1872–1951* (Zorn, 1960): 6,578
headings, 19,389 references, with the compiler's marks for obituaries,
authors, reviews and pictures. A reference to vols. 1–59 opens the page in
the edition, one to vols. 60–80 opens the scan. The index of 1960 is in
copyright, so only its facts are taken and none of its phrasing (RIGHTS.md).

**Authors.** The index's "(auth.)" marks supply the authors of 202 otherwise
unsigned pieces, shown as "from the general index of 1960". Authors now come
from the volume indexes (425), the general index (202) and closing signatures
(191); 1,853 pieces remain unsigned.

**Tables.** The fold-out statistics the text leaves out like plates — the
*Ministeria spiritualia* of every house, the students in every college of the
United States and Canada, the list of the dead — as the OCR read them, line
by line, with a best-effort CSV of each and a link to its scan: 100 tables in
`data/tables/`, 49 of them fold-outs and 51 on numbered pages.

**The run to 1969.** The Volumes page lists vols. 60–98 again, with their
rights tier and links to the scans; no text.

**Checks.** `tools/check_edition.py` verifies the manifest against the volume
files, page order, the plates, the essay's citations, the register and the
legal notice's claim of no third-party loads. It is required before every
commit.

**Essay.** Version 1.2 of the introductory essay describes the register and
the tables; the manuscript in `docs/` is rebuilt from it.

Live site: https://woodstock-letters.netlify.app
