# Progress

| Date | Volumes | Articles | Pages | Repairs | Notes |
|---|---|---|---|---|---|
| 2026-09-24 | 29 (1900) | 70 | 551 | 1443 | Pilot. Pagination 534/534 against IA labels. Open: "The Society in 1899" (p. 137) is not split from the N.E.A. report because its index line wraps; "In De Ab Ipso…" and similar inscriptions sit inside Varia. |
| 2026-09-24 | 30–34 (1901–1905) | 221 | 2170 | 4317 | Pagination against IA labels: 30 466/466, 31 480/484, 32 287/287, 33 408/408, 34 457/457. The 4 in vol. 31 are IA misreads (IA 880–883 for pp. 330–333; checked on the scan). Vol. 29 rebuilt: 550 pages, 1444 repairs (see below). |
| 2026-09-25 | 35–39 (1906–1910) | 222 | 2220 | 3578 | Pagination against IA labels: 35 428/428, 36 422/422, 37 445/445, 38 443/443, 39 429/429. No pagination gaps; every seam explained (below). Vols. 30 and 33 rebuilt for two repairs (`ofi"` → off); their pages and articles are unchanged. Atlas rebuilt over vols. 29–39. |
| 2026-09-25 | 40–44 (1911–1915) | 232 | 2155 | 575 | Pagination against IA labels: 40 408/411, 41 387/387, 42 412/412, 43 435/435, 44 448/450. The 5 differences are IA's: vol. 40 IA 374–376 for pp. 274–276, vol. 44 IA 295–296 for pp. 294–295; checked on the scans (pp. 275, 294, 295). No pagination gaps. Atlas and people map rebuilt over vols. 29–44. |
| 2026-09-25 | 45–49 (1916–1920) | 224 | 2216 | 323 | Pagination against IA labels: 45 445/462, 46 431/431, 47 449/449, 48 443/443, 49 327/385. The differences are IA's: vol. 45 no. 2 IA runs 2 behind for pp. 198–214; vol. 49 no. 1 IA counts some photo plates as pages (pp. 39–133). Both checked on the scans. Vol. 49 lacks pp. 134–135 in the scan. No pagination gaps. Vols. 29–44 rebuilt: same pages; article changes listed below. Atlas, people map and search rebuilt over vols. 29–49. |
| 2026-09-25 | 50–54 (1921–1925) | 204 | 2205 | 289 | Pagination against IA labels: 50 378/378, 51 463/463, 52 424/424, 53 423/426, 54 440/440. The 3 in vol. 53 are the printer's misprint 341–343 for 441–443, which IA copied (checked on the scan). Vol. 54 no. 2 is printed from p. 63 and is cited with the volume's own asterisk (104*). No pagination gaps. Vols. 29–49 rebuilt: same pages except vol. 30 Suppl. xx; 57 articles newly linked to their index entries. Atlas, people map and search rebuilt over vols. 29–54. |
| 2026-09-25 | 55–59 (1926–1930) | 197 | 2746 | 66 | Pagination against IA labels: 55 433/507, 56 384/384, 57 553/555, 58 718/720, 59 451/451. The differences are the printer's and IA's: vol. 55 no. 3 prints 342–417 for 442–517 and says so in an erratum (IA copied the misprint); vol. 57 IA 47–48 and vol. 58 IA 826–827 are IA misreads (checked on the scans). Vol. 56 no. 1 has a section with asterisked folios (1*–92*). No pagination gaps. Vols. 29–54 rebuilt: same pages; one article change (vol. 32). Atlas, people map and search rebuilt over vols. 29–59, the last volumes before the 1930 cutoff. |

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

### Vols. 40–44: what the batch found

Per volume: 40 (1911) 45 articles, 439 pages, 89 repairs; 41 (1912) 46, 408, 65;
42 (1913) 44, 416, 124; 43 (1914) 48, 439, 160; 44 (1915) 49, 453, 137.

Pipeline fixes in `build_volume.py`. Vols. 29–39 rebuild to the same pages and
articles; vols. 33 and 34 gain one joined index entry each.

- **Sections paginated on their own without a SUPPLEMENT heading.** Vol. 41 no. 3
  closes with a *Documentum*, the *Ordinatio studiorum in Assistentia Angliae*,
  pp. 1–14, whose first page is unnumbered. A restart is now also recognised
  from readings of 2, 3 after a run of ten or more numbered pages. The section is
  named by its running head and cited "Documentum 7".
- **Leaves scanned twice.** Vol. 42 no. 1 repeats pp. 129–134 as leaves 145–150,
  and IA labels them 129–134 again. A leaf whose text repeats a leaf shortly before
  it is left out and listed in the QA report.
- **A reading after blank leaves.** Vol. 44 no. 3 goes 453, blank, 455. Alone in its
  stretch, the 455 was ignored as a lone reading. It now stands when it counts
  the blank pages exactly (p. 455 checked on the scan).
- **Wrapped index lines.** An index line that goes on in lower case is joined to the
  one before. This removes two spurious article starts in the Varia of vol. 44
  ("in United States and Canada", "the Summer of 1915").
- **Masthead:** a stray "%" between WOODSTOCK LETTERS and the VOL line (vol. 44 no. 1)
  had kept "Vol. Xliv. No. I" as the opening article's title.

Seams checked and left as they are (blank versos or table pages): vol. 40 p. 144,
vol. 41 p. 274, vol. 42 pp. 135–136 and 280, vol. 43 p. 152, vol. 44 p. 296 (the
Missouri statistics, a fold-out).

### Vols. 45–49: what the batch found

Per volume: 45 (1916) 49 articles, 470 pages, 116 repairs; 46 (1917) 48, 450, 89;
47 (1918) 42, 452, 26; 48 (1919) 41, 448, 44; 49 (1920) 44, 396, 48.

Pagination fixes in `build_volume.py`:

- **Numbers printed bare at the foot.** Vol. 49 no. 1 (the Golden Jubilee number)
  has no running heads; every page carries its number alone on the last line. A bare
  number of one to three digits (not "00") at the foot of a headless page is now read
  as the page number and removed from the text. The trailing-page rule now counts
  pages whose reading was accepted, so a table's final figure (vol. 42, "106") cannot
  pass for a number.
- **The printer's repeated numbers.** Vol. 45 no. 2 prints pp. 213–214 twice (checked
  on the scans). The second pair is cited "213 bis", "214 bis", and the QA report
  lists the repeat. IA labels this stretch two too low from p. 198.
- **Roman Supplement without a heading.** The Pignatelli supplement in vol. 46 no. 2
  (pp. i–ix) is recognised from its roman numerals: a restart at i–iv after ten or
  more arabic pages, where lettered numerals outnumber arabic readings (vol. 40's
  arabic supplement, whose "11" reads like ii, is unaffected).
- **Pages checked by hand: `tools/page_overrides.json`.** For each IA item it lists
  leaves whose page was read on the scan, and pages missing from it. Every entry is
  printed in the QA report. The first entry: vol. 49 leaf 168 is p. 136; pp. 134–135
  are not in the scan (leaf 167 prints 133 and breaks off mid-sentence).
- **Index heading numerals.** "INDEX TO VOLUME XLVIil" (vol. 48): a lower-case l or i
  in a numeral set in capitals is read as I.

Article fixes:

- **Varia under a running head.** From vol. 47 the Varia open on a page headed
  "VARIA 97", with the title repeated below, or mid-page on headless pages (vol. 49
  no. 1). The title-page rule saw neither, so the last obituary ran on through the
  Varia (vol. 48 "Fr. Maurice Prendergast", pp. 92–160). A VARIA heading now opens
  the section when it stands mid-page or under its own running head. Within the Varia,
  running heads the OCR has spoiled ("V A A- /A", "VA IU A") open nothing. This
  removes false splits in vol. 45 ("Ireland", p. 290) and vol. 49 (p. 363). A second
  OBITUARY over a running notice opens nothing either (vol. 49 p. 353).
- **The index a page out.** Vol. 48's index puts five obituaries one page late
  ("Neander 236", which begins on p. 235). An entry that finds no heading on its page
  now tries the pages on either side, for headings only.
- **Obituary name lines run into the text** ("Father Joseph O'Reilly S.J. The Rev.
  Joseph O'Reilly, S.J., after …", vol. 47 pp. 230, 232, 236). For an obituary entry,
  a paragraph that begins with the name is split, and the name becomes the heading.
- **Index lines broken after "of the"** or before "(concluded) 18" are joined (vol. 48).
  "(concluded)" and "(To be continued)" are stripped from authors, and "24o" is read as 240.
- **Varia index entries no longer give a section to the article at their page.** Every
  issue's opening article at p. 1 had been marked "Varia" through an entry such as
  "Mexico … 1, 70" (vols. 33, 36, 38, 40, 43).
- **Folios "(228)"** at the foot of opening pages are removed from the text. Vol. 32
  "Retreats for Men" now finds its signature (Matthew Russell).

Repair fixes. Each wrong repair was traced to its rule, and the rule narrowed:

- A substitution may not turn one word into another unless the reading is much
  commoner (1.5 on the zipf scale): "De Lancy" stays (not "Laney"), "coats-of-arnis"
  no longer becomes "amis", "cornets" is no longer "comets" (vol. 34), and "torna" is
  no longer "toma" (vol. 42). "thern" → them and `supped` → slipped still pass. One
  right repair is lost: "Lord Adlon" (Acton, vol. 35).
- The dl→ct rule no longer accepts a bare -ct ending that is not a word ("proudl}^" had
  become "prouct"; "goodl" "gooct"). Half-repairs such as "efiedl" → "efiect" go with it,
  and the misreading now stands unrepaired.
- The ct-ligature rule leaves numbers alone ("i6tli" is 16th, not "ictli"). `6`→`é`
  no longer applies after *i* ("Troi6-Rivieres").
- Small capitals after the L-fix: "lyOyola", "lyOrdship" now give Loyola, Lordship.

Seams checked and left as they are (blank versos at issue ends): vol. 46 p. 290,
vol. 47 p. 144, vol. 48 p. 298, vol. 49 p. 150.

Rebuilt vols. 29–44: pages unchanged. The article changes are those listed above,
plus vol. 36 "Notes from Vigan", which now starts on its title page (p. 321, not 323),
and vol. 39's Sodality supplement, which takes author Fr. A. J. E. Mullan from the
index entry "Sodality Aggregations" on its page.

### Vols. 50–54: what the batch found

Per volume: 50 (1921) 40 articles, 415 pages, 89 repairs; 51 (1922) 47, 470, 113;
52 (1923) 35, 430, 52; 53 (1924) 45, 445, 18; 54 (1925) 37, 445, 17.

Pagination:

- **Vol. 54 no. 2 is numbered from p. 63.** The printer began the June number at
  p. 63 (checked on the scan), so its pp. 63–161 repeat numbers of no. 1; no. 3 goes
  on from p. 179. The volume's contents marks no. 2's pages with an asterisk
  ("the numbers marked with asterisks will be found in the June issue, Number 2").
  The edition follows it: every page of no. 2 is cited with the asterisk,
  `WL 54 (1925): 104*`, and article ranges read "79*–97*". This is set in
  `tools/page_overrides.json` (`"mark": "*"`) and explained in the QA report.
- **Numbers the printer skipped.** Vol. 54 no. 3 goes from p. 322 to p. 333 on
  consecutive leaves, and the text runs on mid-sentence ("27 different religious /
  orders"). Nothing is missing. Where the next leaf continues a sentence, the report
  now lists such a jump as a printer's skip, not as a pagination gap.
- **Misprinted numbers.** Vol. 53 no. 3 prints 341–345 for 441–445 (checked on the
  scan; IA copied the misprint). The pages are numbered in sequence, and the override
  file records the check.
- **Closing pages of a Supplement.** The last two pages of the Ledóchowski letter
  (vol. 50, Suppl. xxix–xxx) carry no number. A separately paginated section has no
  next issue to leave room for, so its unnumbered closing pages now go on in sequence
  instead of becoming inserts. This also makes the Note closing vol. 30's Supplement
  "Suppl. xx".
- **Advertisements bound mid-issue.** Two unnumbered leaves of publisher's
  advertisements between pp. 282 and 283 (vol. 50 no. 3) had been numbered 283, 282.
  Unnumbered leaves between two read pages that follow on directly are now inserts.

Index and articles:

- **Vol. 54 has a contents list, not an index.** "CONTENTS OF VOL. LIV." at the front
  of no. 1 is read as the index. It is set in two columns, and the OCR puts the
  OBITUARY and VARIA headings after the first line of their blocks. A heading now
  takes the line just before it when that line runs several entries of its own kind
  together (persons for OBITUARY, none for VARIA); vols. 39 and 48 keep theirs.
- **Index entries closed by full stops** ("Fr. Joseph F. Hanselman, 382. Fr. Edward J.
  McGrath, 266.", from vol. 52): vol. 52's index had lost its obituaries and all its
  Varia. "in" and "Ill" at a line's end are read as 111.
- **A heading is never joined to the line before.** "Fr. Joseph Zwinge, in" (111) ends
  in "in", so VARIA was joined to it and vol. 51's Varia entries became obituaries.
- **Later pages of an index entry.** A serial's later parts and each issue's "Books of
  Interest to Ours" are listed as later pages of one entry ("Russian Diary, Notes from
  a … 54, 63, 206"). An article on such a page now takes the entry, and its author,
  when the title shares two words with it. This links 57 articles in vols. 29–49 that
  had shown "not in volume index", among them the serial parts of Zwinge's "Jesuit
  Farms in Maryland", Emerick's "Colored Mission" and Thompkins's "Notes from Vigan".
- **Supplement half-title on a leaf of its own** (vol. 50: "SUPPLEMENT / A NATIVE CLERGY
  IN OUR FOREIGN MISSIONS" on an otherwise empty leaf): the Supplement now opens under
  that title on its first text page. It had been swallowed by the Varia (p. "214–30").
- **Masthead:** "VOIv. LIII, No. I" is recognised as the volume line (vol. 53 had
  opened with an article titled "Voiv. Liii, No. I").
- **A running head that repeats the page's own heading** no longer splits an article
  whose title the index has replaced (vol. 52 "Some Impressions", p. 2).

Repairs: `6`→`ó` in the Spanish ending -ón ("Le6n" → León, "Raz6n" → Razón, formerly
"Leén"); `6`→`e` where that gives a common English word ("th6" → the, formerly "thé");
ordinals with 1 read as i or l and 0 as o ("io6th" → 106th, "i6tli" → 16th, eleven
more in vols. 30–50).

Seams checked and left as they are (blank versos at issue ends): vol. 52 p. 174,
vol. 53 p. 156.

Rebuilt vols. 29–49: pages unchanged except vol. 30 (Suppl. xx, above).

### Vols. 55–59: what the batch found

Per volume: 55 (1926) 53 articles, 515 pages, 21 repairs; 56 (1927) 31, 484, 7;
57 (1928) 40, 563, 13; 58 (1929) 40, 724, 16; 59 (1930) 33, 460, 9. These are the last
volumes before the public-domain cutoff (1930); vols. 60–98 stay catalogue-only.

Pagination:

- **The printer's erratum in vol. 55 no. 3.** A slip after p. 440 reads "From page 440
  to the end of the volume the page numbers are exactly 100 less than they should be".
  The pages are numbered as it directs (442–517 for the printed 342–417). The volume
  index cites the misprinted numbers ("Donlon 341"), so its Obituary and Varia entries
  in pp. 340–417 are moved up by 100 (`index_add` in `tools/page_overrides.json`).
  This splits five obituaries out of Donlon's notice.
- **A section with asterisked folios** (vol. 56 no. 1): the McDonough sketch, the
  Campbell notice, the Varia and the statistics run *1–*92 after p. 112. They are cited
  with the asterisk, `WL 56 (1927): 35*`, the form accepted for vol. 54. Its opening page,
  whose number the OCR read as "8", is now part of the section.
- **Half-titles on leaves of their own** ("VARIA", "Yearly Statistics and Records",
  vol. 57) and short table pages (vol. 59 p. 189) had been taken for plates. Where the
  numbers on either side leave room for exactly the leaves between, they are pages.
  A short leaf under a running head is never demoted to a plate ("STATISTICS 111" is
  p. 177, vol. 57; checked on the scan).
- **Unnumbered tables at an issue's end**, after blank leaves, are pages when the next
  issue leaves room for exactly the blanks and them (vol. 59 no. 1: 191, blank, two
  tables, no. 2 at 195). When it does not, as in vol. 57 no. 1 (177, blank, two
  fold-outs, no. 2 at 179; checked on the scan), they are left out like plates. The
  volume's last issue, which no issue follows, keeps a closing leaf headed like the page
  before it (vol. 55: "VARIA", pp. 516–517).
- **A bug in the old next-issue rule**: two unnumbered pages at an issue's end were
  numbered 333, 335. No earlier volume was affected.

Index and articles:

- **The index from vol. 57** is headed in arabic figures ("INDEX TO VOLUME 57") and
  gives issue and page in two columns ("No. Page"): "Biblical Institute in Jerusalem,
  The by Father William H. McClellan 1 1". The last number is the page, and the author
  follows "by". The column furniture ("2 INDEX", "No. Page") is skipped. "OBITUARIES" and
  "INDEX VARIA" open their sections, and headings of every issue, "Books of Interest to
  Ours I. 126; II, 424; III, 620", give all their pages.
- **The blackletter masthead** (from vol. 57) comes out of the OCR as "tKfje WoobJStotfe
  Hetters!" or "MWMfMfMfJiJM" between rules of ornament. On an issue's first page all is
  dropped down to the legible VOL line, provided what stands above it is unreadable (vol.
  49 keeps THE GOLDEN JUBILEE).
- **Two-line titles**: a running head that repeats a title's second line ("THE CATHOLIC
  ASSOCIATION OF / COMMERCIAL TRAVELLERS", vol. 59) no longer splits the article. This
  also joins vol. 32 p. 175 ("At Eastern Penitentiary") to the article it continues.

Repairs:
- `tl` → `tt` before `tl` → `ct`, in words of five letters or more ("letler" → letter,
  formerly "lecter"; "litlle" → little).
- `dl` → `ct` no longer makes an -ing word of a name ("Moedling" and "Modling" had become
  "Moecting" and "Mocting").
- `ii` → `il` gives way where `ii` → `u` is commoner ("diily" is no longer "dilly").

Seams checked and left as they are: vol. 57 p. 178 (blank); vol. 59 pp. 193–194 are
tables before no. 2 at p. 195, and pp. 304–306 are a blank verso, the title leaf of
no. 3 and a blank.

Rebuilt vols. 29–54: pages unchanged; articles unchanged except vol. 32 p. 175.

## Open issues

- **Vol. 32 has no no. 3 and no index** in the Internet Archive collection
  (items `woodstockletters3211unse`, `woodstockletters3332unse`, the second
  catalogued by IA as "v.33[ie.32]"). Authors in vol. 32 come from signatures only.
- **Citation form for Supplements and inserts** (`WL 30 (1901): Suppl. vii`,
  `WL 30 (1901): insert after p. 332`) needs a decision before it goes into the
  editorial notes.
- Index lines that wrap onto the next line are joined when the continuation starts in
  lower case (since vols. 40–44). Wraps that go on in capitals still lose their page
  number (vol. 29: two entries; vol. 30: the article at p. 94 is titled "J- Ryan", and
  two "Society in …" entries come out as p. 190).
- One-off titles left as they are: vol. 30 p. 353 "A. M. D. G. Et B. V. M. H"
  (a dedication line), vol. 34 p. 30 (garbled OCR), vol. 31 pp. 352–353 (Digmann's
  mission among the Dakota, probably one article in two); vol. 36 p. 1 "Ibt Memory";
  vol. 38 p. 178 "The Ea K 7 Ho Ua Ke" (the Sicilian earthquake, split from p. 177)
  and p. 192 "Fl00t> Anb Gospel" (continues p. 189); vol. 39 p. 102 (two index
  entries run together) and p. 398 "Fa Ther Pa Trick Cle a Son".
- Index entries in inverted form become titles where the page heading is not in
  capitals ("Innsbruck, The Golden Jubilee of", "Kenny Father, Letter of").
- Undecided repairs, left as made: `supped` → `slipped`, `miilenium` → `millenium` (vol. 39).
- Latin and Romance words repaired as English, once each (vols. 40–44): `Indiis` → Indus,
  `iusta` → insta, and `Loius` → Loins (for Louis). There is no narrower rule
  that keeps the correct repairs of the same kind ("iucluding" → including).
- Vol. 43 p. 1 and vol. 39 p. 1: the Curia articles are split at their subheadings
  ("Habitat of the Curia", "Of Father General").
- Vols. 45–49, left as they are: vol. 45 p. 360 "Fordtlam" splits the Fordham history
  (the running head misread); vol. 45 p. 30 and p. 371 have garbled titles; vol. 47
  p. 372, Mr. Hawkins's obituary, is not split (the index is a page out and his name is
  not set as a heading); vol. 49 no. 1, the Jubilee number, keeps "The Scientific Academy"
  as one piece over pp. 48–99, since its index entries ("Theological Disputation 23",
  "Banquet, Addresses 85") name pages without headings.
- Vols. 50–54, left as they are:
  - vol. 50: p. 18 "Silver Jubllkk" and p. 304 "Detroit Uxivrrsitv" (the latter continues p. 303);
  - vol. 51: p. 64 "Pj?03f Fields Afar" (continues p. 36);
  - vol. 53: p. 385 "Father John F. Quirk", whom the index puts at p. 391;
  - vol. 54: no. 2's "Father Himmel as a Missioner" and the philosophers' conference
    stand at pp. 103* and 112*, where the contents gives 111 and 103;
  - vol. 54: the In Memoriam of Fr. Woods ("June, No. 2") is bound at the end of no. 1
    as two unnumbered leaves, kept as inserts after p. 161;
  - vol. 51: `dalcy` → daley, half of the hyphenated "Martin-dale".
- The asterisk citation is accepted (2026-09-25): `WL 54 (1925): 104*` for vol. 54 no. 2 and
  `WL 56 (1927): 35*` for the asterisked section of vol. 56 no. 1. It should go into the
  editorial notes; the Supplement and insert forms are still to be decided.
- Vols. 55–59, left as they are:
  - vol. 58: pp. 606–607 "Gog Photograpiiinc the Eclipse" and "Atcebu, P. I" split Deppermann's
    eclipse article (p. 604), and p. 382 "Hevision of Studrss" splits the Veruela article
    (p. 377): misread running heads;
  - vol. 59 p. 171 "St Ati St Ics" (STATISTICS in spaced capitals);
  - vol. 57 p. 476: the Father General's address to the Procurators, printed within the
    Varia, opens an article that runs on through the rest of the Varia to p. 566;
  - vol. 59 no. 3's Weston College entry is indexed at p. 317, but the article is at p. 217;
  - repairs: `Baius` → Bains (vol. 58, the theologian), `Ciirls` → Curls (vol. 59, for
    Girls), `rning` → ming and `perrn` → perm (vol. 57, both garbled beyond reading).
- Vol. 45 no. 2 and vol. 49 no. 1 differ from IA's page labels (see the table); ours are
  checked on the scans. The IA labels are not corrected upstream.
- Tables (mission statistics, retreat lists) are kept as paragraphs of OCR text where
  they sit on numbered pages; unnumbered fold-out tables are left out like plates.
- Latin passages are not repaired except for the ligature rules, because the frequency gate is English.
- Search and the concordance moved to Pagefind (2026-09-25). The concordance's
  distribution now counts pages with a match rather than hits, and its lines load
  50 pages at a time; words are matched with their inflected forms.
