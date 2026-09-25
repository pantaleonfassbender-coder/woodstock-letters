"""Build data/people.json, the person-to-person network, from the full-text
volumes in data/manifest.json (run after build_volume.py).

  python tools/build_people.py

Persons. A person is named by a title and a surname: "Father Sabetti",
"Fr. J. J. Ryan", "Brother Adams", "Mr. Creighton", "Cardinal Gibbons",
"Pope Pius X". The title gives the class (Fathers, Brothers, "Mr." for
scholastics and laymen, prelates, popes); bishops, archbishops, cardinals
and monsignori are one class, because the same man is Bishop and later
Archbishop Carroll. Offices ("Father General", "Father Rector") are not
persons and are left out.

Identity is class plus surname. Namesakes are kept apart where the text
names them with different first names or initials; a bare "Father Ryan"
then goes to the Ryan named in the same article, if there is exactly one,
and otherwise to no one. Namesakes the text never distinguishes are one
node: a limit of the method, stated on the site.

Links. Two persons are joined when they are named in the same paragraph,
in at least MIN_CO paragraphs. Each keeps its strongest links.

Each person carries the mentions per volume, the articles that name them
most, the articles they wrote (from the article authors) and their
obituary, when one is headed with their name. Derived data, CC0.
"""
import json
import math
import pathlib
import re
from collections import Counter, defaultdict
from itertools import combinations

ROOT = pathlib.Path(__file__).resolve().parent.parent
MIN_F = 5        # mentions for a person to appear
MIN_CO = 2       # paragraphs two persons share before they are joined
PER_NODE = 10    # strongest links kept per person
N_NODES = 320    # persons in the network

CLASS = {"Father": "father", "Fr.": "father", "Rev.": "father", "Brother": "brother", "Br.": "brother",
         "Mr.": "mr", "Bishop": "prelate", "Archbishop": "prelate", "Cardinal": "prelate",
         "Mgr.": "prelate", "Monsignor": "prelate", "Pope": "pope"}
SHOW = {"father": "Fr.", "brother": "Br.", "mr": "Mr.", "prelate": "", "pope": "Pope"}
OFFICES = set("""General Rector Provincial Superior Minister Substitute Assistant Assistants Vicar
Secretary Procurator Socius Master Visitor Spiritual Prefect President Director Pastor Chaplain
Editor Treasurer Instructor Novice Tertian Confessor Delegate Guardian Abbot Prior Holy Christ God
Time Administrator Missionary Coadjutor Apostolic Consultor Admonitor Regent Principal Chancellor
Dean Professor Doctor Mayor Governor Rev Very Reverend Father Fathers Brother Brothers Mr Messrs
Bishop Archbishop Cardinal Pope Superiors Provincials Rectors Generals Novices Scholastics The
And Of In At On For From With To By Ours Our His Her Their This That St Saint Sister Sisters
Mother Magister Pater Frater Dominus Domine Missioner Missionaries Secretary Ordinary Visitator""".split())
PARTICLES = {"de", "De", "van", "Van", "von", "Von", "La", "Le", "du", "Du", "Del", "del", "della", "Della"}
PARTICLE = r"(?:(?:" + "|".join(sorted(PARTICLES)) + r")\s+)"
NAME = rf"((?:(?:[A-Z][a-z]+|[A-Z]\.)\s+){{0,3}}{PARTICLE}?(?:O'|Mc|Mac)?[A-Z][a-z]+(?:-[A-Z][a-z]+)?)"
MENTION = re.compile(r"\b(?:Very\s+Rev\.\s+|Rev\.\s+|Right\s+Rev\.\s+|Most\s+Rev\.\s+)?"
                     r"(Father|Fr\.|Brother|Br\.|Mr\.|Bishop|Archbishop|Cardinal|Mgr\.|Monsignor|Pope)"
                     r"\s+" + NAME + r"(?:\s+([XVI]{1,5})\b)?")


def parse(title, name, numeral=None):
    """(class, surname, first, display, title) or None for an office or noise."""
    parts = name.split()
    # a Father may be given his office before his name: "Father Provincial Ryan" is rare; drop offices
    while parts and parts[0] in OFFICES:
        parts = parts[1:]
    if not parts:
        return None
    cls = CLASS[title]
    if cls == "pope":
        if not numeral:
            return None
        return cls, parts[0] + " " + numeral, "", f"Pope {parts[0]} {numeral}", title
    # surname: the last word, with a particle before it ("De Smet", "Du Ranquet")
    k = len(parts) - 1
    if k >= 1 and parts[k - 1] in PARTICLES:
        k -= 1
    surname = " ".join(parts[k:])
    if surname in OFFICES or len(surname.replace(" ", "")) < 3:
        return None
    first = parts[0][0] if k > 0 else ""
    return cls, surname, first, " ".join(parts), title


def main():
    man = json.loads((ROOT / "data" / "manifest.json").read_text(encoding="utf-8"))
    vols = [v["vol"] for v in man["volumes"]]
    paras = []          # (vol index, article id, [(cls, surname, first, display)])
    articles = {}
    for vi, v in enumerate(vols):
        d = json.loads((ROOT / "data" / "vol" / f"{v:03d}.json").read_text(encoding="utf-8"))
        for a in d["articles"]:
            articles[a["id"]] = {**a, "vol": v, "year": d["year"]}
        for pg in d["pages"]:
            for p in pg.get("paras", []):
                if not p.get("a"):
                    continue
                ms = [x for m in MENTION.finditer(p["t"]) if (x := parse(m[1], m[2], m[3]))]
                if ms:
                    paras.append((vi, p["a"], ms))

    # namesakes: first initials a (class, surname) is named with
    initials = defaultdict(Counter)
    for _, _, ms in paras:
        for cls, sur, first, *_ in ms:
            if first:
                initials[(cls, sur)][first] += 1

    def split(cls, sur):
        return sum(n >= 3 for n in initials[(cls, sur)].values()) > 1

    # resolve every mention to a person key
    by_article = defaultdict(lambda: defaultdict(Counter))
    for _, aid, ms in paras:
        for cls, sur, first, *_ in ms:
            if first:
                by_article[aid][(cls, sur)][first] += 1

    def key(aid, cls, sur, first):
        if not split(cls, sur):
            return f"{cls}:{sur}"
        if not first:  # a bare surname: the one namesake of this article, if any
            here = by_article[aid][(cls, sur)]
            if len(here) != 1:
                return None
            first = next(iter(here))
        return f"{cls}:{sur}:{first}"

    f, fv, disp, arts = Counter(), defaultdict(Counter), defaultdict(Counter), defaultdict(Counter)
    titles = defaultdict(Counter)
    co, cw = Counter(), Counter()
    for vi, aid, ms in paras:
        ks = []
        for cls, sur, first, show, title in ms:
            k = key(aid, cls, sur, first)
            if not k:
                continue
            f[k] += 1
            fv[k][vi] += 1
            disp[k][show] += 1
            arts[k][aid] += 1
            titles[k][title] += 1
            ks.append(k)
        ks = sorted(set(ks))
        # a list of appointments names a dozen men in one paragraph: each
        # paragraph counts 1/(n-1) towards a link, so a pairing outweighs a list
        for a, b in combinations(ks, 2):
            co[(a, b)] += 1
            cw[(a, b)] += 1 / (len(ks) - 1)

    def label(k):
        cls = k.split(":")[0]
        # the fullest form the text gives, among those used at least twice
        forms = [s for s, n in disp[k].most_common() if n >= 2] or [disp[k].most_common(1)[0][0]]
        best = max(forms, key=lambda s: (len(s.split()), disp[k][s]))
        if cls == "pope":
            return best
        # a prelate goes by the title the text gives him most: "Cardinal Gibbons"
        show = titles[k].most_common(1)[0][0] if cls == "prelate" else SHOW[cls]
        return f"{show} {best}"

    keep = {k for k in f if f[k] >= MIN_F}
    edges = []
    np_ = len(paras)
    for (a, b), n in co.items():
        if n < MIN_CO or a not in keep or b not in keep:
            continue
        pmi = math.log(n * np_ / (f[a] * f[b]))
        edges.append({"s": a, "t": b, "f": n, "w": round(cw[(a, b)], 2), "pmi": round(pmi, 3)})
    score = lambda e: e["w"] * max(0.1, e["pmi"])
    best = set()
    for k in keep:
        mine = sorted((e for e in edges if k in (e["s"], e["t"])), key=score, reverse=True)[:PER_NODE]
        best.update((e["s"], e["t"]) for e in mine)
    edges = [e for e in edges if (e["s"], e["t"]) in best]
    linked = Counter(x for e in edges for x in (e["s"], e["t"]))
    nodes_k = sorted((k for k in keep if linked[k]), key=lambda k: -f[k])[:N_NODES]
    ks = set(nodes_k)
    edges = sorted((e for e in edges if e["s"] in ks and e["t"] in ks), key=score, reverse=True)

    # authors and obituaries, matched to the persons by class and surname
    def person_of(text):
        # only a titled name: "Joseph Estrada" alone could be priest or layman
        m = MENTION.search(text or "")
        if not m or not (x := parse(m[1], m[2], m[3])):
            return None
        cls, sur, first, *_ = x
        for k in ([f"{cls}:{sur}:{first}", f"{cls}:{sur}"] if first else [f"{cls}:{sur}"]):
            if k in ks:
                return k
        return None

    wrote, obit = defaultdict(list), {}
    for aid, a in articles.items():
        if a.get("author") and (k := person_of(a["author"])):
            wrote[k].append(aid)
        if a.get("section") == "Obituary" and (k := person_of(a["title"])):
            obit.setdefault(k, aid)

    nodes = []
    for k in nodes_k:
        nodes.append({"id": k, "name": label(k), "cls": k.split(":")[0], "f": f[k],
                      "dist": [fv[k][i] for i in range(len(vols))],
                      "arts": [a for a, _ in arts[k].most_common(6)],
                      **({"wrote": wrote[k][:8]} if wrote.get(k) else {}),
                      **({"obit": obit[k]} if k in obit else {})})
    used = {a for n in nodes for a in n["arts"] + n.get("wrote", []) + ([n["obit"]] if "obit" in n else [])}
    out = {"vols": vols, "paragraphs": np_,
           "articles": {a: {"t": articles[a]["title"], "v": articles[a]["vol"], "y": articles[a]["year"],
                            "p": articles[a].get("pp") or articles[a]["p0"]} for a in sorted(used)},
           "nodes": nodes, "edges": edges}
    path = ROOT / "data" / "people.json"
    path.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"people: {len(nodes)} persons, {len(edges)} links from {np_} paragraphs naming someone "
          f"in vols. {vols[0]}–{vols[-1]} -> {path.relative_to(ROOT)} ({path.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
