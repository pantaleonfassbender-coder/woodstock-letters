"""Download the page-addressable OCR of Woodstock Letters issues into
data/raw/ (git-ignored; every build can re-fetch it).

Per issue we take only three small files the Internet Archive derives
from its ABBYY OCR:
  *_hocr_searchtext.txt.gz   the plain text, one OCR paragraph per line
  *_hocr_pageindex.json.gz   character offsets of each leaf in that text
  *_page_numbers.json        the leaves the IA viewer shows; a leaf's
                             position in this list is its viewer index n
Scans are never downloaded; the site deep-links to the IA viewer.

  python tools/fetch_ia.py --vol 29          all issues of volume 29
  python tools/fetch_ia.py --from 1 --to 66  a range of volumes
"""
import argparse
import json
import pathlib
import time
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
SUFFIXES = ["_hocr_searchtext.txt.gz", "_hocr_pageindex.json.gz", "_page_numbers.json"]


def fetch(identifier):
    RAW.mkdir(parents=True, exist_ok=True)
    got = 0
    for s in SUFFIXES:
        dest = RAW / (identifier + s)
        if dest.exists() and dest.stat().st_size > 0:
            continue
        url = f"https://archive.org/download/{identifier}/{identifier}{s}"
        for attempt in range(3):
            try:
                with urllib.request.urlopen(url, timeout=60) as r:
                    dest.write_bytes(r.read())
                got += 1
                break
            except Exception as e:  # network hiccups on IA are routine
                if attempt == 2:
                    raise RuntimeError(f"{url}: {e}") from e
                time.sleep(5 * (attempt + 1))
        time.sleep(1)  # be polite to archive.org
    return got


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--vol", type=int)
    ap.add_argument("--from", dest="start", type=int)
    ap.add_argument("--to", dest="end", type=int)
    a = ap.parse_args()
    lo, hi = (a.vol, a.vol) if a.vol else (a.start or 1, a.end or 98)
    cat = json.loads((ROOT / "data" / "catalogue.json").read_text(encoding="utf-8"))
    for i in cat["issues"]:
        if lo <= i["vol"] <= hi:
            n = fetch(i["id"])
            print(f"vol {i['vol']} no {i['no']}  {i['id']}  {'fetched' if n else 'cached'}")


if __name__ == "__main__":
    main()
