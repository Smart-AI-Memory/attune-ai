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

  // Canonical workflow names — kept in sync with `attune.ops.data
  // .list_workflows()` output. When this drifts, runner.js still works
  // (mentions of unknown names just render as text), so no hard sync
  // dependency, but worth a periodic glance.
  var WORKFLOW_NAMES = [
    "bug-predict", "code-review", "deep-review", "dependency-check",
    "discovery-sweep", "doc-audit", "doc-gen", "doc-orchestrator",
    "health-check", "orchestrated-health-check", "perf-audit",
    "rag-code-gen", "refactor-plan", "release-prep",
    "research-synthesis", "secure-release", "security-audit",
    "simplify-code", "test-audit", "test-gen"
  ];

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
      WORKFLOW_NAMES: WORKFLOW_NAMES,
      SECTION_HEADERS: SECTION_HEADERS
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

  // Fetch /api/runs/<workflow> and render up to 5 chips into the
  // container element. Each chip is a real anchor element (no
  // innerHTML — workflow name and run id are user-controlled enough
  // that we'd rather treat them as untrusted, and DOM nodes are
  // unambiguous about that).
  function setupRecentRuns(container) {
    if (!container) return;
    var workflow = container.getAttribute("data-recent-runs");
    if (!workflow) return;
    fetch("/api/runs/" + encodeURIComponent(workflow), {
      headers: { Accept: "application/json" }
    })
      .then(function (resp) {
        if (!resp.ok) return null;
        return resp.json();
      })
      .then(function (body) {
        if (!body || !body.runs || body.runs.length === 0) return;
        renderRecentRunsInto(container, body.runs.slice(0, 5));
      })
      .catch(function () {
        // INTENTIONAL: history is a nice-to-have; a failed fetch
        // leaves the container hidden (its default state) so the
        // page renders normally without it.
      });
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
      // Compact label: short id + scope marker. Status conveyed via
      // chip color, not extra text — keeps the strip narrow.
      var idTxt = document.createElement("code");
      idTxt.textContent = String(run.id).slice(0, 8);
      a.appendChild(idTxt);
      if (run.path) {
        a.title = "scope: " + run.path;
      }
      a.appendChild(document.createTextNode(" "));
      var statusTxt = document.createElement("span");
      statusTxt.className = "recent-run-status";
      statusTxt.textContent = String(run.status || "?");
      a.appendChild(statusTxt);
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
        var fetchOpts = { method: "POST" };
        if (scope !== null) {
          fetchOpts.headers = { "Content-Type": "application/json" };
          fetchOpts.body = JSON.stringify({ path: scope });
        }
        var resp = await fetch("/workflows/" + encodeURIComponent(name) + "/run", fetchOpts);
        if (!resp.ok) {
          var detail = await resp.text();
          // Show the inline error on the workflows page — don't navigate
          // away if the run never started, so the user can see why and
          // retry without losing context.
          showLogPane(row);
          appendLine(row, "[error] " + formatErrorDetail(resp.status, detail));
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

  document.addEventListener("DOMContentLoaded", function () {
    document.querySelectorAll("[data-run-button]").forEach(attach);
    document.querySelectorAll("tr[data-workflow]").forEach(wireScopePickerToggle);
    document.querySelectorAll("[data-recent-runs]").forEach(setupRecentRuns);
  });
})();
