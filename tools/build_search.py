"""Build the Pagefind index behind search and the concordance into pagefind/
(git-ignored; Netlify runs this as its build command, see netlify.toml).

  python tools/build_search.py

One record per printed page and article: a page shared by two articles
gives two records, so every hit opens the right article at the right page.
The record's URL is the reader's own link (#/a/<id>?p=<page>), its meta
carry the citation, and its filters the volume and the section. A sort key
in text order lets the concordance read the hits as they stand in the
journal. Only the full-text volumes in data/manifest.json are indexed.
"""
import asyncio
import json
import pathlib
import shutil
import types

import pagefind.service
from pagefind.index import IndexConfig, PagefindIndex

# The Python wrapper (pagefind 1.5.2) sleeps 0.1 s before reading each reply
# from the Pagefind binary, so it indexes at most ten records a second
# (8 min 40 s for 11 volumes). The read that follows the sleep already waits
# for data, so the sleep only costs time: give that module an asyncio whose
# sleep returns at once. The version is pinned in requirements.txt.
_noop_sleep = types.SimpleNamespace(**vars(asyncio))


async def _no_wait(*_args, **_kw):
    return None


_noop_sleep.sleep = _no_wait
pagefind.service.asyncio = _noop_sleep

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "pagefind"


def records():
    man = json.loads((ROOT / "data" / "manifest.json").read_text(encoding="utf-8"))
    for m in man["volumes"]:
        v = m["vol"]
        d = json.loads((ROOT / "data" / "vol" / f"{v:03d}.json").read_text(encoding="utf-8"))
        arts = {a["id"]: a for a in d["articles"]}
        n = 0
        for pg in d["pages"]:
            if pg["kind"] != "text":
                continue
            by_art = {}
            for p in pg["paras"]:
                if p.get("a"):
                    by_art.setdefault(p["a"], []).append(p["t"])
            for aid, texts in by_art.items():
                a, n = arts[aid], n + 1
                label = pg.get("pl") or str(pg["p"])
                url = f"#/a/{aid}?" + ("" if pg.get("insert") else f"p={pg['p']}")
                yield {
                    "url": url.rstrip("?"),
                    "content": "\n".join(texts),
                    "language": "en",
                    "meta": {"title": a["title"], "cite": f"WL {v} ({d['year']}): {label}",
                             "vol": str(v), "year": str(d["year"]), "page": label, "article": aid,
                             **({"author": a["author"]} if a.get("author") else {})},
                    "filters": {"volume": [f"{v} ({d['year']})"], "section": [a.get("section") or "Articles"]},
                    "sort": {"order": f"{v:03d}{n:05d}"},
                }


async def main():
    if OUT.exists():
        shutil.rmtree(OUT)
    count = 0
    async with PagefindIndex(IndexConfig(output_path=str(OUT))) as index:
        # batches of concurrent requests keep the service busy
        batch = []
        for r in records():
            batch.append(index.add_custom_record(**r))
            if len(batch) == 250:
                await asyncio.gather(*batch)
                count, batch = count + len(batch), []
        await asyncio.gather(*batch)
        count += len(batch)
    files = sum(1 for _ in OUT.rglob("*"))
    size = sum(f.stat().st_size for f in OUT.rglob("*") if f.is_file())
    print(f"search: {count} records -> {OUT.relative_to(ROOT)}/ ({files} files, {size // 1024} KB)")


if __name__ == "__main__":
    asyncio.run(main())
