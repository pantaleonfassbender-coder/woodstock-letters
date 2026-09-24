/* net.js — a force-directed network on a canvas, no library. Ported from
   Ignatiana's viz.js (MIT, same author): Fruchterman–Reingold with cooling,
   labels in screen space whose budget grows with the zoom, pointer events so
   that it also works by touch. Colours come from the CSS custom properties,
   read at draw time, so the canvas follows the theme. */
"use strict";

function netTheme() {
  const cs = getComputedStyle(document.documentElement);
  const v = n => cs.getPropertyValue(n).trim();
  return {
    acc: v("--acc"), edge: v("--line2"), labelBg: v("--panel"), labelFg: v("--fg2"), focus: v("--fg"),
    sec: { Articles: v("--sec-articles"), Varia: v("--sec-varia"), Obituary: v("--sec-obituary"),
           Supplement: v("--sec-supplement") },
  };
}

function network(cv, data, opts = {}) {
  const w = cv.clientWidth || 900, h = opts.h || 560;
  const dpr = window.devicePixelRatio || 1;
  cv.width = w * dpr; cv.height = h * dpr; cv.style.height = h + "px";
  const c = cv.getContext("2d");
  c.setTransform(dpr, 0, 0, dpr, 0, 0);

  const nodes = data.nodes.map(n => ({
    ...n, x: w / 2 + (Math.random() - .5) * w * .6, y: h / 2 + (Math.random() - .5) * h * .6 }));
  const byId = new Map(nodes.map(n => [n.id, n]));
  const edges = data.edges.filter(e => byId.has(e.s) && byId.has(e.t))
    .map(e => ({ ...e, a: byId.get(e.s), b: byId.get(e.t) }));
  const maxF = Math.max(...nodes.map(n => n.f));
  for (const n of nodes) n.r = 3.2 + 9 * Math.sqrt(n.f / maxF);
  const maxE = Math.max(1, ...edges.map(e => e.f));

  let alpha = 1, hover = null, sel = null, run = true;
  let t = { k: 1, x: 0, y: 0 };
  // optimal distance; smaller than Ignatiana's 0.74, which with 140+ terms
  // pushed the outer ring against the walls of the box
  const K = 0.5 * Math.sqrt((w * h) / Math.max(1, nodes.length));
  let temp = Math.min(w, h) / 7;

  function step() {
    for (const n of nodes) { n.dx = 0; n.dy = 0; }
    for (let i = 0; i < nodes.length; i++) {
      const a = nodes[i];
      for (let j = i + 1; j < nodes.length; j++) {
        const b = nodes[j];
        let dx = a.x - b.x, dy = a.y - b.y, d = Math.hypot(dx, dy);
        if (d < 0.6) { dx = Math.random() - .5; dy = Math.random() - .5; d = 0.6; }
        const rep = (K * K) / d * (1 + (a.r + b.r) / 26);
        a.dx += dx / d * rep; a.dy += dy / d * rep;
        b.dx -= dx / d * rep; b.dy -= dy / d * rep;
      }
    }
    for (const e of edges) {
      const dx = e.a.x - e.b.x, dy = e.a.y - e.b.y, d = Math.hypot(dx, dy) || 0.6;
      const att = (d * d) / K * (0.35 + 0.9 * (e.f / maxE));
      e.a.dx -= dx / d * att; e.a.dy -= dy / d * att;
      e.b.dx += dx / d * att; e.b.dy += dy / d * att;
    }
    for (const n of nodes) {
      // centring, stronger across the short side, so the graph fills the box
      // instead of piling up against its edges
      n.dx += (w / 2 - n.x) * 0.0012 * K * (h / w);
      n.dy += (h / 2 - n.y) * 0.0012 * K;
      const d = Math.hypot(n.dx, n.dy) || 1, lim = Math.min(d, temp);
      n.x = Math.max(n.r + 10, Math.min(w - n.r - 10, n.x + n.dx / d * lim));
      n.y = Math.max(n.r + 16, Math.min(h - n.r - 10, n.y + n.dy / d * lim));
    }
    temp *= 0.975; alpha *= 0.982;
  }

  function draw() {
    const P = netTheme();
    c.clearRect(0, 0, w, h);
    c.save(); c.translate(t.x, t.y); c.scale(t.k, t.k);
    const focus = hover || sel;
    const near = focus ? new Set(edges.filter(e => e.s === focus || e.t === focus).flatMap(e => [e.s, e.t])) : null;
    for (const e of edges) {
      const on = focus && (e.s === focus || e.t === focus);
      c.globalAlpha = focus ? (on ? .85 : .05) : Math.min(.55, .16 + (e.f / maxE) * .8);
      c.strokeStyle = on ? P.acc : P.edge;
      c.lineWidth = (on ? 1.5 : Math.max(.5, (e.f / maxE) * 2.4)) / t.k;
      c.beginPath(); c.moveTo(e.a.x, e.a.y); c.lineTo(e.b.x, e.b.y); c.stroke();
    }
    for (const n of nodes) {
      c.globalAlpha = focus && !near.has(n.id) && n.id !== focus ? .16 : 1;
      c.beginPath(); c.arc(n.x, n.y, n.r, 0, 7);
      c.fillStyle = P.sec[n.sec] || P.acc; c.fill();
      if (n.id === focus) { c.strokeStyle = P.focus; c.lineWidth = 1.6 / t.k; c.stroke(); }
    }
    c.restore(); c.globalAlpha = 1;
    // labels in screen space: constant size, more of them as the view magnifies
    c.font = "11.5px -apple-system,Segoe UI,Roboto,sans-serif";
    c.textAlign = "center"; c.textBaseline = "bottom";
    const order = (focus ? nodes.filter(n => near.has(n.id) || n.id === focus) : nodes.slice())
      .sort((a, b) => b.f - a.f);
    const placed = [], cap = focus ? 60 : Math.round((opts.labelCap || 40) * t.k * t.k);
    let shown = 0;
    for (const n of order) {
      if (shown >= cap) break;
      const sx = n.x * t.k + t.x, sy = n.y * t.k + t.y, sr = n.r * t.k;
      if (sx < -40 || sx > w + 40 || sy < -20 || sy > h + 20) continue;
      const tw = c.measureText(n.id).width;
      const box = { x0: sx - tw / 2 - 3, x1: sx + tw / 2 + 3, y0: sy - sr - 15, y1: sy - sr - 1 };
      if (placed.some(p => !(box.x1 < p.x0 || box.x0 > p.x1 || box.y1 < p.y0 || box.y0 > p.y1))) continue;
      placed.push(box); shown++;
      c.fillStyle = P.labelBg; c.globalAlpha = .85;
      c.fillRect(box.x0, box.y0, box.x1 - box.x0, box.y1 - box.y0);
      c.globalAlpha = 1; c.fillStyle = n.id === focus ? P.focus : P.labelFg;
      c.fillText(n.id, sx, sy - sr - 3);
    }
  }

  const idle = () => alpha <= .012;
  function loop() { if (!run) return; if (!idle()) { step(); draw(); } requestAnimationFrame(loop); }
  draw(); loop();

  function pick(ev) {
    const rect = cv.getBoundingClientRect();
    const mx = (ev.clientX - rect.left - t.x) / t.k, my = (ev.clientY - rect.top - t.y) / t.k;
    let best = null, bd = 1e9;
    for (const n of nodes) {
      const d = (n.x - mx) ** 2 + (n.y - my) ** 2;
      if (d < bd && d < (n.r + 8) ** 2) { bd = d; best = n; }
    }
    return best;
  }
  function zoomAt(mx, my, f) {
    const k = Math.max(.4, Math.min(8, t.k * f));
    t.x = mx - (mx - t.x) * (k / t.k); t.y = my - (my - t.y) * (k / t.k); t.k = k;
    draw();
  }
  cv.style.touchAction = "none";
  let drag = null;
  cv.onpointerdown = ev => { drag = { x: ev.clientX, y: ev.clientY, tx: t.x, ty: t.y, moved: false }; cv.setPointerCapture(ev.pointerId); };
  cv.onpointermove = ev => {
    if (drag) {
      if (Math.abs(ev.clientX - drag.x) + Math.abs(ev.clientY - drag.y) > 4) drag.moved = true;
      if (drag.moved) { t.x = drag.tx + ev.clientX - drag.x; t.y = drag.ty + ev.clientY - drag.y; draw(); }
      return;
    }
    const n = pick(ev), id = n ? n.id : null;
    if (id !== hover) { hover = id; cv.style.cursor = id ? "pointer" : "grab"; draw(); }
  };
  cv.onpointerup = ev => {
    const moved = drag && drag.moved; drag = null;
    if (moved) return;
    const n = pick(ev); sel = n ? (sel === n.id ? null : n.id) : null;
    if (ev.pointerType !== "mouse") hover = null;
    opts.onSelect && opts.onSelect(sel); draw();
  };
  cv.onpointerleave = () => { hover = null; draw(); };
  cv.onwheel = ev => {
    ev.preventDefault();
    const rect = cv.getBoundingClientRect();
    zoomAt(ev.clientX - rect.left, ev.clientY - rect.top, ev.deltaY < 0 ? 1.12 : 1 / 1.12);
  };
  cv.ondblclick = ev => {
    const rect = cv.getBoundingClientRect();
    zoomAt(ev.clientX - rect.left, ev.clientY - rect.top, 1.7);
  };

  return {
    select(id) { sel = id; draw(); },
    stop() { run = false; },
    reheat() { alpha = 1; temp = Math.min(w, h) / 9; },
    zoomBy(f) { zoomAt(w / 2, h / 2, f); },
    resetView() { t = { k: 1, x: 0, y: 0 }; draw(); },
    redraw: draw,
  };
}
