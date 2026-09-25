"""Biodata for the Jesuits of the people map from the Jesuit Online Necrology.

The Jesuit Online Necrology (Boston College Libraries, with the Archivum
Romanum Societatis Iesu and the Woodstock Theological Library) gives, for the
32,000 men who died in the Society between 1814 and 1970, the dates and places
of birth, entry and death, the grade at death and the entry province, from
Mendizábal's Catalogus defunctorum (1972): https://jesuitonlinenecrology.bc.edu/

For every Jesuit of data/people.json (Fathers, Brothers, scholastics) this looks
the surname up, keeps the records whose Latin forename fits his English one, and
accepts a match only when one record is left: by the year of his obituary in
the Letters where there is one, else by the entry province (North American)
where several remain. A person with no match, or with several, gets none.
The site links every match to its record.

Requests are made one at a time, two seconds apart (the site's Crawl-delay),
and cached in data/raw/necrology/ (git-ignored), so a rerun asks only for what
is new. Writes data/necrology.json.

    python tools/fetch_necrology.py
"""
import html
import json
import pathlib
import re
import time
import unicodedata
import urllib.parse
import urllib.error
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
CACHE = ROOT / "data" / "raw" / "necrology"
BASE = "https://jesuitonlinenecrology.bc.edu"
UA = "woodstock-letters research edition (https://woodstock-letters.netlify.app/)"
_last = [0.0]
FAILED = []

# entry provinces and missions of North America, as the Catalogus names them
NA = re.compile(r"Maryland|Marylandiae|Neo.?Ebor|New York|Missouri|Neo.?Aurel|New Orleans|Californ|Canad|Neo.?Angl|"
                r"New England|Oregon|Chicag|Cincinn|Detroit|Buffalo|Taurin|Mexic|Neo.?Mexic|Montan|Rocky|Alask", re.I)


def get(path, name):
    """GET a JSON path of the necrology, cached."""
    f = CACHE / name
    if f.exists():
        return json.loads(f.read_text(encoding="utf-8"))
    wait = 2.0 - (time.time() - _last[0])
    if wait > 0:
        time.sleep(wait)
    req = urllib.request.Request(BASE + path, headers={"User-Agent": UA, "Accept": "application/json"})
    for attempt in (1, 2):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                data = json.loads(r.read().decode("utf-8"))
            break
        except (urllib.error.URLError, TimeoutError, ValueError) as e:
            _last[0] = time.time()
            if attempt == 2:  # a query the server cannot answer: skipped, not cached, asked again next run
                print(f"  skipped {path}: {e}")
                FAILED.append(path)
                return None
            time.sleep(10)
    _last[0] = time.time()
    CACHE.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return data


def fold(s):
    s = unicodedata.normalize("NFKD", s)
    return re.sub(r"[^a-z]", "", "".join(c for c in s if not unicodedata.combining(c)).lower())


def names_table():
    """Latin forename → its vernacular forms, from the necrology's own list."""
    f = CACHE / "names.json"
    if not f.exists():
        req = urllib.request.Request(BASE + "/pages/names", headers={"User-Agent": UA})
        t = urllib.request.urlopen(req, timeout=60).read().decode("utf-8")
        table = {}
        for row in re.findall(r"<tr[^>]*>(.*?)</tr>", t, re.S)[1:]:
            cells = [html.unescape(re.sub(r"<[^>]+>", "", c)).strip() for c in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", row, re.S)]
            if cells and cells[0]:
                forms = {fold(x) for c in cells for x in re.split(r"[,/]", c) if fold(x)}
                for lat in re.split(r"[,/]", cells[0]):
                    table.setdefault(fold(re.sub(r"\(.*?\)", "", lat)), set()).update(forms)
        CACHE.mkdir(parents=True, exist_ok=True)
        f.write_text(json.dumps({k: sorted(v) for k, v in table.items()}), encoding="utf-8")
    return {k: set(v) for k, v in json.loads(f.read_text(encoding="utf-8")).items()}


def stem(s):
    s = fold(s).replace("j", "i").replace("y", "i")
    return re.sub(r"(us|a|um|o|e)$", "", s)


def forename_fits(first, latin, table):
    """Does the English forename (or its initial) fit a Latin one? "John" /
    "Ioannes", "Aloysius" / "Aloisius", "T." / "Thomas"."""
    if not first:
        return True
    lat = [fold(x) for x in re.split(r"[\s,]+", latin) if fold(x)]
    if not lat:
        return False
    head = lat[0]
    forms = table.get(head, set()) | {head}
    f = first.split()[0].rstrip(".")
    if len(f) == 1:  # an initial: any form of the Latin name that begins with it
        return any(x.startswith(f.lower()) for x in forms | {head.replace("i", "j", 1) if head.startswith("i") else head})
    ff = fold(f)
    return ff in forms or stem(ff)[:5] == stem(head)[:5]


def parse_node(n):
    """(surname, first name or initial, class) from a person of the people map."""
    name = re.sub(r"^(Fr|Br|Mr|Father|Brother|Rev)\.?\s+", "", n["name"])
    sur = n["id"].split(":")[1]
    first = name[: -len(sur)].strip() if name.endswith(sur) else ""
    return sur, first


def year_of(vol):
    return 1871 + vol


def main():
    people = json.loads((ROOT / "data" / "people.json").read_text(encoding="utf-8"))
    table = names_table()
    out, report = {}, {"matched": 0, "none": 0, "ambiguous": 0}
    for n in people["nodes"]:
        if n["cls"] not in ("father", "brother", "mr"):
            continue
        sur, first = parse_node(n)
        q = urllib.parse.urlencode({"q": sur, "search_field": "all_fields", "per_page": 100})
        res = get(f"/catalog.json?{q}", f"q_{fold(sur)}.json")
        if res is None:
            report["none"] += 1
            continue
        docs = []
        for d in res.get("docs", []):
            s, _, lat = d["title"].partition(",")
            if fold(s) != fold(sur):
                continue
            m = re.match(r"\s*(\d{4})?;?\s*(.*?)\s+–\s+(\d{4})?;?\s*(.*)$", d.get("description") or "")
            d["born"], d["died"] = (int(m[1]) if m and m[1] else None), (int(m[3]) if m and m[3] else None)
            if forename_fits(first, lat, table):
                docs.append(d)
        # the obituary in the Letters dates his death: the year of its volume or the one before
        if n.get("obit") and docs:
            y = year_of(int(n["obit"].split("-")[0]))
            docs = [d for d in docs if d["died"] and y - 2 <= d["died"] <= y]
        # a man named in the Letters died after the restoration; with several
        # left, the North American provinces decide
        if len(docs) > 1:
            recs = [(d, get(f"/catalog/{d['id']}.json", f"r_{d['id']}.json")) for d in docs[:8]]
            na = [(d, r) for d, r in recs if r and NA.search(field(r, "entrance_province_tsi") or "")]
            docs = [d for d, _ in na]
        if len(docs) != 1:
            report["none" if not docs else "ambiguous"] += 1
            continue
        d = docs[0]
        r = get(f"/catalog/{d['id']}.json", f"r_{d['id']}.json")
        if r is None:
            report["none"] += 1
            continue
        out[n["id"]] = {
            "id": d["id"], "name": d["title"],
            "born": field(r, "birth_date_display"), "birthplace": field(r, "place_of_birth_tsi"),
            "entered": field(r, "entrance_date_display"), "province": field(r, "entrance_province_tsi"),
            "vows": field(r, "vow_date_display"), "grade": field(r, "title_tsi"),
            "status": field(r, "status_tsi"),
            "died": field(r, "death_date_display"), "deathplace": field(r, "place_of_death_tsi"),
        }
        report["matched"] += 1
    data = {"source": "Jesuit Online Necrology, Boston College Libraries, from R. Mendizábal, "
                      "Catalogus defunctorum in renata Societate Iesu (1972)",
            "url": BASE + "/catalog/", "retrieved": time.strftime("%Y-%m-%d"), "persons": out}
    (ROOT / "data" / "necrology.json").write_text(json.dumps(data, ensure_ascii=False, indent=0), encoding="utf-8")
    print(f"necrology: {report['matched']} matched, {report['ambiguous']} ambiguous, {report['none']} not found "
          f"-> data/necrology.json" + (f"; {len(FAILED)} requests failed (rerun to retry)" if FAILED else ""))


def field(rec, key):
    v = rec.get("data", {}).get("attributes", {}).get(key)
    if not v:
        return None
    return html.unescape(re.sub(r"<[^>]+>", "", str(v["attributes"].get("value") or ""))).strip() or None


if __name__ == "__main__":
    main()
