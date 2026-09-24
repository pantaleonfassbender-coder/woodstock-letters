# Progress

| Date | Volumes | Articles | Pages | Repairs | Notes |
|---|---|---|---|---|---|
| 2026-09-24 | 29 (1900) | 70 | 551 | 1443 | Pilot. Pagination 534/534 against IA labels. Open: "The Society in 1899" (p. 137) is not split from the N.E.A. report because its index line wraps; "In De Ab Ipso…" and similar inscriptions sit inside Varia. |
| 2026-09-24 | 30–34 (1901–1905) | 221 | 2170 | 4317 | Pagination against IA labels: 30 466/466, 31 480/484, 32 287/287, 33 408/408, 34 457/457. The 4 in vol. 31 are IA misreads (IA 880–883 for pp. 330–333; checked on the scan). Vol. 29 rebuilt: 550 pages, 1444 repairs (see below). |
| 2026-09-25 | 35–39 (1906–1910) | 222 | 2220 | 3578 | Pagination against IA labels: 35 428/428, 36 422/422, 37 445/445, 38 443/443, 39 429/429. No pagination gaps; every seam explained (below). Vols. 30 and 33 rebuilt for two repairs (`ofi"` → off); their pages and articles are unchanged. Atlas rebuilt over vols. 29–39. |

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

### Vols. 35–39: what the batch found

Per volume: 35 (1906) 53 articles, 432 pages, 1442 repairs; 36 (1907) 38, 433, 1258
(no. 2/3 is a double issue); 37 (1908) 42, 471, 689; 38 (1909) 42, 451, 115;
39 (1910) 47, 433, 74. The *ct* ligature leaves the printing during vol. 37
(over 100 "6l" per issue before, none from vol. 38), hence the few repairs.

Pipeline fixes in `build_volume.py`. Vols. 29–34 rebuild to the same pages and articles.

- **Supplements that continue the issue's numbering** (vol. 35 pp. 319–341, vol. 39
  pp. 279–301) are a section, not a separate pagination. Only a Supplement whose
  own numbers fall below the issue's last page is cited as "Suppl." (vol. 37,
  pp. 1–19, the decree *De nova provinciarum et missionum constitutione*).
- **A half-title reading only SUPPLEMENT is a printed page** (vol. 37 Suppl. 1,
  vol. 39 p. 279), and it gives its section to the piece that follows.
- **Offsets within a stretch of consecutive scan leaves.** The numbering cannot
  jump between two leaves with no plate or blank between them, so each stretch
  takes its offset from its own readings, after dropping transient misreads (a
  single outlier, or a run sandwiched between agreeing runs). In vols. 38–39 the
  OCR often reads a 5 as 6: vol. 38 pp. 53–58 came out as "68 64 55 66 57 68",
  and vol. 39 pp. 350–352 as "360 361 362". The median of seven followed them.
- **Blocks of table pages** between numbered pages are pages when the numbering
  leaves room for them (vol. 35 p. 317, vol. 39 pp. 299–301). This generalises
  the old rule for a single short leaf.
- **Unnumbered pages at an issue's end** are pages, not inserts, when the next
  issue leaves room (vol. 38 pp. 156–159, the Messina earthquake report; p. 157
  checked on the scan). The Declaration in vol. 30 has no room and stays an insert.
- **The first page of every issue opens an article** even when the OCR has
  spoiled its title (vol. 36 no. 2/3, "irn /iDemonam" for IN MEMORIAM: pp.
  209–256 had been swallowed by the Varia of no. 1). A spoiled title takes the
  index entry that names its page ("Frisbee, Samuel H").
- **QA report:** a gap filled by blank leaves is listed as blank pages (vol. 35 p. 318).
- **Repairs:** years with the 9 read as g ("igo6" → 1906, 27 times in vol. 35,
  previously turned into "igoé"). The ff ligature read as `fi"` ("stafi\" of",
  "Bufi\"alo", "Dufi'y") is joined back into one word. `6`→`é` no longer applies
  before *i* ("distin6i") or in lower-case strings of digit look-alikes ("ij6o").
  `iu`→`in` needs five letters ("sius", a Latin fragment, had become "sins").

Seams checked and left as they are: vol. 35 p. 342 (blank); vol. 38 p. 160 (blank)
and pp. 322–324 (blank, fold-out table, blank); vol. 39 p. 302 (blank).

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
  mission among the Dakota, probably one article in two); vol. 36 p. 1 "Ibt Memory";
  vol. 38 p. 178 "The Ea K 7 Ho Ua Ke" (the Sicilian earthquake, split from p. 177)
  and p. 192 "Fl00t> Anb Gospel" (continues p. 189); vol. 39 p. 102 (two index
  entries run together) and p. 398 "Fa Ther Pa Trick Cle a Son".
- Index entries in inverted form become titles where the page heading is not in
  capitals ("Innsbruck, The Golden Jubilee of", "Kenny Father, Letter of").
- Undecided repairs, left as made: `supped` → `slipped`, `miilenium` → `millenium` (vol. 39).
- Small capitals after the L-fix read "LOuis", "LOrdship".
- Tables (mission statistics, retreat lists) are kept as paragraphs of OCR text where
  they sit on numbered pages; unnumbered fold-out tables are left out like plates.
- Latin passages are not repaired except for the ligature rules, because the frequency gate is English.
- **Search and the concordance are a linear scan in the browser** over all volumes
  (now eleven, about 13 MB). This is past the planned threshold of ten: the move to
  Pagefind is due before the next batch.
