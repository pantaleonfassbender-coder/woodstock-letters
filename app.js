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

async function viewSearch(params) {
  const q = (params.get("q") || "").trim();
  let res = "";
  if (q) {
    const terms = q.toLowerCase().match(/[\p{L}\d']+/gu) || [];
    const res_ = [];
    for (const m of S.man.volumes) {
      const v = await vol(m.vol);
      for (const pg of v.pages) {
        if (pg.kind !== "text") continue;
        for (const p of pg.paras) {
          if (!p.a) continue;
          const low = p.t.toLowerCase();
          if (terms.every(t => new RegExp(`\\b${t.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}`, "u").test(low)))
            res_.push({ v, pg, p });
          if (res_.length >= 300) break;
        }
      }
    }
    const hl = highlighter(q);
    res = `<p class="fine">${res_.length >= 300 ? "First 300" : res_.length} passage${res_.length === 1 ? "" : "s"} in ${S.man.volumes.length} volume${S.man.volumes.length === 1 ? "" : "s"}.</p>` +
      res_.map(({ v, pg, p }) => {
        const a = v.byId.get(p.a);
        const low = p.t.toLowerCase(), i = Math.max(0, low.indexOf(terms[0]) - 160);
        const ctx = (i ? "… " : "") + p.t.slice(i, i + 360) + (i + 360 < p.t.length ? " …" : "");
        return `<div class="kwic"><div class="src"><a href="#/a/${a.id}?${pg.insert ? "" : `p=${pg.p}&`}q=${encodeURIComponent(q)}">WL ${v.vol}: ${esc(String(plab(pg)))}</a> · ${esc(a.title)}${a.author ? " · " + esc(a.author) : ""}</div><div class="ctx">${hl(ctx)}</div></div>`;
      }).join("");
  }
  return `<h1>Search</h1>
  <form class="searchbar" id="sform"><input id="q" type="search" value="${esc(q)}" placeholder="e.g. Georgetown, Indian school, retreat, Sabetti" aria-label="Search the full text"><button class="btn" type="submit">Search</button></form>
  <p class="fine">All words must occur in the same paragraph. The pilot searches the volumes in full text; the full edition will use a prebuilt index (Pagefind).</p>
  ${res}`;
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
  try {
    let html;
    if (r === "home") html = viewHome();
    else if (r === "volumes") html = viewVolumes();
    else if (r === "vol") html = await viewVolume(+seg[1]);
    else if (r === "a") html = await viewArticle(seg[1], params);
    else if (r === "search") html = await viewSearch(params);
    else if (r === "about") html = viewAbout();
    else html = `<h1>Not found</h1>`;
    view.innerHTML = html;
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
});
window.addEventListener("hashchange", route);
boot().then(route).catch(e => { $("#view").innerHTML = `<h1>Could not load the catalogue</h1><p class="mono">${esc(e.message)}</p>`; });
