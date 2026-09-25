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

const S = { cat: null, man: null, vols: new Map() };

async function getJSON(url) {
  const r = await fetch(url);
  if (!r.ok) throw new Error(`${url}: ${r.status}`);
  return r.json();
}
async function boot() {
  [S.cat, S.man, S.plates] = await Promise.all([getJSON("data/catalogue.json"), getJSON("data/manifest.json"),
    getJSON("data/plates.json").catch(() => ({}))]);
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
const years = n => { const y = [...new Set(S.byVol.get(n).map(i => i.year))]; return y.length > 1 ? `${y[0]}–${String(y.at(-1)).slice(2)}` : `${y[0]}`; };

// A Supplement is paginated on its own ("Suppl. vii") and an unnumbered
// insert is cited by the page it follows; both carry a printed label.
const range = a => a.pp ?? (a.p0 === a.p1 ? `${a.p0}` : `${a.p0}–${a.p1}`);
const plab = pg => pg.pl ?? pg.p;

function cite(v, a, page) {
  const pages = page ? page : range(a);
  return `${a.author ? a.author + ", " : ""}“${a.title},” Woodstock Letters ${v.vol} (${v.year}): ${pages}. ${SITE}#/a/${a.id}`;
}

/* ------------------------------------------------------------------ views */

// A plate cut from a public-domain page image (registry data/plates.json, files
// assets/plates/ID.jpg with a _t thumbnail). The image links to its source: the
// scan leaf in the IA viewer, or the atlas at the Library of Congress.
function plate(id, cls = "", thumb = false) {
  const p = (S.plates || {})[id];
  if (!p) return "";
  const href = p.href || (p.issue ? IA(p.issue, p.ia) : null);
  const img = `<img src="assets/plates/${id}${thumb ? "_t" : ""}.jpg" alt="${esc(p.caption)}" loading="lazy">`;
  return `<figure class="plate ${cls}">${href ? `<a class="zoom" href="${href}" target="_blank" rel="noopener" title="Open the source">${img}</a>` : img}
    <figcaption><b>${esc(p.caption)}</b><br>${esc(p.credit).replace(/https?:\/\/\S+?(?=[.,]?(\s|$))/g, u => `<a href="${u}" target="_blank" rel="noopener">${u}</a>`)}</figcaption></figure>`;
}

function viewHome() {
  const vols = [...S.built].sort((a, b) => a - b);
  const first = vols[0], last = vols.at(-1);
  const issues = vols.reduce((s, n) => s + S.byVol.get(n).length, 0);
  const words = S.man.volumes.reduce((s, v) => s + v.words, 0);
  const arts = S.man.volumes.reduce((s, v) => s + v.articles, 0);
  const pages = S.man.volumes.reduce((s, v) => s + v.pages, 0);
  const runLast = Math.max(...S.cat.issues.map(i => i.year));
  const runVols = S.byVol.size;
  return `
  <div class="kicker">Research edition</div>
  <h1>The Woodstock Letters, ${S.byVol.get(first)[0].year}–${S.byVol.get(last).at(-1).year}</h1>
  <p class="lede">For almost a century the Jesuits of North America wrote to one another in a journal printed
  “for circulation among Ours only” at Woodstock College, Maryland: mission reports, college histories, obituaries,
  letters from the frontier and from abroad. The journal ran to ${runVols} volumes, from 1872 to ${runLast}.
  This edition gives the full text of the volumes in the public domain, vols. ${first}–${last}
  (${S.byVol.get(first)[0].year}–${S.byVol.get(last).at(-1).year}), citable page by page, with every page linked to its scan.</p>
  <p class="fine">New here? The <a href="#/introduction">introductory essay</a> describes the journal, the source,
  the method and the apparatus, and can be downloaded as a manuscript.</p>
  <div class="hero">${plate("college-1920")}${plate("map-1877")}</div>
  <div class="stats">
    <div class="stat"><b>${vols.length}</b><span>volumes in full text</span></div>
    <div class="stat"><b>${issues}</b><span>issues</span></div>
    <div class="stat"><b>${pages.toLocaleString("en")}</b><span>pages</span></div>
    <div class="stat"><b>${arts.toLocaleString("en")}</b><span>articles delimited</span></div>
    <div class="stat"><b>${(words / 1e6).toFixed(1)}M</b><span>words edited</span></div>
  </div>
  <h2>The volumes</h2>
  <p class="fine">One cell per volume. Open a volume for its contents.</p>
  <div class="run">${vols.map(n => `<a href="#/vol/${n}" class="t-full" title="Vol. ${n} (${years(n)})">${n}<small>${String(S.byVol.get(n)[0].year).slice(2)}</small></a>`).join("")}</div>
  <div class="grid2" style="margin-top:2rem">
    <div class="card"><h3>Cite by volume and page</h3>
      <p>Every paragraph sits on its printed page, so any passage can be cited as <span class="mono">WL 29 (1900): 46</span>
      and checked against the scan in one click. The page numbers are recomputed from the running heads, not trusted from the OCR.</p></div>
    <div class="card"><h3>Built openly</h3>
      <p>The text is Boston College's scan and OCR, repaired conservatively. Every repair, every overruled page number and
      every correction made by hand is listed in a public QA report, so nothing is silently changed.
      See <a href="#/about">About &amp; rights</a>.</p></div>
  </div>
  <h2 style="margin-top:2.4rem">The place and its makers</h2>
  <p class="fine">Plates from the journal itself, the Golden Jubilee number of 1920 and Dooley's <i>Woodstock and Its Makers</i> of 1927,
  and from the county atlas of 1877. Each opens its source; the whole set is on the <a href="#/plates">plates page</a>.</p>
  <div class="gallery">${["college-1871", "map-county-1877", "community-chart", "disputation", "mortuary-chapel", "keller"].map(id => plate(id, "", true)).join("")}</div>`;
}

function viewPlates() {
  const ids = Object.keys(S.plates || {}).filter(k => k !== "_note");
  return `<div class="kicker">Plates</div><h1>Woodstock in pictures</h1>
  <p class="lede">The illustrations the journal printed of its own house, and two maps: the college as drawn in 1871 and photographed
  about 1920, the makers of Woodstock as Dooley's history portrayed them in 1927, the library, the cemetery, and the place on the
  Patapsco as the county atlas of 1877 recorded it. Every plate is cut from a public-domain page image and links to its source.</p>
  <div class="grid2">${ids.map(id => plate(id, ["keller", "mazzella", "pantanella", "pantanella-1920", "dooley-title"].includes(id) ? "portrait" : "")).join("")}</div>
  <p class="fine" style="margin-top:1.6rem">Faithful reproduction of a public-domain two-dimensional work adds nothing licensable; the plates are as free as
  their sources. The captions and credits are CC0. Sources leaf by leaf: <a href="data/plates.json">data/plates.json</a>.</p>`;
}

/* The register: the headings and references of the printed general index
   (Zorn 1960, vols. 1–80), data/general_index.json. A reference to a
   full-text volume opens the page; one to vols. 60–80 opens the scan. */
async function viewRegister(params) {
  S.gi = S.gi || await getJSON("data/general_index.json");
  const q = (params.get("q") || "").trim().toLowerCase();
  const letter = (params.get("l") || (q ? "" : "A")).toUpperCase();
  const es = S.gi.entries.filter(e => q ? (e.h + " " + e.q).toLowerCase().includes(q) : e.h.toUpperCase().replace(/^(SS?T?|MT|FT)\. /, "").startsWith(letter));
  const KIND = { obit: "obituary", auth: "author", rev: "review", pic: "picture", letter: "letters", sketch: "sketch" };
  const built = [...S.built].sort((a, b) => a - b);
  const ref = r => {
    const [v, p] = r, kinds = r[2] ? r[2].split(",").map(k => KIND[k] || k).join(", ") : "";
    const full = S.built.has(v);
    const iss = S.byVol.get(v);
    const href = full ? `#/p/${v}/${p}` : iss ? `https://archive.org/details/${iss[0].id}` : null;
    return `<a class="pb${full ? "" : " ext"}" ${href ? `href="${href}"` : ""} ${full ? "" : 'target="_blank" rel="noopener"'} title="${full ? "open the page in the edition" : "vol. " + v + " is not in full text: the scan of the volume"}${kinds ? " · " + kinds : ""}">${v}:${p}${kinds ? `<small> ${kinds}</small>` : ""}</a>`;
  };
  const letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ".split("").map(L => `<a class="chip${L === letter && !q ? " on" : ""}" href="#/register?l=${L}">${L}</a>`).join("");
  return `<div class="kicker">Register</div><h1>Persons, places and things, 1872–1951</h1>
  <p class="lede">The headings and references of the printed <i>Woodstock Letters Index, Volumes 1–80, 1872–1951</i>, compiled by
  George Zorn, S.J. (Woodstock College Press, 1960): ${S.gi.entries.length.toLocaleString("en")} headings with
  ${S.gi.entries.reduce((s, e) => s + e.refs.length, 0).toLocaleString("en")} references. A reference to vols. ${built[0]}–${built.at(-1)} opens the page in
  the edition; one to vols. ${built.at(-1) + 1}–80 opens the scan of the volume. The compiler marked obituaries, authors, reviews and pictures, and those marks are kept.</p>
  <p class="fine">The index of 1960 is not in the public domain. The edition takes from it only facts, the headings and the volume-and-page references, and
  reproduces none of its descriptive phrases; an entry here therefore reads “Gibbons, James Cardinal 11:226”, not what the compiler said about the reference.
  The OCR of the index is read by rule, so a few headings and numbers are wrong; the scan is at the
  <a href="https://archive.org/details/${S.gi.item}" target="_blank" rel="noopener">Internet Archive</a>.</p>
  <form class="searchbar" id="rform"><input id="rq" type="search" value="${esc(params.get("q") || "")}" placeholder="a surname, a place, a mission" aria-label="Search the register"><button class="btn" type="submit">Find</button></form>
  <div class="tools">${letters}</div>
  <p class="fine">${es.length.toLocaleString("en")} heading${es.length === 1 ? "" : "s"}${q ? ` for “${esc(q)}”` : ""}.</p>
  <table class="reg"><tbody>${es.slice(0, 1500).map(e => `<tr><td class="h"><b>${esc(e.h)}</b>${e.q ? `, ${esc(e.q)}` : ""}</td><td>${e.refs.map(ref).join(" ")}</td></tr>`).join("")}</tbody></table>
  ${es.length > 1500 ? `<p class="fine">First 1,500 shown; narrow the search.</p>` : ""}`;
}

/* Reading paths (data/paths.json): curated routes through the edition, a
   guiding question per path and a note per station. A path marked
   "discourse" shows each station's measures of voice from data/discourse.json. */
async function viewPaths(id) {
  S.paths = S.paths || await getJSON("data/paths.json");
  const P = S.paths.paths;
  if (!id) {
    return `<div class="kicker">Reading paths</div><h1>Seven ways through sixty years</h1>
    <p class="lede">A path is a short reading list with a question: six to nine articles of the edition in an order that makes
    an argument, each with a note on what to read it for. The paths are the editor's; the notes marked <span class="tag">draft</span>
    were written with the language model and are still to be revised.</p>
    <div class="grid2">${P.map(p => `<div class="card"><div class="kicker">${esc(p.years)} · ${p.stations.length} stations${p.status === "draft" ? " · draft" : ""}</div>
      <h3><a href="#/paths/${p.id}">${esc(p.title)}</a></h3><p class="fine" style="font-family:var(--serif);font-size:.95rem;color:var(--fg2)">${esc(p.question)}</p></div>`).join("")}</div>`;
  }
  const p = P.find(x => x.id === id);
  if (!p) return `<h1>No path “${esc(id)}”</h1><p><a href="#/paths">All paths</a></p>`;
  const arts = await Promise.all(p.stations.map(async s => {
    const v = await vol(+s.a.split("-")[0]);
    return { s, v, a: v.byId.get(s.a) };
  }));
  let disc = null;
  if (p.discourse) {
    S.disc = S.disc || await getJSON("data/discourse.json").catch(() => null);
    disc = S.disc ? new Map(S.disc.articles.map(o => [o.id, o])) : null;
  }
  const measure = o => o ? `<table class="bio"><tr><td>we</td><td>${(100 * (o.n.we || 0) / o.wc).toFixed(2)} %</td></tr>
    <tr><td>I</td><td>${(100 * (o.n.i || 0) / o.wc).toFixed(2)} %</td></tr>
    <tr><td>positive emotion</td><td>${(100 * (o.n.posemo || 0) / o.wc).toFixed(2)} %</td></tr>
    <tr><td>achievement</td><td>${(100 * (o.n.achievement || 0) / o.wc).toFixed(2)} %</td></tr>
    <tr><td>words</td><td>${o.wc.toLocaleString("en")}</td></tr></table>` : "";
  const i = P.indexOf(p), prev = P[i - 1], next = P[i + 1];
  return `<div class="kicker"><a href="#/paths">Reading paths</a> · ${esc(p.years)}${p.status === "draft" ? " · <span class='tag'>draft notes</span>" : ""}</div>
  <h1>${esc(p.title)}</h1>
  <p class="lede"><b>${esc(p.question)}</b></p>
  <p class="prose" style="font-family:var(--serif);font-size:1.02rem">${esc(p.intro)}</p>
  <ol class="stations">${arts.map(({ s, v, a }, k) => a ? `<li>
      <div class="st-head"><span class="st-n">${k + 1}</span>
        <a class="ti" href="#/a/${a.id}${s.p ? `?p=${s.p}` : ""}">${esc(a.title)}</a>
        <span class="fine">${a.author ? esc(a.author) + " · " : ""}WL ${v.vol} (${v.year}): ${esc(range(a))}</span></div>
      <p class="st-note">${esc(s.note)}</p>
      ${disc ? measure(disc.get(a.id)) : ""}</li>` : `<li><span class="st-n">${k + 1}</span> <span class="mono">${esc(s.a)}</span> not found</li>`).join("")}</ol>
  ${p.discourse ? `<p class="fine">Measures: the study's open word lists as percentages of the article's words (<a href="#/discourse">Discourse</a>);
    the corpus means of the study are 0.79 % <i>we</i> and 0.58 % <i>I</i> over its twenty-two texts.</p>` : ""}
  <div class="pager"><span>${prev ? `← <a href="#/paths/${prev.id}">${esc(prev.title)}</a>` : ""}</span><span>${next ? `<a href="#/paths/${next.id}">${esc(next.title)}</a> →` : ""}</span></div>`;
}

/* The statistical tables (data/tables.json, files in data/tables/): the
   journal's fold-out tables as OCR text and best-effort CSV, by kind and year. */
async function viewTables(params) {
  S.tables = S.tables || await getJSON("data/tables.json");
  const kind = params.get("k") || "ministeria";
  const kinds = S.tables.kinds;
  const rows = S.tables.tables.filter(t => t.kind === kind);
  return `<div class="kicker">Tables</div><h1>The journal's statistics</h1>
  <p class="lede">From the 1880s the <i>Letters</i> printed each year the <i>Ministeria spiritualia</i> of every house of the province
  (baptisms, confessions, communions, marriages, sermons, retreats), the number of students in every college of the United States and Canada,
  and the list of the dead. They stand on fold-out leaves without page numbers, which the edition's text leaves out like plates.
  This page gives them as the OCR read them, line by line, with a best-effort CSV: each row is a label and the run of numbers on its line.
  The column headings of a fold-out are usually read as a jumble, so the meaning of the columns is to be taken from the scan, which each row opens.</p>
  <div class="tools">${Object.entries(kinds).map(([k, l]) => `<a class="chip${k === kind ? " on" : ""}" href="#/tables?k=${k}">${esc(l)}<span class="n">${S.tables.tables.filter(t => t.kind === k).length}</span></a>`).join("")}</div>
  <table><thead><tr><th>Vol.</th><th>Year</th><th>Heading as read</th><th>Where</th><th>Lines</th><th>Rows</th><th>Files</th><th>Scan</th></tr></thead><tbody>
  ${rows.map(t => `<tr><td><a href="#/vol/${t.vol}">${t.vol}</a></td><td>${t.year}</td><td class="fine">${esc(t.heading)}</td><td class="fine">${esc(t.where || "")}</td>
    <td class="num">${t.lines}</td><td class="num">${t.rows}</td>
    <td><a href="data/tables/${t.file}.txt">text</a> · <a href="data/tables/${t.file}.csv">csv</a></td>
    <td><a href="${IA(t.issue, t.n)}" target="_blank" rel="noopener">leaf ${t.leaf} ↗</a></td></tr>`).join("")}</tbody></table>
  <p class="fine" style="margin-top:1rem">Built by <span class="mono">tools/extract_tables.py</span>; nothing is corrected by hand. The files are CC0 like the rest of the derived data.</p>`;
}

// #/p/VOL/PAGE: the article that holds a printed page, opened at that page
async function viewPage(volNo, page) {
  if (!S.built.has(volNo)) return viewVolume(volNo);
  const v = await vol(volNo);
  const pg = v.pages.find(x => x.kind === "text" && x.p === page && !x.pl);
  const id = pg?.paras.find(q => q.a)?.a;
  if (!id) return `<h1>Vol. ${volNo}, p. ${page}</h1><p class="lede">No page ${page} in vol. ${volNo} of the edition (the printed index may cite a
    supplement, a misprinted folio or a page missing from the scan). <a href="#/vol/${volNo}">Contents of vol. ${volNo}</a>.</p>`;
  location.replace(`#/a/${id}?p=${page}`);
  return "";
}

/* The introductory essay (data/introduction.json): the first mention of each
   instrument links to it, so the essay doubles as a guided entrance. The same
   file is the source of the downloadable manuscript in docs/. */
const INTRO_LINKS = [
  ["Golden Jubilee number", "#/vol/49"], ["Woodstock and Its Makers", "#/a/56-003"],
  ["Search and concordance", "#/concordance"], ["Atlas", "#/atlas"], ["People", "#/people"], ["Discourse", "#/discourse"],
  ["QA report", "docs/qa/vol029.md"], ["progress notes", "docs/PROGRESS.md"], ["validation report", "docs/discourse_validation.md"],
  ["catalogue", "#/volumes"], ["plates", "#/plates"]
];
const emi = s => esc(s).replace(/\*([^*]+)\*/g, "<em>$1</em>");
const linkify = h => h.replace(/https?:\/\/[^\s<]+?(?=[.,;)]?(\s|$|<))/g, u => `<a href="${u}" target="_blank" rel="noopener">${u}</a>`);
async function viewIntroduction() {
  S.intro = S.intro || await getJSON("data/introduction.json");
  const e = S.intro, used = new Set();
  const fmt = s => {
    let h = emi(s);
    for (const [phrase, href] of INTRO_LINKS) {
      if (used.has(phrase)) continue;
      const i = h.indexOf(phrase);
      if (i < 0) continue;
      used.add(phrase);
      h = h.slice(0, i) + `<a href="${href}">${phrase}</a>` + h.slice(i + phrase.length);
    }
    // the edition's own citation form opens the page cited
    return h.replace(/WL (\d+) \((\d{4})\): (\d+)(?:–\d+)?/g, (m, v, y, p) => `<a href="#/a/${v}-${String(p).padStart(3, "0")}" title="Open in the edition">${m}</a>`);
  };
  const authors = e.authors.map(a => `${esc(a.name)}${a.orcid ? ` <a href="${a.orcid}" target="_blank" rel="noopener" class="fine">ORCID</a>` : ""} <span class="fine">(${esc(a.note)})</span>`).join(" · ");
  return `<div class="essay">
    <div class="kicker">Introductory essay</div>
    <h1>${esc(e.title)}: ${esc(e.subtitle)}</h1>
    <p class="note">${authors}<br>${esc(e.date)} · version ${esc(e.version)} · editorial matter of this site, CC BY 4.0 ·
      <a href="docs/Fassbender-2026-Woodstock-Letters-Introduction.docx">manuscript (.docx, APA 7)</a></p>
    <div class="abstract"><p><b>Abstract.</b> ${fmt(e.abstract)}</p><p><b>Keywords:</b> ${e.keywords.map(esc).join("; ")}</p></div>
    ${e.sections.map(s => `${s.title ? `<h2>${esc(s.title)}</h2>` : ""}${s.paras.map(p => `<p>${fmt(p)}</p>`).join("")}`).join("")}
    <figure class="plate">${plate("college-1871").replace(/^<figure class="plate ">|<\/figure>$/g, "")}</figure>
    <h2>References</h2>
    <div class="refs">${e.references.map(r => `<p>${linkify(emi(r))}</p>`).join("")}</div>
    <p class="note" style="margin-top:1.6rem">${linkify(emi(e.note))}</p>
    <div class="citebox">${esc(e.citation)}</div>
  </div>`;
}

/* Legal notice and privacy: every statement below describes code in this
   repository. Change the code, change this text. */
function viewImprint() {
  return `<div class="prose legal">
  <div class="kicker">Legal notice &amp; privacy</div>
  <h1>Who operates this site, and what it does with data</h1>
  <div class="card"><h2>Operator</h2>
    <p>Dr. Pantaleon Fassbender<br>16751 NE 5th Street<br>Williston, FL 32696<br>United States<br>
    Email: <a href="mailto:pantaleonfassbender@gmail.com">pantaleonfassbender@gmail.com</a></p>
    <p>This site is a personal research project, operated and hosted in the United States by a private individual, and not on
    behalf of any institution, employer, publisher or religious order. It carries no advertising and no sponsorship.
    Responsible for its content: Dr. Pantaleon Fassbender, at the address above.</p></div>
  <div class="card"><h2>Rights in the texts</h2>
    <p>The edition gives the volumes of the <i>Woodstock Letters</i> published before 1 January ${PD_CUTOFF + 1}, which are in the
    public domain in the United States, from the scans Boston College Libraries placed in the Internet Archive. The later volumes
    are listed but not reproduced. The plates are cut from public-domain page images and name their source leaf by leaf. If you hold
    rights in any material shown here and consider its use to exceed what the public domain and scholarly citation permit, write to the
    address above and it will be dealt with promptly. The full account is in <a href="RIGHTS.md">RIGHTS.md</a>.</p></div>
  <div class="card"><h2>What this site is, technically</h2>
    <p>A set of static files: HTML, CSS, JavaScript and JSON data, with a prebuilt search index. There are no user accounts, no login,
    no contact form, no newsletter and no server function of the site's own. The site sets <b>no cookies</b>. It uses no analytics of its own,
    no tag manager, no advertising and no session recording. It loads <b>nothing from third-party servers</b>: fonts are the system's, the
    search library (Pagefind) and every data file are served from this site itself. Links to the Internet Archive, the Library of Congress,
    the Jesuit Online Necrology, Zenodo, GitHub and ORCID are ordinary outbound links; nothing from those sites is embedded here, and they
    receive a request only when you follow a link.</p></div>
  <div class="card"><h2>Stored on your own device</h2>
    <p>One value only: your choice of light or dark theme, kept in the browser's <span class="mono">localStorage</span> under the key
    <span class="mono">wlTheme</span> so that the site opens the way you left it. It is not transmitted anywhere. Clearing site data for this
    domain removes it. Nothing else is stored.</p></div>
  <div class="card"><h2>Server logs and performance measurement</h2>
    <p>The site is hosted by Netlify, Inc. (San Francisco, USA). Like any web server, Netlify records the requests it serves, typically the
    IP address, the time, the URL, the status, the amount of data and the browser's user-agent and referrer strings. This is technically
    unavoidable in delivering a website and is used to operate and secure the service; the operator does not analyse it. Retention follows
    Netlify's own periods.</p>
    <p>Netlify also injects a small script, <span class="mono">/.netlify/scripts/rum</span>, into the pages it serves for this site. It is
    Netlify's real-user metrics: it measures how quickly the page loaded in your browser and reports those timings, with the page's URL and
    coarse technical data, to Netlify, where the operator can see them aggregated. It sets no cookie and builds no profile. It is the one
    thing on this site that is not the operator's own code, and it is stated here for that reason.</p>
    <p>Where the General Data Protection Regulation applies to a reader, the legal basis for both is Article 6(1)(f), the legitimate interest in
    delivering a functioning, secure website and knowing that it performs. The site is operated and hosted in the United States, so for readers
    in the European Economic Area these request data are processed outside the EEA, by the operator and by Netlify as hosting provider.</p></div>
  <div class="card"><h2>Rights of readers in the European Economic Area</h2>
    <p>Where the GDPR applies, you have the rights of access, rectification, erasure, restriction, portability and objection
    (Articles 15–21), and the right to lodge a complaint with a supervisory authority (Article 77). Requests go to the address above. In practice
    the answer is short: apart from the server logs and metrics described, this site holds nothing about you. No representative in the Union
    has been designated under Article 27; the operator relies on Article 27(2)(a), because the processing is occasional, involves no special
    categories of data and is unlikely to result in a risk to the rights and freedoms of natural persons.</p></div>
  <div class="card"><h2>Notice for California residents</h2>
    <p>Under the California Online Privacy Protection Act: the only personally identifiable information collected is internet or network
    activity information in the server logs and performance metrics described above. No name, address, email or other identifier is collected,
    because the site has no field in which to enter one. The only third party with which such information is shared is the hosting provider,
    Netlify, Inc. Nothing is sold, rented or shared for marketing. The site does not track visitors over time or across sites and therefore
    does not respond to Do Not Track signals; there is no tracking to switch off.</p></div>
  <div class="card"><h2>Liability, warranty, children</h2>
    <p>External links were checked when set; their content is the responsibility of their operators, and any link will be removed promptly on
    evidence of a problem. The edition is a research instrument offered free of charge and without warranty. Its text is a repaired OCR, its
    article delimitation and its networks are editorial work that can be wrong, and its limits are set out under
    <a href="#/about">About &amp; rights</a> and in the <a href="#/introduction">introduction</a>; verify anything you intend to publish against
    the scans. The site is addressed to adult readers and knowingly collects no information from children.</p></div>
  <p class="fine">Effective 25 September 2026. Where this notice and the site's behaviour diverge, the notice is wrong and will be corrected.</p>
  </div>`;
}

function viewVolumes() {
  const vols = [...S.built].sort((a, b) => a - b);
  return `<h1>Volumes</h1>
  <p class="lede">The public-domain volumes, ${vols[0]}–${vols.at(-1)}, in full text, with the scans of each issue at the
  Internet Archive (Boston College Libraries).</p>
  <table><thead><tr><th>Vol.</th><th>Year</th><th>Issues (scans)</th><th>Articles</th><th>Pages</th></tr></thead><tbody>
  ${vols.map(n => {
    const m = S.man.volumes.find(x => x.vol === n);
    return `<tr><td><a href="#/vol/${n}">${n}</a></td><td>${years(n)}</td>
      <td>${S.byVol.get(n).map(i => `<a href="https://archive.org/details/${i.id}" target="_blank" rel="noopener">no.&nbsp;${esc(i.no)}${i.season ? " " + esc(i.season) : ""}</a>`).join(" · ")}</td>
      <td class="num">${m.articles}</td><td class="num">${m.pages}</td></tr>`;
  }).join("")}</tbody></table>
  <h2 style="margin-top:2.4rem">The run to ${Math.max(...S.cat.issues.map(i => i.year))}</h2>
  <p class="fine">The journal went on after ${PD_CUTOFF}. These volumes are outside the public domain or not yet cleared
  (see <a href="RIGHTS.md">RIGHTS.md</a>); the edition catalogues them and links their scans, and gives no text.
  Vols. ${vols.at(-1) + 1}–80 are covered by the <a href="#/register">register</a>, which links their references to the scans.</p>
  <table><thead><tr><th>Vol.</th><th>Year</th><th>Issues (scans)</th><th>Status</th></tr></thead><tbody>
  ${[...S.byVol.keys()].filter(n => !S.built.has(n)).sort((a, b) => a - b).map(n => {
    const last = Math.max(...S.byVol.get(n).map(i => i.year));
    const status = last <= PD_CUTOFF ? "public domain, queued" : last <= 1963 ? "renewal check pending" : "presumed in copyright";
    return `<tr><td>${n}</td><td>${years(n)}</td>
      <td>${S.byVol.get(n).map(i => `<a href="https://archive.org/details/${i.id}" target="_blank" rel="noopener">no.&nbsp;${esc(i.no)}${i.season ? " " + esc(i.season) : ""}</a>`).join(" · ")}</td>
      <td><span class="tag">${status}</span></td></tr>`;
  }).join("")}</tbody></table>
  ${S.cat.extras.map(x => `<p class="fine" style="margin-top:1rem">Also held: <a href="https://archive.org/details/${x.id}" target="_blank" rel="noopener">${esc(x.label)}</a>,
    the printed general index compiled by George Zorn, S.J. (1960); its headings and references are the edition's <a href="#/register">register</a>.</p>`).join("")}`;
}

async function viewVolume(n) {
  if (!S.byVol.has(n)) return `<h1>No volume ${n}</h1>`;
  const head = `<div class="kicker">Volume ${n} · ${years(n)}</div><h1>Woodstock Letters, vol. ${n}</h1>`;
  if (!S.built.has(n)) {
    const vols = [...S.built].sort((a, b) => a - b);
    return `${head}<p class="lede">This edition covers the volumes in the public domain, vols. ${vols[0]}–${vols.at(-1)}.
      Vol. ${n} is not among them. <a href="#/volumes">All volumes in the edition</a>.</p>`;
  }
  const v = await vol(n);
  let html = `${head}<p><span class="fine">${v.articles.length} articles · ${S.man.volumes.find(x => x.vol === n).pages} pages · <a href="docs/qa/vol${pad3(n)}.md">QA report</a></span></p>`;
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

// The texts of Fassbender's study that the edition holds (data/discourse_study.json, from
// tools/validate_discourse.py): the article page names the study and sets its values beside the edition's.
async function studyCard(id) {
  S.dstudy = S.dstudy || await getJSON("data/discourse_study.json").catch(() => ({ years: {} }));
  const t = (S.dstudy.texts || []).find(t => t.ids.includes(id));
  if (!t) return "";
  const K = [["we", "we"], ["i", "I"], ["certainty", "certainty"], ["achievement", "achievement"], ["WPS", "words per sentence"]];
  const f = (k, x) => k === "WPS" ? x.toFixed(1) : x.toFixed(2);
  let rows, what;
  if (t.ids.length === 1) {
    S.disc = S.disc || await getJSON("data/discourse.json");
    const o = S.disc.articles.find(a => a.id === id);
    const ed = k => k === "WPS" ? (o.ns ? o.wc / o.ns : 0) : 100 * (o.n[k] || 0) / o.wc;
    what = `one of the study's texts of ${t.year}${t.opt ? " (an optional text, left out of its corpus means)" : ""}`;
    rows = `<tr><th></th><th>study</th><th>edition</th></tr>` +
      K.map(([k, l]) => `<tr><td>${l}${k === "WPS" ? "" : " %"}</td><td>${f(k, t.pkg[k])}</td><td>${f(k, ed(k))}</td></tr>`).join("");
  } else {
    const others = t.ids.filter(x => x !== id);
    what = `part of the study's ${t.jubilee ? "Golden Jubilee corpus" : "corpus"} of ${t.year}, with ${others.map(x => `<a href="#/a/${x}">${esc(x)}</a>`).join(" and ")}`;
    rows = `<tr><th></th><th>corpus of ${t.year}</th></tr>` +
      K.map(([k, l]) => `<tr><td>${l}${k === "WPS" ? "" : " %"}</td><td>${f(k, t.pkg[k])}</td></tr>`).join("");
  }
  return `<div class="card"><h3>In the study</h3>
        <p class="fine">This article is ${what} in P. Fassbender, “Identity and Values in U.S. Jesuit Discourse, 1890–1944”
        (replication package, <a href="https://doi.org/10.5281/zenodo.22697014" target="_blank" rel="noopener">doi:10.5281/zenodo.22697014</a>).
        Open word lists, as percentages of words:</p>
        <table class="bio">${rows}</table>
        <p class="fine"><a href="#/discourse?y=${t.year}">Its year in the Discourse view</a> ·
        <a href="docs/discourse_validation.md">validation report</a></p>
      </div>`;
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
  <p class="fine">${a.author ? esc(a.author) + (a.authorFrom === "signature" ? " (from the signature)" : a.authorFrom === "general index" ? " (from the general index of 1960)" : " (from the volume index)") + " · " : ""}${a.pp ? esc(a.pp) : `pp. ${a.p0}–${a.p1}`}</p>
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
      ${await studyCard(id)}
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
  // biodata of the Jesuits from the Jesuit Online Necrology (tools/fetch_necrology.py)
  S.necro = S.necro || await getJSON("data/necrology.json").catch(() => ({ persons: {} }));
  const P = S.people, NEC = S.necro;
  const MON = ["Jan.", "Feb.", "March", "April", "May", "June", "July", "Aug.", "Sept.", "Oct.", "Nov.", "Dec."];
  const day = d => { const m = /^(\d\d)-(\d\d)-(\d{4})$/.exec(d || ""); return m ? `${+m[1]} ${MON[+m[2] - 1]} ${m[3]}` : esc(d || ""); };
  function bio(b) {
    if (!b) return "";
    const row = (k, d, pl) => d || pl ? `<tr><td>${k}</td><td>${day(d)}${pl ? `, ${esc(pl)}` : ""}</td></tr>` : "";
    return `<table class="bio">
        ${row("Born", b.born, b.birthplace)}
        ${row("Entered", b.entered, b.province)}
        ${row("Final vows", b.vows, null)}
        ${row("Died", b.died, b.deathplace)}
        ${b.grade || b.status ? `<tr><td>Grade</td><td>${esc([b.grade, b.status].filter(Boolean).join(", "))}</td></tr>` : ""}
      </table>
      <p class="fine">From the <a href="${esc(NEC.url + b.id)}" target="_blank" rel="noopener">Jesuit Online Necrology</a>
      (${esc(b.name)}), after Mendizábal's <i>Catalogus defunctorum</i>.</p>`;
  }
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
      ${bio(NEC.persons[id])}
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
    (“Father General”, “Father Rector”) are not persons. Built by <span class="mono">tools/build_people.py</span>; derived data, CC0.
    Dates and places of birth, entry and death for ${Object.keys(NEC.persons).length} of the Jesuits come from the
    <a href="https://jesuitonlinenecrology.bc.edu/" target="_blank" rel="noopener">Jesuit Online Necrology</a> (Boston College
    Libraries, with the Archivum Romanum Societatis Iesu and the Woodstock Theological Library), matched by name and, where the
    Letters print an obituary, by the year of death; a man is matched only when one record fits.</p>`,
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

/* ------------------------------------------------------------- discourse */

// The open word lists of Fassbender, "Identity and Values in U.S. Jesuit Discourse,
// 1890–1944" (replication package, CC BY 4.0), applied by tools/build_discourse.py to
// every article, with the study's filters, sentence count and MATTR.
const DCAT = {
  we: "First-person plural (we)", i: "First-person singular (I)", certainty: "Certainty", achievement: "Achievement",
  affiliation: "Affiliation", power: "Power", posemo: "Positive emotion", negemo: "Negative emotion", future: "Future orientation",
  WPS: "Words per sentence", MATTR: "Lexical diversity (MATTR-200)"
};
const DREG = {
  essay: "Essays and addresses", letter: "Letters and reports", document: "Documents and reprints",
  official: "Papal and Father General's letters", review: "Reviews and queries", table: "Tables and lists",
  varia: "Varia", obituary: "Obituaries"
};
// the study's historiographical frame, and the anniversaries the Letters themselves kept
const DEVENTS = [
  [1891, "Tercentenary of St. Aloysius"], [1894, "Woodstock College, silver jubilee"],
  [1897, "The Letters' silver jubilee"], [1899, "Testem benevolentiae"], [1907, "Pascendi dominici gregis"],
  [1914, "Centenary of the Restoration"], [1920, "Woodstock College, golden jubilee"],
  [1930, "Canonization of the North American Martyrs"]
];

async function viewDiscourse(params) {
  S.disc = S.disc || await getJSON("data/discourse.json");
  S.dstudy = S.dstudy || await getJSON("data/discourse_study.json").catch(() => ({ years: {} }));
  const D = S.disc, ST = S.dstudy.years;
  const inStudy = new Set((S.dstudy.texts || []).flatMap(t => t.ids));
  const byYear = {};
  for (const t of S.dstudy.texts || []) (byYear[t.year] = byYear[t.year] || []).push(t);
  const titleOf = id => D.articles.find(a => a.id === id)?.t || id;
  const cat = DCAT[params.get("c")] ? params.get("c") : "we";
  const regs = new Set((params.get("r") || "essay").split(",").filter(r => DREG[r]));
  const us = params.get("us") !== "0", adj = params.get("adj") === "1", agg = params.get("agg") === "median" ? "median" : "mean";
  const com = ["all", "ordinary", "commemorative", "split"].includes(params.get("com")) ? params.get("com") : "split";
  const min = +(params.get("min") || 300), yearSel = +params.get("y") || null;
  const state = { c: cat, r: [...regs].join(","), us: us ? "" : "0", adj: adj ? "1" : "", agg: agg === "median" ? "median" : "", com, min: min === 300 ? "" : min, y: yearSel || "" };
  const link = (o = {}) => "#/discourse?" + new URLSearchParams(Object.fromEntries(Object.entries({ ...state, ...o })
    .filter(([, x]) => x !== "" && x != null))).toString();
  const hasAdj = cat in (D.articles[0]?.adj || {});

  // one value per article
  const val = a => cat === "WPS" ? (a.ns ? a.wc / a.ns : null) : cat === "MATTR" ? a.mattr
    : 100 * ((adj && hasAdj ? a.adj : a.n)[cat]) / a.wc;
  const pool = D.articles.filter(a => regs.has(a.reg) && (!us || !a.fx) && a.wc >= min && val(a) != null);
  const groups = com === "split" ? [["ordinary", pool.filter(a => !a.com)], ["commemorative", pool.filter(a => a.com)]]
    : [[com, com === "all" ? pool : pool.filter(a => (com === "commemorative") === a.com)]];

  // a year's value: the word-count-weighted mean over its articles (as the study's corpus means),
  // or their median; the band is a bootstrap over the articles (5th–95th percentile)
  let seed = 7;
  const rnd = () => (seed = (seed * 16807) % 2147483647) / 2147483647;
  const stat = arr => {
    if (agg === "median") { const v = arr.map(val).sort((x, y) => x - y); const m = v.length >> 1; return v.length % 2 ? v[m] : (v[m - 1] + v[m]) / 2; }
    let s = 0, w = 0; for (const a of arr) { s += val(a) * a.wc; w += a.wc; } return s / w;
  };
  const yearsAll = [...new Set(D.articles.map(a => a.y))].sort((a, b) => a - b);
  const series = groups.map(([name, arts]) => {
    const by = new Map();
    for (const a of arts) { if (!by.has(a.y)) by.set(a.y, []); by.get(a.y).push(a); }
    const pts = [...by.entries()].sort((a, b) => a[0] - b[0]).map(([y, arr]) => {
      const boots = [];
      for (let b = 0; b < 200 && arr.length > 1; b++) boots.push(stat(arr.map(() => arr[Math.floor(rnd() * arr.length)])));
      boots.sort((x, z) => x - z);
      return { y, v: stat(arr), lo: boots.length ? boots[10] : null, hi: boots.length ? boots[189] : null, n: arr.length, wc: arr.reduce((s, a) => s + a.wc, 0) };
    });
    return { name, pts };
  });
  const studyKey = cat === "MATTR" ? "MATTR200" : cat;
  const study = Object.entries(ST).map(([y, v]) => ({ y: +y, v: v[studyKey] })).filter(p => p.v != null);

  // the chart: an SVG line over the years, dependency-free
  const W = 900, H = 340, L = 52, R = 14, T = 16, B = 34;
  const x0 = yearsAll[0], x1 = yearsAll.at(-1);
  const all = series.flatMap(s => s.pts.flatMap(p => [p.v, p.hi ?? p.v])).concat(study.filter(p => p.y <= x1).map(p => p.v));
  const ymax = Math.max(...all, 0) * 1.08 || 1, ymin = cat === "WPS" || cat === "MATTR" ? Math.min(...series.flatMap(s => s.pts.map(p => p.lo ?? p.v)), ...study.map(p => p.v)) * 0.92 : 0;
  const X = y => L + (y - x0) / (x1 - x0) * (W - L - R), Y = v => T + (1 - (v - ymin) / (ymax - ymin)) * (H - T - B);
  const colour = { ordinary: "var(--acc2)", commemorative: "var(--acc)", all: "var(--acc2)" };
  const ticks = []; for (let i = 0; i <= 4; i++) { const v = ymin + (ymax - ymin) * i / 4; ticks.push(v); }
  const fmt = v => cat === "WPS" ? v.toFixed(1) : cat === "MATTR" ? v.toFixed(3) : v.toFixed(2);
  const svg = `<svg viewBox="0 0 ${W} ${H}" class="dchart" role="img" aria-label="${esc(DCAT[cat])} by year">
    ${ticks.map(v => `<line x1="${L}" x2="${W - R}" y1="${Y(v)}" y2="${Y(v)}" class="grid"/><text x="${L - 6}" y="${Y(v) + 4}" class="ax" text-anchor="end">${fmt(v)}</text>`).join("")}
    ${DEVENTS.filter(([y]) => y >= x0 && y <= x1).map(([y, t]) => `<line x1="${X(y)}" x2="${X(y)}" y1="${T}" y2="${H - B}" class="ev"><title>${y}: ${esc(t)}</title></line>`).join("")}
    ${[1875, 1880, 1890, 1900, 1910, 1920, 1930].filter(y => y >= x0 && y <= x1).map(y => `<text x="${X(y)}" y="${H - B + 18}" class="ax" text-anchor="middle">${y}</text>`).join("")}
    ${series.map(s => {
      const band = s.pts.filter(p => p.lo != null);
      const poly = band.length > 1 ? `<polygon class="band" style="fill:${colour[s.name]}" points="${band.map(p => `${X(p.y)},${Y(p.hi)}`).join(" ")} ${band.slice().reverse().map(p => `${X(p.y)},${Y(p.lo)}`).join(" ")}"/>` : "";
      const line = s.name === "commemorative" ? "" : `<polyline class="ln" style="stroke:${colour[s.name]}" points="${s.pts.map(p => `${X(p.y)},${Y(p.v)}`).join(" ")}"/>`;
      const dots = s.pts.map(p => s.name === "commemorative"
        ? `<a href="${link({ y: p.y })}"><path class="dia${p.y === yearSel ? " sel" : ""}" d="M${X(p.y)},${Y(p.v) - 6} l6,6 l-6,6 l-6,-6z"><title>${p.y} commemorative: ${fmt(p.v)} (${p.n} pieces, ${p.wc.toLocaleString("en")} words)</title></path></a>`
        : `<a href="${link({ y: p.y })}"><circle class="pt${p.y === yearSel ? " sel" : ""}" style="fill:${colour[s.name]}" cx="${X(p.y)}" cy="${Y(p.v)}" r="${p.y === yearSel ? 5.5 : 3.5}"><title>${p.y}: ${fmt(p.v)} (${p.n} articles, ${p.wc.toLocaleString("en")} words)</title></circle></a>`).join("");
      return (s.name === "commemorative" ? "" : poly) + line + dots;
    }).join("")}
    ${study.filter(p => p.y >= x0 && p.y <= x1).map(p => `<rect class="st" x="${X(p.y) - 5}" y="${Y(p.v) - 5}" width="10" height="10"><title>Study, ${p.y}: ${fmt(p.v)}</title></rect>`).join("")}
  </svg>`;

  // the year opened: its articles, by their share of the category's words
  let drill = "";
  if (yearSel) {
    const arts = pool.filter(a => a.y === yearSel).map(a => ({ a, v: val(a) })).sort((p, q) => q.v - p.v);
    drill = `<h2 id="dyear">${yearSel}: ${arts.length} article${arts.length === 1 ? "" : "s"} in the selection</h2>
      <table class="dist dlist"><thead><tr><td>Article</td><td>Register</td><td class="num">Words</td><td class="num">${esc(DCAT[cat])}</td></tr></thead><tbody>
      ${arts.map(({ a, v }) => `<tr><td><a href="#/a/${a.id}">${esc(a.t)}</a> <span class="fine">WL ${a.v} · ${esc(a.id)}</span>${a.com ? ' <span class="tag">commemorative</span>' : ""}${inStudy.has(a.id) ? ' <span class="tag">in the study</span>' : ""}</td>
        <td>${esc(DREG[a.reg])}</td><td class="num">${a.wc.toLocaleString("en")}</td><td class="num">${fmt(v)}</td></tr>`).join("")}</tbody></table>
      <p class="fine">Open an article to read it with its scans. The ${cat in (D.lists || {}) ? `words counted are: <i>${esc(((adj && hasAdj) ? D.lists[cat].filter(w => !D.jesuit_usage.includes(w)) : D.lists[cat]).join(", "))}</i>.` : "measure is computed over the whole text."}</p>`;
  }
  const csv = "year,group,value,lo,hi,articles,words\n" + series.flatMap(s => s.pts.map(p => [p.y, s.name, p.v, p.lo ?? "", p.hi ?? "", p.n, p.wc].join(","))).join("\n");
  const chip = (k, on, href, label) => `<a class="chip${on ? " on" : ""}" href="${href}">${label}</a>`;
  const regLink = r => { const s = new Set(regs); s.has(r) ? s.delete(r) : s.add(r); return link({ r: [...s].join(",") || "essay" }); };
  return {
    html: `<h1>Discourse</h1>
    <p class="lede">How the Letters speak, year by year: the voice they use (<i>we</i>, <i>I</i>), their certainty, motives and
    feeling, measured with the open word lists of a study of U.S. Jesuit discourse and applied to every article of the edition.
    Choose which kinds of text count. Click a year for its articles.</p>
    <div class="chartbox">
      <div class="tools">
        <label>Measure <select id="dcat">${Object.entries(DCAT).map(([k, t]) => `<option value="${k}" ${k === cat ? "selected" : ""}>${esc(t)}</option>`).join("")}</select></label>
        <label>Year value <select id="dagg"><option value="mean" ${agg === "mean" ? "selected" : ""}>word-weighted mean</option><option value="median" ${agg === "median" ? "selected" : ""}>median article</option></select></label>
        <label>Jubilees <select id="dcom">${[["split", "shown apart"], ["all", "included"], ["ordinary", "left out"], ["commemorative", "only"]].map(([k, t]) => `<option value="${k}" ${k === com ? "selected" : ""}>${t}</option>`).join("")}</select></label>
        ${hasAdj ? `<label title="Leave out Society, order, superior, brother, master, office, will: words that in the Letters mostly name the order and its offices"><input type="checkbox" id="dadj" ${adj ? "checked" : ""}> without Jesuit usage</label>` : ""}
        <label><input type="checkbox" id="dus" ${us ? "checked" : ""}> United States only</label>
      </div>
      <div class="tools">${Object.entries(DREG).map(([k, t]) => chip(k, regs.has(k), regLink(k), esc(t))).join("")}</div>
      ${svg}
      <div class="legend">
        <span><i style="background:var(--acc2)"></i>${com === "commemorative" ? "commemorative pieces" : com === "split" ? "ordinary articles, with a 90 % band" : "articles, with a 90 % band"}</span>
        ${com === "split" ? `<span><i class="dia-k"></i>commemorative pieces (jubilees, centenaries)</span>` : ""}
        <span><i class="st-k"></i>the study's corpus means${ST["1944"] && ST["1944"][studyKey] != null ? ` (1944, beyond the edition: ${fmt(ST["1944"][studyKey])})` : ""}</span>
        <span><i class="ev-k"></i>events (hover)</span>
      </div>
      <p class="fine">${pool.length.toLocaleString("en")} articles, ${pool.reduce((s, a) => s + a.wc, 0).toLocaleString("en")} words, each of at least ${min} words.
        <a download="woodstock-discourse-${cat}.csv" href="data:text/csv;charset=utf-8,${encodeURIComponent(csv)}">Download the series (CSV)</a></p>
    </div>
    ${drill}
    <div class="grid2">
      <div class="card"><h3>The study behind the measures</h3>
        <p>Pantaleon Fassbender's study of U.S. Jesuit discourse, 1890–1944, reads six volumes of the Letters (1890, 1900, 1910,
        1920, 1930, 1944) against <i>America</i> and the secular press. It measures voice, certainty, motives and feeling with
        LIWC and with a set of open word lists that converge with LIWC (r = .85–1.00 for the core categories; power only .67).
        Its main finding is a <b>jubilee effect</b>: the corporate <i>we</i> is concentrated in commemorative writing (about 2 % of
        words in the jubilee essays of 1920 and 1944), while ordinary internal prose is impersonal and administrative (0.5–0.8 %).
        Within the commemorative genre, sentence length, certainty and achievement language rise from 1920 to 1944.</p>
        <p class="fine">Word lists, scripts and per-text results: replication package, CC BY 4.0,
        <a href="https://doi.org/10.5281/zenodo.22697014" target="_blank" rel="noopener">doi:10.5281/zenodo.22697014</a>.
        The squares on the chart are its corpus means.</p>
        <details class="dstudy"><summary>The study's texts in the edition</summary>
          <ul class="plain">${Object.entries(byYear).map(([y, ts]) => `<li><b>${y}</b>${y === "1920" ? " (Golden Jubilee)" : ""}: ${ts.map(t => t.ids.map(x => `<a href="#/a/${x}">${esc(titleOf(x))}</a>`).join(", ") + (t.opt ? " <span class=\"fine\">(optional)</span>" : "")).join("; ")}</li>`).join("")}
          <li><b>1944</b> (Diamond Jubilee): vol. 73, after the public-domain cutoff, so not in the edition.</li></ul>
        </details></div>
      <div class="card"><h3>What the edition adds, and how to read it</h3>
        <ul class="plain">
          <li><b>Every year, 1872–1930.</b> The study's six points become an annual series, and every point opens to its articles.</li>
          <li><b>Registers.</b> Each article is classed as an essay or address, a letter or report, a document or reprint, a papal or
          Father General's letter, a review, a table, Varia or an obituary. The default is essays and addresses on the American
          provinces, close to the study's rule; tick letters to add them, but their <i>we</i> and <i>I</i> run higher (1.3 % and
          1.7 % against 1.0 % and 0.9 % in essays), and their share varies from year to year. The classes are made by rule
          and can be corrected by hand.</li>
          <li><b>Checked against the study.</b> Scored from the edition's text, the study's 22 internal texts give the same values
          (r = .99–1.00 per category; <a href="docs/discourse_validation.md">validation report</a>).</li>
          <li><b>Jubilees.</b> The diamonds are every piece whose title names a jubilee, centenary or anniversary, with the whole of
          an issue given to a jubilee. That is wider than the study's commemorative register, the Woodstock jubilee itself (its 1920
          corpus is two pieces, 49-001 and 49-006): other anniversaries, such as the Spring Hill centennial of 1930, speak in the
          ordinary voice. Across 1872–1930 the flagged pieces are not more collective than ordinary essays (<i>we</i> 0.9 % against
          1.0 %); the contrast lies in particular addresses, not in the occasion as such.</li>
          <li><b>Cautions.</b> The study's texts were chosen for identity; the annual series takes all articles of a register, so its
          level differs. Words per sentence depends on the OCR's punctuation. <i>Society</i>, <i>order</i>, <i>superior</i> and
          <i>brother</i> mostly name the order and its offices: tick “without Jesuit usage” to leave them out. A year with few
          articles has a wide band.</li>
        </ul></div>
    </div>`,
    init() {
      const go = o => { location.hash = link({ ...o, y: o.y ?? yearSel ?? "" }); };
      $("#dcat").onchange = e => go({ c: e.target.value });
      $("#dagg").onchange = e => go({ agg: e.target.value === "median" ? "median" : "" });
      $("#dcom").onchange = e => go({ com: e.target.value });
      $("#dus").onchange = e => go({ us: e.target.checked ? "" : "0" });
      $("#dadj")?.addEventListener("change", e => go({ adj: e.target.checked ? "1" : "" }));
      if (yearSel) $("#dyear")?.scrollIntoView({ block: "nearest" });
    }
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
  This edition uses the page-addressed OCR text and links to the scans. It does not mirror the scans; the only images it
  reproduces are the <a href="#/plates">plates</a>, cut from public-domain issues and from the county atlas of 1877, each with its source.</p>
  <h2>Introduction</h2>
  <p>The <a href="#/introduction">introductory essay</a> describes the journal, the source and its rights, the method and the apparatus,
  and discloses how the edition and the essay were made with a generative AI system, as an experiment in distant writing. It can be downloaded as a manuscript in APA style
  (<a href="docs/Fassbender-2026-Woodstock-Letters-Introduction.docx">.docx</a>).</p>
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
    The class is read from the title in use, so a scholastic (“Mr. Stanton”) and the same man as a priest (“Father Stanton”) are two nodes.
    For the Jesuits, the dates and places of birth, entry, final vows and death come from the
    <a href="https://jesuitonlinenecrology.bc.edu/" target="_blank" rel="noopener">Jesuit Online Necrology</a>, the digital
    edition of Mendizábal's <i>Catalogus defunctorum in renata Societate Iesu</i> (1972) by Boston College Libraries, the
    Archivum Romanum Societatis Iesu and the Woodstock Theological Library. A person is matched by surname and forename
    (English to the Catalogus's Latin), by the year of his obituary in the Letters where there is one, and otherwise by a North
    American province where several records fit; where more than one record still fits, none is shown.</li>
    <li><b>Discourse.</b> Every article is scored with the open word lists of Fassbender's study of U.S. Jesuit discourse
    (replication package, CC BY 4.0, <a href="https://doi.org/10.5281/zenodo.22697014" target="_blank" rel="noopener">doi:10.5281/zenodo.22697014</a>),
    with its paragraph filters (headings, tables and foreign-language paragraphs left out), sentence count and MATTR-200.
    Articles are classed by rule into registers (essays and addresses, letters and reports, documents, papal and Father General's
    letters, reviews, tables, Varia, obituaries) and flagged as commemorative or foreign; corrections are by hand. Scored so, the
    study's own texts give its values (<a href="docs/discourse_validation.md">validation report</a>). The annual means are
    word-weighted, with a 90 % band from resampling the articles of the year.</li>
    <li><b>Register.</b> The headings and volume-and-page references of the printed general index to vols. 1–80 (Zorn, 1960), read from
    the Internet Archive's OCR of it by rule, with the compiler's marks for obituaries, authors, reviews and pictures. Because the index
    of 1960 is not in the public domain, none of its descriptive phrases is kept; see <a href="RIGHTS.md">RIGHTS.md</a>. Its “(auth.)”
    marks supply authors for otherwise unsigned pieces, shown as “from the general index of 1960”. <a href="#/register">Open the register</a>.</li>
    <li><b>Tables.</b> The journal's fold-out statistics (<i>Ministeria spiritualia</i>, students in the colleges, the list of the dead) as the OCR
    read them, line by line, with a best-effort CSV per table and a link to the scan; nothing corrected by hand. <a href="#/tables">Open the tables</a>.</li>
    <li><b>Reading paths.</b> Seven curated routes (<span class="mono">data/paths.json</span>): a question, an order of articles and a note per
    station; the jubilee path shows each station's measures of voice. Notes marked <i>draft</i> were written with the language model and await
    the editor's revision. <a href="#/paths">Open the paths</a>.</li>
    <li><b>Checks.</b> <span class="mono">tools/check_edition.py</span> verifies before each commit that the manifest, the volume files, the plates,
    the essay's citations, the register and the legal notice's claim of no third-party loads agree.</li>
  </ol>
  <p>The QA reports are published: ${S.man.volumes.map(v => `<a href="docs/qa/vol${pad3(v.vol)}.md">vol. ${v.vol}</a>`).join(", ")}.</p>
  <h2>Rights</h2>
  <p>The edition gives the volumes published before 1 January ${PD_CUTOFF + 1}, vols. ${[...S.built].sort((a, b) => a - b)[0]}–${Math.max(...S.built)}
  (1872–${PD_CUTOFF}), which are in the public domain in the United States. The journal went on to 1969; the later
  volumes are outside the public domain or not yet cleared, and the edition does not include them. Each January the
  cutoff moves forward by one year. See <a href="RIGHTS.md">RIGHTS.md</a>.</p>
  <h2>Licences</h2>
  <p>Code: MIT. Editorial texts: CC BY 4.0. Derived data (catalogue, pagination, article delimitation, repairs): CC0 1.0.
  The public-domain text itself is not claimed.</p>
  <h2>Citation</h2>
  <p>A passage is cited by volume, year and printed page:</p>
  <ul>
    <li><span class="mono">WL 29 (1900): 46</span>, a page;</li>
    <li><span class="mono">WL 54 (1925): 104*</span>, a page with an asterisked folio (vol. 54 no. 2 and the asterisked section
    of vol. 56 no. 1 repeat numbers already used in their volume, and the journal marks them so);</li>
    <li><span class="mono">WL 30 (1901): Suppl. vii</span>, a page of a Supplement paginated on its own;</li>
    <li><span class="mono">WL 30 (1901): insert after p. 332</span>, an unnumbered insert, by the page it follows.</li>
  </ul>
  <p>The edition itself:</p>
  <p class="citebox">Fassbender, Pantaleon. <i>Woodstock Letters: A Research Edition</i> (${new Date().getFullYear()}). ${SITE}</p>
  <p>The introductory essay:</p>
  <p class="citebox">Fassbender, P. (2026). The Woodstock Letters, 1872–1930: An introduction to a research edition. <i>Woodstock Letters: A Research Edition</i>. ${SITE}#/introduction</p>
  <p class="fine">A companion to <a href="https://ignatian-research.netlify.app/" target="_blank" rel="noopener">Ignatiana</a>
  and to the psycholinguistic study of the Woodstock Letters corpora (replication package on <a href="https://zenodo.org/records/22697014" target="_blank" rel="noopener">Zenodo</a>).
  Operator and privacy: <a href="#/imprint">legal notice</a>.</p>
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
    else if (r === "discourse") out = await viewDiscourse(params);
    else if (r === "about") out = viewAbout();
    else if (r === "introduction") out = await viewIntroduction();
    else if (r === "register") out = await viewRegister(params);
    else if (r === "p") out = await viewPage(+seg[1], +seg[2]);
    else if (r === "tables") out = await viewTables(params);
    else if (r === "paths") out = await viewPaths(seg[1]);
    else if (r === "plates") out = viewPlates();
    else if (r === "imprint" || r === "privacy") out = viewImprint();
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
  $("#rform")?.addEventListener("submit", ev => {
    ev.preventDefault();
    location.hash = "#/register?q=" + encodeURIComponent($("#rq").value.trim());
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
