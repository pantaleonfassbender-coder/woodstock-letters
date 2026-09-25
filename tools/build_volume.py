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
  6. reads the volume index (wherever it is bound, even at the back of the
     previous volume) and takes authors from it by start page, falling back
     to an end signature "..., S. J.".

Separately paginated Supplements and unnumbered inserts keep their text and
carry a printed label ("Suppl. vii", "insert after p. 332") beside p.

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
INDEX_HEAD = re.compile(r"INDEX\s+TO\s+(?:THE\s+)?VOL\w*\.?\s+([XVLI]+)\b", re.I)


def roman(s):
    vals = [{"I": 1, "V": 5, "X": 10, "L": 50}[c] for c in s.upper()]
    return sum(-v if v < w else v for v, w in zip(vals, vals[1:] + [0]))


def roman_page(tok):
    """A roman page number standing alone ("vii", "XIV", "Ill" for iii,
    "11" for ii); None otherwise."""
    t = re.sub(r"^\W+|\W+$", "", tok).lower().translate(str.maketrans("1l|", "iii"))
    return roman(t) if t and len(t) <= 6 and re.fullmatch(r"x{0,3}(ix|iv|v?i{0,3})", t) else None


def to_roman(n):
    out = ""
    for v, s in [(40, "xl"), (10, "x"), (9, "ix"), (5, "v"), (4, "iv"), (1, "i")]:
        while n >= v:
            out, n = out + s, n - v
    return out


def index_like(lf):
    """Most lines of an index leaf end in a page number."""
    ls = [x for x in lf["lines"] if len(x) >= 5]
    return len(ls) >= 5 and sum(bool(re.search(r"\d{1,3}\.?$", x)) for x in ls) / len(ls) >= 0.4
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
    # a page number split by the OCR at either end of the head: "21 8 THE UNION",
    # "THE UNION OF OUR MISSIONS. 21 3", or on a line of its own: "1 68"
    l0 = re.sub(r"^(\d{1,2}) (\d)(?= [A-Z])", r"\1\2", lines[0])
    l0 = re.sub(r"(?<=[A-Z.] )(\d{1,2}) (\d)$", r"\1\2", l0)
    l0 = re.sub(r"^(\d) (\d\d)$|^(\d\d) (\d)$", lambda m: "".join(g for g in m.groups() if g), l0)
    l1 = lines[1] if len(lines) > 1 else ""
    l1 = re.sub(r"^(\d) (\d\d)$|^(\d\d) (\d)$", lambda m: "".join(g for g in m.groups() if g), l1)
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

def tabular(lf):
    ls = lf["lines"]
    return len(ls) >= 10 and sum(len(x) < 25 for x in ls) / len(ls) >= 0.6


def restarts(seq):
    """Positions where a separately paginated section begins: the opening
    page of a Supplement, or a leaf read as 1 followed closely by one read
    as 2."""
    return [i for i, lf in enumerate(seq) if i and ((lf.get("sup") and not seq[i - 1].get("sup")) or (
        lf["cand"] == 1 and any(q["cand"] == 2 for q in seq[i + 1:i + 3])))]


def number_run(seq):
    offs = [(i, lf["cand"] - i) for i, lf in enumerate(seq) if lf["cand"] is not None]
    if offs:
        # a dropped or misread digit ("21" for 218, "880" for 330, "180" for
        # 130) is far from every true number; such votes can outnumber the
        # good ones in a window of seven, so drop them before the median
        mid = statistics.median(o for _, o in offs)
        offs = [(i, o) for i, o in offs if abs(o - mid) <= 20]
    for i, lf in enumerate(seq):
        near = sorted(offs, key=lambda o: abs(o[0] - i))[:7]
        lf["page"] = i + int(statistics.median(o[1] for o in near)) if near else None
    # Within a stretch of consecutive scan leaves (no plate or blank between)
    # the numbering cannot jump, so the stretch takes its offset from its own
    # readings once transient misreads are dropped. The median of seven cannot
    # do this: vol. 38 reads 53–58 as "68 64 55 66 57 68", vol. 39 350–352 as
    # "360 361 362", and at a plate it blends the numbering of both sides.
    start = 0
    for end in range(1, len(seq) + 1):
        if end < len(seq) and seq[end]["leaf"] == seq[end - 1]["leaf"] + 1:
            continue
        runs = steady([(i, o) for i, o in offs if start <= i < end])
        # a lone reading is no evidence against the neighbours ("70" for 79 on a
        # leaf between two plates, vol. 33): only agreeing readings count
        if any(len(pos) > 1 for _, pos in runs):
            anchors = [(i, o) for o, pos in runs for i in pos]
            for i in range(start, end):
                seq[i]["page"] = i + min(anchors, key=lambda a: (abs(a[0] - i), a[0]))[1]
        elif (len(runs) == 1 and start and seq[start - 1]["page"] is not None
              and seq[start].get("blanks_before")
              and start + runs[0][0] == seq[start - 1]["page"] + 1 + seq[start]["blanks_before"]):
            # ... unless it is exactly what the blank pages before it make it
            for i in range(start, end):
                seq[i]["page"] = i + runs[0][0]
        start = end


def steady(votes):
    """Group (position, offset) votes into runs of one offset and drop the
    transient ones: a single vote beside a longer run, or a run between two
    runs that agree with each other (a misread tens digit, as in "360 361 362"
    between 349 and 353). What is left are the offsets the stretch really
    has; more than one means a page is missing from the scan there."""
    runs = []
    for i, o in votes:
        if runs and runs[-1][0] == o:
            runs[-1][1].append(i)
        else:
            runs.append((o, [i]))
    changed = True
    while changed and len(runs) > 1:
        changed = False
        for k, (o, pos) in enumerate(runs):
            prev = runs[k - 1] if k else None
            nxt = runs[k + 1] if k + 1 < len(runs) else None
            lone = len(pos) == 1 and any(r and len(r[1]) > 1 for r in (prev, nxt))
            sandwiched = prev and nxt and prev[0] == nxt[0] and len(pos) < len(prev[1]) + len(nxt[1])
            if lone or sandwiched:
                del runs[k]
                # merge the neighbours that now touch
                if 0 < k < len(runs) and runs[k - 1][0] == runs[k][0]:
                    runs[k - 1] = (runs[k - 1][0], runs[k - 1][1] + runs[k][1])
                    del runs[k]
                changed = True
                break
    return runs


def number(leaves):
    seq = [lf for lf in leaves if lf["text"]]
    for lf in leaves:
        lf["page"] = lf["restart"] = lf["insert"] = None
    # blank leaves are pages without text: number_run lets a lone reading
    # after them stand when it counts them (vol. 44 no. 3: 453, blank, 455)
    for a, b in zip(seq, seq[1:]):
        b["blanks_before"] = sum(leaves[j]["chars"] == 0 for j in range(a["leaf"] + 1, b["leaf"]))
    cuts = restarts(seq)
    for a, b in zip([0] + cuts, cuts + [len(seq)]):
        run = seq[a:b]
        number_run(run)
        # Unheaded, unnumbered leaves after the last numbered page of a run
        # have no page number of their own: a table (vol. 33 no. 3) is left
        # out like a plate; prose (vol. 30 no. 2, the Declaration of the
        # French Provincials, 4 leaves) is kept as an insert after that page.
        last = max((i for i, lf in enumerate(run) if lf["cand"] is not None), default=len(run))
        for lf in run[last + 1:]:
            if lf["head"] is None and lf["cand"] is None:
                if tabular(lf):
                    lf["text"], lf["page"] = False, None
                else:
                    lf["page"], lf["insert"] = run[last]["page"], True
    for i in cuts:
        seq[i]["restart"] = True


def paginate(leaves):
    for lf in leaves:
        head, cand, body = split_head(lf["lines"])
        foot = foot_number(body)
        lf.update(head=head, cand=cand if cand is not None else foot, body=body)
        lf["chars"] = chars = sum(len(x) for x in body)
        lf["text"] = (head is not None and chars > 250) or chars > 700
    # A leaf scanned twice (vol. 42 no. 1 repeats pp. 129–134 as leaves
    # 145–150) repeats the text of a leaf shortly before it: leave it out.
    sig = [re.sub(r"[^a-z]", "", " ".join(lf["body"]).lower())[:240] for lf in leaves]
    for k, lf in enumerate(leaves):
        if lf["text"] and len(sig[k]) > 120 and any(
                leaves[j]["text"] and not leaves[j].get("dup")
                and difflib.SequenceMatcher(None, sig[k], sig[j]).quick_ratio() > 0.9
                and difflib.SequenceMatcher(None, sig[k], sig[j]).ratio() > 0.9
                for j in range(max(0, k - 30), k)):
            lf.update(text=False, dup=True)
    # A Supplement closing an issue is paginated on its own (vol. 30 no. 1:
    # pp. i–xix; vol. 33 no. 3: pp. 1–7). Its leaves form their own run and
    # carry a label, so that "Suppl. vii" never collides with p. 7.
    s = next((k for k, lf in enumerate(leaves) if lf["head"] is None and lf["body"] and difflib.SequenceMatcher(
        None, norm_head(lf["body"][0]), "SUPPLEMENT").ratio() >= 0.75), None)
    if s is None:
        # A section paginated on its own without a SUPPLEMENT heading (vol. 41
        # no. 3 closes with a Documentum, pp. 1–14): the readings start again at
        # 2, 3 on consecutive pages after high numbers; its unnumbered opening
        # page is p. 1. It is named by its running head.
        tl = [k for k, lf in enumerate(leaves) if lf["text"]]
        for a, b in zip(tl, tl[1:]):
            # after a real run of pages: ten readings of 20 or more before it
            # (a year in the index heading, "1900", is not a run)
            if leaves[a]["cand"] == 2 and leaves[b]["cand"] == 3 and \
                    sum((leaves[k]["cand"] or 0) >= 20 for k in tl if k < a) >= 10:
                prev = tl[tl.index(a) - 1]
                s = prev if leaves[prev]["cand"] is None else a
                heads = Counter(norm_head(lf["head"]) for lf in leaves[s:] if lf["head"])
                if heads:
                    leaves[s]["suplabel"] = heads.most_common(1)[0][0].title()
                break
    if s is not None:
        sup = leaves[s:]
        leaves[s]["sup"] = "start"
        leaves[s]["suptitle"] = True  # opens an article, whatever its pagination
        for lf in sup[1:]:
            lf["sup"] = True
            lf["suplabel"] = leaves[s].get("suplabel")
        # roman numbers stand alone on the first line ("vii", "Ill" for iii)
        if sum(roman_page(lf["lines"][0]) is not None for lf in sup if lf["lines"]) >= 3:
            for lf in sup:
                lf["roman"] = True
                r = roman_page(lf["lines"][0]) if lf["lines"] else None
                if r is None:
                    continue
                if lf["head"] is None:  # not taken for a page number: drop it from the text
                    lf["body"] = lf["body"][1:]
                    lf["head"] = ""
                lf["cand"] = r
        # a half-title that says only SUPPLEMENT is a printed page: p. 1 of a
        # separate Supplement (vol. 37), or the next page of the issue (vol. 39)
        if len(leaves[s]["body"]) == 1:
            leaves[s].update(text=True, halftitle=True)
        # A Supplement that goes on with the issue's numbering (vol. 35: pp.
        # 319–341) is a section, not a pagination of its own: its pages read
        # higher than the last pages before it.
        before = [lf["cand"] for lf in leaves[:s] if lf["text"] and lf["cand"] is not None][-5:]
        mine = [lf["cand"] for lf in sup if lf["cand"] is not None]
        if before and mine and statistics.median(mine) > statistics.median(before):
            for lf in sup:
                lf["sup"] = lf["roman"] = None
    # A volume index is front matter, not numbered text, wherever the binder
    # put it: before no. 1, before no. 3 (vol. 31), or at the back of the
    # previous volume (the index to vol. 30 closes vol. 29 no. 3).
    k = 0
    while k < len(leaves):
        m = next((INDEX_HEAD.match(x) for x in leaves[k]["lines"][:3] if INDEX_HEAD.match(x)), None)
        if not m:
            k += 1
            continue
        v = roman(m[1])
        leaves[k].update(text=False, index=v)
        k += 1
        while k < len(leaves) and (index_like(leaves[k]) or leaves[k]["chars"] < 200):
            if index_like(leaves[k]):
                leaves[k].update(text=False, index=v)
            k += 1
    # Leaves before the masthead that opens the issue (a title leaf, a list of
    # books for sale: vol. 31 no. 2) are front matter. Only the first leaves
    # count: vol. 34 no. 1 opens with a Jubilee number and has its masthead
    # on p. 113. The printed cover repeats the masthead, so take the last one.
    mast = max((k for k, lf in enumerate(leaves[:15])
                if any(re.fullmatch(r"WOODSTOCK\s+LETTERS\.?", x, re.I) for x in lf["lines"][:4])), default=None)
    for lf in leaves[:mast or 0]:
        if lf["text"]:
            lf.update(text=False, front=True)
    number(leaves)
    # Round two. A short leaf whose number disagrees with its place is a
    # plate with a numbered caption; a short leaf caught between pages whose
    # numbers jump by two is a real page (a brief opening, a table).
    changed = False
    for lf in leaves:
        if lf["text"] and lf["chars"] < 500 and lf["cand"] != lf["page"] and not lf.get("halftitle"):
            lf["text"], changed = False, True
    # The same holds for a block of such leaves (tables, with blank pages among
    # them: vol. 35 pp. 317–318, vol. 39 pp. 299–301) when the numbering after
    # the block, or a reading inside it, leaves exactly that many pages.
    for k in range(len(leaves) - 1):
        a = leaves[k]
        if not a["text"] or not a["page"]:
            continue
        block = []
        for b in leaves[k + 1:k + 5]:
            if b["text"] or b.get("index") or b.get("front") or b.get("dup") or 0 < b["chars"] <= 150:
                break
            block.append(b)
        rest = leaves[k + 1 + len(block):]
        c = rest[0] if rest and rest[0]["text"] else None
        # c's own reading counts too: with the block left out, the consensus closes the gap
        fits = (c is not None and a["page"] + len(block) + 1 in (c["page"], c["cand"])) or \
            any(b["cand"] == a["page"] + m for m, b in enumerate(block, 1) if b["chars"] > 150)
        if block and fits:
            for b in block:
                if b["chars"] > 150:
                    b["text"], changed = True, True
    if changed:
        number(leaves)
    # Round three. Two leaves on one page number: an unheaded, unnumbered
    # short one is a plate with a long caption or an inscription (vol. 30:
    # "The Pulpit in St. Gudule", "Bonum pro nostris!"), not a page.
    for _ in range(3):
        seq = [lf for lf in leaves if lf["text"]]
        dup = [min((a, b), key=lambda lf: lf["chars"]) for a, b in zip(seq, seq[1:])
               if a["page"] is not None and a["page"] == b["page"] and not b["insert"]]
        dup = [lf for lf in dup if lf["head"] is None and lf["cand"] is None and lf["chars"] < 1200]
        if not dup:
            break
        for lf in dup:
            lf["text"] = False
        number(leaves)
    for lf in leaves:
        if lf.get("index") or lf.get("front"):
            lf["kind"], lf["page"] = "front", None
        elif lf.get("dup"):
            lf["kind"], lf["page"] = "duplicate", None
        elif not lf["text"]:
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
    # "rn" only in longer words: "Tirn-Tchou" is a place, not "Tim"
    SUBS = [("6l", "ct", "any"), ("dl", "ct", "any"), ("6t", "ct", "any"), ("(5t", "ct", "any"),
            # "iu" not in four-letter fragments ("sius" is Latin, not "sins")
            ("fi", "ff", "any"), ("iu", "in", 5), ("rn", "m", 5), ("tl", "ct", "any"),
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
        # (followed by a vowel, r, n, s, z, t or nothing: "tb6k" is noise)
        # (not before i: "distin6i" is the ct ligature; and not in a lower-case
        # string of digit look-alikes: "ij6o", "ipo6" are years)
        if re.fullmatch(r"[A-Za-z]{2,}6([aeournszt][a-z]{0,2})?", core) \
                and not re.fullmatch(r"[ilojgqpsy]+6[ilojgqpsy]*", core):
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
        # ü read as ii in German names: Miiller, Miinster (but Jesiiit is Jesuit)
        if core[0].isupper() and "ii" in core:
            cand = core.replace("ii", "ü", 1)
            if zipf_frequency(cand.lower(), "de") >= 3.0 and zipf_frequency(cand.lower(), "de") > \
                    zipf_frequency(core.replace("ii", "u", 1).lower(), "en"):
                self.log[(core, cand)] += 1
                return w.replace(core, cand)
        for a, b, where in self.SUBS:
            if a not in core or (where == "start" and not core.startswith(a)) \
                    or (isinstance(where, int) and len(core) < where):
                continue
            cand = core.replace(a, b, 1)
            # c→e must reach a common word: "wicrd" gave "wierd" (2.6), a
            # misspelling, where the text has "weird"
            gate = 3.0 if (a, b) == ("c", "e") and not core[0].isupper() else 2.5
            if re.fullmatch(r"[A-Za-z']+", cand) and zipf_frequency(cand.lower(), "en") >= gate:
                self.log[(core, cand)] += 1
                return w.replace(core, cand)
        return w

    def logged(self, old, new):
        self.log[(old, new)] += 1
        return new

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
        # and with the 9 read as g as well: "igo6", "igo7" (1906, 1907)
        s = re.sub(r"\b[iI]g[oO0]\d\b", lambda m: self.logged(m[0], "190" + m[0][-1]), s)
        # the ff ligature read as fi plus a quote: "stafi\" of", "Pontifi\",",
        # "Bufi\"alo", "Dufi'y" (a following 's is left alone)
        s = re.sub(r"[A-Za-z]*[a-z]fi(?:\"|'(?!s\b))[a-z]*",
                   lambda m: self.logged(m[0], re.sub(r"fi[\"']", "ff", m[0])), s)
        s = self.dehyphen(s)
        return re.sub(r"[A-Za-z0-9^(]+", lambda m: self.word(m[0]), s)


# ----------------------------------------------------------- volume index

def parse_index(leaves, vol):
    """Entries "Title — Author . 447" from the index leaves for volume vol
    (paginate() marks them with the volume their heading names)."""
    lines = []
    for lf in leaves:
        if lf.get("index") != vol:
            continue
        for ln in lf["lines"]:
            if INDEX_HEAD.match(ln):
                continue
            for piece in re.split(r"(?<=\d)\s+(?=[A-Z][a-z])", ln):
                # an entry too long for its line goes on in lower case on the
                # next ("Dead, List of Our, / in United States and Canada ... 191"):
                # join it, or the first half loses its page and the second
                # becomes an entry of its own
                if lines and re.match(r"[a-z]", piece) and not re.search(r"\d[.,]?$", lines[-1]):
                    lines[-1] += " " + piece
                else:
                    lines.append(piece)
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
    raw_issues, ranges = [], []
    paged = [(iss, read_issue(iss["id"])) for iss in issues]
    overruled = [paginate(leaves) for _, leaves in paged]
    # Unnumbered leaves after an issue's last readable page are inserts only
    # if the next issue leaves no room for them. Vol. 38 no. 1 ends with three
    # real pages whose numbers the OCR lost (156–158; no. 2 opens at p. 161);
    # the Declaration after p. 332 in vol. 30 has no room and stays an insert.
    for (_, leaves), (_, nxt) in zip(paged, paged[1:]):
        ins = [l for l in leaves if l["kind"] == "text" and l["insert"] and not l.get("sup")]
        first = next((l["page"] for l in nxt if l["kind"] == "text" and not l.get("sup")), None)
        if ins and first and first - ins[0]["page"] - 1 >= len(ins):
            for k, l in enumerate(ins):
                l["insert"], l["page"] = None, ins[0]["page"] + 1 + k
        # likewise a short closing page taken for a plate (vol. 38 no. 1, the
        # last page of the Varia, p. 159), when the next issue leaves room
        main = [l for l in leaves if l["kind"] == "text" and not l.get("sup") and not l["insert"]]
        if main and first and first - main[-1]["page"] > 1:
            nxt_leaf = next((l for l in leaves[leaves.index(main[-1]) + 1:] if l["kind"] != "blank"), None)
            if nxt_leaf and nxt_leaf["kind"] == "plate" and nxt_leaf["chars"] > 150 and not tabular(nxt_leaf):
                nxt_leaf.update(kind="text", page=main[-1]["page"] + 1)

    for (iss, leaves), disagreements in zip(paged, overruled):
        raw_issues.append((iss, leaves))
        report.append(f"\n## {iss['id']} (no. {iss['no']})\n")
        report.append(f"- leaves: {len(leaves)}; text pages: {sum(l['kind'] == 'text' for l in leaves)}; "
                      f"plates: {sum(l['kind'] == 'plate' for l in leaves)}; front: {sum(l['kind'] == 'front' for l in leaves)}")
        ins = [l for l in leaves if l["kind"] == "text" and l["insert"]]
        tl = [l for l in leaves if l["kind"] == "text" and not l["insert"]]
        main = [l["page"] for l in tl if not l.get("sup")]
        if ins:
            report.append(f"- unnumbered leaves kept as inserts ({len(ins)}): "
                          + ", ".join(f"leaf {l['leaf']} after {'Suppl. ' + to_roman(l['page']) if l.get('roman') else 'p. ' + str(l['page'])}"
                                      f" (*{(l['body'] or [''])[0][:40]}*)"
                                      for l in ins))
        if main:
            report.append(f"- printed pages {main[0]}–{main[-1]}")
            ranges.append((iss, main[0], main[-1]))
        sup = [l for l in tl if l.get("sup")]
        if sup:
            lab = (lambda p: to_roman(p)) if sup[0].get("roman") else str
            name = sup[0].get("suplabel")
            report.append(f"- separately paginated {name or 'Supplement'} from leaf {sup[0]['leaf']}: pp. "
                          f"{lab(sup[0]['page'])}–{lab(sup[-1]['page'])}, cited as “{name or 'Suppl.'} …”")
        dups = [l for l in leaves if l.get("dup")]
        if dups:
            report.append(f"- leaves scanned twice, left out: {', '.join(str(l['leaf']) for l in dups)}")
        gaps, blanks = [], []
        for a, b in zip(tl, tl[1:]):
            if b["page"] == a["page"] + 1 or b["restart"]:
                continue
            # a gap filled by blank leaves is blank pages (vol. 35 p. 318), not a fault
            n_blank = sum(l["kind"] == "blank" for l in leaves[a["leaf"] + 1:b["leaf"]])
            if b["page"] > a["page"] and n_blank >= b["page"] - a["page"] - 1:
                blanks.extend(range(a["page"] + 1, b["page"]))
            else:
                gaps.append((a["page"], b["page"]))
        if blanks:
            report.append(f"- blank pages (blank leaves in the scan): {', '.join(map(str, blanks))}")
        for l in tl:
            if l["restart"] and not l.get("sup"):
                report.append(f"- **numbering restarts at p. 1** at leaf {l['leaf']} without a Supplement "
                              f"heading: *{(l['body'] or [''])[0][:60]}*")
        if gaps:
            report.append(f"- **pagination gaps**: {gaps}")
        # independent check: the IA's own page detection, where it has one.
        # Its labels come from the same OCR, so a label out of step with the
        # IA's own neighbours (vol. 31 no. 3: 880 881 882 883 334) is the
        # IA's misreading, not ours; those are listed apart.
        labelled = [l for l in leaves if l["kind"] == "text" and not l.get("sup") and (l["ia"] or "").isdigit()]
        differ, ia_misread = [], []
        for j, l in enumerate(labelled):
            if int(l["ia"]) == l["page"]:
                continue
            near_agree = any(int(q["ia"]) == q["page"] for q in labelled[max(0, j - 5):j + 6])
            (ia_misread if abs(int(l["ia"]) - l["page"]) > 20 and near_agree else differ).append(l)
        report.append(f"- cross-check with the Internet Archive's page labels: {len(labelled) - len(differ) - len(ia_misread)} "
                      f"of {len(labelled)} agree"
                      + (": **differ** " + ", ".join(f"leaf {l['leaf']} IA {l['ia']} / here {l['page']}"
                                                     for l in differ) if differ else ""))
        if ia_misread:
            report.append(f"- IA labels out of step with the IA's own neighbours ({len(ia_misread)}; IA misread, "
                          "check the scan): " + ", ".join(f"leaf {l['leaf']} IA {l['ia']} / here {l['page']}"
                                                          for l in ia_misread))
        if disagreements:
            report.append("- OCR page numbers overruled by consensus (scan leaf: read → assigned): "
                          + ", ".join(f"leaf {k}: {c}→{p}" for k, c, p in disagreements))

    # the issues of a volume share one pagination; a blank closing page may
    # leave a gap of one, an overlap is always wrong
    seams = [(a["no"], hi, b["no"], lo) for (a, _, hi), (b, lo, _) in zip(ranges, ranges[1:]) if lo != hi + 1]
    report.insert(1, "\nIssue seams: " + ("; ".join(
        f"{'**overlap**' if lo <= hi else 'gap'} between no. {x} (ends p. {hi}) and no. {y} (starts p. {lo})"
        for x, hi, y, lo in seams) if seams else "continuous") + "\n")

    vocab = Counter()
    for _, leaves in raw_issues:
        for lf in leaves:
            for ln in lf["body"]:
                vocab.update(w.lower() for w in re.findall(r"[A-Za-z]+", ln))
    rep = Repair(vocab)

    # the index usually opens no. 1, but not always: vol. 31 has it before
    # no. 3, and the index to vol. 30 was bound at the back of vol. 29
    where = [(iss["id"], lv) for iss, lv in raw_issues]
    prev = [i for i in cat["issues"] if i["vol"] == vol - 1]
    if prev and (RAW / f"{prev[-1]['id']}_hocr_pageindex.json.gz").exists():
        lv = read_issue(prev[-1]["id"])
        paginate(lv)
        where.append((prev[-1]["id"], lv))
    index, index_from = [], None
    for ident, lv in where:
        index = parse_index(lv, vol)
        if index:
            index_from = ident
            break
    report.insert(1, f"\nVolume index: {len(index)} entries from {index_from}\n" if index_from
                  else "\nVolume index: **not found** in this volume or at the back of the previous one; "
                       "authors come from signatures only\n")
    for e in index:
        e["entry"] = rep.para(e["entry"])
        if e["author"]:
            e["author"] = rep.para(e["author"])

    # 1. one flat stream of paragraphs; pages keep references into it
    pages_out, flat, prev_insert, opened = [], [], None, set()
    for iss, leaves in raw_issues:
        for lf in leaves:
            entry = {"issue": iss["id"], "leaf": lf["leaf"], "n": lf["n"], "kind": lf["kind"]}
            if lf["kind"] != "text":
                if lf["kind"] == "plate":
                    entry["caption"] = " ".join(lf["lines"])[:300]
                pages_out.append(entry)
                continue
            entry["p"] = lf["page"]
            if lf.get("sup"):  # printed label of a separately paginated page
                entry["pl"] = (lf.get("suplabel") or "Suppl.") + " " + (to_roman(lf["page"]) if lf.get("roman") else str(lf["page"]))
                entry["sec"] = lf.get("suplabel") or "Supplement"
            if lf["insert"]:  # no printed number: cite by the page it follows
                entry["pl"] = f"insert after {entry.get('pl') or 'p. ' + str(lf['page'])}"
                entry["insert"] = 1
            entry["_head"] = norm_head(lf["head"] or "")
            body = list(lf["body"])
            opening = iss["id"] not in opened  # the first text page of the issue
            opened.add(iss["id"])
            # The masthead opening each issue: everything down to "WOODSTOCK
            # LETTERS" and the "VOL. XXX. No. 2." line after it, however the
            # OCR spells them ("I'HE", "'THE;", "VOL. XXXIIL No. I.")
            m = next((j for j, x in enumerate(body[:4]) if len(x) < 25 and difflib.SequenceMatcher(
                None, norm_head(x), "WOODSTOCKLETTERS").ratio() >= 0.85), None)
            if m is not None:
                body = body[m + 1:]
                while body and not re.search(r"[A-Za-z]{2}", body[0]):  # a stray "%" (vol. 44)
                    body = body[1:]
                if body and norm_head(body[0]).startswith("VOL") and len(body[0]) < 60:
                    body = body[1:]
            while body and MASTHEAD.match(body[0]):
                body.pop(0)
            paras = []
            for j, ln in enumerate(body):
                heading = is_upper(ln) and len(ln) < 120
                p = {"t": rep.para(ln)}
                if heading:
                    p["h"] = 1
                paras.append(p)
            # an issue opens with a title even when the OCR has spoiled its
            # capitals ("irn /iDemonam" for IN MEMORIAM, vol. 36 no. 2/3)
            if opening:
                while paras and not re.search(r"[A-Za-z]{2}", paras[0]["t"]):  # masthead residue: "0"
                    paras.pop(0)
            if opening and lf["head"] is None and paras and not paras[0].get("h") and len(paras[0]["t"]) < 60 \
                    and re.search(r"[A-Za-z]{4}", paras[0]["t"]):
                paras[0]["h"] = 1
            # an unheaded page opening with a title block starts an article
            if lf["head"] is None and paras and paras[0].get("h"):
                paras[0]["start"] = ("supplement" if lf.get("suptitle")
                                     else "insert" if lf["insert"] and not prev_insert
                                     # the running heads often shorten the title
                                     # ("State of Our Mission in Alaska" / "The
                                     # Alaska Mission"): an issue's first page
                                     # starts an article whatever they say
                                     else "issue-opening" if opening else "title-page")
            prev_insert = lf["insert"]
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
        pg = next((q for q in text_pages if q["p"] == e["pages"][0] and not q.get("sec")), None)
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
    def part_of(a, b):
        """Is a (fuzzily) a stretch of b? Running heads shorten a title or
        split it over facing pages: "A MESSAGE TO THOSE" / "OUTSIDE THE FOLD"."""
        if len(a) < 6 or len(a) > len(b):
            return False
        return max(difflib.SequenceMatcher(None, a, b[k:k + len(a)]).ratio()
                   for k in range(len(b) - len(a) + 1)) >= 0.8

    def person(s):  # "Fr. Edward V. Boursaud" / "FATHER EDWARD V. BOURSAUD"
        return re.sub(r"^(FATHER|FR|BROTHER|BR|MR|REV)", "", norm_head(s))

    for i, (pg, p) in enumerate(flat):
        if p.get("start") and cur is not None and p["start"] not in ("issue-opening", "supplement", "insert") \
                and pg["issue"] == cur["issue"]:
            nh, ch = person(p["t"]), person(cur["title"])
            if ((pg["p"] - cur["p1"] <= 1 and difflib.SequenceMatcher(None, nh, ch).ratio() >= 0.75)
                    or part_of(nh, ch)
                    or (pg["p"] == cur["p0"] and part_of(ch, nh))):
                if pg["p"] == cur["p0"] and len(nh) > len(ch):  # the fuller title wins
                    cur["title"] = title_case(p["t"])
                p.pop("start")
            # a half-title that says only SUPPLEMENT gives its section to the
            # piece that follows it (vol. 39 p. 279, "Sodality Notes" on p. 280)
            elif (cur.get("section") == "Supplement" and norm_head(cur["title"]) == "SUPPLEMENT"
                  and not cur.get("_body") and pg["p"] - cur["p1"] <= 1):
                cur["title"], cur["subtitle"] = title_case(p["t"]), None
                p.pop("start")
        if p.get("start"):
            tl = [p["t"]]
            k = i + 1
            while k < len(flat) and flat[k][1].get("h") and not flat[k][1].get("start") and len(tl) < 4:
                tl.append(flat[k][1]["t"])
                k += 1
            # a Supplement's pages restart, so its ids do too: 30-S001
            aid = f"{vol}-{'S' if pg.get('sec') else ''}{pg['p']:03d}"
            n = sum(1 for a in articles if a["id"].startswith(aid))
            cur = {"id": aid + (f"-{n + 1}" if n else ""),
                   "title": title_case(tl[0]), "subtitle": " · ".join(title_case(x) for x in tl[1:]) or None,
                   "author": None, "issue": pg["issue"], "p0": pg["p"], "p1": pg["p"], "how": p["start"]}
            if "pl" in pg:  # the printed range, when it is not a plain page number
                cur["pl0"] = cur["pp"] = pg["pl"]
            if p.get("_entry") and not is_upper(p["t"]):
                cur["title"] = p["_entry"]["entry"]
            # the section heads as the OCR gives them: "V a R I a", "Var La", "Obituarv"
            sec = next((s for s in ("VARIA", "OBITUARY", "SUPPLEMENT") if len(norm_head(cur["title"])) <= len(s) + 1
                        and difflib.SequenceMatcher(None, norm_head(cur["title"]), s).ratio() >= 0.75), None)
            if pg.get("sec") or sec == "SUPPLEMENT":  # separately paginated or not (vol. 35)
                cur["section"] = pg.get("sec") or "Supplement"
                if sec == "SUPPLEMENT" and cur["subtitle"]:  # "^tJPPLEMENT." · the real title
                    cur["title"], _, rest = cur["subtitle"].partition(" · ")
                    cur["subtitle"] = rest or None
            elif sec in ("VARIA", "OBITUARY"):
                cur["title"] = cur["section"] = sec.title()
                if cur["title"].upper() == "OBITUARY" and cur["subtitle"]:
                    cur["title"], _, rest = cur["subtitle"].partition(" · ")
                    cur["subtitle"] = rest or None
                elif cur["title"].upper() == "OBITUARY" and k < len(flat):
                    # the name often follows in ordinary type: "Father Edward V. Boursaud."
                    m = re.fullmatch(r"((?:Father|Brother|Fr\.|Br\.|Mr\.|Rev\.) [A-Z][\w.' -]{2,50}?)\.?",
                                     flat[k][1]["t"].strip())
                    if m:  # a fallback: the volume index, if it names him, wins
                        cur["title"], cur["name_line"] = m[1], True
            articles.append(cur)
        if cur is not None:
            p["a"] = cur["id"]
            cur["p1"] = pg["p"]
            if not p.get("h"):
                cur["_body"] = True
            if "pl0" in cur and pg.get("sec") and pg["p"] != cur["p0"]:  # "Suppl. i–xix"
                cur["pp"] = f"{cur['pl0']}–{pg['pl'].split()[-1]}"
        p.pop("start", None)
        p.pop("_entry", None)
    for pg in text_pages:
        pg.pop("_head", None)
    for a in articles:
        a.pop("pl0", None)
        a.pop("_body", None)

    # 5. authors: volume index by start page, else an end signature
    for a in articles:
        cands = [e for e in index if e["pages"] and e["pages"][0] == a["p0"] and "pp" not in a]
        # a title the OCR has spoiled beyond reading ("Irn /Idemonam") takes the
        # index entry that names its page, even as a second locus ("Frisbee,
        # Samuel H … 2, 209")
        if not cands and "pp" not in a and a["title"] not in ("Varia", "Obituary", "Supplement") and not any(zipf_frequency(w.lower(), "en") >= 3.0
                                                   for w in re.findall(r"[A-Za-z]{4,}", a["title"])):
            cands = [e for e in index if a["p0"] in e["pages"]][:1]
            if cands:
                a["title"] = cands[0]["entry"]
        if cands:
            e = max(cands, key=lambda e: difflib.SequenceMatcher(
                None, norm_head(e["entry"]), norm_head(a["title"])).ratio())
            a["indexEntry"] = e["entry"]
            a.setdefault("section", e["section"])
            if a["title"] == "Obituary" or a.get("name_line"):
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
    for a in articles:
        a.pop("name_line", None)

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
