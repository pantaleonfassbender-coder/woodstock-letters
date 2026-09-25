# Rights

The *Woodstock Letters* were printed at Woodstock College, Maryland, from 1872
to 1969. The issues bear the notice “for circulation among Ours only”. They were
distributed within the Society of Jesus and not sold.

## Three tiers

| Tier | Volumes | Years | Treatment |
|---|---|---|---|
| Public domain | 1–59 | 1872–1930 | Full text on the site |
| Renewal check pending | 60–92 | 1931–1963 | Catalogue and scan links only |
| Presumed in copyright | 93–98 | 1964–1969 | Catalogue and scan links only |

**1872–1930.** Works published in the United States before 1 January 1931 are in
the public domain (on 1 January 2026, works of 1930 entered the public domain).
Each January the cutoff moves forward by one year. `tools/build_volume.py` works
it out from the date (`PD_CUTOFF = current year − 96`) and refuses to write full
text for any later volume.

**1931–1963.** For these years, works are in the public domain only if the
copyright was not renewed in the 28th year. Two questions have to be settled
before any full text for these years goes online:

1. **Renewal.** Search the renewal records (Stanford Copyright Renewal Database,
   Catalog of Copyright Entries) for “Woodstock Letters” and Woodstock College.
2. **Publication.** Circulation limited to members of the order may count as a
   *limited publication*, which is not publication in the legal sense. In that
   case the issues would be unpublished works under the 1976 Act, with different
   terms. This is a question for the rights holders, not one to settle
   unilaterally. Write to Boston College (Burns Library / Jesuitica) and the
   Jesuit Archives & Research Center, St. Louis.

**1964–1969.** Renewal became automatic for works first published from 1964 on,
so these issues are presumed to be in copyright.

## What the site never does

- It does not mirror the scans. Every page links to the Internet Archive viewer.
- It does not host full text beyond the public-domain cutoff unless the rights
  holders clear it in writing.
- It leaves the Boston College scans on their own site. The site uses the
  derived OCR text of public-domain volumes and, as illustrations, a small
  number of plates.

## Plates

`assets/plates/` holds page images cut from public-domain sources, registered
with caption and credit in `data/plates.json`: illustrations the journal itself
printed before 1931 (the Golden Jubilee number, vol. 49 no. 1, 1920; Dooley's
*Woodstock and Its Makers*, vol. 56 no. 1, 1927) and details of G. M. Hopkins's
*Atlas of Baltimore County* of 1877 from the Library of Congress. A faithful
reproduction of a public-domain two-dimensional work adds nothing licensable
(*Bridgeman v. Corel*), so the plates are as free as their sources; the
captions and credits are CC0. Every plate names its source leaf or plate and
links to it. No image is taken from an issue after 1930.
