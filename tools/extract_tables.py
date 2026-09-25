"""Pull the journal's recurring statistical tables out of the raw OCR into
data/tables/ and register them in data/tables.json.

The tables (Ministeria spiritualia of every house, students in the colleges
of the United States and Canada, the list of the dead, the colleges in the
United States) are mostly printed on unnumbered fold-out leaves, which the
volume build leaves out like plates. This tool finds those leaves by their
headings, keeps their OCR text line by line (data/tables/*.txt), and makes a
best-effort CSV of each: a row is a label followed by the run of numbers the
OCR read on that line. Column headers of a fold-out are usually read as a
jumble, so the CSV gives the numbers in the order printed and the scan is
one click away for the columns' meaning. Nothing is corrected by hand here.

  python tools/fetch_ia.py --from 1 --to 59
  python tools/extract_tables.py
"""
import csv
import gzip
import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
OUT = ROOT / "data" / "tables"

KINDS = [
    ("ministeria", re.compile(r"MINISTERIA\s+SPIRITUALIA", re.I), "Ministeria spiritualia"),
    ("students", re.compile(r"STUDENTS\s+IN\s+(?:OUR\s+)?(?:COLLEGES|HIGH\s+SCHOOLS)|UNIVERSITY,?\s+COLLEGE\s+AND\s+HIGH\s+SCHOOL\s+REGISTRATION", re.I), "Students in our colleges"),
    ("colleges", re.compile(r"OUR\s+COLLEGES\s+IN\s+THE\s+UNITED\s+STATES", re.I), "Our colleges in the United States"),
    ("dead", re.compile(r"LIST\s+OF\s+OUR\s+DEAD", re.I), "List of our dead"),
]
NUMTOK = re.compile(r"^[\d,.]*\d[\d,.]*$")


def numrow(line):
    """A label followed by a run of numbers: split on whitespace and take the
    trailing numeric tokens (no regex over the whole line: a long line of
    digits made the earlier pattern backtrack for minutes)."""
    toks = line.split()
    n = 0
    while n < len(toks) and NUMTOK.match(toks[-1 - n]):
        n += 1
    if n == 0 or n == len(toks):
        return None
    label = " ".join(toks[:-n])
    if not re.search(r"[A-Za-z]", label):
        return None
    return label.strip(" .,"), [t.strip(",.") for t in toks[-n:]]


def clean(s):
    s = s.replace("�", "—")
    s = re.sub(r"[ \t]+", " ", s).strip()
    return s


def year_in(text):
    m = re.search(r"\b(18[7-9]\d|19[0-3]\d)\b", text)
    return int(m.group(1)) if m else None


def main():
    cat = json.loads((ROOT / "data" / "catalogue.json").read_text(encoding="utf-8"))
    man = json.loads((ROOT / "data" / "manifest.json").read_text(encoding="utf-8"))
    built = {v["vol"] for v in man["volumes"]}
    # is the leaf a numbered text page of the edition (the table sits in the
    # text as OCR paragraphs) or a fold-out the text leaves out?
    kind_of = {}
    for n in built:
        v = json.loads((ROOT / "data" / "vol" / f"{n:03d}.json").read_text(encoding="utf-8"))
        for pg in v["pages"]:
            kind_of[(pg["issue"], pg["leaf"])] = (pg["kind"], pg.get("p"))
    OUT.mkdir(parents=True, exist_ok=True)
    reg = []
    for iss in cat["issues"]:
        if iss["vol"] not in built:
            continue
        ident = iss["id"]
        try:
            idx = json.load(gzip.open(RAW / f"{ident}_hocr_pageindex.json.gz"))
            text = gzip.open(RAW / f"{ident}_hocr_searchtext.txt.gz").read().decode("utf-8")
            shown = json.loads((RAW / f"{ident}_page_numbers.json").read_text(encoding="utf-8"))["pages"]
        except FileNotFoundError:
            print("raw missing:", ident)
            continue
        viewer = {p["leafNum"]: j for j, p in enumerate(shown)}
        for k, (a, b, *_) in enumerate(idx):
            lines = [clean(x) for x in text[a:b].split("\n")]
            lines = [x for x in lines if x]
            head = " ".join(lines[:4])
            kind = next(((key, label) for key, rx, label in KINDS if rx.search(head)), None)
            if not kind or len(lines) < 8:
                continue
            key, label = kind
            rx0 = next(rx for key2, rx, _ in KINDS if key2 == key)
            # a text page that merely mentions the students in our colleges is
            # not a table: on a numbered page the heading must open the leaf
            pk0 = kind_of.get((ident, k), ("?", None))[0]
            if pk0 == "text" and not rx0.search(" ".join(lines[:2])):
                continue
            name = f"{iss['vol']:03d}-{ident}-leaf{k}"
            (OUT / f"{name}.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
            rows = []
            rx = next(rx for key2, rx, _ in KINDS if key2 == key)
            for ln in lines:
                m = numrow(ln)
                if m and not rx.search(ln):  # the heading line is not a row
                    rows.append([m[0]] + m[1])
            with open(OUT / f"{name}.csv", "w", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                w.writerow(["label"] + [f"n{i}" for i in range(1, max((len(r) for r in rows), default=1))])
                w.writerows(rows)
            pk, pp = kind_of.get((ident, k), ("?", None))
            reg.append({"vol": iss["vol"], "year": iss["year"], "issue": ident, "no": iss["no"], "leaf": k, "n": viewer.get(k),
                        "where": f"p. {pp}" if pk == "text" and pp else "fold-out",
                        "kind": key, "title": label, "heading": head[:140], "span": year_in(head), "lines": len(lines),
                        "rows": len(rows), "file": name})
            print(f"vol {iss['vol']} {ident} leaf {k}: {label} ({len(lines)} lines, {len(rows)} numeric rows)")
    reg.sort(key=lambda r: (r["kind"], r["vol"], r["leaf"]))
    (ROOT / "data" / "tables.json").write_text(json.dumps({
        "note": "Statistical tables of the journal as OCR text and best-effort CSV; columns are not identified, see the scan. Built by tools/extract_tables.py.",
        "kinds": {k: label for k, _, label in KINDS},
        "tables": reg}, ensure_ascii=False, indent=1), encoding="utf-8")
    print(len(reg), "tables ->", OUT.relative_to(ROOT))


if __name__ == "__main__":
    main()
