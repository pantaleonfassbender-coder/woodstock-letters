"""Build data/atlas.json, the co-occurrence network behind the concept atlas,
from the full-text volumes in data/manifest.json (run after build_volume.py).

  python tools/build_atlas.py

Terms. Content words (four letters or more, no stop words) chosen by keyness
against general English (wordfreq): a word counts in proportion to how much
more often the Letters use it than English at large does, so the network
shows the journal's own vocabulary (mission, novices, sodality, Georgetown)
rather than "time" and "year". OCR noise is kept out by requiring a term
to be a known English word or frequent across several volumes.

Edges. Two terms are joined when they occur in the same sentence more often
than chance allows (positive pointwise mutual information over sentences,
at least MIN_CO shared sentences). Each term keeps its strongest links.

Every term carries its distribution over volumes and over sections
(articles, Varia, obituaries, supplements); the section where its relative
frequency peaks is its "centre of gravity", which colours it in the atlas.
Derived data only: counts and co-occurrence, CC0 like the rest of data/.
"""
import json
import math
import pathlib
import re
import unicodedata
from collections import Counter
from itertools import combinations

from wordfreq import zipf_frequency

ROOT = pathlib.Path(__file__).resolve().parent.parent
N_TERMS = 260     # terms in the network
MIN_F = 25        # occurrences in the corpus
MIN_VOLS = 2      # volumes a term occurs in
MIN_CO = 6        # sentences two terms share before they are joined
PER_TERM = 8      # strongest links kept per term
SECTIONS = ["Articles", "Varia", "Obituary", "Supplement"]

STOP = set("""the a an and or but of to in on at by for with from as is are was were be been
being it its this that these those he she they we you i his her their our your my me him them us
not no nor so such then than there here which who whom whose what when where while if unless because
shall should will would may might can could must let do does did done have has had having more most
much many other another same own also very just only even still yet upon into unto out up down over
under again further once all any both each few one two three thing things way ways make made take
taken give given go going come came say said see seen know known think thought well good great little
long new old ought thereof therein hereby about after before during through between among against
without within some every last first next like being however though although whether since till until
cannot always never often ever now soon already almost quite rather perhaps indeed thus hence also
itself himself herself themselves ourselves yourself myself others something nothing anything
everything someone anyone everyone whole part same number time times year years day days place
found find told tell asked went took gave got get put set left right hand side part mr mrs rev
very dear sent received order st per
four five six seven eight nine twenty thirty forty fifty hundred thousand second third
twelve several following especially large small called present account half whose
besides latter afterwards owing scarcely nearly seemed above near""".split())
# Latin function words (the catalogue in the Supplement to vol. 30, inscriptions)
STOP |= set("""quam quae quod quia cum sunt esse eodem anno venit etiam enim autem inter
apud sive atque tamen ubi ibi hic haec hoc eius ejus illa ille ipse nobis vobis omnes omnia
sed non est erat fuit""".split())
MIN_RATIO = 4     # a term is at least this many times more frequent than in English


def fold(s):
    return "".join(c for c in unicodedata.normalize("NFD", s) if not unicodedata.combining(c))


def tokens(s):
    return re.findall(r"[a-z][a-z']+[a-z]", fold(s.lower()))


ABBR = re.compile(r"(?:\b[A-Z]|\b(?:Fr|Br|Mr|Mrs|Rev|St|Dr|Very|Ven|Bl|Co|No|Vol|pp?))\.$")


def sentences(s):
    # a sentence ends at . ! ? before a capital; "S. J." and "Fr. Ryan" stay inside
    out = []
    for piece in re.split(r"(?<=[.!?])\s+(?=[A-Z\"'(])", s):
        if out and ABBR.search(out[-1]):
            out[-1] += " " + piece
        else:
            out.append(piece)
    return out


def main():
    man = json.loads((ROOT / "data" / "manifest.json").read_text(encoding="utf-8"))
    vols = [v["vol"] for v in man["volumes"]]
    f, fv, fs, co, nsent = Counter(), {}, {}, Counter(), 0
    words_v, words_s = Counter(), Counter()
    sent_terms = []
    for vi, v in enumerate(vols):
        d = json.loads((ROOT / "data" / "vol" / f"{v:03d}.json").read_text(encoding="utf-8"))
        sec_of = {a["id"]: a.get("section") if a.get("section") in SECTIONS else "Articles"
                  for a in d["articles"]}
        for pg in d["pages"]:
            for p in pg.get("paras", []):
                if p.get("h") or not p.get("a"):
                    continue
                sec = SECTIONS.index(sec_of[p["a"]])
                for s in sentences(p["t"]):
                    tk = [t for t in tokens(s) if len(t) >= 4 and t not in STOP]
                    words_v[vi] += len(tk)
                    words_s[sec] += len(tk)
                    for t in tk:
                        f[t] += 1
                        fv.setdefault(t, Counter())[vi] += 1
                        fs.setdefault(t, Counter())[sec] += 1
                    if tk:
                        sent_terms.append(set(tk))
                        nsent += 1
    total = sum(f.values())

    def ratio(t):
        # corpus frequency per million against English at large (zipf 3 = 1 per million)
        ref = 10 ** (zipf_frequency(t, "en") - 3) if zipf_frequency(t, "en") > 0 else 0.01
        return (f[t] / total * 1e6) / ref

    def keyness(t):
        return f[t] * math.log(ratio(t))

    cands = [t for t in f if f[t] >= MIN_F and len(fv[t]) >= MIN_VOLS and ratio(t) >= MIN_RATIO
             and (zipf_frequency(t, "en") >= 2.0 or len(fv[t]) >= 3)]
    terms = sorted(cands, key=keyness, reverse=True)[:N_TERMS]
    keep = set(terms)

    for st in sent_terms:
        for a, b in combinations(sorted(st & keep), 2):
            co[(a, b)] += 1
    sf = Counter()  # sentences a term occurs in
    for st in sent_terms:
        for t in st & keep:
            sf[t] += 1

    edges = []
    for (a, b), n in co.items():
        if n < MIN_CO:
            continue
        pmi = math.log(n * nsent / (sf[a] * sf[b]))
        if pmi > 0:
            edges.append({"s": a, "t": b, "f": n, "pmi": round(pmi, 3)})
    # each term keeps its strongest links, weighted by both strength and support
    score = lambda e: e["pmi"] * math.log(1 + e["f"])
    best = set()
    for t in terms:
        mine = sorted((e for e in edges if t in (e["s"], e["t"])), key=score, reverse=True)[:PER_TERM]
        best.update((e["s"], e["t"]) for e in mine)
    edges = sorted((e for e in edges if (e["s"], e["t"]) in best), key=score, reverse=True)
    linked = {x for e in edges for x in (e["s"], e["t"])}

    nodes = []
    for t in terms:
        if t not in linked:
            continue
        # centre of gravity: the section where the term is relatively most frequent
        rel = [fs[t][i] / max(1, words_s[i]) for i in range(len(SECTIONS))]
        nodes.append({"id": t, "f": f[t], "sec": SECTIONS[max(range(len(SECTIONS)), key=rel.__getitem__)],
                      "dist": [fv[t][i] for i in range(len(vols))],
                      "sdist": [fs[t][i] for i in range(len(SECTIONS))]})
    out = {"vols": vols, "sections": SECTIONS, "sentences": nsent,
           "words": [words_v[i] for i in range(len(vols))],
           "nodes": nodes, "edges": edges}
    path = ROOT / "data" / "atlas.json"
    path.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"atlas: {len(nodes)} terms, {len(edges)} links over {nsent} sentences "
          f"in vols. {vols[0]}–{vols[-1]} -> {path.relative_to(ROOT)} ({path.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
