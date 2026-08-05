import { test } from "node:test";
import assert from "node:assert/strict";
import { VERSION, CHART_TYPES, render, applyPatch } from "../src/kernel.js";

function fakeEl() {
  return { textContent: "", appendChild() {} };
}

test("exports a version and the five chart types", () => {
  assert.match(VERSION, /^\d+\.\d+\.\d+$/);
  assert.deepEqual(CHART_TYPES, ["bar", "line", "scatter", "area", "heatmap"]);
});

test("render rejects a missing element and unknown types", () => {
  assert.throws(() => render(null, { type: "bar" }), /DOM element/);
  assert.throws(() => render(fakeEl(), { type: "pie" }), /unknown chart type/);
});

test("render accepts every declared chart type (stub)", () => {
  for (const type of CHART_TYPES) {
    const el = fakeEl();
    render(el, { type });
    assert.ok(el.textContent.includes(type));
  }
});

test("applyPatch is explicitly not yet implemented", () => {
  assert.throws(() => applyPatch(), /T5/);
});
