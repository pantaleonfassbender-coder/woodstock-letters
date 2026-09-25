# Release text for v1.0.0 (GitHub release → Zenodo)

Use as the GitHub release title and body. Zenodo takes title, creators,
description and keywords from `.zenodo.json`; the release body appears as the
version's notes. After Zenodo mints the DOI, put the version DOI into
`CITATION.cff` (identifiers), `index.html` (JSON-LD `identifier` and `sameAs`)
and the About page's citation, and the concept DOI into README.md and
`data/introduction.json` (author note and the edition's reference).

## Title

Woodstock Letters: A Research Edition, v1.0.0

## Body

First public release of the research edition of the *Woodstock Letters*
(1872–1969), the private house journal of the Jesuits in North America printed
at Woodstock College, Maryland.

**Contents.** The full text of the volumes in the public domain in the United
States, vols. 1–59 (1872–1930): 172 issues, 24,248 printed pages, 2,671
articles, some ten million words, built from the Boston College scans at the
Internet Archive. Every paragraph is cited by volume, year and printed page
(`WL 29 (1900): 46`) and linked to its scan.

**Method.** Page numbers recomputed by consensus over neighbouring pages and
cross-checked against the Internet Archive's own page labels; articles
delimited from running heads and volume indexes, with authors from the
indexes, from signatures and from the general index of 1960; the OCR repaired
conservatively, every repair and every correction by hand listed in a public
QA report per volume.

**Apparatus.** Search and concordance (Pagefind); a network atlas of the
journal's vocabulary; a person-to-person map with biodata from the Jesuit
Online Necrology; year-by-year discourse measures continuous with the author's
psycholinguistic study of the journal (doi:10.5281/zenodo.22697014);
fourteen plates from the journal and from the county atlas of 1877; an
introductory essay (APA 7 manuscript in `docs/`).

(To tag the state before the register and the tables were added, point the
tag at commit `f60c81a`: `git tag v1.0.0 f60c81a && git push origin v1.0.0`,
then create the release from that tag. Otherwise release the current state
as v1.0.0 and skip v1.1.0.)

**Rights.** Vols. 60–98 (1931–1969) are catalogued with links to the scans and
not reproduced, pending their clearance. Code MIT; editorial texts CC BY 4.0;
derived data CC0 1.0; the journal's text is in the public domain. Details in
RIGHTS.md.

**Made with** Claude (Anthropic) in cloud sessions under written instructions,
every batch reviewed; the essay discloses the method as an experiment in
distant writing (Floridi, in press).

Live site: https://woodstock-letters.netlify.app
