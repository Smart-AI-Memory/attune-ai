const VERSION = "0.1.0";

const CHART_TYPES = ["bar", "line", "scatter", "area", "heatmap"];

function render(el, spec) {
  if (!el || typeof el.appendChild !== "function") {
    throw new Error("chartkit: render(el, spec) needs a DOM element");
  }
  if (!spec || typeof spec !== "object") {
    throw new Error("chartkit: render(el, spec) needs a spec object");
  }
  if (!CHART_TYPES.includes(spec.type)) {
    throw new Error(
      `chartkit: unknown chart type "${spec.type}" (expected one of ${CHART_TYPES.join(", ")})`
    );
  }
  el.textContent = `chartkit v${VERSION}: "${spec.type}" renderer lands in T3/T4`;
}

function applyPatch() {
  throw new Error("chartkit: applyPatch lands in T5");
}

export { VERSION, CHART_TYPES, render, applyPatch };
