"""Build data/vol/NNN.json for one Woodstock Letters volume from the raw
IA OCR in data/raw/ (fetch it first with tools/fetch_ia.py).

What the build does, in order:
  1. reads each issue leaf by leaf (IA hOCR page index);
  2. strips running heads, recording the head title and the printed page
     number they carry;
  3. assigns printed page numbers by consensus, because single OCR digits
     are unreliable ("40" for 49, "4fi" for 46): every text leaf gets
     its running position plus the median offset of its neighbours;
  4. finds article starts (title block at the top of an unheaded page, or
     an upper-case line mid-page that the following running heads repeat);
  5. repairs the OCR conservatively (hyphenation, the ct-ligature misread
     as "6l"/"dl", a few recurrent confusions), checked against an English
     frequency list and the volume's own vocabulary, and logs every
     change to docs/qa/volNNN.md;
  6. reads the volume index (issue 1 front matter) and takes authors from
     it by start page, falling back to an end signature "..., S. J.".

Copyright guard: full text is only written for volumes whose every issue
is in the US public domain (published before 1 Jan of the current year
minus 95). Anything later is refused; see RIGHTS.md.

  python tools/build_volume.py 29
"""
import datetime
import difflib
import gzip
import json
import pathlib
import re
import statistics
import sys
from collections import Counter

from wordfreq import zipf_frequency

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
OUT = ROOT / "data" / "vol"
QA = ROOT / "docs" / "qa"

PD_CUTOFF = datetime.date.today().year - 96  # 2026 -> 1930 inclusive

MASTHEAD = re.compile(
    r"^(A\.?\s*M\.?\s*D\.?\s*G\.?|THE|WOODSTOCK\s+LETTERS\.?|VOL\.?\s*[XVLI]+\.?\s*(No\.?\s*\w+\.?)?)$",
    re.I)
# Printer's signature at the foot of a sheet: "Vol. XXIX. No. i. 2"
SIGNATURE = re.compile(r"\s*Vol\.\s*[XVLI]+\.\s*No\.\s*\w{1,2}\.\s*[\dIl ]{1,4}\s*(\(\d+\))?$")


def pageish(tok):
    """Does an OCR token in a running head stand for a page number? The
    digits are often mangled ("Ill" for 111, "S4t", "15»"), so accept a
    short token with a digit, or one made only of digit look-alikes."""
    t = re.sub(r"^\W+|\W+$", "", tok)
    if not t or len(t) > 4:
        return not t and 0 < len(tok) <= 3  # pure junk like "\^" in a head
    return any(c.isdigit() for c in t) or (len(t) >= 2 and all(c in "lI1|" for c in t))


def digits(tok):
    """Read a page number from an OCR token; None when unreadable."""
    t = re.sub(r"^\W+|\W+$", "", tok)
    if not t:
        return None
    t = t.translate(str.maketrans("ilI|oOSsg", "111100559", "f"))
    return int(t) if t.isdigit() else None


def is_upper(s):
    letters = [c for c in s if c.isalpha()]
    return len(letters) >= 3 and sum(c.isupper() for c in letters) / len(letters) >= 0.75


def norm_head(s):
    return re.sub(r"[^A-Z]", "", s.upper())


def clean_line(s):
    s = s.replace("�", "—")  # the OCR's unmappable dash
    s = re.sub(r"[ \t]+", " ", s).strip()
    s = re.sub(r" ([,;:.!?])", r"\1", s)
    return s


# ---------------------------------------------------------------- reading

def read_issue(ident):
    idx = json.load(gzip.open(RAW / f"{ident}_hocr_pageindex.json.gz"))
    text = gzip.open(RAW / f"{ident}_hocr_searchtext.txt.gz").read().decode("utf-8")
    # The hOCR has one entry per scanned leaf; the IA viewer skips some
    # (colour cards, covers), so its page index n is the leaf's position in
    # _page_numbers.json. Verified in the viewer: vol. 29 no. 1, leaf 14 = n11 = p. 2.
    shown = json.loads((RAW / f"{ident}_page_numbers.json").read_text(encoding="utf-8"))["pages"]
    viewer = {p["leafNum"]: j for j, p in enumerate(shown)}
    label = {p["leafNum"]: p["pageNumber"] for p in shown}
    leaves = []
    for k, (a, b, *_) in enumerate(idx):
        lines = [clean_line(x) for x in text[a:b].split("\n")]
        leaves.append({"leaf": k, "n": viewer.get(k), "ia": label.get(k) or None,
                       "lines": [x for x in lines if x]})
    return leaves


def split_head(lines):
    """Return (head_title, page_candidate, body_lines)."""
    if not lines:
        return None, None, lines
    l0 = lines[0]
    l1 = lines[1] if len(lines) > 1 else ""
    # "N" / "TITLE"  or  "TITLE" / "N"  or a bare "N" (tables, lists)
    if pageish(l0) and " " not in l0 and is_upper(l1) and len(l1) < 90:
        return l1, digits(l0), lines[2:]
    if is_upper(l0) and len(l0) < 90 and pageish(l1) and " " not in l1:
        return l0, digits(l1), lines[2:]
    # "N TITLE" or "TITLE N" on one line
    m = re.match(r"^(\S{1,5})\s+(.+)$", l0)
    if m and pageish(m[1]) and is_upper(m[2]) and len(m[2]) < 90:
        return m[2], digits(m[1]), lines[1:]
    m = re.match(r"^(.+?)\s+(\S{1,5})$", l0)
    if m and pageish(m[2]) and is_upper(m[1]) and 4 < len(m[1]) < 90:
        return m[1], digits(m[2]), lines[1:]
    if pageish(l0) and " " not in l0 and len(l0) <= 5:
        return "", digits(l0), lines[1:]
    return None, None, lines


def foot_number(lines):
    """Article-opening pages carry their number at the foot: "(6)"."""
    if lines:
        m = re.search(r"\((\S{1,4})\)$", lines[-1])
        if m:
            return digits(m[1])
    return None


# ------------------------------------------------------------- pagination

def number(leaves):
    seq = [lf for lf in leaves if lf["text"]]
    offs = [(i, lf["cand"] - i) for i, lf in enumerate(seq) if lf["cand"] is not None]
    for lf in leaves:
        lf["page"] = None
    for i, lf in enumerate(seq):
        near = sorted(offs, key=lambda o: abs(o[0] - i))[:7]
        lf["page"] = i + int(statistics.median(o[1] for o in near)) if near else None


def paginate(leaves):
    for lf in leaves:
        head, cand, body = split_head(lf["lines"])
        foot = foot_number(body)
        lf.update(head=head, cand=cand if cand is not None else foot, body=body)
        lf["chars"] = chars = sum(len(x) for x in body)
        lf["text"] = (head is not None and chars > 250) or chars > 700
    number(leaves)
    # Round two. A short leaf whose number disagrees with its place is a
    # plate with a numbered caption; a short leaf caught between pages whose
    # numbers jump by two is a real page (a brief opening, a table).
    changed = False
    for lf in leaves:
        if lf["text"] and lf["chars"] < 500 and lf["cand"] != lf["page"]:
            lf["text"], changed = False, True
    for k in range(1, len(leaves) - 1):
        a, b, c = leaves[k - 1], leaves[k], leaves[k + 1]
        if (not b["text"] and b["chars"] > 150 and a["text"] and c["text"] and a["page"]
                and c["page"] == a["page"] + 2):
            b["text"], changed = True, True
    if changed:
        number(leaves)
    for lf in leaves:
        if not lf["text"]:
            lf["kind"], lf["page"] = ("plate" if lf["body"] else "blank"), None
        elif lf["page"] is None or lf["page"] < 1:
            lf["kind"], lf["page"] = "front", None
        else:
            lf["kind"] = "text"
    # disagreements are worth a look in the QA report
    return [(lf["leaf"], lf["cand"], lf["page"]) for lf in leaves
            if lf["kind"] == "text" and lf["cand"] is not None and lf["cand"] != lf["page"]]


# -------------------------------------------------------------- OCR repair

class Repair:
    # (misread, reading, where): "any" anywhere in the word, "start" only
    # word-initially, a number = only in words at least that long
    SUBS = [("6l", "ct", "any"), ("dl", "ct", "any"), ("6t", "ct", "any"), ("(5t", "ct", "any"),
            ("fi", "ff", "any"), ("iu", "in", "any"), ("rn", "m", "any"), ("tl", "ct", "any"),
            ("I^", "L", "any"), ("ly", "L", "start"), ("ii", "u", 6), ("ii", "il", 5),
            ("u", "li", 6), ("c", "e", 5), ("aa", "m", 5), ("7i", "n", "any")]

    def __init__(self, vocab):
        self.vocab = vocab
        self.log = Counter()

    def known(self, w):
        # wordfreq splits "I^ent" into tokens and scores the pieces, so only
        # clean alphabetic words may count as known
        if not re.fullmatch(r"[A-Za-z']+", w):
            return False
        lw = w.lower()
        return zipf_frequency(lw, "en") >= 2.0 or self.vocab[lw] >= 3

    def word(self, w):
        core = w.lstrip("(")
        # a digit inside a word is never right: the ct ligature read as 6l
        if re.search(r"[A-Za-z](6l|6t|\(5t|c5t|c5l)|^0?6l", core) and re.search(r"[a-z]", core):
            fixed = re.sub(r"c5[tl]", "ct", core)
            fixed = re.sub(r"6l|6t|\(5t", "ct", re.sub(r"^06l", "Oct", fixed))
            self.log[(core, fixed)] += 1
            return w.replace(core, fixed)
        # é read as 6 in French and Spanish names: Algu6, Jos6, Fr6re, Elz6ar
        if re.fullmatch(r"[A-Za-z]{2,}6[a-z]{0,3}", core):
            fixed = core.replace("6", "é")
            self.log[(core, fixed)] += 1
            return w.replace(core, fixed)
        # the same ligature read as "dl" after a vowel: accept when the
        # reading is attested or ends like a -ct- word (action, rector ...)
        if re.search(r"[aeiou]dl", core) and zipf_frequency(core.lower(), "en") < 1.0:
            cand = re.sub(r"([aeiou])dl", r"\1ct", core)
            if (zipf_frequency(cand.lower(), "en") >= 1.0
                    or re.search(r"ct(ion|ions|or|ors|ory|ure|ures|ive|ed|s|ly|ing)?$", cand)):
                self.log[(core, cand)] += 1
                return w.replace(core, cand)
        # only the frequency list vetoes a repair: a systematic misreading
        # ("fadl" for fact) is frequent in the volume's own vocabulary too
        if len(core) < 4 or not re.search(r"[a-z]", core) or (
                re.fullmatch(r"[A-Za-z']+", core) and zipf_frequency(core.lower(), "en") >= 2.0):
            return w
        for a, b, where in self.SUBS:
            if a not in core or (where == "start" and not core.startswith(a)) \
                    or (isinstance(where, int) and len(core) < where):
                continue
            cand = core.replace(a, b, 1)
            if re.fullmatch(r"[A-Za-z']+", cand) and zipf_frequency(cand.lower(), "en") >= 2.5:
                self.log[(core, cand)] += 1
                return w.replace(core, cand)
        return w

    def dehyphen(self, s):
        def join(m):
            a, b = m[1], m[2]
            whole = a + b
            if self.known(whole):
                return whole
            if self.known(a) and self.known(b):
                return f"{a}-{b}"
            return whole
        return re.sub(r"(\w+)- (\w+)", lambda m: join(m) if m[2][0].islower() else m[0], s)

    def para(self, s):
        s = SIGNATURE.sub("", s)
        # years split or misread by the OCR: "1 861", "i898", "i8gg", "i2mo"
        s = re.sub(r"\b1 ([5-9]\d\d)\b", r"1\1", s)
        s = re.sub(r"\b[iI]([0-9][0-9gqioIlOs]{0,3})(?=\b|th\b|mo\b|st\b|nd\b|rd\b)",
                   lambda m: "1" + m[1].translate(str.maketrans("gqioIlOs", "99101105")), s)
        s = self.dehyphen(s)
        return re.sub(r"[A-Za-z0-9^(]+", lambda m: self.word(m[0]), s)


# ----------------------------------------------------------- volume index

def parse_index(leaves):
    """Entries "Title — Author . 447" from the issue-1 front matter."""
    lines, on = [], False
    for lf in leaves:
        if lf["kind"] in ("text",):
            break
        for ln in lf["lines"]:
            if ln.upper().startswith("INDEX TO VOLUME"):
                on = True
                continue
            if on:
                lines.extend(re.split(r"(?<=\d)\s+(?=[A-Z][a-z])", ln))
    entries, section = [], "Articles"
    for ln in lines:
        if ln.rstrip(".").upper() in ("OBITUARY", "VARIA"):
            section = ln.rstrip(".").title()
            continue
        m = re.match(r"^(.*?[A-Za-z].*?)[\s.,—]*((?:\d{1,3},?\s*)+)$", ln)
        if not m:
            continue
        pages = [int(x) for x in re.findall(r"\d{1,3}", m[2])]
        body = m[1].strip(" .,—")
        parts = [p.strip(" .,") for p in body.split("—") if p.strip(" .,")]
        author = None
        if len(parts) > 1 and re.match(r"^(Fr|Br|Mr|Rev|Very|Leo)\b", parts[-1]):
            author = parts.pop()
        entries.append({"entry": " — ".join(parts), "author": author,
                        "pages": pages, "section": section})
    return entries


# --------------------------------------------------------------- articles

def title_case(s):
    small = {"a", "an", "and", "at", "by", "for", "in", "of", "on", "the", "to", "from", "with", "during"}
    words = s.lower().split()
    out = []
    for i, w in enumerate(words):
        if i and w in small:
            out.append(w)
        else:
            out.append(re.sub(r"^([^a-z]*)([a-z])", lambda m: m[1] + m[2].upper(), w))
    t = " ".join(out)
    t = re.sub(r"\b(S\.?\s*J|U\.?\s*S|N\.?\s*Y)\b\.?", lambda m: m[0].upper(), t, flags=re.I)
    return re.sub(r"\bMc([a-z])", lambda m: "Mc" + m[1].upper(), t).rstrip(".")


def build(vol):
    cat = json.loads((ROOT / "data" / "catalogue.json").read_text(encoding="utf-8"))
    issues = [i for i in cat["issues"] if i["vol"] == vol]
    if not issues:
        sys.exit(f"volume {vol} not in catalogue")
    if max(i["year"] for i in issues) > PD_CUTOFF:
        sys.exit(f"volume {vol} ({issues[-1]['year']}) is after the public-domain cutoff "
                 f"({PD_CUTOFF}); full text refused — see RIGHTS.md")

    report = [f"# QA report — volume {vol}\n"]
    raw_issues = []
    for iss in issues:
        leaves = read_issue(iss["id"])
        disagreements = paginate(leaves)
        raw_issues.append((iss, leaves))
        report.append(f"\n## {iss['id']} (no. {iss['no']})\n")
        report.append(f"- leaves: {len(leaves)}; text pages: {sum(l['kind'] == 'text' for l in leaves)}; "
                      f"plates: {sum(l['kind'] == 'plate' for l in leaves)}; front: {sum(l['kind'] == 'front' for l in leaves)}")
        pages = [l["page"] for l in leaves if l["kind"] == "text"]
        if pages:
            report.append(f"- printed pages {pages[0]}–{pages[-1]}")
            gaps = [(a, b) for a, b in zip(pages, pages[1:]) if b != a + 1]
            if gaps:
                report.append(f"- **pagination gaps**: {gaps}")
        # independent check: the IA's own page detection, where it has one
        labelled = [l for l in leaves if l["kind"] == "text" and (l["ia"] or "").isdigit()]
        differ = [l for l in labelled if int(l["ia"]) != l["page"]]
        report.append(f"- cross-check with the Internet Archive's page labels: {len(labelled) - len(differ)} "
                      f"of {len(labelled)} agree"
                      + (": **differ** " + ", ".join(f"leaf {l['leaf']} IA {l['ia']} / here {l['page']}"
                                                     for l in differ) if differ else ""))
        if disagreements:
            report.append("- OCR page numbers overruled by consensus (scan leaf: read → assigned): "
                          + ", ".join(f"leaf {k}: {c}→{p}" for k, c, p in disagreements))

    vocab = Counter()
    for _, leaves in raw_issues:
        for lf in leaves:
            for ln in lf["body"]:
                vocab.update(w.lower() for w in re.findall(r"[A-Za-z]+", ln))
    rep = Repair(vocab)

    index = parse_index(raw_issues[0][1])
    for e in index:
        e["entry"] = rep.para(e["entry"])
        if e["author"]:
            e["author"] = rep.para(e["author"])

    # 1. one flat stream of paragraphs; pages keep references into it
    pages_out, flat = [], []
    for iss, leaves in raw_issues:
        for lf in leaves:
            entry = {"issue": iss["id"], "leaf": lf["leaf"], "n": lf["n"], "kind": lf["kind"]}
            if lf["kind"] != "text":
                if lf["kind"] == "plate":
                    entry["caption"] = " ".join(lf["lines"])[:300]
                pages_out.append(entry)
                continue
            entry["p"] = lf["page"]
            entry["_head"] = norm_head(lf["head"] or "")
            body = list(lf["body"])
            while body and MASTHEAD.match(body[0]):  # the masthead opening each issue
                body.pop(0)
            paras = []
            for j, ln in enumerate(body):
                heading = is_upper(ln) and len(ln) < 120
                p = {"t": rep.para(ln)}
                if heading:
                    p["h"] = 1
                paras.append(p)
            # an unheaded page opening with a title block starts an article
            if lf["head"] is None and paras and paras[0].get("h"):
                paras[0]["start"] = "title-page"
            if paras and not paras[0].get("h") and re.match(r"^[a-z]", paras[0]["t"]):
                paras[0]["c"] = 1  # continues the previous page's paragraph
            entry["paras"] = paras
            pages_out.append(entry)
            flat.extend((entry, p) for p in paras)

    text_pages = [pg for pg in pages_out if pg["kind"] == "text"]

    def similar(a, b):
        if not a or not b:
            return False
        if len(a) > 6 and len(b) > 6 and (a in b or b in a):
            return True
        return difflib.SequenceMatcher(None, a, b).ratio() >= 0.75

    index_starts = {e["pages"][0] for e in index if e["pages"] and e["section"] != "Varia"}
    index_starts |= {pg["p"] for pg in text_pages if pg["paras"] and pg["paras"][0]["t"].rstrip(".").upper() in ("VARIA", "OBITUARY")}

    # 2. a title-page start that only repeats the running article is a
    #    continuation; a mid-page heading that the following running heads
    #    repeat (and the preceding ones do not) opens a new article
    for k, pg in enumerate(text_pages):
        before = [q["_head"] for q in text_pages[max(0, k - 2):k]]
        after = [q["_head"] for q in text_pages[k:k + 4]]
        for j, p in enumerate(pg["paras"]):
            if not p.get("h"):
                continue
            nh = norm_head(p["t"])
            if p.get("start") == "title-page" and (
                    any(similar(nh, b) for b in before)
                    or not (any(similar(nh, a) for a in after[1:]) or pg["p"] in index_starts)):
                del p["start"]
            elif (j > 0 and not p.get("start") and not pg["paras"][j - 1].get("h")
                  and any(similar(nh, a) for a in after) and not any(similar(nh, b) for b in before)):
                p["start"] = "running-head"

    # 3. the volume index names start pages; split where a named piece
    #    (above all the separate obituaries) begins mid-page
    stop = {"the", "and", "our", "father", "with", "from", "during", "letter", "society"}
    unmatched = []
    for e in index:
        if not e["pages"] or e["section"] == "Varia":
            continue
        pg = next((q for q in text_pages if q["p"] == e["pages"][0]), None)
        if pg is None:
            continue
        if any(p.get("start") for p in pg["paras"]):
            continue
        words = {w.lower() for w in re.findall(r"[A-Za-z]{4,}", e["entry"])} - stop
        hit = None
        for p in pg["paras"]:
            toks = [w.lower() for w in re.findall(r"[A-Za-z^<:]{4,}", p["t"])]
            if len(p["t"]) < 110 and any(difflib.get_close_matches(w, toks, 1, 0.75) for w in words):
                hit = p
                break
        if hit:
            hit["start"] = "index"
            hit["h"] = 1
            hit["_entry"] = e
        else:
            unmatched.append(e)

    # 4. assign paragraphs to articles
    articles, cur = [], None
    for i, (pg, p) in enumerate(flat):
        if (p.get("start") and cur is not None and pg["p"] - cur["p1"] <= 1
                and difflib.SequenceMatcher(None, norm_head(p["t"]), norm_head(cur["title"])).ratio() >= 0.75):
            p.pop("start")
        if p.get("start"):
            tl = [p["t"]]
            k = i + 1
            while k < len(flat) and flat[k][1].get("h") and not flat[k][1].get("start") and len(tl) < 4:
                tl.append(flat[k][1]["t"])
                k += 1
            aid = f"{vol}-{pg['p']:03d}"
            n = sum(1 for a in articles if a["id"].startswith(aid))
            cur = {"id": aid + (f"-{n + 1}" if n else ""),
                   "title": title_case(tl[0]), "subtitle": " · ".join(title_case(x) for x in tl[1:]) or None,
                   "author": None, "issue": pg["issue"], "p0": pg["p"], "p1": pg["p"], "how": p["start"]}
            if p.get("_entry") and not is_upper(p["t"]):
                cur["title"] = p["_entry"]["entry"]
            if cur["title"].upper() in ("OBITUARY", "VARIA") :
                cur["section"] = cur["title"].title()
                if cur["title"].upper() == "OBITUARY" and cur["subtitle"]:
                    cur["title"], _, rest = cur["subtitle"].partition(" · ")
                    cur["subtitle"] = rest or None
            articles.append(cur)
        if cur is not None:
            p["a"] = cur["id"]
            cur["p1"] = pg["p"]
        p.pop("start", None)
        p.pop("_entry", None)
    for pg in text_pages:
        pg.pop("_head", None)

    # 5. authors: volume index by start page, else an end signature
    for a in articles:
        cands = [e for e in index if e["pages"] and e["pages"][0] == a["p0"]]
        if cands:
            e = max(cands, key=lambda e: difflib.SequenceMatcher(
                None, norm_head(e["entry"]), norm_head(a["title"])).ratio())
            a["indexEntry"] = e["entry"]
            a.setdefault("section", e["section"])
            if a["title"] == "Obituary":
                a["title"] = e["entry"]
            if e["author"]:
                a["author"] = e["author"]
        if not a["author"]:
            body = [p for _, p in flat if p.get("a") == a["id"] and not p.get("h")]
            if body:
                m = re.search(r"^([A-Z][\w.' ]{3,40}),\s*S\.\s*J\.?$", body[-1]["t"].strip())
                if m:
                    a["author"] = m[1].strip()
                    a["authorFrom"] = "signature"

    OUT.mkdir(parents=True, exist_ok=True)
    out = {
        "vol": vol,
        "year": issues[0]["year"],
        "issues": [{"id": i["id"], "no": i["no"], "season": i["season"]} for i in issues],
        "articles": articles,
        "pages": pages_out,
        "index": index,
    }
    path = OUT / f"{vol:03d}.json"
    path.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

    report.append(f"\n## Articles ({len(articles)})\n")
    for a in articles:
        report.append(f"- p. {a['p0']}–{a['p1']}  **{a['title']}** [{a['how']}]"
                      + (f" — {a['author']}" if a["author"] else " — *no author*")
                      + ("" if a.get("indexEntry") else "  ⚠ not in volume index"))
    if unmatched:
        report.append(f"\n## Index entries without a detected article start ({len(unmatched)})\n")
        report.extend(f"- p. {e['pages'][0]} {e['entry']}" for e in unmatched)
    report.append(f"\n## OCR repairs ({sum(rep.log.values())})\n")
    report.extend(f"- `{a}` → `{b}` ×{n}" for (a, b), n in rep.log.most_common())
    QA.mkdir(parents=True, exist_ok=True)
    (QA / f"vol{vol:03d}.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    # the manifest lists the volumes that have full text on the site
    mpath = ROOT / "data" / "manifest.json"
    manifest = json.loads(mpath.read_text(encoding="utf-8")) if mpath.exists() else {"volumes": []}
    words = sum(len(p["t"].split()) for pg in pages_out for p in pg.get("paras", []))
    rec = {"vol": vol, "year": out["year"], "articles": len(articles),
           "pages": sum(pg["kind"] == "text" for pg in pages_out), "words": words,
           "built": datetime.date.today().isoformat()}
    manifest["volumes"] = sorted([v for v in manifest["volumes"] if v["vol"] != vol] + [rec],
                                 key=lambda v: v["vol"])
    mpath.write_text(json.dumps(manifest, indent=1), encoding="utf-8")
    kb = path.stat().st_size // 1024
    print(f"vol {vol}: {len(articles)} articles, {sum(p['kind'] == 'text' for p in pages_out)} pages, "
          f"{sum(rep.log.values())} repairs, {kb} KB -> {path.relative_to(ROOT)}")


if __name__ == "__main__":
    for v in sys.argv[1:]:
        build(int(v))
