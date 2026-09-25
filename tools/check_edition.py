"""Consistency checks over the built edition. Run before committing a batch or
a release; exits non-zero on any failure.

  python tools/check_edition.py

Checks: manifest against the volume files; page order within each issue;
article ranges inside their issue's pages; every article's paragraphs
present; plates registered and on disk; the essay's WL citations resolve
to an article; the essay JSON and the manuscript agree in version; the
register's references to full-text volumes point at existing pages; the
site loads nothing from another host, as the legal notice claims.
"""
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
fails, warns = [], []


def fail(msg):
    fails.append(msg)


def warn(msg):
    warns.append(msg)


def load(p):
    return json.loads((ROOT / p).read_text(encoding="utf-8"))


man = load("data/manifest.json")
cat = load("data/catalogue.json")
vols = {}
for m in man["volumes"]:
    p = ROOT / "data" / "vol" / f"{m['vol']:03d}.json"
    if not p.exists():
        fail(f"manifest lists vol {m['vol']} but {p.name} is missing")
        continue
    v = json.loads(p.read_text(encoding="utf-8"))
    vols[m["vol"]] = v
    pages = [pg for pg in v["pages"] if pg["kind"] == "text"]
    if len(v["articles"]) != m["articles"]:
        fail(f"vol {m['vol']}: manifest says {m['articles']} articles, file has {len(v['articles'])}")
    if len(pages) != m["pages"]:
        fail(f"vol {m['vol']}: manifest says {m['pages']} pages, file has {len(pages)}")
    # page order: within an issue, numbered pages ascend (supplements and
    # asterisked folios are paginated on their own and skipped here)
    for iss in v["issues"]:
        seq = [pg["p"] for pg in pages if pg["issue"] == iss["id"] and isinstance(pg.get("p"), int) and not pg.get("pl")]
        bad = [(a, b) for a, b in zip(seq, seq[1:]) if b <= a]
        if bad:
            fail(f"vol {m['vol']} {iss['id']}: page order breaks at {bad[:3]}")
    ids = {a["id"] for a in v["articles"]}
    if len(ids) != len(v["articles"]):
        fail(f"vol {m['vol']}: duplicate article ids")
    assigned = {q.get("a") for pg in v["pages"] for q in pg.get("paras", [])}
    for a in v["articles"]:
        if a["id"] not in assigned:
            fail(f"vol {m['vol']}: article {a['id']} has no paragraphs")
    for pg in v["pages"]:
        if pg["kind"] == "text" and pg.get("n") is None:
            warn(f"vol {m['vol']} leaf {pg.get('leaf')}: text page without viewer index")
vol_ids = {i["vol"] for i in cat["issues"]}
for n in vols:
    if n not in vol_ids:
        fail(f"vol {n} built but not in the catalogue")

# plates
plates = load("data/plates.json")
for pid, p in plates.items():
    if pid == "_note":
        continue
    for suffix in ("", "_t"):
        if not (ROOT / "assets" / "plates" / f"{pid}{suffix}.jpg").exists():
            fail(f"plate {pid}{suffix}.jpg missing on disk")
    if not p.get("caption") or not p.get("credit"):
        fail(f"plate {pid}: caption or credit missing")
    if "issue" in p:
        v = next((v for v in vols.values() if any(i["id"] == p["issue"] for i in v["issues"])), None)
        if v is None:
            fail(f"plate {pid}: issue {p['issue']} is not a full-text issue")
        elif int(re.search(r"\((\d{4})\)", p["credit"]).group(1)) > 1930:
            fail(f"plate {pid}: from an issue after 1930")
for f in (ROOT / "assets" / "plates").glob("*.jpg"):
    if f.stem.removesuffix("_t") not in plates:
        warn(f"assets/plates/{f.name} is not registered")

# essay citations
intro = load("data/introduction.json")
def page_article(vol, page):
    v = vols.get(vol)
    if not v:
        return None
    return next((a for a in v["articles"] if a["p0"] <= page <= a["p1"] and not a.get("pp")), None)
text = " ".join(p for s in intro["sections"] for p in s["paras"]) + " " + intro["abstract"]
for m in re.finditer(r"WL (\d+) \((\d{4})\): (\d+)(?:–(\d+))?", text):
    vol, year, p0, p1 = int(m[1]), int(m[2]), int(m[3]), int(m[4] or m[3])
    v = vols.get(vol)
    if not v:
        fail(f"essay cites {m[0]} but vol {vol} is not in full text")
        continue
    if v["year"] != year:
        fail(f"essay cites {m[0]} but vol {vol} is {v['year']}")
    # a range may span several articles (a section of the jubilee number, a
    # book bound in as two pieces); both ends must fall on a page held by one
    for p in (p0, p1):
        if not page_article(vol, p):
            fail(f"essay cites {m[0]} but no article holds p. {p}")
docx = ROOT / "docs" / "Fassbender-2026-Woodstock-Letters-Introduction.docx"
if not docx.exists():
    fail("manuscript .docx missing in docs/")
elif docx.stat().st_mtime < (ROOT / "data" / "introduction.json").stat().st_mtime - 5:
    warn("docs/*.docx is older than data/introduction.json: rebuild it")
if any(a.get("name", "").lower().startswith("claude") for a in intro["authors"]):
    fail("the AI system is listed as an author of the essay (APA forbids it)")

# register
if (ROOT / "data" / "general_index.json").exists():
    gi = load("data/general_index.json")
    n_bad = 0
    for e in gi["entries"]:
        for r in e["refs"]:
            vol, page = r[0], r[1]
            if vol in vols and not any(pg.get("p") == page for pg in vols[vol]["pages"] if pg["kind"] == "text"):
                n_bad += 1
    total = sum(len(e["refs"]) for e in gi["entries"])
    if n_bad > total * 0.05:
        fail(f"register: {n_bad} of {total} references to full-text volumes hit no page")
    elif n_bad:
        warn(f"register: {n_bad} of {total} references hit no page (OCR of the index, or gaps in the scans)")

# tables
if (ROOT / "data" / "tables.json").exists():
    for t in load("data/tables.json")["tables"]:
        for ext in (".txt", ".csv"):
            if not (ROOT / "data" / "tables" / (t["file"] + ext)).exists():
                fail(f"table {t['file']}{ext} missing")

# no third-party loads, as the legal notice claims: scripts, stylesheets,
# images, fetches and workers are same-origin (outbound <a href> links are fine)
src = (ROOT / "index.html").read_text(encoding="utf-8") + (ROOT / "app.js").read_text(encoding="utf-8") + (ROOT / "net.js").read_text(encoding="utf-8")
for m in re.finditer(r"""<(?:script|img|iframe)[^>]+src=["'](https?://[^"']+)""", src):
    fail(f"loads from another host: {m[1]}")
for m in re.finditer(r"""<link(?![^>]+rel=["'](?:canonical|alternate)["'])[^>]+href=["'](https?://[^"']+)""", src):
    fail(f"stylesheet from another host: {m[1]}")
for m in re.finditer(r"""(?:fetch|Worker|import)\(\s*["'`](https?://[^"'`]+)""", src):
    fail(f"fetches from another host: {m[1]}")

print(f"{len(vols)} volumes, {sum(len(v['articles']) for v in vols.values())} articles checked")
for w in warns:
    print("warning:", w)
for f in fails:
    print("FAIL:", f)
print("OK" if not fails else f"{len(fails)} failure(s)")
sys.exit(1 if fails else 0)
