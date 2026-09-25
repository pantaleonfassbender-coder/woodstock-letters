// Build the downloadable manuscript of the introductory essay from
// data/introduction.json, in APA 7 manuscript form (US Letter, 12 pt Times,
// double spacing, title page with author note, abstract, level-1 headings,
// references with hanging indent). The site renders the same JSON, so the
// two never drift apart.
//
//   node tools/build_introduction_docx.js
//
// Needs the npm package "docx" on NODE_PATH or in node_modules.
const fs = require("fs");
const path = require("path");
const D = require("docx");
const { Document, Packer, Paragraph, TextRun, HeadingLevel, AlignmentType, PageBreak,
        PageNumber, Header, Footer, ImageRun, TabStopType } = D;

const ROOT = path.resolve(__dirname, "..");
const e = JSON.parse(fs.readFileSync(path.join(ROOT, "data", "introduction.json"), "utf8"));
const OUT = path.join(ROOT, "docs", "Fassbender-2026-Woodstock-Letters-Introduction.docx");

const FONT = "Times New Roman";
const runs = (s, extra = {}) => s.split(/(\*[^*]+\*)/).filter(Boolean).map(t =>
  t.startsWith("*") ? new TextRun({ text: t.slice(1, -1), italics: true, font: FONT, size: 24, ...extra })
                    : new TextRun({ text: t, font: FONT, size: 24, ...extra }));
const para = (s, opts = {}) => new Paragraph({ children: runs(s, opts.run || {}), spacing: { line: 480 }, ...opts.p });
const body = s => para(s, { p: { indent: { firstLine: 720 }, alignment: AlignmentType.LEFT } });
const centred = (s, extra = {}) => para(s, { p: { alignment: AlignmentType.CENTER }, run: extra });

const runningHead = new Header({ children: [new Paragraph({
  tabStops: [{ type: TabStopType.RIGHT, position: 9360 }],
  children: [new TextRun({ text: "THE WOODSTOCK LETTERS, 1872–1930", font: FONT, size: 24 }),
             new TextRun({ children: ["\t", PageNumber.CURRENT], font: FONT, size: 24 })] })] });

const title = `${e.title}: ${e.subtitle}`;
const titlePage = [
  ...Array(6).fill(0).map(() => new Paragraph({ spacing: { line: 480 } })),
  centred(title, { bold: true }),
  new Paragraph({ spacing: { line: 480 } }),
  centred(e.authors.map(a => a.name).join(" and ")),
  ...e.authors.map(a => centred(a.note.charAt(0).toUpperCase() + a.note.slice(1))),
  new Paragraph({ spacing: { line: 480 } }),
  centred(e.date),
  ...Array(3).fill(0).map(() => new Paragraph({ spacing: { line: 480 } })),
  centred("Author Note", { bold: true }),
  body(e.note.replace(/^Author note\.\s*/, "")),
  new Paragraph({ children: [new PageBreak()] }),
];

const abstract = [
  centred("Abstract", { bold: true }),
  para(e.abstract, { p: { alignment: AlignmentType.LEFT } }),
  para(`*Keywords:* ${e.keywords.join(", ")}`, { p: { indent: { firstLine: 720 } } }),
  new Paragraph({ children: [new PageBreak()] }),
];

const main = [centred(title, { bold: true })];
for (const s of e.sections) {
  if (s.title) main.push(new Paragraph({ heading: HeadingLevel.HEADING_1, alignment: AlignmentType.CENTER, spacing: { line: 480, before: 240 },
    children: [new TextRun({ text: s.title, bold: true, font: FONT, size: 24, color: "000000" })] }));
  for (const p of s.paras) main.push(body(p));
}

// the plate, if the image is there, with its caption in APA figure form
const platePath = path.join(ROOT, "assets", "plates", "college-1871.jpg");
const plates = JSON.parse(fs.readFileSync(path.join(ROOT, "data", "plates.json"), "utf8"));
if (fs.existsSync(platePath)) {
  main.push(new Paragraph({ children: [new PageBreak()] }));
  main.push(para("*Figure 1*", { p: { alignment: AlignmentType.LEFT } }));
  main.push(para("*Woodstock College in 1871*", { p: { alignment: AlignmentType.LEFT } }));
  main.push(new Paragraph({ alignment: AlignmentType.CENTER, children: [new ImageRun({ type: "jpg", data: fs.readFileSync(platePath),
    transformation: { width: 600, height: Math.round(600 * 936 / 1600) } })] }));
  main.push(para(`*Note.* ${plates["college-1871"].caption} ${plates["college-1871"].credit}`, { p: { alignment: AlignmentType.LEFT } }));
}

const refs = [new Paragraph({ children: [new PageBreak()] }), centred("References", { bold: true }),
  ...e.references.map(r => para(r, { p: { indent: { left: 720, hanging: 720 }, alignment: AlignmentType.LEFT } }))];

const doc = new Document({
  creator: e.authors.map(a => a.name).join("; "), title, description: e.abstract.slice(0, 200),
  styles: { default: { document: { run: { font: FONT, size: 24 } } } },
  sections: [{
    properties: { page: { size: { width: 12240, height: 15840 }, margin: { top: 1440, right: 1440, bottom: 1440, left: 1440 } } },
    headers: { default: runningHead },
    children: [...titlePage, ...abstract, ...main, ...refs],
  }],
});
Packer.toBuffer(doc).then(buf => { fs.writeFileSync(OUT, buf); console.log("wrote", path.relative(ROOT, OUT), (buf.length / 1024).toFixed(0), "KB"); });
