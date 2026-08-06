const VERSION = "0.1.0";

const CHART_TYPES = [
  "bar",
  "line",
  "scatter",
  "area",
  "heatmap",
  "donut",
  "box",
  "waterfall",
  "treemap",
];

const SVG_NS = "http://www.w3.org/2000/svg";

const PALETTE = [
  ["--chartkit-c1", "#4269d0"],
  ["--chartkit-c2", "#efb118"],
  ["--chartkit-c3", "#ff725c"],
  ["--chartkit-c4", "#6cc5b0"],
  ["--chartkit-c5", "#a463f2"],
  ["--chartkit-c6", "#9c6b4e"],
];

const W = 640;
const H = 360;
const M = { t: 30, r: 16, b: 40, l: 48 };

function seriesColor(i) {
  const [v, fb] = PALETTE[i % PALETTE.length];
  return `var(${v}, ${fb})`;
}

function fmt(n) {
  if (typeof n !== "number" || !isFinite(n)) return String(n);
  if (Math.abs(n) >= 1e6) return `${+(n / 1e6).toFixed(1)}M`;
  if (Math.abs(n) >= 1e3) return `${+(n / 1e3).toFixed(1)}k`;
  return String(+n.toFixed(2));
}

function fieldValue(row, enc) {
  const v = row[enc.field];
  if (enc.type === "temporal") {
    const t = typeof v === "number" ? v : Date.parse(v);
    return isFinite(t) ? t : NaN;
  }
  if (enc.type === "quantitative") {
    const n = typeof v === "number" ? v : Number(v);
    return isFinite(n) ? n : NaN;
  }
  return v;
}

function extent(values) {
  let lo = Infinity;
  let hi = -Infinity;
  for (const v of values) {
    if (typeof v !== "number" || !isFinite(v)) continue;
    if (v < lo) lo = v;
    if (v > hi) hi = v;
  }
  if (lo === Infinity) return [0, 1];
  if (lo === hi) return lo === 0 ? [0, 1] : [0, hi];
  return [Math.min(lo, 0), hi];
}

function niceTicks([lo, hi], count) {
  const span = hi - lo || 1;
  const step0 = span / Math.max(1, count);
  const mag = 10 ** Math.floor(Math.log10(step0));
  const step = [1, 2, 5, 10].map((m) => m * mag).find((s) => span / s <= count) || mag * 10;
  const ticks = [];
  for (let t = Math.ceil(lo / step) * step; t <= hi + step / 1e6; t += step) {
    ticks.push(+t.toFixed(10));
  }
  return ticks;
}

function linearScale([lo, hi], [r0, r1]) {
  const d = hi - lo || 1;
  const s = (v) => r0 + ((v - lo) / d) * (r1 - r0);
  s.domain = [lo, hi];
  return s;
}

function bandScale(cats, [r0, r1], pad = 0.15) {
  const n = Math.max(1, cats.length);
  const step = (r1 - r0) / n;
  const bw = step * (1 - pad);
  const s = (c) => r0 + cats.indexOf(c) * step + (step - bw) / 2;
  s.bandwidth = bw;
  s.step = step;
  s.categories = cats;
  return s;
}

function el(doc, name, attrs) {
  const node = doc.createElementNS(SVG_NS, name);
  for (const k in attrs) node.setAttribute(k, String(attrs[k]));
  return node;
}

function label(doc, parent, str, attrs) {
  const t = el(doc, "text", {
    "font-size": 11,
    "font-family": "inherit",
    fill: "var(--text-secondary, #667)",
    ...attrs,
  });
  t.textContent = String(str);
  parent.appendChild(t);
  return t;
}

function tooltip(doc, node, str) {
  const t = doc.createElementNS(SVG_NS, "title");
  t.textContent = String(str);
  node.appendChild(t);
}

function categoriesOf(data, enc) {
  const seen = [];
  for (const row of data) {
    const v = fieldValue(row, enc);
    if (!seen.includes(v)) seen.push(v);
  }
  return seen;
}

function drawYAxis(doc, g, scale, x0, x1) {
  for (const t of niceTicks(scale.domain, 5)) {
    const y = scale(t);
    g.appendChild(
      el(doc, "line", {
        x1: x0,
        x2: x1,
        y1: y,
        y2: y,
        stroke: "var(--border, #ddd)",
        "stroke-width": 1,
      })
    );
    label(doc, g, fmt(t), { x: x0 - 6, y: y + 4, "text-anchor": "end" });
  }
}

function drawXTick(doc, g, x, str) {
  label(doc, g, str, { x, y: H - M.b + 16, "text-anchor": "middle" });
}

function drawLegend(doc, g, names, startX) {
  // Starts after the title (startX) so the two never collide, and
  // wraps to a second 14px row on overflow — both rows fit inside
  // the top margin. Beyond two rows entries keep flowing on the
  // second row and clip at the right edge (tooltips still carry
  // the full labels).
  let x = startX == null ? M.l : startX;
  let row = 0;
  names.forEach((name, i) => {
    const w = 13 + 7 * String(name).length + 18;
    if (x + w > W - M.r && row < 1) {
      row += 1;
      x = M.l;
    }
    const y = 6 + row * 14;
    g.appendChild(el(doc, "rect", { x, y, width: 9, height: 9, rx: 2, fill: seriesColor(i) }));
    label(doc, g, name, { x: x + 13, y: y + 8, "text-anchor": "start" });
    x += w;
  });
}

function legendStart(spec) {
  const title = spec.options && spec.options.title;
  return title ? M.l + Math.round(7.8 * String(title).length) + 16 : M.l;
}

function splitSeries(data, colorEnc) {
  if (!colorEnc) return [{ name: null, rows: data }];
  const names = categoriesOf(data, colorEnc);
  return names.map((name) => ({
    name,
    rows: data.filter((r) => fieldValue(r, colorEnc) === name),
  }));
}

function renderBar(doc, g, spec, x, y, series) {
  const stacked = spec.options && spec.options.stacked;
  const sums = {};
  series.forEach((s, si) => {
    for (const row of s.rows) {
      const cx = fieldValue(row, spec.encodings.x);
      const vy = fieldValue(row, spec.encodings.y);
      let bx = x(cx);
      let bw = x.bandwidth;
      let y0 = y(0);
      if (stacked && series.length > 1) {
        const prev = sums[cx] || 0;
        y0 = y(prev);
        sums[cx] = prev + vy;
      } else if (series.length > 1) {
        bw = x.bandwidth / series.length;
        bx += si * bw;
      }
      const y1 = stacked && series.length > 1 ? y(sums[cx]) : y(vy);
      const rect = el(doc, "rect", {
        x: bx,
        y: Math.min(y0, y1),
        width: Math.max(1, bw),
        height: Math.abs(y0 - y1),
        fill: seriesColor(si),
      });
      tooltip(doc, rect, `${cx}${s.name != null ? " · " + s.name : ""}: ${fmt(vy)}`);
      g.appendChild(rect);
    }
  });
}

function renderLine(doc, g, spec, x, y, series, asArea) {
  series.forEach((s, si) => {
    const pts = s.rows
      .map((r) => [fieldValue(r, spec.encodings.x), fieldValue(r, spec.encodings.y)])
      .filter((p) => isFinite(p[0]) && isFinite(p[1]))
      .sort((a, b) => a[0] - b[0]);
    if (!pts.length) return;
    const path = pts.map((p, i) => `${i ? "L" : "M"}${x(p[0])},${y(p[1])}`).join("");
    if (asArea) {
      const base = y(0);
      const area = `${path}L${x(pts[pts.length - 1][0])},${base}L${x(pts[0][0])},${base}Z`;
      g.appendChild(
        el(doc, "path", { d: area, fill: seriesColor(si), "fill-opacity": 0.25, stroke: "none" })
      );
    }
    const line = el(doc, "path", {
      d: path,
      fill: "none",
      stroke: seriesColor(si),
      "stroke-width": 2,
    });
    if (s.name != null) tooltip(doc, line, String(s.name));
    g.appendChild(line);
  });
}

function renderScatter(doc, g, spec, x, y, series) {
  series.forEach((s, si) => {
    for (const row of s.rows) {
      const cx = fieldValue(row, spec.encodings.x);
      const cy = fieldValue(row, spec.encodings.y);
      if (!isFinite(cx) || !isFinite(cy)) continue;
      const dot = el(doc, "circle", { cx: x(cx), cy: y(cy), r: 4, fill: seriesColor(si), "fill-opacity": 0.85 });
      tooltip(doc, dot, `${fmt(cx)}, ${fmt(cy)}${s.name != null ? " · " + s.name : ""}`);
      g.appendChild(dot);
    }
  });
}

function renderHeatmap(doc, g, spec) {
  const data = spec.data || [];
  const xEnc = spec.encodings.x;
  const yEnc = spec.encodings.y;
  const vEnc = spec.encodings.color;
  if (!vEnc) throw new Error("chartkit: heatmap needs encodings.color for cell values");
  const xCats = categoriesOf(data, xEnc);
  const yCats = categoriesOf(data, yEnc);
  const x = bandScale(xCats, [M.l, W - M.r], 0.05);
  const y = bandScale(yCats, [M.t, H - M.b], 0.05);
  const vals = data.map((r) => fieldValue(r, vEnc));
  const [lo, hi] = extent(vals);
  const span = hi - lo || 1;
  xCats.forEach((c) => drawXTick(doc, g, x(c) + x.bandwidth / 2, c));
  yCats.forEach((c) =>
    label(doc, g, c, { x: M.l - 6, y: y(c) + y.bandwidth / 2 + 4, "text-anchor": "end" })
  );
  for (const row of data) {
    const cx = fieldValue(row, xEnc);
    const cy = fieldValue(row, yEnc);
    const v = fieldValue(row, vEnc);
    const cell = el(doc, "rect", {
      x: x(cx),
      y: y(cy),
      width: x.bandwidth,
      height: y.bandwidth,
      rx: 2,
      fill: seriesColor(0),
      "fill-opacity": isFinite(v) ? 0.12 + 0.88 * ((v - lo) / span) : 0,
      stroke: "var(--border, #ddd)",
      "stroke-width": 0.5,
    });
    tooltip(doc, cell, `${cx} · ${cy}: ${fmt(v)}`);
    g.appendChild(cell);
  }
}

function renderBarH(doc, g, spec) {
  const data = spec.data || [];
  const cats = categoriesOf(data, spec.encodings.x);
  const yb = bandScale(cats, [M.t, H - M.b], 0.25);
  const vals = data.map((r) => fieldValue(r, spec.encodings.y));
  const lx = M.l + 72;
  const x = linearScale(extent(vals), [lx, W - M.r]);
  for (const t of niceTicks(x.domain, 6)) {
    g.appendChild(
      el(doc, "line", {
        x1: x(t),
        x2: x(t),
        y1: M.t,
        y2: H - M.b,
        stroke: "var(--border, #ddd)",
        "stroke-width": 1,
      })
    );
    label(doc, g, fmt(t), { x: x(t), y: H - M.b + 16, "text-anchor": "middle" });
  }
  for (const row of data) {
    const c = fieldValue(row, spec.encodings.x);
    const v = fieldValue(row, spec.encodings.y);
    label(doc, g, c, { x: lx - 6, y: yb(c) + yb.bandwidth / 2 + 4, "text-anchor": "end" });
    const rect = el(doc, "rect", {
      x: Math.min(x(0), x(v)),
      y: yb(c),
      width: Math.max(1, Math.abs(x(v) - x(0))),
      height: yb.bandwidth,
      fill: seriesColor(0),
    });
    tooltip(doc, rect, `${c}: ${fmt(v)}`);
    g.appendChild(rect);
  }
}

function renderDonut(doc, g, spec) {
  const data = spec.data || [];
  const cx = W / 2;
  const cy = (H + M.t - M.b) / 2 + 8;
  const R = (H - M.t - M.b) / 2 - 10;
  const r0 = R * 0.55;
  const rows = data.map((row) => {
    const v = fieldValue(row, spec.encodings.y);
    return [fieldValue(row, spec.encodings.x), isFinite(v) && v > 0 ? v : 0];
  });
  const total = rows.reduce((a, p) => a + p[1], 0);
  if (!total) throw new Error("chartkit: donut needs at least one positive value");
  let a = -Math.PI / 2;
  rows.forEach(([name, v], i) => {
    if (!v) return;
    const a1 = a + Math.min((v / total) * 2 * Math.PI, 2 * Math.PI - 1e-4);
    const big = a1 - a > Math.PI ? 1 : 0;
    const p = (ang, rad) => `${cx + rad * Math.cos(ang)},${cy + rad * Math.sin(ang)}`;
    const arc = el(doc, "path", {
      d:
        `M${p(a, R)}A${R},${R} 0 ${big} 1 ${p(a1, R)}` +
        `L${p(a1, r0)}A${r0},${r0} 0 ${big} 0 ${p(a, r0)}Z`,
      fill: seriesColor(i),
    });
    tooltip(doc, arc, `${name}: ${fmt(v)} (${fmt((100 * v) / total)}%)`);
    g.appendChild(arc);
    a = a1;
  });
  if (!spec.options || spec.options.legend !== false) {
    drawLegend(doc, g, rows.filter((r) => r[1] > 0).map((r) => String(r[0])), legendStart(spec));
  }
}

function renderBox(doc, g, spec) {
  const data = spec.data || [];
  const keys = ["min", "q1", "median", "q3", "max"];
  const cats = categoriesOf(data, spec.encodings.x);
  const x = bandScale(cats, [M.l, W - M.r], 0.4);
  const vals = [];
  for (const r of data) vals.push(Number(r.min), Number(r.max));
  const y = linearScale(extent(vals), [H - M.b, M.t]);
  drawYAxis(doc, g, y, M.l, W - M.r);
  cats.forEach((c) => drawXTick(doc, g, x(c) + x.bandwidth / 2, c));
  data.forEach((row, i) => {
    const c = fieldValue(row, spec.encodings.x);
    const [mn, q1, md, q3, mx] = keys.map((k) => Number(row[k]));
    if (![mn, q1, md, q3, mx].every(isFinite)) {
      throw new Error("chartkit: box rows need numeric min, q1, median, q3, max");
    }
    const bx = x(c);
    const bw = x.bandwidth;
    const mid = bx + bw / 2;
    g.appendChild(
      el(doc, "line", {
        x1: mid,
        x2: mid,
        y1: y(mn),
        y2: y(mx),
        stroke: seriesColor(i),
        "stroke-width": 1.5,
      })
    );
    const boxEl = el(doc, "rect", {
      x: bx,
      y: y(q3),
      width: bw,
      height: Math.max(1, y(q1) - y(q3)),
      fill: seriesColor(i),
      "fill-opacity": 0.35,
      stroke: seriesColor(i),
    });
    tooltip(
      doc,
      boxEl,
      `${c}: min ${fmt(mn)} · q1 ${fmt(q1)} · med ${fmt(md)} · q3 ${fmt(q3)} · max ${fmt(mx)}`
    );
    g.appendChild(boxEl);
    g.appendChild(
      el(doc, "line", {
        x1: bx,
        x2: bx + bw,
        y1: y(md),
        y2: y(md),
        stroke: seriesColor(i),
        "stroke-width": 2,
      })
    );
  });
}

function renderWaterfall(doc, g, spec) {
  const data = spec.data || [];
  let run = 0;
  const steps = data.map((r) => {
    const v = fieldValue(r, spec.encodings.y);
    const s = { name: String(fieldValue(r, spec.encodings.x)), v, y0: run, y1: run + v };
    run += v;
    return s;
  });
  const totalLabel = spec.options && spec.options.total;
  if (totalLabel) steps.push({ name: String(totalLabel), v: run, y0: 0, y1: run, total: true });
  const x = bandScale(steps.map((s) => s.name), [M.l, W - M.r], 0.25);
  const y = linearScale(extent(steps.flatMap((s) => [s.y0, s.y1])), [H - M.b, M.t]);
  drawYAxis(doc, g, y, M.l, W - M.r);
  steps.forEach((s) => {
    drawXTick(doc, g, x(s.name) + x.bandwidth / 2, s.name);
    const rect = el(doc, "rect", {
      x: x(s.name),
      y: Math.min(y(s.y0), y(s.y1)),
      width: x.bandwidth,
      height: Math.max(1, Math.abs(y(s.y0) - y(s.y1))),
      fill: s.total ? seriesColor(0) : s.v >= 0 ? seriesColor(3) : seriesColor(2),
    });
    tooltip(
      doc,
      rect,
      s.total
        ? `${s.name}: ${fmt(s.v)} (total)`
        : `${s.name}: ${s.v >= 0 ? "+" : ""}${fmt(s.v)} → ${fmt(s.y1)}`
    );
    g.appendChild(rect);
  });
}

function renderTreemap(doc, g, spec) {
  const data = spec.data || [];
  const rows = data
    .map((r) => [String(fieldValue(r, spec.encodings.x)), fieldValue(r, spec.encodings.y)])
    .filter((p) => isFinite(p[1]) && p[1] > 0)
    .sort((a, b) => b[1] - a[1]);
  if (!rows.length) throw new Error("chartkit: treemap needs at least one positive value");
  let total = rows.reduce((a, p) => a + p[1], 0);
  let x0 = M.l;
  let y0 = M.t;
  let x1 = W - M.r;
  let y1 = H - M.b;
  rows.forEach(([name, v], i) => {
    const frac = total > 0 ? v / total : 1;
    let rx = x0;
    let ry = y0;
    let rw;
    let rh;
    if (x1 - x0 > y1 - y0) {
      rw = (x1 - x0) * frac;
      rh = y1 - y0;
      x0 += rw;
    } else {
      rw = x1 - x0;
      rh = (y1 - y0) * frac;
      y0 += rh;
    }
    total -= v;
    const rect = el(doc, "rect", {
      x: rx + 1,
      y: ry + 1,
      width: Math.max(1, rw - 2),
      height: Math.max(1, rh - 2),
      rx: 2,
      fill: seriesColor(i),
      "fill-opacity": 0.85,
    });
    tooltip(doc, rect, `${name}: ${fmt(v)} (${fmt((100 * v) / (total + v))}% of remaining)`);
    g.appendChild(rect);
    if (rw > 46 && rh > 20) {
      label(doc, g, name, { x: rx + 6, y: ry + 15, fill: "#fff", "text-anchor": "start" });
    }
  });
}

function render(root, spec) {
  if (!root || typeof root.appendChild !== "function") {
    throw new Error("chartkit: render(el, spec) needs a DOM element");
  }
  if (!spec || typeof spec !== "object" || !spec.encodings) {
    throw new Error("chartkit: render(el, spec) needs a spec with encodings");
  }
  if (!CHART_TYPES.includes(spec.type)) {
    throw new Error(
      `chartkit: unknown chart type "${spec.type}" (expected one of ${CHART_TYPES.join(", ")})`
    );
  }
  const doc = root.ownerDocument;
  while (root.firstChild) root.removeChild(root.firstChild);
  const svg = el(doc, "svg", {
    viewBox: `0 0 ${W} ${H}`,
    width: "100%",
    role: "img",
    "data-chartkit": VERSION,
  });
  const g = el(doc, "g", {});
  svg.appendChild(g);

  const data = spec.data || [];
  const drawTitle = () => {
    if (spec.options && spec.options.title) {
      label(doc, g, spec.options.title, {
        x: M.l,
        y: 16,
        "font-size": 13,
        "font-weight": 500,
        fill: "var(--text-primary, #222)",
        "text-anchor": "start",
      });
    }
  };
  const OWN_AXES = {
    heatmap: renderHeatmap,
    donut: renderDonut,
    box: renderBox,
    waterfall: renderWaterfall,
    treemap: renderTreemap,
  };
  const special =
    OWN_AXES[spec.type] ||
    (spec.type === "bar" && spec.options && spec.options.horizontal ? renderBarH : null);
  if (special) {
    special(doc, g, spec);
    drawTitle();
    root.appendChild(svg);
    return svg;
  }
  const colorEnc = spec.encodings.color;
  const series = splitSeries(data, colorEnc);
  const yVals = data.map((r) => fieldValue(r, spec.encodings.y));
  const yDom =
    spec.type === "bar" && spec.options && spec.options.stacked && series.length > 1
      ? extent(
          categoriesOf(data, spec.encodings.x).map((c) =>
            data
              .filter((r) => fieldValue(r, spec.encodings.x) === c)
              .reduce((a, r) => a + fieldValue(r, spec.encodings.y), 0)
          )
        )
      : extent(yVals);
  const y = linearScale(yDom, [H - M.b, M.t]);
  drawYAxis(doc, g, y, M.l, W - M.r);

  const xEnc = spec.encodings.x;
  if (spec.type === "bar" || xEnc.type === "nominal") {
    const cats = categoriesOf(data, xEnc);
    const x = bandScale(cats, [M.l, W - M.r]);
    cats.forEach((c) => drawXTick(doc, g, x(c) + x.bandwidth / 2, c));
    if (spec.type === "bar") renderBar(doc, g, spec, x, y, series);
    else renderLine(doc, g, spec, (c) => x(c) + x.bandwidth / 2, y, series, spec.type === "area");
  } else {
    const xVals = data.map((r) => fieldValue(r, xEnc));
    const x = linearScale(extent(xVals.filter(isFinite)), [M.l, W - M.r]);
    for (const t of niceTicks(x.domain, 6)) {
      drawXTick(doc, g, x(t), xEnc.type === "temporal" ? new Date(t).toISOString().slice(0, 10) : fmt(t));
    }
    if (spec.type === "scatter") renderScatter(doc, g, spec, x, y, series);
    else renderLine(doc, g, spec, x, y, series, spec.type === "area");
  }

  if (colorEnc && (!spec.options || spec.options.legend !== false)) {
    drawLegend(doc, g, series.map((s) => String(s.name)), legendStart(spec));
  }
  drawTitle();
  root.appendChild(svg);
  return svg;
}

function applyPatch(target, patch) {
  if (patch === null || typeof patch !== "object" || Array.isArray(patch)) {
    return patch;
  }
  const out =
    target && typeof target === "object" && !Array.isArray(target) ? { ...target } : {};
  for (const k in patch) {
    const v = patch[k];
    if (v === null) delete out[k];
    else out[k] = applyPatch(out[k], v);
  }
  return out;
}

export { VERSION, CHART_TYPES, render, applyPatch };
