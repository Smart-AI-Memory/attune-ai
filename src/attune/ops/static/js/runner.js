// SSE-driven workflow runner UI with rich line rendering.
// No frameworks. Wires the per-row Run button to POST /workflows/<name>/run,
// then attaches an EventSource to /runs/<id>/stream.
//
// Line rendering (since v6.X) parses each streamed line for URLs, file
// paths, workflow-name mentions, and section headers; renders them as
// clickable links / styled chips / bold headers. No innerHTML — every
// segment becomes a real DOM node, so attacker-controlled output (file
// paths, error messages) can't inject script.
(function () {
  "use strict";

  // Canonical workflow names — generated from `attune.ops.data
  // .list_workflows()`. When this drifts, runner.js still works (mentions
  // of unknown names just render as text), so no hard runtime dependency,
  // but the backstop test fails so the array stays honest.
  // >>> AUTO-GENERATED: WORKFLOW_NAMES — do not hand-edit.
  // Source of truth: attune.ops.data.list_workflows().
  // Regenerate: python scripts/sync_runner_workflow_names.py
  var WORKFLOW_NAMES = [
    "bug-predict", "code-review", "deep-review", "dependency-check",
    "discovery-sweep", "doc-audit", "doc-gen", "doc-orchestrator",
    "fix", "health-check", "orchestrated-health-check", "perf-audit",
    "rag-code-gen", "refactor-plan", "release-gate", "release-notes",
    "release-prep", "research-synthesis", "secure-release", "security-audit",
    "simplify-code", "test-audit", "test-gen"
  ];
  // <<< AUTO-GENERATED: WORKFLOW_NAMES

  // Section headers (line-leader text) that get bolded/colored so users
  // can scan workflow output quickly. Matched case-insensitively against
  // the start of the line.
  var SECTION_HEADERS = [
    "Recommendations", "Recommendation",
    "Next steps", "Next step",
    "Issues found", "Issues", "Findings", "Finding",
    "Summary", "Suggestions", "Suggestion",
    "Warnings", "Warning", "Errors", "Error",
    "Notes", "Note"
  ];

  // localStorage key for the user's most-recently-picked scope. Shared
  // across all workflow rows on the page — the user's working scope is
  // a session-level fact, not a per-workflow fact.
  var SCOPE_STORAGE_KEY = "attune-ops:lastScope";

  // Full regex-meta escape for any string going into a RegExp. Covers
  // every regex metacharacter including backslash, so even if
  // WORKFLOW_NAMES is ever populated from a less-trusted source, the
  // regex semantics stay intact (no injection bypass via embedded
  // metacharacters). CodeQL flagged the previous one-character version
  // as "incomplete string escaping" — fair, even though today's input
  // is a hardcoded safe array.
  function reEscape(s) {
    return s.replace(/[.*+?^${}()|[\]\\-]/g, "\\$&");
  }

  // Build a single regex that matches a URL, file path, or workflow
  // name. Order in the alternation is important: URLs first (they
  // might contain dots), then file paths, then workflow names.
  var FILE_EXTS = "py|pyi|js|jsx|ts|tsx|md|rst|txt|yml|yaml|json|toml|cfg|ini|html|css|sh|bash|zsh";
  var TOKEN_RE = new RegExp(
    "(https?:\\/\\/[^\\s<>\"']+)" +                                  // 1: URL
    "|" +
    "((?:[\\w][\\w./\\-]*\\/)?[\\w][\\w.\\-]*\\.(?:" + FILE_EXTS + ")(?::\\d+(?::\\d+)?)?)" +  // 2: file path
    "|" +
    "\\b(" + WORKFLOW_NAMES.map(reEscape).join("|") + ")\\b",                                 // 3: workflow name
    "g"
  );

  function findRow(name) {
    return document.querySelector('tr[data-workflow="' + CSS.escape(name) + '"]');
  }

  function setStatus(row, status) {
    var el = row.querySelector("[data-status]");
    if (el) el.textContent = status;
  }

  // Detect a section-header prefix on a line. Returns {header, rest} if
  // matched, else null. Tolerates leading whitespace and bullet markers
  // so "- Recommendations:" or "  ## Next steps" both qualify.
  function detectSectionHeader(line) {
    var stripped = line.replace(/^[\s\-*#>•]+/, "");
    for (var i = 0; i < SECTION_HEADERS.length; i++) {
      var h = SECTION_HEADERS[i];
      var re = new RegExp("^" + h.replace(/\s/g, "\\s") + "\\s*:", "i");
      var match = stripped.match(re);
      if (match) {
        var leader = line.slice(0, line.length - stripped.length) + match[0];
        var rest = stripped.slice(match[0].length);
        return { leader: leader, rest: rest };
      }
    }
    return null;
  }

  // Append inline-parsed segments of `text` to `parent`. Each segment is
  // either a Text node (safe by construction) or a styled child element.
  function appendInline(parent, text) {
    if (!text) return;
    var lastIndex = 0;
    var m;
    TOKEN_RE.lastIndex = 0;
    while ((m = TOKEN_RE.exec(text)) !== null) {
      if (m.index > lastIndex) {
        parent.appendChild(document.createTextNode(text.slice(lastIndex, m.index)));
      }
      if (m[1]) {
        // URL
        var a = document.createElement("a");
        a.href = m[1];
        a.target = "_blank";
        a.rel = "noopener noreferrer";
        a.className = "log-link";
        a.textContent = m[1];
        parent.appendChild(a);
      } else if (m[2]) {
        // File path with optional :line[:col] suffix
        var span = document.createElement("span");
        span.className = "log-file";
        span.textContent = m[2];
        parent.appendChild(span);
      } else if (m[3]) {
        // Workflow name — inert pill in Tier 1; Tier 2 will make it clickable
        var pill = document.createElement("span");
        pill.className = "log-workflow";
        pill.textContent = m[3];
        parent.appendChild(pill);
      }
      lastIndex = TOKEN_RE.lastIndex;
    }
    if (lastIndex < text.length) {
      parent.appendChild(document.createTextNode(text.slice(lastIndex)));
    }
  }

  // Render one streamed line into the log pane with rich segments.
  function appendLine(row, line) {
    var pre = row.querySelector("[data-log]");
    if (!pre) return;

    var header = detectSectionHeader(line);
    if (header) {
      var leaderSpan = document.createElement("span");
      leaderSpan.className = "log-header";
      leaderSpan.textContent = header.leader;
      pre.appendChild(leaderSpan);
      appendInline(pre, header.rest);
    } else {
      appendInline(pre, line);
    }
    pre.appendChild(document.createTextNode("\n"));
    pre.scrollTop = pre.scrollHeight;
  }

  function showLogPane(row) {
    var pane = row.querySelector("[data-log-pane]");
    if (pane) pane.hidden = false;
    var pre = row.querySelector("[data-log]");
    // Clear via removing all children (faster than textContent = "" for
    // a pre with many child nodes after rich rendering).
    if (pre) while (pre.firstChild) pre.removeChild(pre.firstChild);
  }

  // Phase 6.1 — fire-and-forget UI interaction counter ping. Sends
  // a small JSON POST to /api/telemetry/interaction. Any failure
  // (network, 4xx/5xx, missing endpoint) is swallowed silently:
  // these counters are best-effort dashboard telemetry, never on
  // the critical path of a user action.
  function recordInteraction(event, target) {
    if (typeof fetch !== "function") return;
    var body = { event: String(event || "") };
    if (target != null && target !== "") {
      body.target = String(target);
    }
    try {
      fetch("/api/telemetry/interaction", {
        method: "POST",
        headers: attuneClientHeaders({ "Content-Type": "application/json" }),
        body: JSON.stringify(body),
        // keepalive lets the request survive a navigation away
        // from the page (e.g. pill-click → navigate to new run).
        keepalive: true
      }).catch(function () {
        // INTENTIONAL: best-effort telemetry, no surfacing.
      });
    } catch (e) {
      // INTENTIONAL: same as above — never raise from telemetry.
    }
  }

  // Export internals for the test page (tests/unit/ops/static/test_runner.html).
  // Wrapped in a check so it's a no-op in environments without window.
  if (typeof window !== "undefined") {
    window.__attuneRunner = {
      detectSectionHeader: detectSectionHeader,
      appendInline: appendInline,
      appendLine: appendLine,
      getScope: getScope,
      wireScopePickerToggle: wireScopePickerToggle,
      setupRecentRuns: setupRecentRuns,
      renderRecentRunsInto: renderRecentRunsInto,
      statusClass: statusClass,
      loadSavedScope: loadSavedScope,
      saveScope: saveScope,
      applyScopeToRow: applyScopeToRow,
      restoreScopeOnLoad: restoreScopeOnLoad,
      wireScopeSave: wireScopeSave,
      SCOPE_STORAGE_KEY: SCOPE_STORAGE_KEY,
      WORKFLOW_NAMES: WORKFLOW_NAMES,
      SECTION_HEADERS: SECTION_HEADERS,
      appendBusyErrorLine: appendBusyErrorLine,
      applyChipCounts: applyChipCounts,
      refreshSweepChips: refreshSweepChips,
      wireSweepChipRefresh: wireSweepChipRefresh,
      recordInteraction: recordInteraction
    };
  }

  // Format server error responses into something a human can read.
  // 409 in particular has a structured payload {detail: {message,
  // current_run_id}} — surface just the message + the run id, not
  // the raw JSON envelope.
  function formatErrorDetail(status, rawText) {
    if (status === 409) {
      try {
        var parsed = JSON.parse(rawText);
        var detail = parsed && parsed.detail ? parsed.detail : {};
        var msg = detail.message || "another workflow is running";
        var runId = detail.current_run_id ? " (run " + detail.current_run_id + ")" : "";
        return msg.charAt(0).toUpperCase() + msg.slice(1) + runId +
          ". Wait for it to finish, then try again.";
      } catch (e) {
        // Fall through to raw text on parse failure.
      }
    }
    return rawText;
  }

  // Render a 409 "runner busy" error inline with a clickable link to the
  // currently-running run's view page. Falls back to plain-text rendering
  // when the payload can't be parsed or the run_id doesn't match our
  // expected shape (defensive against injection: the href is only
  // constructed from a value matching ``^[A-Za-z0-9_-]{1,64}$``, which
  // mirrors the server-side validator at ``dashboard.py:run_view_page``).
  function appendBusyErrorLine(row, rawText) {
    var pre = row.querySelector("[data-log]");
    if (!pre) return;
    var msg = "another workflow is running";
    var runId = "";
    try {
      var parsed = JSON.parse(rawText);
      var detail = parsed && parsed.detail ? parsed.detail : {};
      if (detail.message) msg = String(detail.message);
      if (detail.current_run_id) runId = String(detail.current_run_id);
    } catch (e) {
      // Fall through — plain text rendering below.
    }
    // Strict run-id shape check before building the href. Mirrors the
    // server-side regex; anything else degrades to a plain text run id
    // without a clickable link.
    var safeRunId = /^[A-Za-z0-9_-]{1,64}$/.test(runId) ? runId : "";
    var leader = document.createElement("span");
    leader.textContent = "[error] " + msg.charAt(0).toUpperCase() + msg.slice(1);
    pre.appendChild(leader);
    if (runId) {
      pre.appendChild(document.createTextNode(" (run "));
      if (safeRunId) {
        var link = document.createElement("a");
        link.href = "/runs/" + encodeURIComponent(safeRunId) + "/view";
        link.className = "link";
        var code = document.createElement("code");
        code.textContent = safeRunId;
        link.appendChild(code);
        pre.appendChild(link);
      } else {
        pre.appendChild(document.createTextNode(runId));
      }
      pre.appendChild(document.createTextNode(")"));
    }
    pre.appendChild(document.createTextNode(". Wait for it to finish, then try again.\n"));
    pre.scrollTop = pre.scrollHeight;
  }

  // Format an elapsed-seconds count as "Xs" or "Xm Ys" for readability.
  // Updates roughly every second so the user sees the run is alive even
  // when subagents are mid-call and no new log lines are arriving.
  function formatElapsed(seconds) {
    var s = Math.floor(seconds);
    if (s < 60) return s + "s";
    var m = Math.floor(s / 60);
    var rem = s % 60;
    return m + "m " + rem + "s";
  }

  // Start a 1-second tick on a row. Returns a stopper to clear the timer.
  // The label argument lets us reuse this for "running" vs "starting…".
  function startTick(row, label) {
    var startedAt = Date.now();
    setStatus(row, label + " 0s");
    var id = setInterval(function () {
      var elapsed = (Date.now() - startedAt) / 1000;
      setStatus(row, label + " " + formatElapsed(elapsed));
    }, 1000);
    return function stop() { clearInterval(id); };
  }

  // Read the scope the user picked for this workflow row.
  // Returns null for "Project-wide" (default) or workflows that don't
  // support --path (no picker in the row). Returns the string value of
  // the dropdown for a feature pick, or the custom text input's value
  // when the user picked "Custom path…". Trims whitespace; an empty
  // custom value falls back to project-wide (null).
  function getScope(row) {
    var picker = row.querySelector("[data-scope-picker]");
    if (!picker) return null;
    var val = picker.value;
    if (val === "" || val === null || val === undefined) return null;
    if (val === "__custom__") {
      var custom = row.querySelector("[data-scope-custom]");
      if (!custom) return null;
      var trimmed = (custom.value || "").trim();
      return trimmed === "" ? null : trimmed;
    }
    return val;
  }

  // Toggle the custom-path text input based on the picker's value. Shown
  // when "Custom path…" is selected, hidden otherwise.
  function wireScopePickerToggle(row) {
    var picker = row.querySelector("[data-scope-picker]");
    var custom = row.querySelector("[data-scope-custom]");
    if (!picker || !custom) return;
    picker.addEventListener("change", function () {
      if (picker.value === "__custom__") {
        custom.hidden = false;
        custom.focus();
      } else {
        custom.hidden = true;
      }
    });
  }

  // Read the saved scope from localStorage. Returns the stored string
  // (which may be "" for an explicit Project-wide pick), or null if the
  // key was never set OR localStorage is unavailable. Never throws.
  function loadSavedScope() {
    try {
      return window.localStorage.getItem(SCOPE_STORAGE_KEY);
    } catch (e) {
      // INTENTIONAL: localStorage disabled / quota exceeded / sandboxed.
      // Degrade gracefully — picker stays at its server-rendered default.
      return null;
    }
  }

  // Save the resolved scope to localStorage. ``value`` is the literal
  // picker value to remember ("" for Project-wide, a feature path, or
  // a custom path string). Never throws.
  function saveScope(value) {
    try {
      window.localStorage.setItem(SCOPE_STORAGE_KEY, value == null ? "" : String(value));
    } catch (e) {
      // INTENTIONAL: best-effort write. Same degradation as loadSavedScope.
    }
  }

  // Read the server-injected scope-picker config block. After Phase
  // A3, the only field this block carries is ``workspaceRoot`` (used
  // for cross-worktree validation of saved localStorage scopes).
  // First-paint defaults moved to per-row ``data-scope-default``
  // attributes, so the previous ``firstFeaturePath`` / ``allCodePath``
  // fields are gone.
  function readScopePickerConfig() {
    var el = document.getElementById("scope-picker-config");
    if (!el) return { workspaceRoot: "" };
    try {
      var cfg = JSON.parse(el.textContent || "{}");
      return {
        workspaceRoot:
          typeof cfg.workspaceRoot === "string" ? cfg.workspaceRoot : ""
      };
    } catch (e) {
      return { workspaceRoot: "" };
    }
  }

  // Returns true if ``value`` is a scope this workspace can actually
  // accept at run-trigger time. Catches stale localStorage from a
  // previous session in a different worktree — the run endpoint would
  // reject it with "outside allowed directory" anyway, but the scope
  // picker should never restore a value that's structurally invalid
  // for the current workspace.
  //
  // Rules:
  //   - "" (Project-wide) is always valid.
  //   - A relative path (no leading "/") is always treated as valid;
  //     the server resolves it against project_root at run time.
  //   - An absolute path is valid iff it equals workspaceRoot or sits
  //     beneath it (prefix match guarded by trailing-slash to avoid
  //     "/foo" matching "/foobar").
  //   - If workspaceRoot is empty (server didn't emit it — old build),
  //     accept all values to preserve previous behavior.
  function isScopeInWorkspace(value, workspaceRoot) {
    if (value === "" || value == null) return true;
    if (!workspaceRoot) return true;
    if (value.charAt(0) !== "/") return true;
    if (value === workspaceRoot) return true;
    return value.indexOf(workspaceRoot + "/") === 0;
  }

  // Apply a scope value to a single row's picker. ``value`` is:
  //   - "" (Project-wide)             — select the empty-value option.
  //   - matches a feature option      — select that option directly.
  //   - any other non-empty string    — select "Custom path…" and
  //                                     pre-fill the custom input.
  // Also syncs the custom input's visibility with the picker state so
  // wireScopePickerToggle's invariant holds without a synthetic event.
  function applyScopeToRow(row, value) {
    var picker = row.querySelector("[data-scope-picker]");
    if (!picker) return;
    var custom = row.querySelector("[data-scope-custom]");

    var matched = false;
    for (var i = 0; i < picker.options.length; i++) {
      if (picker.options[i].value === value) {
        picker.value = value;
        matched = true;
        break;
      }
    }
    if (!matched && value !== "") {
      // Saved path doesn't match any feature option — fall to Custom
      // path… with the saved string pre-filled. Handles features
      // removed from features.yaml since the user last saved.
      picker.value = "__custom__";
      if (custom) {
        custom.value = value;
      }
    }
    if (custom) {
      custom.hidden = picker.value !== "__custom__";
    }
  }

  // Restore the saved scope (or the per-row first-load default) on
  // every picker row at page load. Per-row resolution:
  //   1. localStorage has a saved scope (could be "") — apply it to
  //      every row (preserves PR #344's "remember last-used scope"
  //      contract; the saved value is a global last-used, not
  //      per-workflow).
  //   2. Else, read each row's ``data-scope-default`` (server-rendered
  //      from features.yaml by workflow_default_scope). Empty string
  //      means project-wide — leave that row at the template default.
  function restoreScopeOnLoad() {
    var cfg = readScopePickerConfig();
    var saved = loadSavedScope();
    // Workspace validation: if the saved scope is an absolute path
    // that's not under this workspace's root, discard it (stale from
    // a different worktree). Done once before the per-row loop so the
    // warning logs exactly once per page load.
    if (saved !== null && !isScopeInWorkspace(saved, cfg.workspaceRoot)) {
      try {
        window.localStorage.removeItem(SCOPE_STORAGE_KEY);
      } catch (e) {
        // INTENTIONAL: best-effort. If localStorage is unavailable
        // the picker just falls back to defaults on each load.
      }
      console.warn(
        "attune-ops: discarded stale scope (" + saved +
        ") — not under workspace " + cfg.workspaceRoot
      );
      saved = null;
    }
    document.querySelectorAll("tr[data-workflow]").forEach(function (row) {
      var value;
      if (saved !== null) {
        value = saved;
      } else {
        value = row.getAttribute("data-scope-default") || "";
      }
      if (value === "") return; // Project-wide is the template default.
      applyScopeToRow(row, value);
    });
  }

  // Persist the scope whenever the user changes the picker dropdown or
  // the custom-path input. Picker change saves directly unless the
  // selection is "__custom__", in which case we wait for the custom
  // input's own change event so we save the actual typed value, not an
  // empty placeholder.
  function wireScopeSave(row) {
    var picker = row.querySelector("[data-scope-picker]");
    var custom = row.querySelector("[data-scope-custom]");
    if (!picker) return;
    // Phase 6.1 — workflow name is the per-row data attribute set by
    // the workflows.html template (data-workflow=<name>). Falls back
    // to "" so recordInteraction buckets unidentified rows under
    // "(unknown)" rather than mislabeling them.
    var workflowName = row.getAttribute("data-workflow") || "";
    picker.addEventListener("change", function () {
      if (picker.value === "__custom__") return;
      saveScope(picker.value);
      recordInteraction("scope_picker_change", workflowName);
    });
    if (custom) {
      custom.addEventListener("change", function () {
        // Guard: only save if the picker is still on Custom path. The
        // user might have moved on between typing and the change event
        // firing (race with picker.change).
        if (picker.value !== "__custom__") return;
        var trimmed = (custom.value || "").trim();
        if (trimmed === "") return; // Blank custom is Project-wide; skip.
        saveScope(trimmed);
        recordInteraction("scope_picker_change", workflowName);
      });
    }
  }

  // Fetch /api/runs/<workflow> and render up to 5 chips into the
  // container element. Each chip is a real anchor element (no
  // innerHTML — workflow name and run id are user-controlled enough
  // that we'd rather treat them as untrusted, and DOM nodes are
  // unambiguous about that).
  function setupRecentRuns(container) {
    if (!container) return;
    var workflow = container.getAttribute("data-recent-runs");
    if (!workflow) return;
    // Optional: when rendered on /runs/<id>/view, the page sets
    // data-exclude-run-id to the current run's id so the strip shows
    // *other* recent runs of this workflow rather than including the
    // run the user is already looking at (P1-5 in the 2026-05-14 QA
    // punch list).
    var excludeRunId = container.getAttribute("data-exclude-run-id") || "";
    fetch("/api/runs/" + encodeURIComponent(workflow), {
      headers: { Accept: "application/json" }
    })
      .then(function (resp) {
        if (!resp.ok) return null;
        return resp.json();
      })
      .then(function (body) {
        if (!body || !body.runs || body.runs.length === 0) return;
        var runs = body.runs;
        if (excludeRunId) {
          runs = runs.filter(function (r) { return r.id !== excludeRunId; });
        }
        if (runs.length === 0) return;
        renderRecentRunsInto(container, runs.slice(0, 5));
      })
      .catch(function () {
        // INTENTIONAL: history is a nice-to-have; a failed fetch
        // leaves the container hidden (its default state) so the
        // page renders normally without it.
      });
  }

  // Render an ISO 8601 timestamp as a compact relative label:
  //   - same calendar day  -> "h:MM AM/PM" (12h)
  //   - previous day       -> "Yesterday"
  //   - within last 7 days -> "Sun" .. "Sat"
  //   - older              -> "May 14"
  // Returns "?" for missing/unparseable input. Falls back to UTC date
  // pieces if Date methods throw (defensive; shouldn't happen in
  // practice for well-formed ISO inputs from the server).
  function formatRunDate(isoString) {
    if (!isoString) return "?";
    var d = new Date(isoString);
    if (isNaN(d.getTime())) return "?";
    var now = new Date();
    var sameDay = d.toDateString() === now.toDateString();
    if (sameDay) {
      var h = d.getHours();
      var ampm = h >= 12 ? "PM" : "AM";
      var h12 = h % 12;
      if (h12 === 0) h12 = 12;
      var mm = String(d.getMinutes()).padStart(2, "0");
      return h12 + ":" + mm + " " + ampm;
    }
    var yesterday = new Date(now);
    yesterday.setDate(now.getDate() - 1);
    if (d.toDateString() === yesterday.toDateString()) {
      return "Yesterday";
    }
    var daysAgo = Math.floor((now.getTime() - d.getTime()) / 86400000);
    if (daysAgo >= 0 && daysAgo < 7) {
      return ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"][d.getDay()];
    }
    var months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
    return months[d.getMonth()] + " " + d.getDate();
  }

  function renderRecentRunsInto(container, runs) {
    while (container.firstChild) container.removeChild(container.firstChild);
    var label = document.createElement("span");
    label.className = "recent-runs-label";
    label.textContent = "Recent: ";
    container.appendChild(label);
    runs.forEach(function (run) {
      var a = document.createElement("a");
      a.className = "recent-run-chip chip-" + statusClass(run.status);
      a.href = "/runs/" + encodeURIComponent(run.id) + "/view";
      // Visible label: date · status. The short run-id used to live
      // here but conveyed nothing actionable; it's preserved in the
      // tooltip alongside the full ISO timestamp and scope path so
      // power users can still see it on hover.
      var dateTxt = document.createElement("span");
      dateTxt.className = "recent-run-date";
      dateTxt.textContent = formatRunDate(run.started_at);
      a.appendChild(dateTxt);
      a.appendChild(document.createTextNode(" "));
      var statusTxt = document.createElement("span");
      statusTxt.className = "recent-run-status";
      statusTxt.textContent = String(run.status || "?");
      a.appendChild(statusTxt);
      // Tooltip carries the previously-visible run id plus full
      // timestamp + scope. Matches the dashboard's tooltip-positive
      // UX rule — supplemental detail on hover, compact label always.
      var tipParts = [];
      if (run.started_at) tipParts.push(run.started_at);
      tipParts.push("id " + String(run.id).slice(0, 8));
      if (run.path) tipParts.push("scope: " + run.path);
      a.setAttribute("data-tooltip", tipParts.join(" · "));
      a.setAttribute("aria-label", tipParts.join(", "));
      container.appendChild(a);
    });
    container.hidden = false;
  }

  function statusClass(status) {
    if (status === "completed") return "ok";
    if (status === "failed") return "danger";
    if (status === "running" || status === "pending") return "warn";
    return "muted";
  }

  // Export getScope for tests (alongside the existing rendering helpers).
  // Note: window.__attuneRunner is populated farther below, after these
  // helpers are defined; the assignment block lives at the same scope.

  function attach(button) {
    button.addEventListener("click", async function () {
      var name = button.dataset.workflow;
      var row = findRow(name);
      if (!row) return;
      button.disabled = true;
      setStatus(row, "starting…");
      try {
        var scope = getScope(row);
        // Always send the client token; add Content-Type + body only
        // when a scope path is set (else it's a bare project-wide run).
        var fetchOpts = { method: "POST", headers: attuneClientHeaders() };
        if (scope !== null) {
          fetchOpts.headers = attuneClientHeaders({ "Content-Type": "application/json" });
          fetchOpts.body = JSON.stringify({ path: scope });
        }
        var resp = await fetch("/workflows/" + encodeURIComponent(name) + "/run", fetchOpts);
        if (!resp.ok) {
          var detail = await resp.text();
          // Show the inline error on the workflows page — don't navigate
          // away if the run never started, so the user can see why and
          // retry without losing context.
          showLogPane(row);
          if (resp.status === 409) {
            // Render with a clickable link to the in-flight run so the
            // user can jump back instead of starting a duplicate run.
            appendBusyErrorLine(row, detail);
          } else {
            appendLine(row, "[error] " + formatErrorDetail(resp.status, detail));
          }
          setStatus(row, "error");
          button.disabled = false;
          return;
        }
        var body = await resp.json();
        // Run started successfully — navigate to the full-page run view.
        // The view page reconnects to the same SSE stream and replays the
        // buffered log on refresh, so the output survives a reload (the
        // long-standing inline-log-pane refresh-loses-state bug).
        window.location.assign("/runs/" + encodeURIComponent(body.run_id) + "/view");
      } catch (err) {
        showLogPane(row);
        appendLine(row, "[error] " + err);
        setStatus(row, "error");
        button.disabled = false;
      }
    });
  }

  // ----------------------------------------------------------------
  // Phase 3 (discovery-sweep) — chip refresh on scope-picker change
  // ----------------------------------------------------------------
  //
  // Server first-paints chip counts from the row's default scope. When
  // the user picks a different scope (or types a custom path), refresh
  // the chips via the chips API so they reflect the new scope's
  // persisted sweep result. Failure modes fall through to "no sweep
  // recorded" — never throws, never blocks the picker.
  function refreshSweepChips(row) {
    var chipRow = row.querySelector("[data-sweep-chips]");
    if (!chipRow) return;
    var scope = getScope(row);
    var params = new URLSearchParams();
    if (scope !== null) params.set("scope", scope);
    fetch("/api/workflows/discovery-sweep/chips?" + params.toString(), {
      headers: { Accept: "application/json" }
    })
      .then(function (resp) {
        if (!resp.ok) return null;
        return resp.json();
      })
      .then(function (body) {
        if (!body) return;
        applyChipCounts(chipRow, body);
      })
      .catch(function () {
        // INTENTIONAL: chip refresh is best-effort. Stale counts are
        // better than an error message blocking the picker.
      });
  }

  function applyChipCounts(chipRow, body) {
    var hash = String(body.scope_hash || "");
    chipRow.setAttribute("data-scope-hash", hash);
    chipRow.setAttribute("data-has-result", body.has_result ? "1" : "0");
    ["queue", "questions", "rejected"].forEach(function (bucket) {
      var anchor = chipRow.querySelector('[data-chip="' + bucket + '"]');
      if (!anchor) return;
      var count = body[bucket];
      if (typeof count !== "number") count = 0;
      var span = anchor.querySelector("[data-chip-count]");
      if (span) span.textContent = String(count);
      // Update href so detail-page navigation lands on the new scope.
      // /^[0-9a-f]{16}$/ guard mirrors the server route's validation
      // so a garbled API payload doesn't yield a broken link.
      if (/^[0-9a-f]{16}$/.test(hash)) {
        anchor.href = "/workflows/discovery-sweep/results/" + hash + "?bucket=" + bucket;
      }
    });
    var status = chipRow.querySelector("[data-sweep-chip-status]");
    if (status) {
      if (body.has_result) {
        status.textContent = "latest result";
        status.removeAttribute("data-empty");
      } else {
        status.textContent = "no sweep recorded for this scope yet";
        status.setAttribute("data-empty", "1");
      }
    }
  }

  function wireSweepChipRefresh(row) {
    if (row.getAttribute("data-workflow") !== "discovery-sweep") return;
    var picker = row.querySelector("[data-scope-picker]");
    var custom = row.querySelector("[data-scope-custom]");
    if (picker) {
      picker.addEventListener("change", function () {
        // Defer until any wireScopePickerToggle effects settle.
        if (picker.value !== "__custom__") refreshSweepChips(row);
      });
    }
    if (custom) {
      custom.addEventListener("change", function () {
        refreshSweepChips(row);
      });
    }
  }

  document.addEventListener("DOMContentLoaded", function () {
    document.querySelectorAll("[data-run-button]").forEach(attach);
    document.querySelectorAll("tr[data-workflow]").forEach(wireScopePickerToggle);
    document.querySelectorAll("tr[data-workflow]").forEach(wireScopeSave);
    document.querySelectorAll("tr[data-workflow]").forEach(wireSweepChipRefresh);
    restoreScopeOnLoad();
    document.querySelectorAll("[data-recent-runs]").forEach(setupRecentRuns);
    // After scope restoration, refresh chips once so a localStorage-restored
    // scope (different from the server's default-scope first paint) shows
    // its own counts.
    var sweepRow = document.querySelector('tr[data-workflow="discovery-sweep"]');
    if (sweepRow) refreshSweepChips(sweepRow);
  });
})();
