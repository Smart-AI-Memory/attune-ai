const VERSION = "0.1.0";

const CHART_TYPES = ["bar", "line", "scatter", "area", "heatmap"];

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

function drawLegend(doc, g, names) {
  let x = M.l;
  names.forEach((name, i) => {
    g.appendChild(el(doc, "rect", { x, y: 6, width: 9, height: 9, rx: 2, fill: seriesColor(i) }));
    const t = label(doc, g, name, { x: x + 13, y: 14, "text-anchor": "start" });
    x += 13 + 7 * String(name).length + 18;
    void t;
  });
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
  if (spec.type === "heatmap") {
    renderHeatmap(doc, g, spec);
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
    drawLegend(doc, g, series.map((s) => String(s.name)));
  }
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
