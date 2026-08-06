import { test } from "node:test";
import assert from "node:assert/strict";
import { VERSION, CHART_TYPES, render, applyPatch } from "../src/kernel.js";

class FakeNode {
  constructor(doc, name) {
    this.ownerDocument = doc;
    this.nodeName = name;
    this.children = [];
    this.attrs = {};
    this._text = "";
  }
  setAttribute(k, v) {
    this.attrs[k] = v;
  }
  appendChild(c) {
    this.children.push(c);
    return c;
  }
  removeChild(c) {
    this.children = this.children.filter((x) => x !== c);
  }
  get firstChild() {
    return this.children[0] || null;
  }
  set textContent(s) {
    this._text = String(s);
    this.children = [];
  }
  get textContent() {
    return this._text;
  }
}

class FakeDoc {
  createElementNS(_ns, name) {
    return new FakeNode(this, name);
  }
}

function host() {
  return new FakeNode(new FakeDoc(), "div");
}

function walk(node, fn) {
  fn(node);
  for (const c of node.children) walk(c, fn);
}

function collect(root, name) {
  const out = [];
  walk(root, (n) => {
    if (n.nodeName === name) out.push(n);
  });
  return out;
}

const barSpec = {
  v: 1,
  type: "bar",
  data: [
    { month: "Jan", sales: 12 },
    { month: "Feb", sales: 19 },
    { month: "Mar", sales: 7 },
  ],
  encodings: {
    x: { field: "month", type: "nominal" },
    y: { field: "sales", type: "quantitative" },
  },
};

const lineSpec = {
  v: 1,
  type: "line",
  data: [
    { t: 0, v: 1 },
    { t: 1, v: 3 },
    { t: 2, v: 2 },
  ],
  encodings: {
    x: { field: "t", type: "quantitative" },
    y: { field: "v", type: "quantitative" },
  },
};

test("exports version and the nine chart types", () => {
  assert.match(VERSION, /^\d+\.\d+\.\d+$/);
  assert.deepEqual(CHART_TYPES, [
    "bar",
    "line",
    "scatter",
    "area",
    "heatmap",
    "donut",
    "box",
    "waterfall",
    "treemap",
  ]);
});

test("bar fixture renders one rect per row with tooltips", () => {
  const el = host();
  const svg = render(el, barSpec);
  assert.equal(svg.attrs["data-chartkit"], VERSION);
  const rects = collect(svg, "rect");
  assert.equal(rects.length, barSpec.data.length);
  assert.equal(collect(svg, "title").length, barSpec.data.length);
});

test("line fixture renders a path through the points", () => {
  const svg = render(host(), lineSpec);
  const paths = collect(svg, "path");
  assert.equal(paths.length, 1);
  assert.match(paths[0].attrs.d, /^M[\d.]+,[\d.]+L/);
});

test("area adds a fill path under the line", () => {
  const svg = render(host(), { ...lineSpec, type: "area" });
  assert.equal(collect(svg, "path").length, 2);
});

test("scatter renders one circle per finite point", () => {
  const svg = render(host(), { ...lineSpec, type: "scatter" });
  assert.equal(collect(svg, "circle").length, lineSpec.data.length);
});

test("color channel splits series and draws a legend", () => {
  const spec = {
    ...barSpec,
    data: [
      { month: "Jan", sales: 5, region: "east" },
      { month: "Jan", sales: 7, region: "west" },
      { month: "Feb", sales: 6, region: "east" },
      { month: "Feb", sales: 4, region: "west" },
    ],
    encodings: { ...barSpec.encodings, color: { field: "region", type: "nominal" } },
  };
  const svg = render(host(), spec);
  const rects = collect(svg, "rect");
  assert.equal(rects.length, 4 + 2);
  const fills = new Set(rects.map((r) => r.attrs.fill));
  assert.ok(fills.size >= 2);
});

test("hostile spec strings never become elements — text nodes only", () => {
  const hostile = '<script>alert(1)</script><img src=x onerror=alert(1)>';
  const spec = {
    ...barSpec,
    data: [{ month: hostile, sales: 3 }],
    options: { title: hostile },
  };
  const svg = render(host(), spec);
  assert.equal(collect(svg, "script").length, 0);
  assert.equal(collect(svg, "img").length, 0);
  let seenAsText = 0;
  walk(svg, (n) => {
    if (n.textContent.includes(hostile)) seenAsText += 1;
    for (const v of Object.values(n.attrs)) {
      assert.ok(!String(v).includes("<script"), "hostile string leaked into an attribute");
    }
  });
  assert.ok(seenAsText >= 2, "hostile string should surface only as inert text");
});

test("re-render clears previous chart from the host element", () => {
  const el = host();
  render(el, barSpec);
  render(el, barSpec);
  assert.equal(el.children.length, 1);
});

test("unknown type and missing encodings are rejected", () => {
  assert.throws(() => render(host(), { type: "pie", encodings: {} }), /unknown chart type/);
  assert.throws(() => render(host(), { type: "bar" }), /encodings/);
  assert.throws(() => render(null, barSpec), /DOM element/);
});

test("heatmap renders one cell per row with value tooltips", () => {
  const spec = {
    v: 1,
    type: "heatmap",
    data: [
      { day: "Mon", hour: "am", n: 2 },
      { day: "Mon", hour: "pm", n: 8 },
      { day: "Tue", hour: "am", n: 5 },
      { day: "Tue", hour: "pm", n: 1 },
    ],
    encodings: {
      x: { field: "day", type: "nominal" },
      y: { field: "hour", type: "nominal" },
      color: { field: "n", type: "quantitative" },
    },
  };
  const svg = render(host(), spec);
  const cells = collect(svg, "rect");
  assert.equal(cells.length, spec.data.length);
  const opacities = cells.map((c) => Number(c.attrs["fill-opacity"]));
  assert.ok(Math.max(...opacities) > Math.min(...opacities), "value maps to opacity ramp");
  assert.equal(collect(svg, "title").length, spec.data.length);
});

test("heatmap without a color channel is rejected", () => {
  const spec = {
    type: "heatmap",
    data: [{ a: "x", b: "y" }],
    encodings: {
      x: { field: "a", type: "nominal" },
      y: { field: "b", type: "nominal" },
    },
  };
  assert.throws(() => render(host(), spec), /encodings\.color/);
});

test("every declared chart type renders from a fixture", () => {
  for (const type of CHART_TYPES) {
    const spec =
      type === "heatmap"
        ? {
            type,
            data: [{ a: "x", b: "y", n: 1 }],
            encodings: {
              x: { field: "a", type: "nominal" },
              y: { field: "b", type: "nominal" },
              color: { field: "n", type: "quantitative" },
            },
          }
        : type === "box"
          ? {
              type,
              data: [{ lane: "a", min: 1, q1: 2, median: 3, q3: 4, max: 5 }],
              encodings: {
                x: { field: "lane", type: "nominal" },
                y: { field: "median", type: "quantitative" },
              },
            }
          : ["donut", "waterfall", "treemap"].includes(type)
            ? { ...barSpec, type }
            : { ...(type === "bar" ? barSpec : lineSpec), type };
    const svg = render(host(), spec);
    assert.equal(svg.attrs["data-chartkit"], VERSION, `${type} should render`);
  }
});

test("applyPatch follows RFC 7386 merge-patch semantics", () => {
  const spec = { a: 1, nest: { keep: true, drop: 2 }, arr: [1, 2, 3] };
  const out = applyPatch(spec, {
    a: 9,
    added: "new",
    nest: { drop: null, deep: { x: 1 } },
    arr: [4],
  });
  assert.deepEqual(out, {
    a: 9,
    added: "new",
    nest: { keep: true, deep: { x: 1 } },
    arr: [4],
  });
  assert.deepEqual(spec.nest, { keep: true, drop: 2 }, "input spec is not mutated");
  assert.equal(applyPatch({ a: 1 }, null), null, "non-object patch replaces wholesale");
});

test("a data-only patch re-renders with rescaled axes", () => {
  const el = host();
  render(el, lineSpec);
  const before = collect(el, "text").map((t) => t.textContent);
  const patched = applyPatch(lineSpec, {
    data: [
      { t: 0, v: 100 },
      { t: 1, v: 900 },
    ],
  });
  render(el, patched);
  const after = collect(el, "text").map((t) => t.textContent);
  assert.equal(el.children.length, 1, "replaced in place");
  assert.notDeepEqual(after, before, "axis ticks rescaled to the new domain");
  assert.ok(after.some((s) => s.includes("k") || Number(s) >= 100), "ticks reflect new magnitude");
});

test("horizontal bar renders one rect per row with category labels", () => {
  const spec = { ...barSpec, options: { horizontal: true } };
  const svg = render(host(), spec);
  assert.equal(collect(svg, "rect").length, barSpec.data.length);
  const texts = collect(svg, "text").map((t) => t.textContent);
  for (const row of barSpec.data) assert.ok(texts.includes(row.month));
});

test("donut renders one arc path per positive slice plus legend", () => {
  const svg = render(host(), { ...barSpec, type: "donut" });
  const paths = collect(svg, "path");
  assert.equal(paths.length, barSpec.data.length);
  for (const p of paths) assert.match(p.attrs.d, /A/);
});

test("donut with no positive values throws", () => {
  const spec = {
    ...barSpec,
    type: "donut",
    data: [{ month: "Jan", sales: 0 }],
  };
  assert.throws(() => render(host(), spec), /positive value/);
});

test("box renders whisker, box, and median per row", () => {
  const spec = {
    type: "box",
    data: [
      { lane: "ubuntu", min: 1, q1: 2, median: 3, q3: 4, max: 6 },
      { lane: "windows", min: 4, q1: 6, median: 8, q3: 11, max: 13 },
    ],
    encodings: {
      x: { field: "lane", type: "nominal" },
      y: { field: "median", type: "quantitative" },
    },
  };
  const svg = render(host(), spec);
  assert.equal(collect(svg, "rect").length, 2);
  const tips = collect(svg, "title").map((t) => t.textContent);
  assert.ok(tips.some((t) => t.includes("med 8")));
});

test("box with non-numeric stats throws a field-naming error", () => {
  const spec = {
    type: "box",
    data: [{ lane: "a", min: 1, q1: 2, median: "oops", q3: 4, max: 5 }],
    encodings: {
      x: { field: "lane", type: "nominal" },
      y: { field: "median", type: "quantitative" },
    },
  };
  assert.throws(() => render(host(), spec), /min, q1, median, q3, max/);
});

test("waterfall renders running-offset bars and a total when asked", () => {
  const spec = {
    type: "waterfall",
    data: [
      { step: "start", delta: 10 },
      { step: "refund", delta: -4 },
      { step: "growth", delta: 6 },
    ],
    encodings: {
      x: { field: "step", type: "nominal" },
      y: { field: "delta", type: "quantitative" },
    },
    options: { total: "net" },
  };
  const svg = render(host(), spec);
  assert.equal(collect(svg, "rect").length, 4);
  const tips = collect(svg, "title").map((t) => t.textContent);
  assert.ok(tips.some((t) => t.includes("net: 12 (total)")));
});

test("treemap renders one tile per positive row, largest first", () => {
  const svg = render(host(), { ...barSpec, type: "treemap" });
  assert.equal(collect(svg, "rect").length, barSpec.data.length);
});

test("treemap with no positive values throws", () => {
  const spec = { ...barSpec, type: "treemap", data: [{ month: "Jan", sales: -1 }] };
  assert.throws(() => render(host(), spec), /positive value/);
});
