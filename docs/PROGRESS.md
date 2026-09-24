# Progress

| Date | Volumes | Articles | Pages | Repairs | Notes |
|---|---|---|---|---|---|
| 2026-09-24 | 29 (1900) | 70 | 551 | 1443 | Pilot. Pagination 534/534 against IA labels. Open: "The Society in 1899" (p. 137) is not split from the N.E.A. report because its index line wraps; "In De Ab Ipso…" and similar inscriptions sit inside Varia. |
| 2026-09-24 | 30–34 (1901–1905) | 221 | 2170 | 4317 | Pagination against IA labels: 30 466/466, 31 480/484, 32 287/287, 33 408/408, 34 457/457. The 4 in vol. 31 are IA misreads (IA 880–883 for pp. 330–333; checked on the scan). Vol. 29 rebuilt: 550 pages, 1444 repairs (see below). |

### Vols. 30–34: what the batch found

Per volume: 30 (1901) 54 articles, 503 pages, 1225 repairs; 31 (1902) 59, 492, 24;
32 (1903) 25, 289, 401; 33 (1904) 41, 426, 1241; 34 (1905) 42, 460, 1426.
Vols. 31–32 were printed without the *ct* ligature, hence the few repairs.

Pipeline fixes in `build_volume.py`, each for a pattern that recurred:

- **Volume index found wherever it is bound.** Before no. 1 (29, 33, 34), before
  no. 3 (31), or at the back of the previous volume: the index to vol. 30 closes
  vol. 29 no. 3. It is matched to its volume by the numeral in its heading.
  `fetch_ia.py` now also fetches the previous volume's last issue.
- **Vol. 29 corrected.** Its last "page", p. 551, was the vol. 30 index. The text
  now ends at p. 550, and the table on leaf 170 keeps its printed 550 (it was
  overruled to 549).
- **Misread page numbers.** Votes far from the run's consensus ("880" for 330,
  "21" for 218, "180" for 130) are dropped before the median. Numbers split by
  the OCR ("21 8", "1 68") are joined.
- **Supplements** are paginated on their own and cited as `Suppl.`: vol. 30 no. 1,
  "The First Century of the Society in China", pp. i–xix (roman); vol. 33 no. 3,
  "The Beatification of Our Hungarian Martyrs", pp. 1–7. Article ids `30-S001`,
  pages carry `pl` ("Suppl. vii"), articles `pp` ("Suppl. i–xix").
- **Unnumbered inserts** after an issue's last page are kept as text and cited
  "insert after p. 332" (vol. 30 no. 2: the Declaration of the French
  Provincials, 4 leaves). Unnumbered tables there are left out like plates.
- **Plates with long captions** (vol. 30: the pulpit of St. Gudule, "Bonum pro
  nostris!") no longer take a page number.
- **Front matter before the masthead** of nos. 2 and 3 (cover, list of books for
  sale) is no longer numbered.
- **Issue openings.** The first page of every issue starts an article even when
  the running heads shorten its title. Before this, the opening articles of vols.
  30, 32, 33 and 34 were missing. The masthead is stripped however the OCR spells it.
- **False splits.** A start whose title is a stretch of the current article's
  title is a continuation (running heads split titles over facing pages: "A
  Message to Those" / "Outside the Fold"). "Fr." and "Father" compare equal.
  "V a R I a", "Var La" and "Obituarv" are recognised as Varia and Obituary.
- **QA report** now checks the seams between issues and lists IA labels that are
  out of step with the IA's own neighbours.
- **Repairs narrowed.** `ii` in German names is ü (Müller, Münster, Würzburg;
  was "Muller"). `rn`→`m` only in words of five letters or more ("Tirn-Tchou"
  had become "Tim"). `6`→`é` not before other consonants ("tb6k"). `c`→`e` in
  lower-case words needs a common result ("wicrd" had become "wierd").

Checked and left as they are:

- Seam gaps of one page are blank versos or unreadable tables: vol. 30 p. 176,
  vol. 32 p. 154 (table), vol. 33 p. 266. Vol. 34 opens at p. 3 after the Jubilee
  half-title.
- Vol. 33 no. 2: the table page is printed 265 (the OCR reads 266); checked on the scan.

## Open issues

- **Vol. 32 has no no. 3 and no index** in the Internet Archive collection
  (items `woodstockletters3211unse`, `woodstockletters3332unse`, the second
  catalogued by IA as "v.33[ie.32]"). Authors in vol. 32 come from signatures only.
- **Citation form for Supplements and inserts** (`WL 30 (1901): Suppl. vii`,
  `WL 30 (1901): insert after p. 332`) needs a decision before it goes into the
  editorial notes.
- Index lines that wrap onto the next line lose their page number (vol. 29: two
  entries; vol. 30: the article at p. 94 is titled "J- Ryan", and two "Society in …"
  entries come out as p. 190).
- One-off titles left as they are: vol. 30 p. 353 "A. M. D. G. Et B. V. M. H"
  (a dedication line), vol. 34 p. 30 (garbled OCR), vol. 31 pp. 352–353 (Digmann's
  mission among the Dakota, probably one article in two).
- Small capitals after the L-fix read "LOuis", "LOrdship".
- Tables (mission statistics, retreat lists) are kept as paragraphs of OCR text.
- Latin passages are not repaired except for the ligature rules, because the frequency gate is English.
- Search is a linear scan in the browser. Move to Pagefind at about 10 volumes (now six).
