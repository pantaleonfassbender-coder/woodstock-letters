"""Build data/general_index.json from the printed Woodstock Letters Index,
Volumes 1-80, 1872-1951, compiled by George Zorn, S.J. (Woodstock College
Press, 1960; Internet Archive woodstockletters1801unse).

The index was published in 1960 and is not in the public domain. What this
build takes from it are facts, which are not protected: the headings
(persons, places, things) and, for each, the volume and page references,
with the kind of reference the compiler marked (obituary, author, book
review, picture). The compiler's descriptive phrases are read to detect
those kinds and then discarded; none is published. See RIGHTS.md.

  python tools/fetch_ia.py --item woodstockletters1801unse   (or fetch by hand)
  python tools/build_general_index.py
"""
import gzip
import json
import pathlib
import re
from collections import Counter

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
ITEM = "woodstockletters1801unse"
OUT = ROOT / "data" / "general_index.json"

FIRST_LEAF, LAST_LEAF = 12, 365  # the alphabetical body; front matter before

ROMAN = re.compile(r"^[IVXLC]+$")
# a heading opens with a word in capitals of three letters or more (or "SS.")
HEAD = re.compile(r"(?:(?<=^)|(?<=[;.] )|(?<=\. ))([A-Z][A-Z'\-]{2,}(?:[ \-][A-Z][A-Z'\-]{2,})*)(?=[,.]? )")
REF = re.compile(r"\b(\d{1,2}),\s*(\d{1,3})\b(\s*ff)?")
KINDS = [("obit", re.compile(r"\(obit\.?\)|\bobit\b|\bdeath of\b|\bdied\b", re.I)),
         ("auth", re.compile(r"\(auth\.?\)", re.I)),  # only the compiler's explicit mark: the heading is the author
         ("rev", re.compile(r"\(bk\.?\s*rv\.?\)|book review", re.I)),
         ("pic", re.compile(r"\bpicture\b|\bportrait\b|opp\. p\.", re.I)),
         ("letter", re.compile(r"\bletters? (?:of|from)\b", re.I)),
         ("sketch", re.compile(r"\bsketch\b|\bbiog", re.I))]


def leaves():
    idx = json.load(gzip.open(RAW / f"{ITEM}_hocr_pageindex.json.gz"))
    text = gzip.open(RAW / f"{ITEM}_hocr_searchtext.txt.gz").read().decode("utf-8")
    for k, (a, b, *_) in enumerate(idx):
        if FIRST_LEAF <= k <= LAST_LEAF:
            yield k, text[a:b]


def clean(s):
    s = s.replace("�", "—")
    s = re.sub(r"(\w)- (\w)", r"\1\2", s)          # line-end hyphenation
    s = re.sub(r"[ \t]+", " ", s)
    return s.strip()


def page_text(raw):
    lines = [clean(x) for x in raw.split("\n")]
    lines = [x for x in lines if x]
    # drop running heads: a page number, "WOODSTOCK LETTERS", "INDEX", a single letter
    body = [x for x in lines if not re.fullmatch(r"\d{1,3}|WOODSTOCK LETTERS|INDEX|[A-Z]", x)]
    return " ".join(body)


def split_entries(text):
    """Cut the running text before every word in capitals of three letters or
    more that opens an entry (not preceded by a letter, not a roman numeral,
    not a cross-reference word). "ST. MARY'S" keeps its saint's prefix."""
    cuts = []
    for m in re.finditer(r"(?<![A-Za-z'\-])((?:S[ST]\.|MT\.|FT\.)? ?[A-Z][A-Z'\-]{2,})(?=[,.;: ]|$)", text):
        w = m.group(1)
        core = re.sub(r"^(?:S[ST]\.|MT\.|FT\.) ?", "", w)
        if ROMAN.match(core.replace("-", "")) or core in ("SEE", "ALSO", "OCR", "ABC", "III"):
            continue
        cuts.append(m.start())
    cuts.append(len(text))
    return [text[a:b].strip() for a, b in zip(cuts, cuts[1:]) if b > a]


def parse_entry(s):
    m = re.match(r"((?:S[ST]\.|MT\.|FT\.)? ?[A-Z][A-Z'\-]{2,})", s)
    if not m:
        return None
    head = m.group(1)
    rest = s[m.end():].lstrip(",. ")
    first = REF.search(rest)
    lead = rest[:first.start()] if first else rest
    lead = lead.split(";")[0]
    # the name part of the qualifier: up to the first comma, plus life dates
    # if the compiler gave them; the descriptive phrase after it is dropped
    # a person's entry: "AHERN, M. J. (auth.) Catholic Congress …" — the name
    # runs to the compiler's mark, else to the first comma
    mark = re.search(r"\((?:auth|obit|bk\.? ?rv)\.?\)", lead, flags=re.I)
    name = (lead[:mark.start()] if mark else lead).split(",")[0].strip(" ,")
    name = re.sub(r"\s+", " ", name)
    name = re.sub(r"\s+(?:[a-z]|\().*$", "", name)  # a phrase after the name is the compiler's, not kept
    if len(name) == 1:  # a lone initial is not a name
        name = ""
    dates = re.search(r"\((\d{4})\s*-\s*(\d{4})\)", lead)
    if dates:
        name = re.sub(r"\s*\(\d{4}\s*-\s*\d{4}\)", "", name).strip() + f" ({dates.group(1)}–{dates.group(2)})"
    if len(name) > 45:
        name = ""
    refs = []
    for part in re.split(r";\s*", rest):
        kinds = [k for k, rx in KINDS if rx.search(part)]
        for r in REF.finditer(part):
            v, p = int(r.group(1)), int(r.group(2))
            if 1 <= v <= 80 and 1 <= p <= 999:
                refs.append([v, p] + ([",".join(kinds)] if kinds else []))
    if not refs:
        return None
    h = " ".join(w.capitalize() if w.isupper() else w for w in head.split(" "))
    h = re.sub(r"'S", "'s", h).replace("Mc", "Mc")
    return {"h": h, "q": name, "refs": refs}


def main():
    entries, per_leaf = [], Counter()
    for k, raw in leaves():
        text = page_text(raw)
        for chunk in split_entries(text):
            e = parse_entry(chunk)
            if e:
                e["leaf"] = k
                entries.append(e)
                per_leaf[k] += 1
    # merge entries the OCR split (same heading and qualifier on the same leaf)
    merged = {}
    for e in entries:
        key = (e["h"], e["q"], e["leaf"])
        if key in merged:
            merged[key]["refs"].extend(e["refs"])
        else:
            merged[key] = e
    entries = list(merged.values())
    for e in entries:
        seen, uniq = set(), []
        for r in e["refs"]:
            if (r[0], r[1]) not in seen:
                seen.add((r[0], r[1]))
                uniq.append(r)
        e["refs"] = sorted(uniq, key=lambda r: (r[0], r[1]))
    n_refs = sum(len(e["refs"]) for e in entries)
    OUT.write_text(json.dumps({
        "source": "Woodstock Letters Index, Volumes 1-80, 1872-1951, compiled by George Zorn, S.J. (Woodstock College Press, 1960). Internet Archive woodstockletters1801unse. Headings and references only; the compiler's phrases are not reproduced.",
        "item": ITEM,
        "entries": entries,
    }, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"{len(entries)} entries, {n_refs} references, leaves {min(per_leaf)}–{max(per_leaf)} -> {OUT.relative_to(ROOT)}")
    kinds = Counter(k for e in entries for r in e["refs"] if len(r) > 2 for k in r[2].split(","))
    print("kinds:", dict(kinds))


if __name__ == "__main__":
    main()
