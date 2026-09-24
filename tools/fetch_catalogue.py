"""Build data/catalogue.json: one record per Woodstock Letters issue held by
the Internet Archive (collection `woodstockletters`, Boston College scans).

The catalogue is metadata only, so it covers the whole run 1872-1969
regardless of copyright tier. Run:  python tools/fetch_catalogue.py
"""
import json
import pathlib
import re
import urllib.parse
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "catalogue.json"

FIELDS = ["identifier", "volume", "year", "imagecount"]

# The volume statement, e.g. "v.29:no.1 (1900)", "v.95:no.4 (1966:Fall)",
# "v.37[i.e.36]:no.2/3 (1907)". A bracketed "i.e." gives the true volume.
VOL_RE = re.compile(
    r"v\.(?P<printed>\d+)(?:\[i\.?e\.(?P<true>\d+)\])?:no\.(?P<no>\d+(?:/\d+)?)"
    r"\s*\((?P<year>\d{4})(?::(?P<season>[^)]+))?\)"
)


def search():
    q = urllib.parse.urlencode(
        [("q", "collection:woodstockletters"), ("rows", "1000"), ("output", "json")]
        + [("fl[]", f) for f in FIELDS]
    )
    with urllib.request.urlopen("https://archive.org/advancedsearch.php?" + q) as r:
        return json.load(r)["response"]["docs"]


def main():
    issues, extras = [], []
    for d in search():
        m = VOL_RE.search(d.get("volume", ""))
        if not m:
            extras.append({"id": d["identifier"], "label": d.get("volume", ""),
                           "year": d.get("year"), "leaves": d.get("imagecount")})
            continue
        vol = int(m["true"] or m["printed"])
        issues.append({
            "id": d["identifier"],
            "vol": vol,
            "printedVol": int(m["printed"]) if m["true"] else None,
            "no": m["no"],
            "year": int(m["year"]),
            "season": (m["season"] or "").rstrip(".") or None,
            "leaves": d.get("imagecount"),
        })
    issues.sort(key=lambda x: (x["vol"], int(x["no"].split("/")[0])))
    OUT.write_text(json.dumps({
        "source": "Internet Archive, collection woodstockletters (Boston College Libraries)",
        "issues": issues,
        "extras": extras,
    }, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{len(issues)} issues, {len(extras)} extra items -> {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
