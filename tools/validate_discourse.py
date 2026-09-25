"""Check the edition's measures against the replication package of the study.

Scores the edition's articles that correspond to the package's per-article
files (Woodstock Letters 1900, 1910, 1930) and its 1890 and 1920 corpora, with data/discourse.json, and
compares them with the package's results/open_measures.csv, file by file and
as the study's corpus means (Table 2: word-count-weighted means over the
non-optional texts). Writes docs/discourse_validation.md.

    python tools/validate_discourse.py PATH/TO/UNZIPPED/PACKAGE

The package: https://doi.org/10.5281/zenodo.22697014 (CC BY 4.0).
"""
import csv
import glob
import json
import os
import pathlib
import re
import statistics as st
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
CATS = ["i", "we", "certainty", "achievement", "affiliation", "power", "posemo", "negemo", "future"]
YV = {"1900": 29, "1910": 39, "1930": 59}
# the corpora the package gives as one file each, and the edition's articles whose words they are
# (found by shared 8-word runs; each article is taken whole). 1944 (vol. 73) lies past the edition's cutoff.
COMBINED = {"WL1890.txt": ["19-003", "19-179", "19-396"],  # Satolli at Woodstock; Spain; Retractation of Clement XIV
            "WL1920.txt": ["49-001", "49-006"]}  # The Golden Jubilee; The Academy in Honor of the Cardinal


def words(t):
    return set(re.findall(r"[a-z']+", t.lower()))


def main(pkg):
    pk = {r["file"]: r for r in csv.DictReader(open(os.path.join(pkg, "results", "open_measures.csv"), encoding="utf-8"))}
    disc = {a["id"]: a for a in json.loads((ROOT / "data" / "discourse.json").read_text(encoding="utf-8"))["articles"]}
    texts = {}
    for v in YV.values():
        d = json.loads((ROOT / "data" / "vol" / f"{v:03d}.json").read_text(encoding="utf-8"))
        for pg in d["pages"]:
            for q in pg.get("paras", []):
                if q.get("a") and not q.get("h"):
                    texts.setdefault(q["a"], []).append(q["t"])
    rows = []
    for f in sorted(glob.glob(os.path.join(pkg, "corpus", "*.txt"))):
        name = os.path.basename(f)
        if name[:4] not in YV or "america" in name or "sample" in name:
            continue
        W = words(open(f, encoding="utf-8").read())
        cands = [a for a in texts if a.startswith(f"{YV[name[:4]]}-")]
        best = max(cands, key=lambda a: len(W & words(" ".join(texts[a]))) / (len(W | words(" ".join(texts[a]))) + 1))
        o, p = disc[best], pk[name]
        ours = {k: 100 * o["n"][k] / o["wc"] for k in CATS}
        rows.append({"file": name, "id": best, "title": o["t"], "reg": o["reg"], "p": p, "o": o, "ours": ours,
                     "wps": o["wc"] / o["ns"] if o["ns"] else 0})
    out = ["# The edition's measures against the study's replication package\n",
           "Written by `tools/validate_discourse.py`. The study: P. Fassbender, “Identity and Values in U.S. Jesuit "
           "Discourse, 1890–1944”, replication package, CC BY 4.0, https://doi.org/10.5281/zenodo.22697014. "
           "Each of the package's per-article files of the Woodstock Letters is matched to the edition's article by "
           "its words, and scored from the edition's text with the package's word lists, filters, sentence count "
           "and MATTR (`tools/build_discourse.py`).\n",
           "## Agreement, per text (n = %d)\n" % len(rows),
           "| Measure | r | mean abs. difference | package mean |", "|---|---|---|---|"]
    for k in CATS:
        a = [float(r["p"][k]) for r in rows]
        b = [r["ours"][k] for r in rows]
        out.append(f"| {k} | {st.correlation(a, b):.3f} | {st.mean(abs(x - y) for x, y in zip(a, b)):.3f} | {st.mean(a):.3f} |")
    a = [float(r["p"]["WPS"]) for r in rows]
    b = [r["wps"] for r in rows]
    out.append(f"| WPS | {st.correlation(a, b):.3f} | {st.mean(abs(x - y) for x, y in zip(a, b)):.2f} | {st.mean(a):.2f} |")
    a = [int(r["p"]["WC"]) for r in rows]
    b = [r["o"]["wc"] for r in rows]
    out.append(f"| words | {st.correlation(a, b):.3f} | ratio {sum(b) / sum(a):.3f} | {st.mean(a):.0f} |")
    out += ["\n## The study's corpus means (Table 2), recomputed\n",
            "Word-count-weighted means over the non-optional texts of each year, from the package's values and from the edition's.\n",
            "| Year | words | WPS | I % | we % | certainty % | achievement % |", "|---|---|---|---|---|---|---|"]
    for y in YV:
        R = [r for r in rows if r["file"].startswith(y) and "_OPT" not in r["file"]]
        for src in ("package", "edition"):
            if src == "package":
                wc = sum(int(r["p"]["WC"]) for r in R)
                val = lambda k: sum(float(r["p"][k]) * int(r["p"]["WC"]) for r in R) / wc
                wps = sum(float(r["p"]["WPS"]) * int(r["p"]["WC"]) for r in R) / wc
            else:
                wc = sum(r["o"]["wc"] for r in R)
                val = lambda k: 100 * sum(r["o"]["n"][k] for r in R) / wc
                wps = sum(r["wps"] * r["o"]["wc"] for r in R) / wc  # (the study's corpus mean: word-weighted over texts)
            out.append(f"| {y} ({src}) | {wc:,} | {wps:.1f} | {val('i'):.2f} | {val('we'):.2f} | {val('certainty'):.2f} | {val('achievement'):.2f} |")
    out += ["\nThe small difference in first-person singular is the package's: its OCR texts keep \"I^oyola\", "
            "\"I^etters\", \"I^ouis\" (the L read as I^), which its tokeniser counts as the pronoun *I*; the edition "
            "repairs them to Loyola, Letters, Louis.\n"]
    # the study's own corpus means, as reference points for the view (internal registers only)
    ref = {}
    for r in csv.DictReader(open(os.path.join(pkg, "results", "open_measures.csv"), encoding="utf-8")):
        f = r["file"]
        if "america" in f.lower() or "_OPT" in f:
            continue
        y = re.search(r"(18|19)\d\d", f)[0]  # ("1900_badge_of_loyola.txt", "WL1944.txt")
        g = ref.setdefault(y, {"wc": 0, "WPS": 0.0, "MATTR200": 0.0, **{k: 0.0 for k in CATS}})
        wc = int(r["WC"])
        g["wc"] += wc
        for k in ["WPS", "MATTR200"] + CATS:
            g[k] += float(r[k]) * wc
    study = {y: {k: round(g[k] / g["wc"], 3) for k in ["WPS", "MATTR200"] + CATS} | {"words": g["wc"]}
             for y, g in sorted(ref.items())}
    # every text of the study that the edition holds, with the package's values, for the links on the site
    texts = []
    for r in rows:
        texts.append({"file": r["file"], "year": int(r["file"][:4]), "ids": [r["id"]], "opt": "_OPT" in r["file"],
                      "jubilee": False, "wc": int(r["p"]["WC"]),
                      "pkg": {k: round(float(r["p"][k]), 3) for k in ["WPS"] + CATS}})
    for f, ids in COMBINED.items():
        p = pk[f]
        texts.append({"file": f, "year": int(f[2:6]), "ids": ids, "opt": False, "jubilee": f == "WL1920.txt",
                      "wc": int(p["WC"]), "pkg": {k: round(float(p[k]), 3) for k in ["WPS"] + CATS}})
    texts.sort(key=lambda t: (t["year"], t["ids"][0]))
    (ROOT / "data" / "discourse_study.json").write_text(json.dumps({
        "source": "P. Fassbender, “Identity and Values in U.S. Jesuit Discourse, 1890–1944”, replication package "
                  "(results/open_measures.csv), CC BY 4.0, https://doi.org/10.5281/zenodo.22697014",
        "note": "Word-count-weighted means over the study's internal Woodstock Letters texts of each year "
                "(optional texts excluded); 1920 and 1944 are the jubilee corpora. 'texts': the study's texts "
                "in the edition (1944, vol. 73, lies past its cutoff), with the package's values.",
        "years": study, "texts": texts}, ensure_ascii=False, indent=1), encoding="utf-8")
    # the 1890 and 1920 corpora come as one file each; their words are those of whole articles of the edition
    out += ["\n## The corpora of 1890 and 1920\n",
            "The package gives the 1890 sample and the Golden Jubilee essays of 1920 as one cleaned file each. "
            "Their words are those of whole articles of the edition, found by shared runs of eight words.\n",
            "| Year | Articles | words (pkg / ed.) | we % | I % | certainty % | achievement % |",
            "|---|---|---|---|---|---|---|"]
    for f, ids in COMBINED.items():
        J, p = [disc[i] for i in ids], pk[f]
        wc = sum(a["wc"] for a in J)
        out.append(f"| {f[2:6]} | " + "; ".join(f"[{a['id']}](../#/a/{a['id']}) {a['t']}" for a in J)
                   + f" | {int(p['WC']):,} / {wc:,} | "
                   + " | ".join(f"{float(p[k]):.2f} / {100 * sum(a['n'][k] for a in J) / wc:.2f}"
                                for k in ("we", "i", "certainty", "achievement")) + " |")
    out += ["\nPackage / edition. The study's commemorative register is thus the Woodstock jubilee itself. Other anniversary pieces "
            "(the Spring Hill centennial, the Papal Jubilee celebration, the Auriesville celebration of 1930) stand "
            "in its ordinary series, and their first-person plural is low (0.12–0.48 %). The edition's automatic "
            "commemorative flag is wider (every piece whose title names a jubilee, centenary or anniversary, and "
            "the whole of an issue given to a jubilee), so its annual contrast is weaker than the study's.\n"]
    out += ["\n## Per text\n", "| Package file | Edition article | Register | words (pkg / ed.) | we % (pkg / ed.) |", "|---|---|---|---|---|"]
    for r in rows:
        out.append(f"| {r['file']} | [{r['id']}](../#/a/{r['id']}) {r['title']} | {r['reg']} | {r['p']['WC']} / {r['o']['wc']} | "
                   f"{float(r['p']['we']):.2f} / {r['ours']['we']:.2f} |")
    (ROOT / "docs" / "discourse_validation.md").write_text("\n".join(out) + "\n", encoding="utf-8")
    print(f"validation: {len(rows)} texts -> docs/discourse_validation.md")


if __name__ == "__main__":
    main(sys.argv[1])
