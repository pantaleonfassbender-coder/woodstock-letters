"""Fill the cached fields of the reading paths (data/paths.json) from the
volume files, so that the site can show a path without loading a volume per
station: for each station, the article's title, author, volume, year and
page range. Run after editing the paths or rebuilding volumes.

  python tools/build_paths.py
"""
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
P = ROOT / "data" / "paths.json"

paths = json.loads(P.read_text(encoding="utf-8"))
vols = {}
for path in paths["paths"]:
    for s in path["stations"]:
        vol = int(s["a"].split("-")[0])
        if vol not in vols:
            vols[vol] = json.loads((ROOT / "data" / "vol" / f"{vol:03d}.json").read_text(encoding="utf-8"))
        v = vols[vol]
        a = next((x for x in v["articles"] if x["id"] == s["a"]), None)
        if not a:
            raise SystemExit(f"path {path['id']}: station {s['a']} is not an article")
        s["t"] = a["title"]
        s["au"] = a.get("author")
        s["v"], s["y"] = vol, v["year"]
        s["pp"] = a.get("pp") or (f"{a['p0']}" if a["p0"] == a["p1"] else f"{a['p0']}–{a['p1']}")
P.write_text(json.dumps(paths, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(f"{len(paths['paths'])} paths, {sum(len(p['stations']) for p in paths['paths'])} stations filled")
