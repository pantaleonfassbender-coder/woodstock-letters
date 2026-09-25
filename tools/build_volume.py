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

# Page numbers read by eye on the scan, for the few leaves where the OCR and
# the consensus cannot decide, and pages a scan lacks; keyed by IA item.
_ov = pathlib.Path(__file__).with_name("page_overrides.json")
OVERRIDES = {k: v for k, v in json.loads(_ov.read_text(encoding="utf-8")).items()
             if not k.startswith("_")} if _ov.exists() else {}

MASTHEAD = re.compile(
    r"^(A\.?\s*M\.?\s*D\.?\s*G\.?|THE|WOODSTOCK\s+LETTERS\.?|VOL\.?\s*[XVLI]+\.?\s*(No\.?\s*\w+\.?)?)$",
    re.I)
# vol. 54 has no index, only a front-matter "CONTENTS OF VOL. LIV." of the same form
# and from vol. 57 in arabic figures: "INDEX TO VOLUME 57"
# ("INDKX TO VOLUME XXV", vol. 25)
# ("CONTENTS OF rOL. XVII.", vol. 17)
INDEX_HEAD = re.compile(r"(?:IND[EK]X\s+TO|CONTENTS\s+OF)\s+(?:THE\s+)?[VvrY]OL\w*\.?\s+([XVLI]+[a-z]*|\d{2})\b", re.I)


def index_numeral(s):
    """The volume numeral of an index heading. In a numeral set in capitals a
    lower-case l or i is the OCR's I: "XLVIil" is XLVIII (vol. 48)."""
    if s.isdigit():
        return int(s)
    return roman(re.sub(r"[il]", "I", s) if re.search(r"[XVL]", s) else s)


def roman(s):
    vals = [{"I": 1, "V": 5, "X": 10, "L": 50}[c] for c in s.upper()]
    return sum(-v if v < w else v for v, w in zip(vals, vals[1:] + [0]))


def roman_page(tok):
    """A roman page number standing alone ("vii", "XIV", "Ill" for iii,
    "11" for ii); None otherwise."""
    t = re.sub(r"^\W+|\W+$", "", tok).lower().translate(str.maketrans("1l|", "iii"))
    return roman(t) if t and len(t) <= 6 and re.fullmatch(r"x{0,3}(ix|iv|v?i{0,3})", t) else None


def romanish(lf):
    """A leaf's roman page number, wherever the running head puts it: alone on
    the first line ("V"), alone on the second ("JOSEPH M. PIGNATELLI, S. J." /
    "VI"), or at the end of the first ("... S. J. iV"). Returns (number, lines
    of running head to drop, the token read) or (None, 0, "")."""
    ls = lf["lines"]
    if ls and (r := roman_page(ls[0])):
        return r, 1, ls[0]
    if len(ls) > 1 and is_upper(ls[0]) and (r := roman_page(ls[1])):
        return r, 2, ls[1]
    if ls and is_upper(ls[0]) and len(ls[0].split()) > 1 and (r := roman_page(ls[0].split()[-1])):
        return r, 1, ls[0].split()[-1]
    return None, 0, ""


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


def foot_number(lines, bare=False):
    """Article-opening pages carry their number at the foot: "(6)". Where an
    issue has no running heads (vol. 49 no. 1, the Golden Jubilee number)
    every page carries it there bare: "3"."""
    if lines:
        m = re.search(r"\((\S{1,4})\)$", lines[-1])
        if m:
            return digits(m[1])
        if bare and re.fullmatch(r"[1-9]\d{0,2}", lines[-1].strip()):  # not "00" closing a table
            return int(lines[-1])
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
        lf["voted"] = False
    for i, _ in offs:
        seq[i]["voted"] = True
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
        # (a reading the consensus rejected counts as none: a table's last
        # figure, "106", is not its page number)
        # A running head's number marks a numbered page even when misread ("•i72")
        last = max((i for i, lf in enumerate(run) if lf.get("voted") or lf["head"] is not None), default=len(run))
        for k, lf in enumerate(run[last + 1:], 1):
            if lf["head"] is None and not lf.get("voted"):
                if tabular(lf):
                    lf["text"], lf["page"] = False, None
                elif a and last < len(run) and run[last]["page"] is not None:
                    # a separately paginated section (a Supplement) has no next
                    # issue to leave room for: its closing pages simply go on
                    # (vol. 50, the Ledóchowski letter, Suppl. xxix–xxx)
                    lf["page"] = run[last]["page"] + k
                else:
                    lf["page"], lf["insert"] = run[last]["page"], True
        # Unnumbered leaves between two read pages that follow on (282, two
        # leaves of publisher's advertisements, 283: vol. 50 no. 3) are no
        # pages either: inserts after the page before them
        read = [i for i, lf in enumerate(run) if lf.get("voted")]
        for i, j in zip(read, read[1:]):
            if j - i > 1 and run[j]["page"] == run[i]["page"] + 1 and run[j]["cand"] == run[j]["page"] \
                    and run[i]["cand"] == run[i]["page"] \
                    and all(lf["head"] is None and lf["cand"] is None for lf in run[i + 1:j]):
                for lf in run[i + 1:j]:
                    lf["page"], lf["insert"] = run[i]["page"], True
    for i in cuts:
        seq[i]["restart"] = True


def paginate(leaves):
    for lf in leaves:
        head, cand, body = split_head(lf["lines"])
        foot = foot_number(body, bare=head is None)
        if foot is not None and cand is None and body and re.fullmatch(r"[1-9]\d{0,2}", body[-1].strip()):
            body = body[:-1]  # the bare number is not text
        lf.update(head=head, cand=cand if cand is not None else foot, body=body)
        lf["chars"] = chars = sum(len(x) for x in body)
        lf["text"] = (head is not None and chars > 250) or chars > 700
        if foot is not None and cand is None and re.fullmatch(r"\(\S{1,4}\)", body[-1].strip()):
            lf["body"] = body[:-1]  # nor is the "(228)" at the foot of an opening page
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
                # its opening page is unnumbered: unread, or unheaded with a
                # reading far from the pages before ("8" for *1, vol. 56 no. 1)
                before = [leaves[k]["cand"] for k in tl if k < prev and leaves[k]["cand"] is not None][-3:]
                s = prev if leaves[prev]["cand"] is None or (
                    leaves[prev]["head"] is None and before and abs(leaves[prev]["cand"] - before[-1]) > 5) else a
                heads = Counter(norm_head(lf["head"]) for lf in leaves[s:] if lf["head"])
                if heads:
                    leaves[s]["suplabel"] = heads.most_common(1)[0][0].title()
                break
    if s is None:
        # ... or in roman numerals (vol. 46 no. 2 closes with "The
        # Glorification of a Great Restorer", Ven. Fr. Pignatelli, pp. [i]–ix)
        tl = [k for k, lf in enumerate(leaves) if lf["text"]]
        for j in range(1, len(tl) - 1):
            a, b = tl[j], tl[j + 1]
            ra, rb = romanish(leaves[a])[0], romanish(leaves[b])[0]
            if ra and ra <= 4 and rb == ra + 1 and \
                    sum((leaves[k]["cand"] or 0) >= 20 for k in tl if k < a) >= 10:
                prev = tl[j - 1]
                s = prev if ra == 2 and not romanish(leaves[prev])[0] else a
                break
    if s is not None:
        sup = leaves[s:]
        leaves[s]["sup"] = "start"
        leaves[s]["suptitle"] = True  # opens an article, whatever its pagination
        # a half-title on a leaf of its own ("SUPPLEMENT / A NATIVE CLERGY IN
        # OUR FOREIGN MISSIONS", vol. 50 no. 2): the text opens on the next
        # text leaf, under that title
        if not leaves[s]["text"] and len(leaves[s]["body"]) > 1:  # (SUPPLEMENT alone: below)
            t = next((k for k in range(s + 1, len(leaves)) if leaves[k]["text"]), None)
            if t is not None:
                leaves[t]["suptitle"] = True
                leaves[t]["supheading"] = [x for x in leaves[s]["lines"][1:3] if is_upper(x)]
        for lf in sup[1:]:
            lf["sup"] = True
            lf["suplabel"] = leaves[s].get("suplabel")
        # a section whose folios carry an asterisk ("*35", "36*", vol. 56 no. 1)
        # is cited so: "35*", as the index of vol. 54 cites its no. 2
        if sum(bool(re.search(r"[*♦]\s*\d{1,3}\b|\b\d{1,3}\s*\*", " ".join(lf["lines"][:2]))) for lf in sup) >= 3:
            for lf in sup:
                lf["supmark"], lf["suplabel"] = "*", None
        # roman numbers in the running head ("vii", "Ill" for iii, "... S. J. iV"),
        # when numerals in letters outnumber arabic readings: "11" and "1*" in an
        # arabic Supplement (vol. 40) also read as ii and i
        lettered = sum(romanish(lf)[0] is not None and re.search(r"[ivxlIVXL]", romanish(lf)[2]) is not None
                       for lf in sup)
        arabic = sum(lf["cand"] is not None for lf in sup)
        if lettered >= 3 and lettered > arabic:
            for lf in sup:
                lf["roman"] = True
                r, drop, _ = romanish(lf)
                if r is None:
                    continue
                if lf["head"] is None:  # not taken for a running head: drop it from the text
                    lf["body"] = lf["body"][drop:]
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
        # a numeral the OCR has spoiled ("XXin.-i894", vol. 23) gives way to the
        # year beside it: vol. N appeared in 1871 + N
        y = re.search(r"[1iIl]8[0-9gqo]{2}", m.string[m.end():])
        if not re.fullmatch(r"[XVLIil]+|\d{2}", m[1]) and y:
            v = int(y[0].translate(str.maketrans("iIlgqo", "111990"))) - 1871
        else:
            v = index_numeral(m[1])
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
    # An offprint bound in before the issue ("(From the WOODSTOCK LETTERS, Oct.
    # 1895.)", 16 pages before vol. 25 no. 1's masthead on leaf 29) is front
    # matter too: its text is in the volume it came from.
    reprint = any(re.match(r"\W*From the WOODSTOCK LETTERS", x, re.I) for lf in leaves[:15] for x in lf["lines"][:2])
    mast = max((k for k, lf in enumerate(leaves[:60 if reprint else 15])
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
        # (not a leaf under a running head: "STATISTICS 111" is p. 177, vol. 57)
        if lf["text"] and lf["chars"] < 500 and lf["cand"] != lf["page"] and not lf.get("halftitle") \
                and not (lf["head"] and len(norm_head(lf["head"])) >= 5):
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
            ("fi", "ff", "any"), ("iu", "in", 5), ("rn", "m", 5), ("tl", "tt", 5), ("tl", "ct", "any"),
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
        # ordinals with 1 read as i or l and 0 as o: "io6th" 106th, "i6tli" 16th (vols. 46, 50)
        m = re.fullmatch(r"([iIl][iIlo]*\d[\dio]*)(th|tli|st|nd|rd)", core)
        if m:
            fixed = m[1].translate(str.maketrans("iIlo", "1110")) + m[2].replace("tli", "th")
            self.log[(core, fixed)] += 1
            return w.replace(core, fixed)
        # (but "i6tli" is 16th, vol. 46)
        if re.search(r"[A-Za-z](6l|6t|\(5t|c5t|c5l)|^0?6l", core) and re.search(r"[a-z]", core) \
                and not re.match(r"[iIl][iIlo]*\d", core):  # nor "io6th", 106th (vol. 50)
            fixed = re.sub(r"c5[tl]", "ct", core)
            fixed = re.sub(r"6l|6t|\(5t", "ct", re.sub(r"^06l", "Oct", fixed))
            self.log[(core, fixed)] += 1
            return w.replace(core, fixed)
        # é read as 6 in French and Spanish names: Algu6, Jos6, Fr6re, Elz6ar
        # (followed by a vowel, r, n, s, z, t or nothing: "tb6k" is noise)
        # (not before i: "distin6i" is the ct ligature; and not in a lower-case
        # string of digit look-alikes: "ij6o", "ipo6" are years)
        # (nor after i: "Troi6-Rivieres" is Trois, vol. 49)
        if re.fullmatch(r"[A-Za-z]{2,}6([aeournszt][a-z]{0,2})?", core) and "i6" not in core \
                and not re.fullmatch(r"[ilojgqpsy]+6[ilojgqpsy]*", core):
            fixed = core.replace("6", "é")
            # but ó in the Spanish -ón ("Le6n" is León, vol. 51), and plain e
            # where that makes a common English word ("th6", the)
            if core.islower() and zipf_frequency(core.replace("6", "ct"), "en") >= 3.0:
                fixed = core.replace("6", "ct")  # the ct ligature again: "subje6" is subject (vol. 19)
            elif re.search(r"6n$", core):
                fixed = core[:-2] + "ón"
            elif core.islower() and zipf_frequency(core.replace("6", "e"), "en") >= 4.0:
                fixed = core.replace("6", "e")
            self.log[(core, fixed)] += 1
            return w.replace(core, fixed)
        # the same ligature read as "dl" after a vowel: accept when the
        # reading is attested or ends like a -ct- word (action, rector ...)
        if re.search(r"[aeiou]dl", core) and zipf_frequency(core.lower(), "en") < 1.0:
            cand = re.sub(r"([aeiou])dl", r"\1ct", core)
            if (zipf_frequency(cand.lower(), "en") >= 1.0
                    # (not a bare -ct: "proudl}^" is proudly, not "prouct")
                    # (-ing not in a name: "Moedling" is a place, not "Moecting")
                    or re.search(r"ct(ion|ions|or|ors|ory|ure|ures|ive|ed|s|ly)$", cand)
                    or (not core[0].isupper() and cand.endswith("cting"))):
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
            # tl for tt only inside a word ("letler", "litlle"): "lovetl" is no "lovett" (vol. 15)
            if (a, b) == ("tl", "tt") and core.endswith("tl"):
                continue
            # the Latin dative and ablative plural: "in Indiis", "Dominiis" (vols. 24, 26)
            # (but "religioiis" is religious, "Jesiis" Jesus: only an -iis that is
            # not -oiis and whose reading is no common word)
            if a == "ii" and core.endswith("iis") and not core.endswith("oiis") \
                    and zipf_frequency(core.replace("ii", "u", 1).lower(), "en") < 3.5:
                continue
            cand = core.replace(a, b, 1)
            # ii is u more often than il: "diily" is duly, not "dilly"
            if (a, b) == ("ii", "il") and zipf_frequency(core.replace("ii", "u", 1).lower(), "en") > \
                    zipf_frequency(cand.lower(), "en"):
                continue
            if b == "L" and re.match(r"L[A-Z][a-z]", cand):  # small capitals: "lyOyola" is Loyola
                cand = "L" + cand[1].lower() + cand[2:]
            # c→e must reach a common word: "wicrd" gave "wierd" (2.6), a
            # misspelling, where the text has "weird"
            gate = 3.0 if (a, b) == ("c", "e") and not core[0].isupper() else 2.5
            # and a misreading that is itself a word must lose by a wide margin:
            # "thern" gives "them", but "De Lancy" is not "Laney", nor the
            # "coats-of-arnis" (arms) "amis", nor "cornets" "comets"
            zc = zipf_frequency(cand.lower(), "en")
            if re.fullmatch(r"[A-Za-z']+", cand) and zc >= gate and (
                    not re.fullmatch(r"[A-Za-z']+", core) or zc - zipf_frequency(core.lower(), "en") >= 1.5):
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
    lines, raw = [], []  # raw: the OCR line each piece comes from
    numbered = False
    for lf in leaves:
        if lf.get("index") != vol:
            continue
        for ln in lf["lines"]:
            r = len(raw) and raw[-1] + 1
            if INDEX_HEAD.match(ln):
                continue
            # from vol. 57 the index gives issue and page in two columns
            # ("No. Page"), and each leaf repeats "2 INDEX" / "INDEX 3"
            if re.fullmatch(r"No\.?\s*Page", ln.strip()):
                numbered = True
                continue
            if re.fullmatch(r"[\d^\s]*INDEX[\d\s]*", ln.strip()):
                continue
            ln = re.sub(r"^\W*INDEX\s+(VARIA|OBITUARY)\W*$", r"\1", ln.strip())  # "INDEX VARIA" (vol. 59)
            ln = re.sub(r"(?<=\d)[oO](?=[\s,.]|$)", "0", ln)  # "24o" is 240 (vol. 48)
            ln = re.sub(r"(?<=\d)\*", "", ln)  # "142*": a page of no. 2 (vol. 54, see page_overrides.json)
            ln = re.sub(r"(,\s*in|\s(?:Ill|lll|IIl))$", " 111", ln)  # "Zwinge, in", "Stanton Ill" (vols. 51, 54)
            # (from vol. 52 the entries run on, each closed by a full stop:
            # "Fr. Joseph F. Hanselman, 382. Fr. Edward J. McGrath, 266.")
            for piece in re.split(r"(?<=\d)\.?\s+(?=[A-Z][a-z])", ln):
                # an entry too long for its line goes on in lower case on the
                # next ("Dead, List of Our, / in United States and Canada ... 191"):
                # join it, or the first half loses its page and the second
                # becomes an entry of its own
                # So too a line broken after "of the" or before "(concluded) 18"
                # (vol. 48)
                # (never a section heading: "Fr. Joseph Zwinge, in" + VARIA, vol. 51)
                if lines and not re.search(r"\d[.,]?$", lines[-1]) \
                        and piece.rstrip(".").upper() not in ("OBITUARY", "OBITUARIES", "VARIA") and (
                        re.match(r"[a-z(]", piece)
                        or re.search(r"\b(?:of|the|and|in|at|to|for)$", lines[-1])):
                    lines[-1] += " " + piece
                else:
                    lines.append(piece)
                    raw.append(r)
    entries, section = [], "Articles"
    def heading(ln):
        """OBITUARY / OBITUARIES / VARIA, as the OCR gives them ("lUTUARV.", vol. 25)"""
        ln = ln.strip().rstrip(".,*:; ")  # "Obituary,", "Varia,", "Obituary*" (vols. 21, 23)
        n = norm_head(ln)
        if ln.upper() in ("OBITUARY", "OBITUARIES", "VARIA"):  # OBITUARIES from vol. 57
            return "Varia" if n == "VARIA" else "Obituary"
        if len(ln) <= 12 and 5 <= len(n) and sum(c.isupper() for c in ln) >= len(n) - 2:
            if difflib.SequenceMatcher(None, n, "OBITUARY").ratio() >= 0.6:
                return "Obituary"
            if difflib.SequenceMatcher(None, n, "VARIA").ratio() >= 0.75:
                return "Varia"
        return None
    has_varia = any(heading(ln) == "Varia" for ln in lines)
    for ln, r in zip(lines, raw):
        # the contents of the early volumes run the obituaries together:
        # "Obituaries— Mr. Christian F. Wise, 95; Fr. John Verdin, 97; …" (vol. 19)
        ob = re.match(r"Obituar\w*\W*[—-]\s*(.+)", ln)
        if ob:
            for part in re.split(r"[;:]", ob[1]):  # ("254: Fr. Louis Sache", vol. 19)
                pm = re.match(r"\s*(.*?[A-Za-z].*?)[\s.,]*(\d{1,3})\.?\s*$", part)
                if pm:
                    entries.append({"entry": pm[1].strip(" .,"), "author": None, "pages": [int(pm[2])],
                                    "section": "Obituary", "_raw": r})
            continue
        if heading(ln):
            section = heading(ln)
            # in a contents set in two columns (vol. 54) the OCR gives the
            # heading after the first line of its block, which runs several
            # entries together: that line is the section's, if its entries are
            # of the section's kind (persons for OBITUARY, none for VARIA);
            # elsewhere such a line belongs to the block before (vols. 39, 48)
            # (a stray note may stand between: "Note — The numbers marked … Number 2.")
            groups = [[e for e in entries if e["_raw"] == r0] for r0 in dict.fromkeys(e["_raw"] for e in entries[-12:])]
            last = next((g for g in groups[::-1][:2] if len(g) >= 3), [])
            persons = [bool(re.match(r"(Fr|Br|Bro|Mr|Rev)\b", e["entry"])) for e in last]
            if len(last) >= 3 and (all(persons) if section == "Obituary" else not any(persons)):
                for e in last:
                    e["section"] = section
            continue
        if numbered:
            # a heading of every issue, its pages after the issue in roman:
            # "Books of Interest to Ours I. 126; II, 424; III, 620"
            rm = re.match(r"^([A-Za-z][^;]*?)\s+((?:(?:I{1,3}|Ill|Il|lI)[.,]\s*\d{1,3}[;.,]?\s*)+)$", ln)
            if rm:
                entries.append({"entry": rm[1].strip(" .,"), "author": None,
                                "pages": [int(x) for x in re.findall(r"[.,]\s*(\d{1,3})", rm[2])],
                                "section": section, "_raw": r})
                continue
            # "Biblical Institute in Jerusalem, The by Father William H. McClellan 1 1":
            # the issue, then the page; the author after "by"
            m = re.match(r"^(.*?[A-Za-z].*?)[\s.,—_\-]*(\d)\.?\s+(\d{1,3})\s*\W?$", ln)
            if not m:
                continue
            body, author = m[1].strip(" .,—-"), None
            a = re.search(r"\s*\.*\s*\bb[yv]\s+((?:Father|Fr\.|Mr\.?|Msgr\.|Rev\.|Brother|Br\.|Very)\s.+)$", body)
            if a:
                body, author = body[:a.start()].strip(" .,—-"), a[1].strip(" .")
            entries.append({"entry": body, "author": author, "pages": [int(m[3])], "no": int(m[2]),
                            "section": section, "_raw": r})
            continue
        m = re.match(r"^(.*?[A-Za-z].*?)[\s.,—]*((?:\d{1,3},?\s*)+)\.?$", ln)
        if not m:
            continue
        pages = [int(x) for x in re.findall(r"\d{1,3}", m[2])]
        body = m[1].strip(" .,—")
        parts = [p.strip(" .,") for p in body.split("—") if p.strip(" .,")]
        author = None
        if len(parts) > 1 and re.match(r"^(Fr|Br|Mr|Rev|Very|Leo)\b", parts[-1]):
            author = parts.pop()
            # "Mr. T. J. McGrath (concluded)": the serial's note is not the name
            author = re.sub(r"\s*\((?:concluded|(?:to be )?continued)\W*$", "", author, flags=re.I)
        entries.append({"entry": " — ".join(parts), "author": author,
                        "pages": pages, "section": section, "_raw": r,
                        # ("Holland. 339": a full stop for the comma, but not a leader "Castillo.... 30")
                        "_comma": bool(re.search(r"[A-Za-z)](?:,|\.(?!\.))\s*\d{1,3}", ln))})
    # A contents in two columns (vol. 25) interleaves the obituaries and the
    # Varia with the headings that name them. After the last article entry,
    # entries of the form "Name, page" are persons (Obituary) or Varia.
    if has_varia:
        last = max((k for k, e in enumerate(entries) if e["section"] == "Articles" and not e.get("_comma")), default=-1)
        # (a block of them, not one article that happens to end in ", 340", vol. 35)
        block = [e for e in entries[last + 1:] if e["section"] == "Articles" and e.get("_comma")]
        for e in block if len(block) >= 5 else []:
            e["section"] = "Obituary" if re.match(r"(Fr|Ft|Br|Bro|Mr|Rev|Father|Brother)\b", e["entry"]) else "Varia"  # ("Ft." is Fr., vol. 54)
    # an obituary is a person: a place in the Obituary section is a Varia item
    # whose heading the OCR has lost (vol. 23: "Alaska, 434" after the obituaries)
    # (three in a row at least: a brother listed without "Br.", "Sanctus
    # Traverso", vol. 36, is an obituary all the same)
    place = [e["section"] == "Obituary" and bool(e.get("_comma"))
             and not re.match(r"(Fr|Ft|Br|Bro|Mr|Rev|Father|Brother|Very)\b", e["entry"]) for e in entries]
    for k in range(len(entries)):
        if place[k] and (all(place[k:k + 3]) and len(place[k:k + 3]) == 3 or (k and entries[k - 1]["section"] == "Varia")):
            entries[k]["section"] = "Varia"
    for e in entries:
        e.pop("_raw", None), e.pop("_comma", None)
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
    # page numbers checked by eye on the scan where the text cannot decide
    # (tools/page_overrides.json; every one is listed in the QA report)
    for iss, leaves in paged:
        for k, p in OVERRIDES.get(iss["id"], {}).get("leaves", {}).items():
            leaves[int(k)].update(page=p, kind="text", text=True)
    # Unnumbered leaves after an issue's last readable page are inserts only
    # if the next issue leaves no room for them. Vol. 38 no. 1 ends with three
    # real pages whose numbers the OCR lost (156–158; no. 2 opens at p. 161);
    # the Declaration after p. 332 in vol. 30 has no room and stays an insert.
    for (_, leaves), (_, nxt) in zip(paged, paged[1:]):
        first = next((l["page"] for l in nxt if l["kind"] == "text" and not l.get("sup")), None)
        # Unread leaves after blank leaves at an issue's end (tables of
        # statistics) are pages when the next issue leaves room for exactly the
        # blanks and them (vol. 59 no. 1: 191, blank, two tables, no. 2 at 195),
        # and inserts when it does not (vol. 57 no. 1: 177, blank, two tables,
        # no. 2 at 179)
        main = [l for l in leaves if l["kind"] == "text" and not l.get("sup")]
        # (a page is read by its number, or by the running head of the pages
        # before it: "STATISTICS 111" for p. 177, vol. 57)
        heads = {norm_head(l["head"]) for l in main if l["head"] and l["cand"] == l["page"]}
        read = max((k for k, l in enumerate(main) if not l["insert"] and (
            l["cand"] == l["page"] or (l["head"] and norm_head(l["head"]) in heads))), default=None)
        if first and read is not None and read + 1 < len(main):
            tail, last = main[read + 1:], main[read]
            gap = leaves[last["leaf"] + 1:tail[0]["leaf"]]
            if gap and all(l["kind"] == "blank" for l in gap) and all(l["cand"] != l["page"] for l in tail) \
                    and all(l["leaf"] == m["leaf"] + 1 for m, l in zip(tail, tail[1:])):
                if first - last["page"] - 1 == len(gap) + len(tail):
                    for k, l in enumerate(tail):
                        l["insert"], l["page"] = None, last["page"] + len(gap) + 1 + k
                else:  # no room: tables (fold-outs) are left out like plates, prose is an insert
                    for l in tail:
                        if tabular(l):
                            l.update(kind="plate", text=False, page=None, insert=None)
                        else:
                            l["insert"], l["page"] = True, last["page"]
        # an unread table closing an issue on the number the next issue opens
        # with (vol. 20 no. 1: the Missouri statistics, "1 / 1", given p. 151)
        # has no page: it is left out like a plate
        mains = [l for l in leaves if l["kind"] == "text" and not l.get("sup") and not l["insert"]]
        if first and mains and mains[-1]["page"] >= first and mains[-1]["cand"] != mains[-1]["page"] \
                and tabular(mains[-1]):
            mains[-1].update(kind="plate", text=False, page=None)
        ins = [l for l in leaves if l["kind"] == "text" and l["insert"] and not l.get("sup")]
        if ins and first and first - ins[0]["page"] - 1 >= len(ins):
            base = ins[0]["page"]  # (not ins[0]["page"] in the loop: it changes on the first pass)
            for k, l in enumerate(ins):
                l["insert"], l["page"] = None, base + 1 + k
        # likewise a short closing page taken for a plate (vol. 38 no. 1, the
        # last page of the Varia, p. 159), when the next issue leaves room
        main = [l for l in leaves if l["kind"] == "text" and not l.get("sup") and not l["insert"]]
        if main and first and first - main[-1]["page"] > 1:
            nxt_leaf = next((l for l in leaves[leaves.index(main[-1]) + 1:] if l["kind"] != "blank"), None)
            if nxt_leaf and nxt_leaf["kind"] == "plate" and nxt_leaf["chars"] > 150 and not tabular(nxt_leaf):
                nxt_leaf.update(kind="text", page=main[-1]["page"] + 1)

    # A section's half-title on a leaf of its own ("VARIA", "Yearly Statistics
    # and Records", vol. 57) or a short table page (vol. 59 p. 189) is taken
    # for a plate; where the numbers on either side leave room for exactly the
    # leaves between (blank or short), it is a page
    for _, leaves in paged:
        tl = [l for l in leaves if l["kind"] == "text" and not l["insert"] and l["page"] is not None]
        for a, b in zip(tl, tl[1:]):
            between = leaves[a["leaf"] + 1:b["leaf"]]
            short = [l for l in between if l["kind"] == "plate" and l["chars"] < 200]
            if short and b["page"] - a["page"] - 1 == len(between) and b.get("sup") == a.get("sup") \
                    and all(l["kind"] == "blank" or l in short for l in between):
                for k, l in enumerate(between, 1):
                    if l in short:
                        l.update(kind="text", text=True, page=a["page"] + k, halfpage=True,
                                 sup=a.get("sup") and True, suplabel=a.get("suplabel"), roman=a.get("roman"))

    # The volume's last issue has no next issue to leave room: there a closing
    # leaf that carries the running head of the page before it without its
    # number ("VARIA", vol. 55 no. 3, pp. 516–517) is that page's successor
    if paged:
        leaves = paged[-1][1]
        ins = [l for l in leaves if l["kind"] == "text" and l["insert"] and not l.get("sup")]
        prev = [l for l in leaves if l["kind"] == "text" and not l["insert"] and not l.get("sup")]
        # (or, when its running head is garbled, "1/A klA." under "t^AP/A.",
        # vol. 25: prose that nothing but plates and blank leaves follow)
        if ins and prev and prev[-1]["leaf"] < ins[0]["leaf"] and ins[0]["body"] and prev[-1]["head"] is not None \
                and not any(tabular(l) for l in ins) \
                and all(l["kind"] == "blank" for l in leaves[prev[-1]["leaf"] + 1:ins[0]["leaf"]]) and (
                # (not the second half of a fold-out table after its plate, vols. 48–49)
                difflib.SequenceMatcher(None, norm_head(ins[0]["body"][0]), norm_head(prev[-1]["head"])).ratio() >= 0.8
                or all(l["kind"] in ("plate", "blank") for l in leaves[ins[-1]["leaf"] + 1:])):
            for k, l in enumerate(ins):
                l["insert"], l["page"] = None, prev[-1]["page"] + 1 + k
            ins[0]["body"] = ins[0]["body"][1:]  # the running head is not text

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
            if sup[0].get("supmark"):
                report.append(f"- separately paginated section with asterisked folios from leaf {sup[0]['leaf']}: "
                              f"pp. {sup[0]['page']}*–{sup[-1]['page']}*, cited as “35*”")
            else:
                report.append(f"- separately paginated {name or 'Supplement'} from leaf {sup[0]['leaf']}: pp. "
                              f"{lab(sup[0]['page'])}–{lab(sup[-1]['page'])}, cited as “{name or 'Suppl.'} …”")
        dups = [l for l in leaves if l.get("dup")]
        if dups:
            report.append(f"- leaves scanned twice, left out: {', '.join(str(l['leaf']) for l in dups)}")
        gaps, blanks, repeats = [], [], []
        missing = set(OVERRIDES.get(iss["id"], {}).get("missing", []))
        skips = []
        for a, b in zip(tl, tl[1:]):
            if b["page"] == a["page"] + 1 or b["restart"]:
                continue
            # a gap filled by blank leaves is blank pages (vol. 35 p. 318), not a fault
            n_blank = sum(l["kind"] == "blank" for l in leaves[a["leaf"] + 1:b["leaf"]])
            if b["page"] > a["page"] and n_blank >= b["page"] - a["page"] - 1:
                blanks.extend(range(a["page"] + 1, b["page"]))
            elif b["page"] > a["page"] and set(range(a["page"] + 1, b["page"])) <= missing:
                continue  # pages the scan lacks, recorded in page_overrides.json
            elif b["page"] <= a["page"] and b["cand"] == b["page"]:
                repeats.append((a["page"], b["page"]))  # the print goes back: a printer's error
            elif (b["page"] > a["page"] and b["leaf"] == a["leaf"] + 1 and b["cand"] == b["page"]
                  and a["body"] and b["body"] and not re.search(r"[.!?:\"”')]$", a["body"][-1].strip())
                  and re.match(r"[a-z]", b["body"][0].strip())):
                # the next leaf goes on mid-sentence: nothing is missing, the
                # printer skipped numbers (vol. 54: "27 different religious /
                # orders", pp. 322 / 333)
                skips.append((a["page"], b["page"]))
            else:
                gaps.append((a["page"], b["page"]))
        if blanks:
            report.append(f"- blank pages (blank leaves in the scan): {', '.join(map(str, blanks))}")
        if missing:
            report.append(f"- pages missing from the scan: {', '.join(map(str, sorted(missing)))}")
        if skips:
            report.append("- printed numbers skipped (the printer's error; the text runs on, nothing is missing): "
                          + ", ".join(f"p. {a} is followed by p. {b}" for a, b in skips))
        if repeats:
            report.append("- printed numbers repeated (the printer's error; the later pages are cited “bis”): "
                          + ", ".join(f"after p. {a} the print goes back to p. {b}" for a, b in repeats))
        fixed = OVERRIDES.get(iss["id"], {}).get("leaves", {})
        if fixed:
            report.append("- page numbers set by hand after checking the scan: "
                          + ", ".join(f"leaf {k} = p. {v}" for k, v in fixed.items())
                          + (f" ({OVERRIDES[iss['id']]['note']})" if OVERRIDES[iss["id"]].get("note") else ""))
        elif OVERRIDES.get(iss["id"], {}).get("note") and not OVERRIDES[iss["id"]].get("mark"):
            report.append(f"- checked on the scan: {OVERRIDES[iss['id']]['note']}")
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
    marked = {i["no"]: OVERRIDES[i["id"]] for i in issues if OVERRIDES.get(i["id"], {}).get("mark")}
    report.insert(1, "\nIssue seams: " + ("; ".join(
        (f"overlap between no. {x} (ends p. {hi}) and no. {y} (starts p. {lo}), as printed: no. {y}'s pages "
         f"are cited “{lo}{marked[y]['mark']}” ({marked[y].get('note', '')})" if lo <= hi and y in marked else
         f"{'**overlap**' if lo <= hi else 'gap'} between no. {x} (ends p. {hi}) and no. {y} (starts p. {lo})")
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
    # the binder put an index where he pleased: at the back of the previous
    # volume (the index to vol. 30), or at the front of it (the index to
    # vol. 26 opens vol. 25 no. 1): look through the neighbours' issues too
    nearby = [i for i in cat["issues"] if i["vol"] == vol - 1][::-1] + [i for i in cat["issues"] if i["vol"] == vol + 1]
    index, index_from = [], None
    for ident, lv in where:
        index = parse_index(lv, vol)
        if index:
            index_from = ident
            break
    for i in nearby if not index else []:
        if not (RAW / f"{i['id']}_hocr_pageindex.json.gz").exists():
            continue
        lv = read_issue(i["id"])
        paginate(lv)
        index = parse_index(lv, vol)
        if index:
            index_from = i["id"]
            break
    report.insert(1, f"\nVolume index: {len(index)} entries from {index_from}\n" if index_from
                  else "\nVolume index: **not found** in this volume or the issues of the volumes either side; "
                       "authors come from signatures only\n")
    for e in index:
        e["entry"] = rep.para(e["entry"])
        if e["author"]:
            e["author"] = rep.para(e["author"])
    # an index that cites misprinted numbers (vol. 55: see page_overrides.json)
    for iss in issues:
        fix = OVERRIDES.get(iss["id"], {}).get("index_add")
        if fix:
            lo, hi = fix["range"]
            moved = [e for e in index if e["section"] in fix["sections"] and e["pages"] and lo <= e["pages"][0] <= hi]
            for e in moved:
                e["pages"] = [p + fix["add"] if lo <= p <= hi else p for p in e["pages"]]
            report.insert(2, f"\nIndex pages corrected: {len(moved)} {' and '.join(fix['sections'])} entries "
                             f"in pp. {lo}–{hi} + {fix['add']} ({fix['note']})\n")

    # 1. one flat stream of paragraphs; pages keep references into it
    pages_out, flat, prev_insert, opened, seen_pages = [], [], None, set(), set()
    for iss, leaves in raw_issues:
        for lf in leaves:
            entry = {"issue": iss["id"], "leaf": lf["leaf"], "n": lf["n"], "kind": lf["kind"]}
            if lf["kind"] != "text":
                if lf["kind"] == "plate":
                    entry["caption"] = " ".join(lf["lines"])[:300]
                pages_out.append(entry)
                continue
            entry["p"] = lf["page"]
            # a number the printer used twice (vol. 45: pp. 213–214 twice) is
            # cited "213 bis" the second time, so every citation stays unique
            if not lf.get("sup") and not lf["insert"]:
                key = (iss["id"], lf["page"])
                if key in seen_pages:
                    entry["pl"] = f"{lf['page']} bis"
                seen_pages.add(key)
            if lf.get("sup"):  # printed label of a separately paginated page
                entry["pl"] = (lf.get("suplabel") or "Suppl.") + " " + (to_roman(lf["page"]) if lf.get("roman") else str(lf["page"]))
                if lf.get("supmark"):
                    entry["pl"] = f"{lf['page']}{lf['supmark']}"
                entry["sec"] = lf.get("suplabel") or "Supplement"
            # an issue whose numbers repeat another's is cited with the mark
            # the volume's own index gives it (vol. 54 no. 2: "104*")
            mark = OVERRIDES.get(iss["id"], {}).get("mark")
            if mark and not lf.get("sup"):
                entry["pl"] = f"{entry.get('pl', lf['page'])}{mark}"
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
                # ("VOIv. LIII, No. I", vol. 53: a roman numeral must follow)
                if body and len(body[0]) < 60 and (norm_head(body[0]).startswith("VOL") or re.match(
                        r"V[O0][LIl1]\w*\.?\s+[XVLIl1]+\b", body[0], re.I)):
                    body = body[1:]
            # From vol. 57 the title is set in blackletter, which the OCR cannot
            # read ("tKfje WoobJStotfe Hetters!", "MWMfMfMfJiJM"), between rules
            # of ornament ("ummmmmmmmmmm"): on an issue's first page drop all
            # down to the VOL line, which stays legible ("| VOL. LVII, No. 3. |")
            elif opening:
                v = next((j for j, x in enumerate(body[:6]) if len(x) < 40 and re.search(
                    r"\bV[O0][LIl1]\w*\.?\s+[XVLIl1]+[.,]?\s*No\b", x)), None)
                # (only when what stands above it is unreadable: vol. 49 opens
                # with its title, THE GOLDEN JUBILEE, above the VOL line)
                if v is not None and all(sum(zipf_frequency(w.lower(), "en") >= 3.0
                                             for w in re.findall(r"[A-Za-z]{3,}", x)) <= 1 for x in body[:v]):
                    body = body[v + 1:]
                    while body and re.fullmatch(r"[\W_mMuUwWnNiIjJfF]{6,}", body[0].strip()):
                        body = body[1:]
            while body and MASTHEAD.match(body[0]):
                body.pop(0)
            paras = []
            for j, ln in enumerate(body):
                # (and a section title in small capitals, read "Varia.", vol. 24)
                heading = (is_upper(ln) and len(ln) < 120) or ln.strip().rstrip(".").upper() in ("VARIA", "OBITUARY")
                p = {"t": rep.para(ln)}
                if heading:
                    p["h"] = 1
                paras.append(p)
            # an issue opens with a title even when the OCR has spoiled its
            # capitals ("irn /iDemonam" for IN MEMORIAM, vol. 36 no. 2/3)
            if opening:
                while paras and not re.search(r"[A-Za-z]{2}", paras[0]["t"]):  # masthead residue: "0"
                    paras.pop(0)
            # the masthead's "THE" taken for a running head is none (vol. 25 no. 1)
            unheaded = lf["head"] is None or (opening and m is not None)
            # a title run into its first line of ordinary type, as in the 1890s:
            # "OUR COLLEGE AT BATON ROUGE, LOUISIANA. A Letter from Father Gache."
            if unheaded and paras and not paras[0].get("h"):
                t = re.match(r"([A-Z][A-Z0-9 ,.'’&—-]{10,}?[.:])\s+(?=[A-Z][a-z]|A\s+[A-Za-z])", paras[0]["t"])
                if t and len(re.findall(r"[A-Z]{2,}", t[1])) >= 2:
                    paras[0:1] = [{"t": t[1], "h": 1}, {"t": paras[0]["t"][t.end():], "h": 1}] \
                        if len(paras[0]["t"]) - t.end() < 120 else [{"t": t[1], "h": 1}, {"t": paras[0]["t"][t.end():]}]
            if opening and unheaded and paras and not paras[0].get("h") and len(paras[0]["t"]) < 60 \
                    and re.search(r"[A-Za-z]{4}", paras[0]["t"]):
                paras[0]["h"] = 1
            if lf.get("supheading"):
                paras = [{"t": title_case(x), "h": 1} for x in lf["supheading"]] + paras
            # an unheaded page opening with a title block starts an article
            if unheaded and paras and paras[0].get("h"):
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
        # the index is sometimes a page out (vol. 48: "Neander 236" begins on
        # p. 235, and the four notices after him likewise): try the pages on
        # either side, for a heading only
        for q in (q for q in text_pages if not hit and not q.get("sec")
                  and q["issue"] == pg["issue"] and abs(q["p"] - pg["p"]) == 1):
            hit = next((p for p in q["paras"] if p.get("h") and not p.get("start") and len(p["t"]) < 110
                        and any(difflib.get_close_matches(w, [x.lower() for x in re.findall(r"[A-Za-z^<:]{4,}", p["t"])],
                                                          1, 0.75) for w in words)), None)
        # an obituary whose name line the OCR has run into the first paragraph
        # ("Father Joseph O'Reilly S.J. The Rev. Joseph O'Reilly, S.J., after",
        # vol. 47): split the name off as the heading
        if not hit and e["section"] == "Obituary":
            for j, p in enumerate(pg["paras"]):
                m = re.match(r"((?:Father|Brother|Mr\.|Fr\.|Br\.|Rev\.) [A-Z][\w.' -]{2,50}?[a-z]{2}(?:,? S\.\s?J\.|\.))\s+(?=[A-Z])",
                             p["t"])
                if m and any(difflib.get_close_matches(w, [x.lower() for x in re.findall(r"[A-Za-z]{4,}", m[1])], 1, 0.75)
                             for w in words):
                    hit = {"t": m[1], "h": 1}
                    p["t"] = p["t"][m.end():]
                    pg["paras"].insert(j, hit)
                    flat.insert(next(k for k, (_, q) in enumerate(flat) if q is p), (pg, hit))
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

    def section_head(t):  # the section heads as the OCR gives them: "V a R I a", "Var La", "Obituarv"
        return next((s for s in ("VARIA", "OBITUARY", "SUPPLEMENT") if len(norm_head(t)) <= len(s) + 1
                     and difflib.SequenceMatcher(None, norm_head(t), s).ratio() >= 0.75), None)

    for i, (pg, p) in enumerate(flat):
        # In the Obituary, each notice opens with its name on a line of its
        # own, "Fr. John Cunningham." (vols. 15, 16, 18, which have no index to
        # name the start pages): a new notice, if prose follows and it is no
        # letter's signature
        # (not the name line under the notice's own heading: "FR. CHARLES H.
        # HEICHEMER" / "Father Charles H. Heichemer.", vol. 23)
        if cur is not None and cur.get("section") == "Obituary" and pg["issue"] == cur["issue"] \
                and cur.get("_body") \
                and not p.get("start") and not p.get("h") and len(p["t"]) < 50 \
                and re.fullmatch(r"(?:Father|Brother|F[rk]|B[rj]\^?|Mr)[.,]?\s+[A-Z][\w.'’ ^>-]{2,40}\.", p["t"].strip()) \
                and i + 1 < len(flat) and not flat[i + 1][1].get("h") and len(flat[i + 1][1]["t"]) > 150 \
                and not (i and flat[i - 1][1]["t"].rstrip().endswith(",")):
            p["start"], p["h"] = "name", 1
        # From vol. 47 the Varia open under a running head ("VARIA 97" over the
        # title VARIA), or mid-page on unheaded pages (vol. 49 no. 1), so no
        # title-page rule sees them; a VARIA heading always opens the section,
        # and within it the running heads the OCR has spoiled ("V A A- /A",
        # vol. 49 p. 363) open nothing
        if p.get("h") and cur is not None and pg["issue"] == cur["issue"] \
                and p.get("start") not in ("issue-opening", "supplement", "insert"):
            n = norm_head(p["t"])
            j = next(k for k, q in enumerate(pg["paras"]) if q is p)
            if cur.get("section") == "Varia" and 3 <= len(n) <= 6 \
                    and difflib.SequenceMatcher(None, n, "VARIA").ratio() >= 0.6:
                p.pop("start", None)
            # a second OBITUARY over a notice already running (vol. 49 p. 353)
            elif cur.get("section") == "Obituary" and section_head(p["t"]) == "OBITUARY":
                p.pop("start", None)
            # the title, not a running head left in the text (the VARIA over
            # the retreat tables, vol. 45 p. 460): mid-page, or under its own
            # running head
            elif section_head(p["t"]) == "VARIA" and (
                    (j > 0 and not pg["paras"][j - 1].get("h")) or section_head(pg["_head"] or "") == "VARIA"
                    # or at the top of an unheaded page whose running heads the
                    # OCR has spoiled ("VARI A." then "U A Ft I A.", vol. 26)
                    # (a page of prose: over the retreat tables, VARIA is only
                    # a running head, vols. 45 and 54)
                    or (j == 0 and not pg["_head"]
                        and statistics.mean(len(q["t"]) for q in pg["paras"]) >= 80)):
                p["start"] = p.get("start") or "section"
        if p.get("start") and cur is not None and p["start"] not in ("issue-opening", "supplement", "insert") \
                and pg["issue"] == cur["issue"]:
            nh, ch = person(p["t"]), person(cur["title"])
            if ((pg["p"] - cur["p1"] <= 1 and difflib.SequenceMatcher(None, nh, ch).ratio() >= 0.75)
                    or part_of(nh, ch)
                    # the page's own heading, where the index entry has
                    # replaced it ("Impressions, Letter of …" / SOME IMPRESSIONS, vol. 52)
                    or part_of(nh, cur.get("_t0", ""))
                    # or the second line of a two-line title ("THE CATHOLIC
                    # ASSOCIATION OF / COMMERCIAL TRAVELLERS", vol. 59)
                    or (cur.get("subtitle") and part_of(nh, person(cur["title"] + cur["subtitle"])))
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
                   "author": None, "issue": pg["issue"], "p0": pg["p"], "p1": pg["p"], "how": p["start"],
                   "_t0": person(p["t"])}
            if "pl" in pg:  # the printed range, when it is not a plain page number
                cur["pl0"] = cur["pp"] = pg["pl"]
                if OVERRIDES.get(pg["issue"], {}).get("mark") or pg["pl"].endswith("*"):
                    cur["_mark"] = True  # a numbered page all the same (vol. 54 no. 2)
            if p.get("_entry") and not is_upper(p["t"]):
                cur["title"] = p["_entry"]["entry"]
            if (p.get("_entry") and p["_entry"]["section"] == "Obituary") or p["start"] == "name":
                cur["section"] = "Obituary"
            sec = section_head(cur["title"])
            # (the Varia inside an asterisked section stay Varia, vol. 56 no. 1)
            if (pg.get("sec") and not (sec in ("VARIA", "OBITUARY") and pg.get("pl", "").endswith("*"))) \
                    or sec == "SUPPLEMENT":  # separately paginated or not (vol. 35)
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
                    # ("Fk. John Clarke.", vol. 15)
                    m = re.fullmatch(r"((?:Father|Brother|F[rk]\.|B[rj]\.|Mr\.|Rev\.) [A-Z][\w.' :-]{2,50}?)\.?",
                                     flat[k][1]["t"].strip())
                    if m:  # a fallback: the volume index, if it names him, wins
                        cur["title"], cur["name_line"] = m[1], True
            articles.append(cur)
        if cur is not None:
            p["a"] = cur["id"]
            cur["p1"] = pg["p"]
            if not p.get("h"):
                cur["_body"] = True
            if "pl0" in cur and (pg.get("sec") or cur.get("_mark")) and pg["p"] != cur["p0"] and "pl" in pg:
                cur["pp"] = f"{cur['pl0']}–{pg['pl'].split()[-1]}"  # "Suppl. i–xix", "135*–141*"
        p.pop("start", None)
        p.pop("_entry", None)
    for pg in text_pages:
        pg.pop("_head", None)
    for a in articles:
        a.pop("pl0", None)
        a.pop("_body", None)

    # 5. authors: volume index by start page, else an end signature
    for a in articles:
        cands = [e for e in index if e["pages"] and e["pages"][0] == a["p0"] and ("pp" not in a or a.get("_mark"))
                 and (e["section"] != "Varia" or a.get("section") == "Varia")]
        # a serial's later parts, and each issue's Books of Interest, are the
        # entry's later pages ("Russian Diary, Notes from a … 54, 63, 206"):
        # accept one when the title shares its words
        if not cands and ("pp" not in a or a.get("_mark")):
            tw = {w.lower() for w in re.findall(r"[A-Za-z]{4,}", a["title"])}
            cands = [e for e in index if e["section"] != "Varia" and a["p0"] in e["pages"][1:]
                     and len(tw & {w.lower() for w in re.findall(r"[A-Za-z]{4,}", e["entry"])}) >= 2]
        # a title the OCR has spoiled beyond reading ("Irn /Idemonam") takes the
        # index entry that names its page, even as a second locus ("Frisbee,
        # Samuel H … 2, 209")
        if not cands and ("pp" not in a or a.get("_mark")) and a["title"] not in ("Varia", "Obituary", "Supplement") and not any(zipf_frequency(w.lower(), "en") >= 3.0
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
        a.pop("_mark", None)
        a.pop("_t0", None)

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
