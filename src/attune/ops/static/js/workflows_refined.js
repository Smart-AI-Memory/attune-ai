// Workflows page — concern-chip filter + search + URL state (A3a + A3c).
//
// Reads the server-rendered table at /workflows and applies client-side
// filtering by concern bucket + workflow name substring. URL state
// (?bucket=…&q=…) is the source of truth — JS reads on init, writes
// on chip toggle / search input.
//
// Default state per docs/specs/ops-workflows-page-refinement/decisions.md D1/D2:
//   - All 7 concern chips active (no chip is structurally "noise"
//     unlike Specs page's Complete-off default)
//   - Search empty
//
// No sort dropdown — workflows render alphabetical by name from the
// server (decisions.md D7: alphabetical-by-name; v2 may add by-last-run).
//
// Exports a `window.__attuneWorkflows` namespace so future PRs and
// source-grep tests can verify the surface (matches the
// `__attuneSpecs` + `__attuneRunner` convention).

(function () {
  "use strict";

  // All 7 buckets per decisions.md D1. Stable order; chips render in
  // the template in this order so the JS doesn't need to enforce it.
  var VALID_BUCKETS = new Set([
    "review",
    "test",
    "docs",
    "refactor",
    "audit",
    "meta",
    "other",
  ]);

  // Mutable state. All buckets active by default. Search empty.
  var state = {
    buckets: new Set(VALID_BUCKETS),
    search: "",
  };

  // ---------- URL state (A3c) ----------
  //
  // ?bucket=review,audit&q=security  → state.buckets={review,audit}, search="security"
  //
  // Defaults are normalized OUT of the URL — a "clean" URL (no params)
  // means "default state: all buckets, no search". This keeps shared
  // links short and survives back/forward navigation cleanly.

  function readURLState() {
    try {
      var u = new URL(window.location.href);
      var bucketParam = u.searchParams.get("bucket");
      if (bucketParam !== null && bucketParam.length > 0) {
        var candidates = bucketParam
          .split(",")
          .map(function (b) {
            return b.trim();
          })
          .filter(function (b) {
            return VALID_BUCKETS.has(b);
          });
        // Empty after filtering → invalid param, fall back to defaults
        // (don't strand the user with zero chips active on first paint).
        if (candidates.length > 0) {
          state.buckets = new Set(candidates);
        }
      }
      var q = u.searchParams.get("q");
      if (q !== null) {
        state.search = q;
      }
    } catch (e) {
      // URL parse failure in older browsers / restrictive contexts —
      // silent fall-through to defaults is fine, no UX regression.
    }
  }

  function bucketsAreDefault(bucketSet) {
    // "Default" = all 7 buckets on. URL stays clean in that case.
    return bucketSet.size === VALID_BUCKETS.size;
  }

  function syncURL() {
    try {
      var u = new URL(window.location.href);
      if (bucketsAreDefault(state.buckets)) {
        u.searchParams.delete("bucket");
      } else {
        // Sort for stable URLs — same bucket set always serializes the
        // same way regardless of toggle order.
        var sorted = Array.from(state.buckets).sort();
        u.searchParams.set("bucket", sorted.join(","));
      }
      var q = (state.search || "").trim();
      if (q.length === 0) {
        u.searchParams.delete("q");
      } else {
        u.searchParams.set("q", q);
      }
      // Use replaceState — toggling a chip shouldn't push a history
      // entry per toggle. Back button still leaves /workflows entirely.
      window.history.replaceState({}, "", u.toString());
    } catch (e) {
      // Older browser — silent no-op (state still works, just no URL sync).
    }
  }

  // ---------- DOM helpers ----------

  function $(sel) {
    return document.querySelector(sel);
  }
  function $$(sel) {
    return Array.prototype.slice.call(document.querySelectorAll(sel));
  }

  function rowConcern(tr) {
    return tr.getAttribute("data-concern") || "";
  }
  function rowName(tr) {
    return (tr.getAttribute("data-workflow") || "").toLowerCase();
  }

  // ---------- Filter application ----------

  function applyFilters() {
    var tbody = $(".workflows-table tbody");
    if (!tbody) return;
    var rows = $$(".workflows-table tbody tr");
    var query = state.search.trim().toLowerCase();
    var anyVisible = false;

    rows.forEach(function (tr) {
      var inBucket = state.buckets.has(rowConcern(tr));
      var matchesQuery = !query || rowName(tr).indexOf(query) !== -1;
      var visible = inBucket && matchesQuery;
      if (visible) anyVisible = true;
      tr.hidden = !visible;
    });

    updateEmptyState(anyVisible, query);
  }

  function updateEmptyState(anyVisible, query) {
    // Reuse the existing .empty <p> from the template when present, or
    // inject an empty-state row inside the table body. Keeping the
    // affordance close to the table to mirror the Specs page UX.
    var box = $("#workflows-empty-state");
    if (!box) {
      box = document.createElement("div");
      box.id = "workflows-empty-state";
      box.className = "empty-state";
      box.setAttribute("role", "status");
      box.hidden = true;
      var table = $(".workflows-table");
      if (table && table.parentNode) {
        table.parentNode.insertBefore(box, table.nextSibling);
      }
    }
    if (anyVisible) {
      box.hidden = true;
      return;
    }
    box.hidden = false;
    if (state.buckets.size === 0) {
      box.textContent =
        "All concerns filtered out — re-enable at least one chip above.";
    } else if (query) {
      box.textContent =
        "No workflows in active concerns match '" + query + "'.";
    } else {
      box.textContent = "No workflows match the current filters.";
    }
  }

  // ---------- Chip toggle ----------

  function setChipState(chip, active) {
    chip.classList.toggle("chip-active", active);
    chip.classList.toggle("chip-inactive", !active);
    chip.setAttribute("aria-pressed", active ? "true" : "false");
    // Add or remove the "✗" hidden-count marker on inactive chips so
    // the visual state matches the Specs page convention.
    var mark = chip.querySelector(".chip-hidden-mark");
    if (!active && !mark) {
      var span = document.createElement("span");
      span.className = "chip-hidden-mark";
      span.setAttribute("aria-hidden", "true");
      span.textContent = "✗";
      chip.appendChild(span);
    } else if (active && mark) {
      mark.remove();
    }
  }

  function wireChips() {
    $$(".workflows-toolbar .chip[data-bucket]").forEach(function (chip) {
      chip.addEventListener("click", function () {
        var bucket = chip.getAttribute("data-bucket");
        if (!VALID_BUCKETS.has(bucket)) return;
        if (state.buckets.has(bucket)) {
          state.buckets.delete(bucket);
          setChipState(chip, false);
        } else {
          state.buckets.add(bucket);
          setChipState(chip, true);
        }
        applyFilters();
        syncURL();
      });
    });
  }

  function wireSearch() {
    var input = $("#workflows-search");
    if (!input) return;
    input.addEventListener("input", function () {
      state.search = input.value;
      applyFilters();
      syncURL();
    });
  }

  // ---------- Init ----------

  function syncChipsToState() {
    // After readURLState() runs, the visual chip state may not match
    // what state.buckets says. Server-rendered HTML has all chips
    // chip-active; URL params may have flipped some off. This brings
    // visual state in line with the logical state on first paint.
    $$(".workflows-toolbar .chip[data-bucket]").forEach(function (chip) {
      var bucket = chip.getAttribute("data-bucket");
      setChipState(chip, state.buckets.has(bucket));
    });
  }

  function init() {
    // A3c — URL state is the source of truth on init. Read it before
    // wiring handlers so the first handler invocation already sees
    // the URL-derived state.
    readURLState();
    syncChipsToState();
    wireChips();
    wireSearch();
    // Sync the search <input>'s value to the URL-derived state.
    var input = $("#workflows-search");
    if (input) {
      input.value = state.search;
    }
    applyFilters();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }

  // Exports — namespace mirrors `window.__attuneSpecs` from
  // specs_refined.js so source-grep tests can verify the surface.
  window.__attuneWorkflows = {
    VALID_BUCKETS: VALID_BUCKETS,
    state: state,
    applyFilters: applyFilters,
    setChipState: setChipState,
    readURLState: readURLState,
    syncURL: syncURL,
    bucketsAreDefault: bucketsAreDefault,
    init: init,
  };
})();
