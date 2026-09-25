/* Woodstock Letters — research edition. Vanilla JS, hash routes, static data:
   data/catalogue.json  every issue 1872–1969 (metadata only)
   data/manifest.json   volumes built with full text
   data/vol/NNN.json    one volume: articles, pages, paragraphs, volume index */
"use strict";

const $ = (s, el = document) => el.querySelector(s);
const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const pad3 = n => String(n).padStart(3, "0");
// n is the IA viewer's page index (the build maps scan leaves onto it)
const IA = (id, n) => n == null ? `https://archive.org/details/${id}` : `https://archive.org/details/${id}/page/n${n}/mode/1up`;
const SITE = "https://woodstock-letters.netlify.app/";

// US public domain: published before 1 January of (this year − 95)
const PD_CUTOFF = new Date().getFullYear() - 96;
const TIER = {
  full:   { label: "Full text",              cls: "full"  },
  pd:     { label: "Public domain · queued", cls: "pd"    },
  check:  { label: "Renewal check pending",  cls: "check" },
  closed: { label: "Catalogue only",         cls: "closed"}
};

const S = { cat: null, man: null, vols: new Map() };

async function getJSON(url) {
  const r = await fetch(url);
  if (!r.ok) throw new Error(`${url}: ${r.status}`);
  return r.json();
}
async function boot() {
  [S.cat, S.man] = await Promise.all([getJSON("data/catalogue.json"), getJSON("data/manifest.json")]);
  S.byVol = new Map();
  for (const i of S.cat.issues) {
    if (!S.byVol.has(i.vol)) S.byVol.set(i.vol, []);
    S.byVol.get(i.vol).push(i);
  }
  S.built = new Set(S.man.volumes.map(v => v.vol));
}
async function vol(n) {
  if (!S.vols.has(n)) S.vols.set(n, getJSON(`data/vol/${pad3(n)}.json`).then(indexVolume));
  return S.vols.get(n);
}
function indexVolume(v) {
  v.byId = new Map(v.articles.map((a, i) => [a.id, Object.assign(a, { i })]));
  return v;
}
function tierOf(n) {
  if (S.built.has(n)) return "full";
  const last = Math.max(...S.byVol.get(n).map(i => i.year));
  if (last <= PD_CUTOFF) return "pd";
  if (last <= 1963) return "check";
  return "closed";
}
const years = n => { const y = [...new Set(S.byVol.get(n).map(i => i.year))]; return y.length > 1 ? `${y[0]}–${String(y.at(-1)).slice(2)}` : `${y[0]}`; };
const tag = t => `<span class="tag ${TIER[t].cls}">${TIER[t].label}</span>`;

// A Supplement is paginated on its own ("Suppl. vii") and an unnumbered
// insert is cited by the page it follows; both carry a printed label.
const range = a => a.pp ?? (a.p0 === a.p1 ? `${a.p0}` : `${a.p0}–${a.p1}`);
const plab = pg => pg.pl ?? pg.p;

function cite(v, a, page) {
  const pages = page ? page : range(a);
  return `${a.author ? a.author + ", " : ""}“${a.title},” Woodstock Letters ${v.vol} (${v.year}): ${pages}. ${SITE}#/a/${a.id}`;
}

/* ------------------------------------------------------------------ views */

function viewHome() {
  const vols = [...S.byVol.keys()].sort((a, b) => a - b);
  const counts = { full: 0, pd: 0, check: 0, closed: 0 };
  vols.forEach(n => counts[tierOf(n)]++);
  const words = S.man.volumes.reduce((s, v) => s + v.words, 0);
  const arts = S.man.volumes.reduce((s, v) => s + v.articles, 0);
  return `
  <div class="kicker">Research edition · pilot</div>
  <h1>The Woodstock Letters, 1872–1969</h1>
  <p class="lede">For almost a century the Jesuits of North America wrote to one another in a journal printed
  “for circulation among Ours only” at Woodstock College, Maryland: mission reports, college histories, obituaries,
  letters from the frontier and from abroad. This edition makes the run citable page by page, links every page to its
  scan, and gives the full text of the volumes that are in the public domain.</p>
  <div class="stats">
    <div class="stat"><b>${S.cat.issues.length}</b><span>issues catalogued</span></div>
    <div class="stat"><b>${vols.length}</b><span>volumes, 1872–1969</span></div>
    <div class="stat"><b>${counts.full}</b><span>volume${counts.full === 1 ? "" : "s"} in full text</span></div>
    <div class="stat"><b>${arts}</b><span>articles delimited</span></div>
    <div class="stat"><b>${(words / 1000).toFixed(0)}k</b><span>words edited</span></div>
  </div>
  <h2>The run</h2>
  <p class="fine">One cell per volume. Open a volume for its contents or its scans.</p>
  <div class="run">${vols.map(n => `<a href="#/vol/${n}" class="t-${tierOf(n)}" title="Vol. ${n} (${years(n)}) · ${TIER[tierOf(n)].label}">${n}<small>${String(S.byVol.get(n)[0].year).slice(2)}</small></a>`).join("")}</div>
  <div class="legend">
    <span><i class="t-full"></i>full text here (${counts.full})</span>
    <span><i class="t-pd"></i>public domain, queued (${counts.pd})</span>
    <span><i class="t-check"></i>1931–1963, renewal check pending (${counts.check})</span>
    <span><i class="t-closed"></i>1964–1969, catalogue only (${counts.closed})</span>
  </div>
  <div class="grid2" style="margin-top:2rem">
    <div class="card"><h3>Cite by volume and page</h3>
      <p>Every paragraph sits on its printed page, so any passage can be cited as <span class="mono">WL 29 (1900): 46</span>
      and checked against the scan in one click. The page numbers are recomputed from the running heads, not trusted from the OCR.</p></div>
    <div class="card"><h3>Built openly</h3>
      <p>The text is Boston College's scan and OCR, repaired conservatively. Every repair and every overruled page number
      is listed in a public QA report, so nothing is silently changed. See <a href="#/about">About &amp; rights</a>.</p></div>
  </div>`;
}

function viewVolumes() {
  const vols = [...S.byVol.keys()].sort((a, b) => a - b);
  return `<h1>Volumes</h1>
  <p class="lede">The whole run as held by the Internet Archive (Boston College Libraries). Full text appears here as the
  public-domain volumes are processed. The others are listed with links to their scans.</p>
  <table><thead><tr><th>Vol.</th><th>Year</th><th>Issues (scans)</th><th>Status</th></tr></thead><tbody>
  ${vols.map(n => {
    const t = tierOf(n);
    return `<tr><td><a href="#/vol/${n}">${n}</a></td><td>${years(n)}</td>
      <td>${S.byVol.get(n).map(i => `<a href="https://archive.org/details/${i.id}" target="_blank" rel="noopener">no.&nbsp;${esc(i.no)}${i.season ? " " + esc(i.season) : ""}</a>`).join(" · ")}</td>
      <td>${tag(t)}</td></tr>`;
  }).join("")}</tbody></table>
  ${S.cat.extras.map(x => `<p class="fine" style="margin-top:1rem">Also held: <a href="https://archive.org/details/${x.id}" target="_blank" rel="noopener">${esc(x.label)}</a>, the general index to vols. 1–80. It will guide the article catalogue for the later volumes.</p>`).join("")}`;
}

async function viewVolume(n) {
  if (!S.byVol.has(n)) return `<h1>No volume ${n}</h1>`;
  const t = tierOf(n);
  const issues = S.byVol.get(n);
  const head = `<div class="kicker">Volume ${n} · ${years(n)}</div><h1>Woodstock Letters, vol. ${n}</h1>`;
  if (t !== "full") {
    const why = {
      pd: "This volume is in the US public domain and is queued for processing. Until then, read it in the scans.",
      check: "Issues from 1931 to 1963 are in the public domain only if their copyright was not renewed. That check is pending, so for now only the catalogue entry and the scans are shown.",
      closed: "Issues from 1964 on are presumed to be in copyright. The edition lists them and links the scans the Internet Archive already provides."
    }[t];
    return `${head}<p>${tag(t)}</p><p class="lede">${why}</p>
      <ul class="toc">${issues.map(i => `<li><span class="pg">no. ${esc(i.no)}</span><span><a href="https://archive.org/details/${i.id}" target="_blank" rel="noopener">${esc(i.season || "")} ${i.year} · scan and OCR at the Internet Archive</a></span></li>`).join("")}</ul>`;
  }
  const v = await vol(n);
  let html = `${head}<p>${tag(t)} <span class="fine">${v.articles.length} articles · ${S.man.volumes.find(x => x.vol === n).pages} pages · <a href="docs/qa/vol${pad3(n)}.md">QA report</a></span></p>`;
  for (const iss of v.issues) {
    const arts = v.articles.filter(a => a.issue === iss.id);
    html += `<h2 style="margin-top:2rem">No. ${esc(iss.no)}${iss.season ? " · " + esc(iss.season) : ""} <a class="fine" href="https://archive.org/details/${iss.id}" target="_blank" rel="noopener">scan ↗</a></h2><ul class="toc">`;
    let sec = null;
    for (const a of arts) {
      const s = a.section && a.section !== "Articles" ? a.section : null;
      if (s !== sec && s) html += `<h3>${esc(s)}</h3>`;
      sec = s;
      html += `<li><span class="pg">${esc(range(a))}</span><span>
        <a class="ti" href="#/a/${a.id}">${esc(a.title)}</a>${a.subtitle ? `<br><span class="au">${esc(a.subtitle)}</span>` : ""}
        ${a.author ? `<br><span class="au">${esc(a.author)}</span>` : ""}</span></li>`;
    }
    html += `</ul>`;
  }
  return html;
}

function highlighter(q) {
  const terms = (q || "").toLowerCase().match(/[\p{L}\d']+/gu) || [];
  if (!terms.length) return s => esc(s);
  const re = new RegExp(`\\b(${terms.map(t => t.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")).join("|")})`, "giu");
  return s => esc(s).replace(re, "<mark>$1</mark>");
}

async function viewArticle(id, params) {
  const n = +id.split("-")[0];
  if (!S.built.has(n)) return viewVolume(n);
  const v = await vol(n);
  const a = v.byId.get(id);
  if (!a) return `<h1>Article ${esc(id)} not found</h1>`;
  const hl = highlighter(params.get("q"));
  const target = +params.get("p") || null;
  const out = [];
  let open = false, titleBlock = true, seen = false;
  for (const pg of v.pages) {
    if (pg.kind === "plate" && seen && pg.issue === a.issue && out.length) {
      out.push(`<p class="fine"><a href="${IA(pg.issue, pg.n)}" target="_blank" rel="noopener">Plate between pages (scan) ↗</a>${pg.caption ? " · " + esc(pg.caption.slice(0, 120)) : ""}</p>`);
      continue;
    }
    if (pg.kind !== "text") continue;
    const ps = pg.paras.filter(p => p.a === id);
    if (!ps.length) { if (seen && pg.p > a.p1) break; continue; }
    seen = true;
    const hit = pg.p === target && !pg.insert;
    const marker = `<a class="pb${hit ? " hit" : ""}" id="${pg.insert ? "l" + pg.leaf : "p" + pg.p}" href="${IA(pg.issue, pg.n)}" target="_blank" rel="noopener" title="WL ${n}: ${esc(String(plab(pg)))}. Open the scan of this page">${n}:${esc(String(plab(pg)))}</a>`;
    let placed = false;
    for (const p of ps) {
      if (p.h) {
        if (titleBlock) continue;          // the title block is shown as the heading
        if (open) { out.push("</p>"); open = false; }
        if (!placed) { out.push(`<p>${marker}</p>`); placed = true; }
        out.push(`<h4>${hl(p.t)}</h4>`);
        continue;
      }
      titleBlock = false;
      if (p.c && open && !placed) {         // paragraph runs on across the page break
        const prev = out.pop();
        out.push(prev.replace(/-$/, "­") + ` ${marker} ${hl(p.t)}`);
        placed = true;
        continue;
      }
      if (open) out.push("</p>");
      out.push(`<p>${placed ? "" : marker + " "}${hl(p.t)}`);
      open = true; placed = true;
    }
    titleBlock = false;
  }
  if (open) out.push("</p>");
  const prev = v.articles[a.i - 1], next = v.articles[a.i + 1];
  const iss = v.issues.find(i => i.id === a.issue);
  setTimeout(() => { if (target) document.getElementById("p" + target)?.scrollIntoView({ block: "center" }); }, 0);
  return `<div class="kicker"><a href="#/vol/${n}">Vol. ${n} (${v.year})</a> · no. ${esc(iss.no)}${a.section && a.section !== "Articles" ? " · " + esc(a.section) : ""}</div>
  <h1>${esc(a.title)}</h1>
  ${a.subtitle ? `<p class="lede">${esc(a.subtitle)}</p>` : ""}
  <p class="fine">${a.author ? esc(a.author) + (a.authorFrom === "signature" ? " (from the signature)" : " (from the volume index)") + " · " : ""}${a.pp ? esc(a.pp) : `pp. ${a.p0}–${a.p1}`}</p>
  <div class="reader">
    <article>${out.join("")}</article>
    <aside class="side">
      <div class="card"><h3>Cite</h3>
        <div class="citebox" id="cite">${esc(cite(v, a))}</div>
        <button class="btn" id="copycite" type="button">Copy citation</button>
        <p class="fine" style="margin-top:.7rem">Page markers such as <span class="pb">${n}:${a.pp ? esc(a.pp.split("–")[0]) : a.p0}</span> give the printed page and open its scan.</p>
      </div>
      <div class="card"><h3>Source</h3>
        <p class="fine">Scan and OCR: Boston College Libraries, <a href="https://archive.org/details/${a.issue}" target="_blank" rel="noopener">${esc(a.issue)}</a>. OCR repaired conservatively; see the <a href="docs/qa/vol${pad3(n)}.md">QA report</a>.</p>
        ${a.indexEntry ? `<p class="fine">Volume index: “${esc(a.indexEntry)}”</p>` : ""}
      </div>
    </aside>
  </div>
  <div class="pager">
    <span>${prev ? `← <a href="#/a/${prev.id}">${esc(prev.title)}</a>` : ""}</span>
    <span>${next ? `<a href="#/a/${next.id}">${esc(next.title)}</a> →` : ""}</span>
  </div>`;
}

/* ---------------------------------------------------------------- search */

// Search and the concordance read the Pagefind index (pagefind/, built by
// tools/build_search.py): one record per printed page and article, with the
// citation in its meta and the volume and section as filters. Only the
// fragments of matching pages are fetched, never whole volumes.
function pagefind() {
  S.pf = S.pf || import("./pagefind/pagefind.js").then(async pf => {
    await pf.options({ excerptLength: 36 });
    await pf.filters();  // loads the filter index, so every search reports its counts
    return pf;
  });
  return S.pf;
}
const noIndex = e => `<p class="fine">The search index is not available (${esc(e.message)}).
  Locally, build it with <span class="mono">python tools/build_search.py</span>.</p>`;
const hitLink = (d, q) => d.url.replace(/^\//, "") + (d.url.includes("?") ? "&" : "?") + "q=" + encodeURIComponent(q);
const fold = s => s.normalize("NFD").replace(/[̀-ͯ]/g, "");
const STOP = new Set(("the a an and or but of to in on at by for with from as is are was were be been being it its " +
  "this that these those he she they we you i his her their our your my me him them us not no nor so such then than " +
  "there here which who whom whose what when where while if all any both each one two had has have having would could " +
  "should shall will may might must can did does done upon into unto also very more most much many other some only " +
  "even about after before over under again once said made came went being").split(" "));

// the filter chips of a result: volume or section, with the page counts Pagefind reports
function filterChips(counts, name, active, href) {
  return Object.entries(counts || {}).filter(([, n]) => n).map(([k, n]) =>
    `<a class="chip ${active === k ? "on" : ""}" href="${href(active === k ? "" : k)}">${esc(k)}<span class="n">${n}</span></a>`).join("");
}

async function viewSearch(params) {
  const q = (params.get("q") || "").trim();
  const vf = params.get("v") || "", sf = params.get("s") || "";
  const link = (o = {}) => "#/search?" + new URLSearchParams(Object.fromEntries(Object.entries(
    { q, v: vf, s: sf, ...o }).filter(([, x]) => x))).toString();
  return {
    html: `<h1>Search</h1>
    <form class="searchbar" id="sform"><input id="q" type="search" value="${esc(q)}" placeholder="e.g. Georgetown, Indian school, retreat, Sabetti" aria-label="Search the full text"><button class="btn" type="submit">Search</button></form>
    <p class="fine">Every word is searched in its inflected forms as well (<i>sodality</i> finds <i>sodalities</i>); put a phrase in
    quotation marks (<a href="#/search?q=%22Sacred%20Heart%22">"Sacred Heart"</a>). Accents are ignored. Results are printed pages,
    best matches first; the <a href="#/concordance${q ? "?q=" + encodeURIComponent(q) : ""}">concordance</a> lists them in the order of the text.</p>
    <div id="sout">${q ? '<p class="fine">Searching …</p>' : ""}</div>`,
    async init() {
      const here = location.hash;
      if (!q) return;
      const out = $("#sout");
      let pf;
      try { pf = await pagefind(); } catch (e) { out.innerHTML = noIndex(e); return; }
      const filters = {};
      if (vf) filters.volume = vf;
      if (sf) filters.section = sf;
      const s = await pf.search(q, { filters });
      if (location.hash !== here) return;  // the reader moved on while we searched
      let shown = 0;
      out.innerHTML = `<p class="fine">${s.results.length} page${s.results.length === 1 ? "" : "s"} ${vf ? "in WL " + esc(vf) : `in ${S.man.volumes.length} volumes`}${sf ? ", " + esc(sf) : ""}.</p>
        <p>${filterChips(s.filters.volume, "v", vf, k => link({ v: k }))}</p>
        <p>${filterChips(s.filters.section, "s", sf, k => link({ s: k }))}</p>
        <div id="hits"></div><p><button class="btn" id="more" type="button" hidden>More results</button></p>`;
      const more = async () => {
        const ds = await Promise.all(s.results.slice(shown, shown + 20).map(r => r.data()));
        if (location.hash !== here) return;  // left the page while loading
        shown += ds.length;
        $("#hits").insertAdjacentHTML("beforeend", ds.map(d => `<div class="kwic">
          <div class="src"><a href="${hitLink(d, q)}">${esc(d.meta.cite)}</a> · ${esc(d.meta.title)}${d.meta.author ? " · " + esc(d.meta.author) : ""}</div>
          <div class="ctx">${d.excerpt}</div></div>`).join(""));  // Pagefind escapes the excerpt and adds only <mark>
        $("#more").hidden = shown >= s.results.length;
      };
      $("#more").onclick = more;
      await more();
    },
  };
}

/* ----------------------------------------------------------- concordance */

const WIN = 64;       // characters of context on each side
const BATCH = 50;     // pages read at a time

async function viewConcordance(params) {
  const q = (params.get("q") || "").trim();
  const sort = params.get("sort") || "text";
  const vf = params.get("v") || "";
  const link = (o = {}) => "#/concordance?" + new URLSearchParams(Object.fromEntries(Object.entries(
    { q, sort, v: vf, ...o }).filter(([, x]) => x))).toString();
  const starts = ["sodality", "retreat", "novices", "Indians", "cholera", "observatory", '"Immaculate Conception"', "Georgetown"];
  return {
    html: `<h1>Concordance</h1>
    <p class="lede">Keyword in context across every volume in full text, in the order of the text, each line cited to its
    printed page and linked to it.</p>
    <form class="searchbar" id="cform"><input id="cq" type="search" value="${esc(q)}" placeholder="Word or phrase …" aria-label="Word or phrase"><button class="btn" type="submit">Search</button></form>
    <p class="fine">A word is found in its inflected forms (<i>sodality, sodalities</i>), which are counted apart below; a phrase
    goes in quotation marks. Accents are ignored.</p>
    ${q ? "" : `<p>${starts.map(t => `<a class="chip" href="#/concordance?q=${encodeURIComponent(t)}">${esc(t)}</a>`).join("")}</p>`}
    <div id="cout">${q.length >= 3 ? '<p class="fine">Searching …</p>' : q ? '<p class="fine">Type at least three characters.</p>' : ""}</div>`,
    async init() {
      const here = location.hash;
      $("#cform").addEventListener("submit", ev => { ev.preventDefault(); location.hash = link({ q: $("#cq").value.trim() }); });
      if (q.length < 3) return;
      const out = $("#cout");
      let pf;
      try { pf = await pagefind(); } catch (e) { out.innerHTML = noIndex(e); return; }
      const s = await pf.search(q, { sort: { order: "asc" }, ...(vf ? { filters: { volume: vf } } : {}) });
      if (location.hash !== here) return;
      const pages = new Map(S.man.volumes.map(m => [`${m.vol} (${m.year})`, m.pages]));
      const counts = (vf ? s.totalFilters : s.filters).volume || {};
      const rate = k => (counts[k] || 0) / (pages.get(k) || 1) * 1000, maxRate = Math.max(1e-9, ...Object.keys(counts).map(rate));
      const rows = [];
      let read = 0;

      // KWIC lines from the word positions Pagefind reports; a run of
      // consecutive positions is one hit (a phrase)
      function lines(d) {
        const w = d.content.split(/\s+/), locs = [...d.locations].sort((a, b) => a - b);
        for (let i = 0; i < locs.length;) {
          let j = i;
          while (j + 1 < locs.length && locs[j + 1] === locs[j] + 1) j++;
          const l = w.slice(Math.max(0, locs[i] - 14), locs[i]).join(" ");
          const r = w.slice(locs[j] + 1, locs[j] + 15).join(" ");
          rows.push({ d, n: rows.length, k: w.slice(locs[i], locs[j] + 1).join(" "),
                      l: l.length > WIN ? l.slice(-WIN) : l, r: r.length > WIN ? r.slice(0, WIN) : r, lcut: l.length > WIN, rcut: r.length > WIN });
          i = j + 1;
        }
      }
      const key = s => fold(s.toLowerCase()).replace(/[^a-z]+/g, " ").trim();
      const cmp = (a, b) => (!a) - (!b) || a.localeCompare(b);  // no context word: last
      function draw() {
        const shown = rows.slice();
        if (sort === "left") shown.sort((x, y) => cmp(key(x.l).split(" ").reverse().join(" "), key(y.l).split(" ").reverse().join(" ")));
        if (sort === "right") shown.sort((x, y) => cmp(key(x.r), key(y.r)));
        const forms = new Map(), coll = new Map();
        const qwords = new Set(key(q).split(" "));
        for (const x of rows) {
          const f = key(x.k);
          forms.set(f, (forms.get(f) || 0) + 1);
          for (const t of [...x.l.split(/\s+/).slice(-5), ...x.r.split(/\s+/).slice(0, 5)]) {
            const c = key(t);
            if (c.length >= 4 && !c.includes(" ") && !STOP.has(c) && !qwords.has(c) && !forms.has(c)) coll.set(c, (coll.get(c) || 0) + 1);
          }
        }
        out.innerHTML = `<div class="grid2">
          <div class="card"><h3>Distribution</h3>
            <table class="dist">${[...pages.keys()].map(k => `<tr>
              <td><a href="${link({ v: vf === k ? "" : k })}" class="${vf === k ? "on" : ""}">WL ${esc(k)}</a></td>
              <td class="num">${counts[k] || 0}</td><td class="num">${rate(k).toFixed(1)}</td>
              <td style="width:45%"><div class="bar"><i style="width:${Math.round(100 * rate(k) / maxRate)}%"></i></div></td></tr>`).join("")}
            </table>
            <p class="fine" style="margin:.5rem 0 0">Pages with a match, and per 1,000 pages. Click a volume to read only its lines.</p></div>
          <div class="card"><h3>Forms</h3>
            <p>${[...forms].sort((a, b) => b[1] - a[1]).slice(0, 12).map(([f, n]) => `<span class="chip">${esc(f)}<span class="n">${n}</span></span>`).join("")}</p>
            <h3>Collocates <span class="fine">± 5 words</span></h3>
            <p>${[...coll].sort((a, b) => b[1] - a[1]).slice(0, 24).map(([w, n]) =>
              `<a class="chip" href="#/concordance?q=${encodeURIComponent(w)}">${esc(w)}<span class="n">${n}</span></a>`).join("") || '<span class="fine">none</span>'}</p>
            <p class="fine">From the lines read so far.</p></div>
        </div>
        <div class="tools">${rows.length} line${rows.length === 1 ? "" : "s"} from ${read} of ${s.results.length} pages${vf ? ` in WL ${esc(vf)} (<a href="${link({ v: "" })}">all volumes</a>)` : ""}.
          Sort by <select id="csort" aria-label="Sort lines">${[["text", "order in the text"], ["left", "word to the left"], ["right", "word to the right"]]
            .map(([k, t]) => `<option value="${k}" ${k === sort ? "selected" : ""}>${t}</option>`).join("")}</select></div>
        <div class="scroll"><table class="conc"><tbody>${shown.map(x => `<tr>
          <td class="l">${x.lcut ? "…" : ""}${esc(x.l)}</td><td class="k">${esc(x.k)}</td><td class="r">${esc(x.r)}${x.rcut ? "…" : ""}</td>
          <td class="ref"><a href="${hitLink(x.d, q)}" title="${esc(x.d.meta.title)}">${esc(x.d.meta.cite.replace(/ \(\d{4}\)/, ""))}</a></td></tr>`).join("")}</tbody></table></div>
        ${read < s.results.length ? `<p><button class="btn" id="cmore" type="button">Read ${Math.min(BATCH, s.results.length - read)} more pages</button></p>` : ""}`;
        $("#csort").addEventListener("change", ev => { location.hash = link({ sort: ev.target.value }); });
        $("#cmore")?.addEventListener("click", more);
      }
      async function more() {
        const ds = await Promise.all(s.results.slice(read, read + BATCH).map(r => r.data()));
        if (location.hash !== here) return;  // left the page while loading
        read += ds.length;
        ds.forEach(lines);
        draw();
      }
      if (!s.results.length) { out.innerHTML = `<p class="fine">No page matches.</p>`; return; }
      await more();
    },
  };
}

/* ----------------------------------------------------------------- atlas */

const SECTION_LABEL = { Articles: "articles", Varia: "Varia", Obituary: "obituaries", Supplement: "supplements" };

async function viewAtlas(params) {
  S.atlas = S.atlas || await getJSON("data/atlas.json");
  const A = S.atlas;
  const nb = new Map(A.nodes.map(n => [n.id, []]));
  for (const e of A.edges) { nb.get(e.s).push([e.t, e]); nb.get(e.t).push([e.s, e]); }
  const node = new Map(A.nodes.map(n => [n.id, n]));
  // terms whose neighbours reach into the most sections, then the best connected
  const bridges = A.nodes.map(n => ({ id: n.id, span: new Set(nb.get(n.id).map(([m]) => node.get(m).sec)).size, deg: nb.get(n.id).length }))
    .filter(b => b.deg >= 4).sort((a, b) => b.span - a.span || b.deg - a.deg).slice(0, 18);
  const words = new Map(S.man.volumes.map(m => [m.vol, m.words]));

  function panel(id) {
    const n = node.get(id);
    if (!n) return `<h3>Selection</h3><p class="fine">Click a term for its neighbours and its spread across the volumes.</p>`;
    const rates = A.vols.map((v, i) => n.dist[i] / (words.get(v) || 1) * 1e4), mx = Math.max(...rates, 1e-9);
    return `<h3>${esc(n.id)}</h3>
      <p class="fine">${n.f} occurrences · centre of gravity in the ${SECTION_LABEL[n.sec]}</p>
      <table class="dist">${A.vols.map((v, i) => `<tr><td>WL ${v}</td><td class="num">${n.dist[i]}</td>
        <td style="width:50%"><div class="bar"><i style="width:${Math.round(100 * rates[i] / mx)}%"></i></div></td></tr>`).join("")}</table>
      <p class="fine" style="margin:.3rem 0 .8rem">Bars: occurrences per 10,000 words of each volume.</p>
      <h3 style="font-size:.95rem">Strongest neighbours</h3>
      <p>${nb.get(id).sort((a, b) => b[1].pmi * Math.log(1 + b[1].f) - a[1].pmi * Math.log(1 + a[1].f)).slice(0, 16)
        .map(([m, e]) => `<button class="chip" type="button" data-n="${esc(m)}" title="${e.f} shared sentences · PMI ${e.pmi}">${esc(m)}</button>`).join("")}</p>
      <a class="btn" href="#/concordance?q=${encodeURIComponent(id)}">Concordance →</a>`;
  }

  return {
    html: `<h1>Atlas</h1>
    <p class="lede">What stands next to what. Two terms are joined when they occur in the same sentence more often than chance
    allows. The terms are the journal's own vocabulary: words the Letters use far more often than English at large.
    Colour marks the section in which a term is most at home. Scroll or double-click to zoom, drag to pan.</p>
    <div class="chartbox">
      <div class="tools">
        <label>Density <select id="dens">${[[80, "sparse (80 terms)"], [140, "medium (140 terms)"], [200, "dense (200 terms)"], [999, "everything"]]
          .map(([k, t]) => `<option value="${k}" ${k === 140 ? "selected" : ""}>${t}</option>`).join("")}</select></label>
        <button class="btn" id="reheat" type="button">Re-arrange</button>
        <button class="btn" id="zin" type="button" aria-label="Zoom in">+</button>
        <button class="btn" id="zout" type="button" aria-label="Zoom out">−</button>
        <button class="btn" id="zreset" type="button">Reset</button>
      </div>
      <canvas id="net" aria-label="Co-occurrence network of the journal's vocabulary"></canvas>
      <div class="legend" style="margin-top:.6rem">${A.sections.map(s =>
        `<span><i class="sec" style="background:var(--sec-${s.toLowerCase()})"></i>${SECTION_LABEL[s]}</span>`).join("")}</div>
    </div>
    <div class="grid2">
      <div class="card" id="sel">${panel(params.get("t"))}</div>
      <div class="card"><h3>Terms that bridge the sections</h3>
        <p class="fine">Terms whose neighbours reach into the most sections: the vocabulary that holds the journal together.</p>
        <p>${bridges.map(b => `<button class="chip" type="button" data-n="${esc(b.id)}">${esc(b.id)}<span class="n">${b.deg}</span></button>`).join("")}</p></div>
    </div>
    <p class="fine">${A.nodes.length} terms and ${A.edges.length} links from ${A.sentences.toLocaleString("en")} sentences in vols.
    ${A.vols[0]}–${A.vols.at(-1)}. Built by <span class="mono">tools/build_atlas.py</span>; derived data, CC0.</p>`,
    init() {
      const show = id => {
        $("#sel").innerHTML = panel(id);
        bind($("#sel"));
      };
      const bind = root => root.querySelectorAll("[data-n]").forEach(b => b.onclick = () => { S.net.select(b.dataset.n); show(b.dataset.n); });
      const build = () => {
        S.net?.stop();
        const lim = +$("#dens").value;
        const keep = new Set(A.nodes.slice().sort((a, b) => b.f - a.f).slice(0, lim).map(n => n.id));
        S.net = network($("#net"), {
          nodes: A.nodes.filter(n => keep.has(n.id)),
          edges: A.edges.filter(e => keep.has(e.s) && keep.has(e.t)),
        }, { h: Math.min(600, Math.max(380, innerHeight * .62)), onSelect: show });
        if (params.get("t")) S.net.select(params.get("t"));
      };
      $("#dens").onchange = build;
      $("#reheat").onclick = () => S.net.reheat();
      $("#zin").onclick = () => S.net.zoomBy(1.4);
      $("#zout").onclick = () => S.net.zoomBy(1 / 1.4);
      $("#zreset").onclick = () => S.net.resetView();
      bind(document);
      build();
    },
  };
}

/* ---------------------------------------------------------------- people */

const CLS = { father: "Fathers", brother: "Brothers", mr: "Mr. (scholastics, laymen)", prelate: "bishops, cardinals", pope: "popes" };

async function viewPeople(params) {
  S.people = S.people || await getJSON("data/people.json");
  const P = S.people;
  const node = new Map(P.nodes.map(n => [n.id, n]));
  const nb = new Map(P.nodes.map(n => [n.id, []]));
  for (const e of P.edges) { nb.get(e.s).push([e.t, e]); nb.get(e.t).push([e.s, e]); }
  const words = new Map(S.man.volumes.map(m => [m.vol, m.words]));
  const artLink = id => { const a = P.articles[id]; return a ? `<a href="#/a/${id}">${esc(a.t)}</a> <span class="fine">WL ${a.v} (${a.y}): ${esc(String(a.p))}</span>` : ""; };
  const surname = n => n.id.split(":")[1];
  const hubs = P.nodes.map(n => ({ n, deg: nb.get(n.id).length })).sort((a, b) => b.deg - a.deg || b.n.f - a.n.f).slice(0, 18);

  function panel(id) {
    const n = node.get(id);
    if (!n) return `<h3>Selection</h3><p class="fine">Click a person, or find one by name, to see who is named with them, and where.</p>`;
    const rates = P.vols.map((v, i) => n.dist[i] / (words.get(v) || 1) * 1e4), mx = Math.max(...rates, 1e-9);
    const links = nb.get(id).sort((a, b) => b[1].w - a[1].w).slice(0, 16);
    return `<h3>${esc(n.name)}</h3>
      <p class="fine">${CLS[n.cls]} · named ${n.f} times${n.obit ? " · obituary " + artLink(n.obit) : ""}</p>
      <table class="dist">${P.vols.map((v, i) => n.dist[i] ? `<tr><td>WL ${v}</td><td class="num">${n.dist[i]}</td>
        <td style="width:50%"><div class="bar"><i style="width:${Math.round(100 * rates[i] / mx)}%"></i></div></td></tr>` : "").join("")}</table>
      <h3 style="font-size:.95rem;margin-top:.8rem">Named with</h3>
      <p>${links.map(([m, e]) => `<button class="chip" type="button" data-n="${esc(m)}" title="named together in ${e.f} paragraph${e.f === 1 ? "" : "s"}">${esc(node.get(m).name)}<span class="n">${e.f}</span></button>`).join("") || '<span class="fine">no links</span>'}</p>
      ${n.wrote ? `<h3 style="font-size:.95rem">Wrote</h3><ul class="plain">${n.wrote.map(a => `<li>${artLink(a)}</li>`).join("")}</ul>` : ""}
      <h3 style="font-size:.95rem">Named most in</h3><ul class="plain">${n.arts.map(a => `<li>${artLink(a)}</li>`).join("")}</ul>
      <a class="btn" href="#/concordance?q=${encodeURIComponent(surname(n))}">Concordance →</a>`;
  }

  return {
    html: `<h1>People</h1>
    <p class="lede">Who is named with whom. Two persons are joined when the Letters name them in the same paragraph,
    in two paragraphs at least; a paragraph that lists many names counts for less. Colour marks the class the title gives.
    Scroll or double-click to zoom, drag to pan.</p>
    <div class="chartbox">
      <div class="tools">
        <label>Density <select id="dens">${[[80, "sparse (80 persons)"], [160, "medium (160 persons)"], [999, "everyone"]]
          .map(([k, t]) => `<option value="${k}" ${k === 160 ? "selected" : ""}>${t}</option>`).join("")}</select></label>
        <input id="who" list="whos" placeholder="Find a person …" aria-label="Find a person" style="min-width:14rem">
        <datalist id="whos">${P.nodes.map(n => `<option value="${esc(n.name)}">`).join("")}</datalist>
        <button class="btn" id="reheat" type="button">Re-arrange</button>
        <button class="btn" id="zin" type="button" aria-label="Zoom in">+</button>
        <button class="btn" id="zout" type="button" aria-label="Zoom out">−</button>
        <button class="btn" id="zreset" type="button">Reset</button>
      </div>
      <div class="tools">${Object.keys(CLS).filter(c => P.nodes.some(n => n.cls === c)).map(c =>
        `<button class="chip on" type="button" data-cls="${c}"><i class="sw" style="background:var(--cls-${c})"></i>${CLS[c]}</button>`).join("")}</div>
      <canvas id="net" aria-label="Network of persons named together"></canvas>
    </div>
    <div class="grid2">
      <div class="card" id="sel">${panel(params.get("id"))}</div>
      <div class="card"><h3>Most connected</h3>
        <p class="fine">The persons named with the most others.</p>
        <p>${hubs.map(h => `<button class="chip" type="button" data-n="${esc(h.n.id)}">${esc(h.n.name)}<span class="n">${h.deg}</span></button>`).join("")}</p></div>
    </div>
    <p class="fine">${P.nodes.length} persons and ${P.edges.length} links from ${P.paragraphs.toLocaleString("en")} paragraphs that name someone,
    vols. ${P.vols[0]}–${P.vols.at(-1)}. A person is a title and a surname (“Father Sabetti”, “Cardinal Gibbons”); namesakes are kept
    apart only where the text gives them different first names or initials, so two men of one name may still share a node. Offices
    (“Father General”, “Father Rector”) are not persons. Built by <span class="mono">tools/build_people.py</span>; derived data, CC0.</p>`,
    init() {
      let shown = params.get("id");
      const show = id => { shown = id; $("#sel").innerHTML = panel(id); bind($("#sel")); };
      const bind = root => root.querySelectorAll("[data-n]").forEach(b => b.onclick = () => { S.net.select(b.dataset.n); show(b.dataset.n); });
      const on = new Set(Object.keys(CLS));
      const build = () => {
        S.net?.stop();
        const lim = +$("#dens").value;
        const keep = new Set(P.nodes.filter(n => on.has(n.cls)).slice(0, lim).map(n => n.id));
        S.net = network($("#net"), {
          nodes: P.nodes.filter(n => keep.has(n.id)),
          edges: P.edges.filter(e => keep.has(e.s) && keep.has(e.t)).map(e => ({ ...e, f: e.w })),
        }, { h: Math.min(620, Math.max(400, innerHeight * .66)), onSelect: show, color: n => `--cls-${n.cls}`, labelCap: 30 });
        if (params.get("id")) S.net.select(params.get("id"));
      };
      document.querySelectorAll("[data-cls]").forEach(b => b.onclick = () => {
        on.has(b.dataset.cls) ? on.delete(b.dataset.cls) : on.add(b.dataset.cls);
        b.classList.toggle("on"); build();
      });
      $("#who").addEventListener("change", ev => {
        // "change" fires again when the box loses focus: pick a person once
        const n = P.nodes.find(x => x.name === ev.target.value);
        if (n && n.id !== shown) { S.net.select(n.id); show(n.id); }
        ev.target.value = "";
      });
      $("#dens").onchange = build;
      $("#reheat").onclick = () => S.net.reheat();
      $("#zin").onclick = () => S.net.zoomBy(1.4);
      $("#zout").onclick = () => S.net.zoomBy(1 / 1.4);
      $("#zreset").onclick = () => S.net.resetView();
      bind(document);
      build();
    },
  };
}

function viewAbout() {
  return `<div class="prose">
  <h1>About &amp; rights</h1>
  <h2>The journal</h2>
  <p>The <em>Woodstock Letters</em> (1872–1969) were printed at Woodstock College, Maryland, the Jesuit scholasticate
  of the Maryland and New York provinces, as “a record of current events and historical notes connected with the
  colleges and missions of the Society of Jesus”. They circulated privately among the Jesuits themselves.</p>
  <h2>Source</h2>
  <p>Boston College Libraries scanned the run in 2015. The scans and the ABBYY OCR are at the Internet Archive
  (collection <a href="https://archive.org/details/woodstockletters" target="_blank" rel="noopener">woodstockletters</a>).
  This edition uses only the page-addressed OCR text and links to the scans. It does not copy any images.</p>
  <h2>Method</h2>
  <ol>
    <li><b>Pages.</b> Running heads are stripped. Printed page numbers are recomputed by consensus over neighbouring
    pages, because single OCR digits are unreliable. Every number overruled in this way is listed in the QA report.</li>
    <li><b>Articles.</b> An article starts at a title page, at a mid-page heading that the following running heads repeat,
    or at a start page named in the volume index. Authors are taken from the volume index, otherwise from a closing signature.</li>
    <li><b>Repair.</b> Two things are repaired: line-end hyphenation, and recurrent OCR confusions such as the <i>ct</i>
    ligature read as “6l” or “dl”. A repair is made only when the word is unknown and the repaired form is a common English word.
    Every repair is logged.</li>
    <li><b>Search and concordance.</b> Both read a prebuilt index (<a href="https://pagefind.app/" target="_blank" rel="noopener">Pagefind</a>)
    with one record per printed page and article, so the browser fetches only the pages that match. A word is found in its
    inflected forms (<i>sodality, sodalities</i>) and accents are ignored; a phrase goes in quotation marks. The concordance reads
    the matching pages in the order of the text, cuts each line from the positions of the match, and counts the forms apart.
    Its distribution counts pages with a match per volume. Collocates are the content words within five words of a hit, in the lines read so far.</li>
    <li><b>Atlas.</b> The terms are the journal's own vocabulary: content words the Letters use at least four times more
    often than English at large (the <i>wordfreq</i> list), ranked by keyness. Two terms are joined when they share at
    least six sentences and occur together more often than chance (positive pointwise mutual information). Each term keeps
    its eight strongest links. A term's colour is the section (articles, Varia, obituaries, supplements) in which it is
    relatively most frequent. The network is rebuilt with every batch of volumes, so it describes the volumes in full text, not the whole run.</li>
    <li><b>People.</b> Persons are found by title and surname (“Father Sabetti”, “Fr. J. J. Ryan”, “Cardinal Gibbons”, “Pope Pius X”).
    The title gives the class; bishops, archbishops, cardinals and monsignori are one class, because the same man is first Bishop,
    then Archbishop Carroll. Offices such as “Father General” are not persons. Namesakes are kept apart only where the text gives
    them different first names or initials; a bare “Father Ryan” is assigned to the Ryan named in the same article, if there is only one.
    Two persons are joined when they are named in the same paragraph, in two paragraphs at least, and a paragraph naming <i>n</i>
    persons counts 1/(<i>n</i> − 1) towards each of its links, so that a list of appointments does not outweigh a letter.
    The class is read from the title in use, so a scholastic (“Mr. Stanton”) and the same man as a priest (“Father Stanton”) are two nodes.</li>
  </ol>
  <p>The QA reports are published: ${S.man.volumes.map(v => `<a href="docs/qa/vol${pad3(v.vol)}.md">vol. ${v.vol}</a>`).join(", ")}.</p>
  <h2>Rights: three tiers</h2>
  <ul>
    <li><b>1872–${PD_CUTOFF}.</b> Public domain in the United States (published more than 95 years ago). Full text.</li>
    <li><b>${PD_CUTOFF + 1}–1963.</b> Public domain only if the copyright was not renewed. The renewal records still have
    to be checked. There is a further question: the issues bear “for circulation among Ours only”, so they may not
    count as published at all. Until this is clarified with the rights holders, the edition shows these volumes as catalogue only.</li>
    <li><b>1964–1969.</b> Presumed in copyright. Catalogue only.</li>
  </ul>
  <p>Each January the cutoff moves forward by one year, and the site computes it from the date.</p>
  <h2>Licences</h2>
  <p>Code: MIT. Editorial texts: CC BY 4.0. Derived data (catalogue, pagination, article delimitation, repairs): CC0 1.0.
  The public-domain text itself is not claimed.</p>
  <h2>Citation</h2>
  <p class="citebox">Fassbender, Pantaleon. <i>Woodstock Letters: A Research Edition</i> (pilot, ${new Date().getFullYear()}). ${SITE}</p>
  <p class="fine">A companion to <a href="https://ignatian-research.netlify.app/" target="_blank" rel="noopener">Ignatiana</a>
  and to the psycholinguistic study of the Woodstock Letters corpora (replication package on <a href="https://zenodo.org/records/22697014" target="_blank" rel="noopener">Zenodo</a>).</p>
  </div>`;
}

/* ---------------------------------------------------------------- router */

async function route() {
  const raw = location.hash.slice(1) || "/";
  const [path, qs] = raw.split("?");
  const params = new URLSearchParams(qs || "");
  const seg = path.split("/").filter(Boolean);
  const r = seg[0] || "home";
  document.querySelectorAll("#nav a").forEach(a => a.classList.toggle("active",
    a.dataset.r === r || (a.dataset.r === "volumes" && (r === "vol" || r === "a"))));
  const view = $("#view");
  S.net?.stop(); S.net = null;
  try {
    // a view returns its HTML, or { html, init } when it wires itself up after rendering
    let out;
    if (r === "home") out = viewHome();
    else if (r === "volumes") out = viewVolumes();
    else if (r === "vol") out = await viewVolume(+seg[1]);
    else if (r === "a") out = await viewArticle(seg[1], params);
    else if (r === "search") out = await viewSearch(params);
    else if (r === "concordance") out = await viewConcordance(params);
    else if (r === "atlas") out = await viewAtlas(params);
    else if (r === "people") out = await viewPeople(params);
    else if (r === "about") out = viewAbout();
    else out = `<h1>Not found</h1>`;
    view.innerHTML = typeof out === "string" ? out : out.html;
    Promise.resolve(out.init?.()).catch(e => {
      view.insertAdjacentHTML("beforeend", `<p class="mono">Something went wrong: ${esc(e.message)}</p>`);
    });
  } catch (e) {
    view.innerHTML = `<h1>Something went wrong</h1><p class="mono">${esc(e.message)}</p>`;
  }
  if (!params.get("p")) window.scrollTo(0, 0);
  const t = $("h1", view);
  document.title = (t && r !== "home" ? t.textContent + " · " : "") + "Woodstock Letters · A Research Edition";
  $("#sform")?.addEventListener("submit", ev => {
    ev.preventDefault();
    location.hash = "#/search?q=" + encodeURIComponent($("#q").value.trim());
  });
  $("#copycite")?.addEventListener("click", async ev => {
    try { await navigator.clipboard.writeText($("#cite").textContent); ev.target.textContent = "Copied"; }
    catch { ev.target.textContent = "Select and copy the text above"; }
  });
}

$("#theme").addEventListener("click", () => {
  const light = document.documentElement.getAttribute("data-theme") !== "light";
  document.documentElement.setAttribute("data-theme", light ? "light" : "dark");
  try { localStorage.setItem("wlTheme", light ? "light" : "dark"); } catch (e) {}
  S.net?.redraw();  // the atlas canvas reads its colours from the theme
});
window.addEventListener("hashchange", route);
boot().then(route).catch(e => { $("#view").innerHTML = `<h1>Could not load the catalogue</h1><p class="mono">${esc(e.message)}</p>`; });
