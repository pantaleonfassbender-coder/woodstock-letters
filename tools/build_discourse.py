"""Psycholinguistic measures over the full-text volumes, by article and register.

Applies the open word lists of Fassbender, "Identity and Values in U.S. Jesuit
Discourse, 1890–1944" (replication package, CC BY 4.0,
https://doi.org/10.5281/zenodo.22697014) to every article of the edition, with
the package's own tokenisation, sentence count, MATTR and paragraph filters, so
that the edition's annual series and the study's six measurement points are
measured alike.

Every article gets a register, so that a series can follow the study's
selection rule ("essays bearing on formation, self-understanding, and
institutional identity"; chronicles, Varia, obituaries, foreign mission
reports, Roman documents and tables excluded) and still show the excluded
registers apart:

    essay       essays, histories, addresses and reports in the editors' or an author's voice
    letter      letters and mission reports (a salutation, a dateline, "Letter from …")
    document    historical documents and reprints, and texts mostly in Latin
    official    letters and decrees of the Pope or the Father General
    review      books of interest, queries, notices of publications
    table       statistics, lists and catalogues
    varia       the Varia (news and chronicle)
    obituary    the obituaries

a flag, `com`, for commemorative pieces (jubilees, centenaries,
anniversaries), and a flag, `fx`, for pieces set outside the United States (the
title names a foreign country or region; the study keeps to U.S. identity). A register read by eye goes in tools/article_overrides.json
under "register" (and "commemorative", "foreign") by article id; it wins over the rules.

Beside the study's lists, each category that holds words of Jesuit usage
("Society", "order", "superior", "brother", "master", "office", "will") is also
counted without them ("adjusted"), since these name the order and its offices
more often than they express the motive.

    python tools/build_discourse.py            # writes data/discourse.json
"""
import json
import pathlib
import re
from collections import Counter

ROOT = pathlib.Path(__file__).resolve().parents[1]
EDITS = json.loads((ROOT / "tools" / "article_overrides.json").read_text(encoding="utf-8"))

# the study's open word lists, verbatim (wordlists.md)
LISTS = {
    "i": "i me my mine myself",
    "we": "we us our ours ourselves",
    "certainty": "absolutely always certain certainly certainty clearly definite definitely doubtless evident evidently indeed inevitable inevitably must necessarily never obvious obviously positively sure surely true truly truth undeniable undoubtedly unquestionably wholly",
    "achievement": "accomplish accomplished accomplishment accomplishments achieve achieved achievement achievements advance advanced advancement ambition attain attained attainment best better effort efforts excel excellence excellent improve improved improvement improvements master mastered mastery progress succeed succeeded success successes successful successfully triumph victory win won efficient efficiency",
    "affiliation": "ally allies together union unity united companion companions community communities brother brothers brotherhood friend friends friendship fellow fellows fellowship common cooperate cooperation mutual society congregation communal collective we us our ours ourselves",
    "power": "authority authorities command commanded commands control dominion govern government governed governor influence lead leader leaders leadership obedience obey obeyed order orders power powerful rule ruled ruler rulers superior superiors supreme force rank president bishop archbishop cardinal pope king emperor law laws official officials office chief master lord majesty",
    "posemo": "good great happy happiness joy joyful glad delight delightful love loved beautiful blessed blessing blessings success successful noble generous kind kindness devoted zeal zealous glorious glory splendid excellent admirable cordial warm gracious triumph hope hopeful cheerful consolation fervent faithful",
    "negemo": "bad sad sadness sorrow grief pain painful suffering fear afraid anxious anxiety anger angry hostile bitter loss lost death dying trouble troubled difficulty difficulties hard harsh cruel persecution attack attacked enemy enemies danger dangerous evil wretched miserable distress",
    "future": "will shall future soon hope hopes hoped prospect prospects forthcoming hereafter tomorrow anticipate anticipated expectation expectations",
}
LISTS = {k: set(v.split()) for k, v in LISTS.items()}
# words that in the Letters mostly name the order and its offices
JESUIT = {"society", "congregation", "order", "orders", "superior", "superiors", "brother", "brothers",
          "master", "office", "will"}
ADJUSTED = {k: v - JESUIT for k, v in LISTS.items() if v & JESUIT}

SW = {"the", "of", "and", "to", "a", "in", "that", "is", "was", "it", "for", "with", "as", "his", "on", "be", "at", "by",
      "not", "this", "are", "from", "or", "have", "an", "they", "which", "we", "their", "has", "were", "been", "will",
      "he", "our", "all", "its", "who", "but"}


def keep(p):
    """The package's paragraph filters (extract.py): no heading in capitals, no
    table or junk (under 75 % letters), no Latin or French (a paragraph of more
    than 30 words with under 10 % English function words)."""
    s = p.strip()
    letters = [c for c in s if c.isalpha()]
    if not letters or (sum(c.isupper() for c in letters) / len(letters) > 0.7 and len(s) < 95):
        return False
    if sum(c.isalpha() or c.isspace() for c in s) / len(s) < 0.75:
        return False
    toks = re.findall(r"[A-Za-z']+", s.lower())
    return not (len(toks) > 30 and sum(t in SW for t in toks) / len(toks) < 0.10)


def nsent(t):
    """The package's sentence count (measures.py)."""
    tmp = re.sub(r"\b([A-Z])\.\s*(?=[A-Z]\b|\W*[a-z])", r"\1@ ", t)
    tmp = re.sub(r"\b(Fr|St|Rev|Mr|Mrs|Dr|Prof|Hon|Bro|Sr|Jr|vs|etc|viz|cf|Vol|No|pp)\.", r"\1@", tmp)
    return len(re.findall(r"[.!?]+", tmp))


def mattr(tokens, w=200):
    if len(tokens) < w:
        return len(set(tokens)) / len(tokens) if tokens else 0
    vals = [len(set(tokens[i:i + w])) / w for i in range(0, len(tokens) - w + 1, 20)]
    return sum(vals) / len(vals)


SALUTE = re.compile(r"^\W*(Rev(erend)?\.?(,| and)? (Very )?Dear (Father|Brother|Sir|Mr\.)|(My )?(Very )?Dear (Father|Brother|Rev)|"
                    r"Rev(erend)?\.? Father( in Christ)?[,.:;]|P\.\s?C\.$|Pax Christi|Dearest|Rev\. and Dear)", re.I)
DATELINE = re.compile(r"^[A-Z][\w.' ]{2,40}, (\w+[.,]? )?(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\w*\.? \d{1,2}(th|st|nd|rd)?,? '?\d{2,4}")
PERSON = re.compile(r"(?:(?:The )?(?:Late )?(?:Rev(?:erend)?\.?|Very Rev\.|Fr\.?|Father|Br\.?|Bro\.|Brother|Mr\.?)\s+)"
                    r"[A-Z][\w.'’^-]*(?:\s+(?:[A-Z][\w.'’^-]*|de|van|von|du|da|di|del|la|le)){0,5}(?:,?\s*S\.\s?J\.?)?\.?")
# a piece set outside the United States: its title names a foreign country or region
# a piece set outside the United States: its title names a foreign country or city (not the
# New York–Canada Mission or Alaska, which belong to the American provinces' own story, and
# not a nationality: the German Fathers of the Buffalo Mission worked in the United States)
FOREIGN = re.compile(r"\b(India|Bombay|Mangalore|Madura|Calcutta|Ceylon|China|Shanghai|Nankin|Zi-?ka-?wei|Japan|Tokyo|Philippines?|"
                     r"Manila|Vigan|Mindanao|Jamaica|Honduras|Belize|Guatemala|Peten|Mexico|Cuba|Havana|Brazil|Argentin\w*|"
                     r"Chile|Peru|Ecuador|Colombia|Venezuela|Bolivia|Paraguay|Uruguay|South America|Central America|"
                     r"Australia|Africa|Zambesi|Egypt|Syria|Beirut|Armenia|Turkey|Constantinople|Russia|Poland|Bosnia|"
                     r"Travnik|Austria|Vienna|Hungary|Germany|Holland|Belgium|Louvain|France|Paris|Spain|Portugal|Italy|"
                     r"Rome|Naples|Sicily|England|Ireland|Scotland|Wales|Oxford|Stonyhurst|Innsbruck|Switzerland|Europe|"
                     r"Posilipo|Velehrad|Mungret|Manresa, Spain)\b")
COMMEM = re.compile(r"\b(jubilee|centenar\w*|centennial|tercentenar\w*|bicentenar\w*|anniversar\w*|semi-?centennial)\b", re.I)


def register(a, paras, latin_share, table_share):
    t = f"{a['title']} {a.get('subtitle') or ''}"
    sec = a.get("section")
    if sec == "Obituary":
        return "obituary"
    if sec == "Varia":
        return "varia"
    if re.search(r"\b(books of interest|queries|answers to queries|publications|reviews?|bibliograph|books? (in press|by ours))", t, re.I):
        return "review"
    if table_share > 0.5 or re.search(r"\b(statistics|catalogue|catalogus|list of|status|ministeria|necrolog|"
                                        r"students in our colleges|our colleges in the|retreats,? given|summer retreats|"
                                        r"dead,? list|summary of)", t, re.I):
        return "table"
    if re.search(r"\b(letter|encyclical|brief|decree|allocution|address|instruction)\b.*\b(pope|holy father|pius|leo|benedict|"
                 r"fr\.? general|father general|very rev(erend)? father general|general of the society|his paternity)", t, re.I) \
            or re.search(r"\b(encyclical|apostolic letter|motu proprio|decree of)\b", t, re.I):
        return "official"
    # an obituary outside the Obituary section: the title is a man's name
    if PERSON.fullmatch(a["title"].strip()) and not re.search(r"['’]s\b", a["title"]):  # (not "Father White's Relation")
        return "obituary"
    if latin_share > 0.4:
        return "document"
    # (historical documents and reprints; a missionary's diary of his own day is a report)
    if re.search(r"\b(relation|relatio|documents?|papers relating)\b", t, re.I):
        return "document"
    head = [p["t"] for p in paras[:4]]
    if re.search(r"^(an? )?(letter|letters|extracts?)\b|\b(extracts? )?from (a |the |two )?letters?\b|"
                 r"\bletters? (from|of)\b|\bdiary\b|\bnotes from\b", t, re.I) \
            or any(SALUTE.search(h) or DATELINE.search(h) for h in head):
        return "letter"
    return "essay"


def main():
    man = json.loads((ROOT / "data" / "manifest.json").read_text(encoding="utf-8"))
    out, regs = [], Counter()
    for m in man["volumes"]:
        v = json.loads((ROOT / "data" / "vol" / f"{m['vol']:03d}.json").read_text(encoding="utf-8"))
        ed = EDITS.get(str(m["vol"]), {})
        by = {a["id"]: [] for a in v["articles"]}
        for pg in v["pages"]:
            for q in pg.get("paras", []):
                if q.get("a") in by:
                    by[q["a"]].append(q)
        # the Golden Jubilee number and other issues given wholly to a jubilee
        jub_issue = {a["issue"] for a in v["articles"] if a["p0"] == min(x["p0"] for x in v["articles"] if x["issue"] == a["issue"])
                     and COMMEM.search(a["title"]) and re.search(r"jubilee number|golden jubilee|diamond jubilee", a["title"] + " " + (a.get("subtitle") or ""), re.I)}
        for a in v["articles"]:
            paras = by[a["id"]]
            body = [q for q in paras if not q.get("h")]
            kept = [q["t"] for q in body if keep(q["t"])]
            text = "\n\n".join(kept)
            toks = [w.lower() for w in re.findall(r"[A-Za-z']+", text)]
            allt = [w.lower() for q in body for w in re.findall(r"[A-Za-z']+", q["t"])]
            latin = 1 - len(toks) / len(allt) if allt else 0
            table = sum(1 for q in body if sum(c.isdigit() for c in q["t"]) > 0.15 * len(q["t"])) / len(body) if body else 0
            reg = ed.get("register", {}).get(a["id"]) or register(a, paras, latin, table)
            com = ed.get("commemorative", {}).get(a["id"])
            if com is None:  # (the notices and lists of a jubilee issue are not commemorative pieces)
                com = reg in ("essay", "letter", "official", "document") and (
                    bool(COMMEM.search(f"{a['title']} {a.get('subtitle') or ''}")) or a["issue"] in jub_issue)
            foreign = ed.get("foreign", {}).get(a["id"])
            if foreign is None:
                foreign = bool(FOREIGN.search(f"{a['title']} {a.get('subtitle') or ''}"))
            regs[reg] += 1
            c = Counter(toks)
            row = {"id": a["id"], "v": m["vol"], "y": m["year"], "t": a["title"], "reg": reg, "com": com, "fx": foreign,
                   "wc": len(toks), "ns": nsent(text), "mattr": round(mattr(toks), 4)}
            row["n"] = {k: sum(c[w] for w in S) for k, S in LISTS.items()}
            row["adj"] = {k: sum(c[w] for w in S) for k, S in ADJUSTED.items()}
            out.append(row)
    data = {
        "source": "Open word lists of P. Fassbender, “Identity and Values in U.S. Jesuit Discourse, 1890–1944”, "
                  "replication package, CC BY 4.0, https://doi.org/10.5281/zenodo.22697014",
        "lists": {k: sorted(v) for k, v in LISTS.items()},
        "jesuit_usage": sorted(JESUIT),
        "articles": out,
    }
    (ROOT / "data" / "discourse.json").write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"discourse: {len(out)} articles, {sum(r['wc'] for r in out):,} words; registers {dict(regs.most_common())} "
          f"-> data/discourse.json")


if __name__ == "__main__":
    main()
