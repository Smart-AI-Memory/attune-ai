// Specs page — chip filter / search / sort behavior (A3a).
//
// Reads the server-rendered table at /specs and applies client-side
// filtering by lifecycle bucket, slug substring, and a 3-way sort.
// State lives entirely in memory; URL persistence + chip-state-from-URL
// ships in A3c.
//
// Default state (per docs/specs/ops-specs-page-refinement/decisions.md):
//   - All lifecycle buckets active EXCEPT Complete
//   - Search empty
//   - Sort: "recent" (newest last-modified first)
//
// Exports a `window.__attuneSpecs` namespace so future PRs (A3c URL
// params, A3b kebab integration) can hook the same state object
// without re-implementing the chip/search/sort wiring.

(function () {
  "use strict";

  // Default buckets active per R1.3 — all on except Complete.
  // Stale is default-on: stale specs need attention, not concealment.
  var DEFAULT_BUCKETS = [
    "active",
    "approved-not-shipped",
    "paused",
    "parked",
    "stale",
    "draft",
  ];

  var VALID_BUCKETS = new Set([
    "active",
    "approved-not-shipped",
    "complete",
    "paused",
    "parked",
    "stale",
    "draft",
  ]);

  var VALID_SORTS = new Set(["recent", "alpha", "oldest"]);

  // A3c — read initial state from URL (`?bucket=...&sort=...&q=...`).
  // Server already renders the right chips/sort/search on first paint
  // (via dashboard.py's _parse_specs_url_state); this is the JS-side
  // mirror so in-memory state matches the DOM before any user action.
  function readURLState() {
    var params = new URLSearchParams(window.location.search);
    var bucketParam = params.get("bucket");
    var sortParam = params.get("sort");
    var qParam = params.get("q");

    var buckets;
    if (bucketParam === null) {
      buckets = new Set(DEFAULT_BUCKETS);
    } else {
      var candidates = bucketParam.split(",").map(function (b) {
        return b.trim();
      }).filter(function (b) {
        return b && VALID_BUCKETS.has(b);
      });
      buckets = candidates.length > 0
        ? new Set(candidates)
        : new Set(DEFAULT_BUCKETS);
    }
    var sort = (sortParam && VALID_SORTS.has(sortParam)) ? sortParam : "recent";
    var search = qParam ? qParam.slice(0, 200) : "";
    return { buckets: buckets, sort: sort, search: search };
  }

  var state = readURLState();

  // -------------------------------------------------------------------
  // Element lookups (idempotent on missing — script may load on
  // an empty-state page where most elements don't exist).
  // -------------------------------------------------------------------

  function $(sel) { return document.querySelector(sel); }
  function $$(sel) { return Array.prototype.slice.call(document.querySelectorAll(sel)); }

  // -------------------------------------------------------------------
  // URL sync (A3c). Writes the current state back to the URL via
  // history.replaceState so refreshes preserve filters and the URL
  // can be shared. Params that match the default are OMITTED from
  // the URL to keep shared links tidy (`?bucket=stale` instead of
  // `?bucket=active,approved-not-shipped,paused,stale,draft&sort=recent`).
  // -------------------------------------------------------------------

  function bucketsAreDefault(bucketSet) {
    if (bucketSet.size !== DEFAULT_BUCKETS.length) return false;
    for (var i = 0; i < DEFAULT_BUCKETS.length; i++) {
      if (!bucketSet.has(DEFAULT_BUCKETS[i])) return false;
    }
    return true;
  }

  function syncURL() {
    var params = new URLSearchParams(window.location.search);
    // Preserve any params we didn't author (future-proofs against
    // other tools sharing the URL).
    if (bucketsAreDefault(state.buckets)) {
      params.delete("bucket");
    } else {
      // Sort buckets alphabetically for stable URLs.
      var bucketList = Array.from(state.buckets).sort();
      params.set("bucket", bucketList.join(","));
    }
    if (state.sort === "recent") {
      params.delete("sort");
    } else {
      params.set("sort", state.sort);
    }
    if (!state.search) {
      params.delete("q");
    } else {
      params.set("q", state.search);
    }
    var qs = params.toString();
    var newURL = window.location.pathname + (qs ? "?" + qs : "") +
      window.location.hash;
    try {
      window.history.replaceState(null, "", newURL);
    } catch (e) {
      // Older browsers / restrictive contexts — silent fail is fine,
      // the in-memory state is still correct, just not persisted to URL.
    }
  }

  // -------------------------------------------------------------------
  // Filter / sort application
  // -------------------------------------------------------------------

  function rowBucket(tr) {
    return tr.getAttribute("data-bucket") || "";
  }

  function rowSlug(tr) {
    return (tr.getAttribute("data-slug") || "").toLowerCase();
  }

  function rowMtime(tr) {
    var v = tr.getAttribute("data-mtime");
    if (!v) return 0;
    var t = Date.parse(v);
    return isNaN(t) ? 0 : t;
  }

  function applyFilters() {
    var tbody = $(".specs-table tbody");
    if (!tbody) return;
    var rows = $$(".specs-table tbody tr");
    var query = state.search.trim().toLowerCase();
    var anyVisible = false;

    rows.forEach(function (tr) {
      var inBucket = state.buckets.has(rowBucket(tr));
      var matchesQuery = !query || rowSlug(tr).indexOf(query) !== -1;
      var visible = inBucket && matchesQuery;
      if (visible) anyVisible = true;
      tr.hidden = !visible;
    });

    updateEmptyState(anyVisible, query);
  }

  function applySort() {
    var tbody = $(".specs-table tbody");
    if (!tbody) return;
    var rows = $$(".specs-table tbody tr");
    var sort = state.sort;

    rows.sort(function (a, b) {
      if (sort === "alpha") {
        return rowSlug(a).localeCompare(rowSlug(b));
      } else if (sort === "oldest") {
        return rowMtime(a) - rowMtime(b);
      }
      // "recent" — newest first; rows without mtime sink to bottom.
      return rowMtime(b) - rowMtime(a);
    });

    var frag = document.createDocumentFragment();
    rows.forEach(function (tr) { frag.appendChild(tr); });
    tbody.appendChild(frag);
  }

  // -------------------------------------------------------------------
  // Empty state
  // -------------------------------------------------------------------

  function updateEmptyState(anyVisible, query) {
    var box = $("#specs-empty-state");
    var titleEl = $("#specs-empty-title");
    var hintEl = $("#specs-empty-hint");
    if (!box || !titleEl || !hintEl) return;

    if (anyVisible) {
      box.hidden = true;
      return;
    }

    box.hidden = false;
    if (state.buckets.size === 0) {
      titleEl.textContent = "All buckets filtered out";
      hintEl.textContent =
        "Re-enable at least one lifecycle chip above to see specs.";
    } else if (query) {
      titleEl.textContent = "No matches";
      hintEl.textContent =
        "No specs in active buckets match “" + query +
        "”. Try clearing the search or enabling more chips above.";
    } else {
      titleEl.textContent = "No specs in active buckets";
      hintEl.textContent =
        "Toggle more chips above to surface specs.";
    }
  }

  // -------------------------------------------------------------------
  // Wiring
  // -------------------------------------------------------------------

  function setChipState(chip, active) {
    chip.classList.toggle("chip-active", active);
    chip.classList.toggle("chip-inactive", !active);
    chip.setAttribute("aria-pressed", active ? "true" : "false");

    // Add/remove the "✗" hidden-count marker on inactive chips.
    var mark = chip.querySelector(".chip-hidden-mark");
    if (!active && !mark) {
      var span = document.createElement("span");
      span.className = "chip-hidden-mark";
      span.setAttribute("aria-hidden", "true");
      span.textContent = " ✗";
      chip.appendChild(span);
    } else if (active && mark) {
      mark.parentNode.removeChild(mark);
    }
  }

  function wireChips() {
    $$(".specs-toolbar .chip[data-bucket]").forEach(function (chip) {
      chip.addEventListener("click", function () {
        var bucket = chip.getAttribute("data-bucket");
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
    var input = $("#specs-search");
    if (!input) return;
    input.addEventListener("input", function () {
      state.search = input.value;
      applyFilters();
      syncURL();
    });
  }

  function wireSort() {
    var sel = $("#specs-sort");
    if (!sel) return;
    sel.addEventListener("change", function () {
      state.sort = sel.value;
      applySort();
      syncURL();
    });
  }

  function wireResetButton() {
    var btn = $("#specs-reset-filters");
    if (!btn) return;
    btn.addEventListener("click", function () {
      // Reset chips to default and clear search.
      state.buckets = new Set(DEFAULT_BUCKETS);
      state.search = "";
      var input = $("#specs-search");
      if (input) input.value = "";
      $$(".specs-toolbar .chip[data-bucket]").forEach(function (chip) {
        var bucket = chip.getAttribute("data-bucket");
        setChipState(chip, state.buckets.has(bucket));
      });
      applyFilters();
      syncURL();
    });
  }

  function init() {
    // Sync the sort <select>'s value to match state — server template
    // honors initial_sort via the `selected` attribute, but if the
    // user pressed back / restored a tab, the select's value may not
    // match the URL. Be defensive.
    var sortSel = $("#specs-sort");
    if (sortSel && sortSel.value !== state.sort) {
      sortSel.value = state.sort;
    }
    wireChips();
    wireSearch();
    wireSort();
    wireResetButton();
    // Apply the current sort on load — server renders rows in
    // directory order (sorted by slug), but the live sort is
    // determined by state. Re-order on first paint so users see
    // what the sort control claims to be doing.
    applySort();
    applyFilters();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }

  // Exports — namespace mirrors `window.__attuneRunner` from
  // runner.js so source-grep tests (per the test_runner_js_parsing
  // convention) can verify the surface.
  window.__attuneSpecs = {
    DEFAULT_BUCKETS: DEFAULT_BUCKETS,
    VALID_BUCKETS: VALID_BUCKETS,
    VALID_SORTS: VALID_SORTS,
    state: state,
    applyFilters: applyFilters,
    applySort: applySort,
    setChipState: setChipState,
    readURLState: readURLState,
    syncURL: syncURL,
    bucketsAreDefault: bucketsAreDefault,
    init: init,
  };
})();
