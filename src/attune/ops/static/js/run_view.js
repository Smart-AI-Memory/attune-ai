// Per-run page logic: SSE replay + status, recent-runs strip, chained-
// from badge, and Phase-4 clickable workflow-name pills.
//
// Configuration comes from a server-injected <script
// type="application/json" id="run-view-data"> block (see
// templates/run_view.html). Reading from a tagged JSON block avoids
// global-namespace pollution and keeps the data flow inspectable in
// devtools.
(function () {
  "use strict";

  var dataEl = document.getElementById("run-view-data");
  if (!dataEl) return;

  var DATA;
  try {
    DATA = JSON.parse(dataEl.textContent || "{}");
  } catch (e) {
    DATA = {};
  }

  var STREAM_URL = DATA.stream_url || "";
  var INITIAL_STATUS = DATA.initial_status || "";
  var SOURCE_WORKFLOW = DATA.workflow || "";
  var SOURCE_PATH = DATA.path == null ? null : DATA.path;
  var ALLOW_RUN = DATA.allow_run === true;

  var pre = document.querySelector("[data-log]");
  var statusEl = document.querySelector("[data-status]");
  var chainedFromEl = document.querySelector("[data-chained-from]");
  var startedAt = Date.now();
  var tickerId = null;

  function setStatus(text) {
    if (statusEl) statusEl.textContent = text;
  }

  function setStatusClass(extra) {
    if (!statusEl) return;
    statusEl.className = "run-view-status chip " + (extra || "");
  }

  function appendLine(line) {
    if (!pre) return;
    pre.appendChild(document.createTextNode(line + "\n"));
    pre.scrollTop = pre.scrollHeight;
  }

  function startTicker() {
    if (tickerId) return;
    tickerId = setInterval(function () {
      var s = Math.floor((Date.now() - startedAt) / 1000);
      var label;
      if (s < 60) {
        label = s + "s";
      } else {
        label = Math.floor(s / 60) + "m " + (s % 60) + "s";
      }
      setStatus("running " + label);
    }, 1000);
  }

  function stopTicker() {
    if (tickerId) {
      clearInterval(tickerId);
      tickerId = null;
    }
  }

  // SSE attachment — replays buffered output for refresh-survival.
  if (STREAM_URL) {
    var es = new EventSource(STREAM_URL);

    if (INITIAL_STATUS === "running" || INITIAL_STATUS === "pending") {
      startTicker();
    } else {
      setStatusClass(
        INITIAL_STATUS === "completed" ? "chip-ok" :
        INITIAL_STATUS === "failed" ? "chip-danger" :
        "chip-muted"
      );
    }

    es.addEventListener("line", function (ev) {
      // The raw line is broadcast verbatim; wrap in JSON.parse to
      // unwrap the JSON-string the server emits.
      appendLine(JSON.parse(ev.data));
    });

    es.addEventListener("done", function (ev) {
      var info = JSON.parse(ev.data);
      stopTicker();
      setStatus(info.status + " (exit " + info.exit_code + ")");
      setStatusClass(
        info.status === "completed" ? "chip-ok" :
        info.status === "failed" ? "chip-danger" :
        "chip-muted"
      );
      es.close();
    });

    es.addEventListener("error", function () {
      stopTicker();
      setStatus("stream error");
      setStatusClass("chip-danger");
      es.close();
    });
  }

  // ----------------------------------------------------------------
  // Phase 4 — clickable workflow-name pills inside the log
  // ----------------------------------------------------------------

  function showInlineError(message) {
    var section = document.querySelector(".run-view-head") || document.body;
    var existing = section.querySelector(".run-view-error");
    if (existing) existing.remove();
    var box = document.createElement("div");
    box.className = "run-view-error";
    box.textContent = message;
    section.appendChild(box);
  }

  function pillTargetFromEvent(ev) {
    // Walk up to the nearest .log-workflow chip; bail if the click was
    // somewhere else.
    var el = ev.target;
    while (el && el !== document) {
      if (el.classList && el.classList.contains("log-workflow")) return el;
      el = el.parentNode;
    }
    return null;
  }

  function handlePillClick(ev) {
    var pill = pillTargetFromEvent(ev);
    if (!pill) return;
    ev.preventDefault();
    var target = (pill.textContent || "").trim();
    if (!target) return;
    if (!ALLOW_RUN) {
      showInlineError(
        "Read-only mode — restart attune ops without --read-only to chain runs."
      );
      return;
    }
    var body = {};
    if (SOURCE_PATH) body.path = SOURCE_PATH;
    // Disable the pill to deduplicate double-clicks while the POST is
    // in flight.
    pill.classList.add("pill-disabled");
    fetch("/workflows/" + encodeURIComponent(target) + "/run", {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "application/json" },
      body: JSON.stringify(body)
    })
      .then(function (resp) {
        return resp.text().then(function (text) {
          return { status: resp.status, text: text };
        });
      })
      .then(function (result) {
        pill.classList.remove("pill-disabled");
        if (result.status === 201) {
          var parsed;
          try { parsed = JSON.parse(result.text); } catch (e) { parsed = null; }
          if (parsed && parsed.run_id) {
            window.location.assign(
              "/runs/" + encodeURIComponent(parsed.run_id) +
              "/view?from=" + encodeURIComponent(SOURCE_WORKFLOW)
            );
            return;
          }
        }
        if (result.status === 409) {
          // Busy — surface inline; don't navigate away from this run.
          var msg = "Another workflow is running. Wait for it to finish, then click again.";
          try {
            var parsed409 = JSON.parse(result.text);
            if (parsed409 && parsed409.detail && parsed409.detail.message) {
              msg = parsed409.detail.message;
              if (parsed409.detail.current_run_id) {
                msg += " (run " + parsed409.detail.current_run_id + ")";
              }
            }
          } catch (e) { /* keep default msg */ }
          showInlineError(msg);
          return;
        }
        if (result.status === 403) {
          showInlineError(
            "Runs are disabled — restart attune ops without --read-only to chain runs."
          );
          return;
        }
        showInlineError("Could not start " + target + " (HTTP " + result.status + ")");
      })
      .catch(function (err) {
        pill.classList.remove("pill-disabled");
        showInlineError("Could not start " + target + ": " + err);
      });
  }

  // Delegated listener — pills are inside the streaming log, so new
  // ones appear over the lifetime of the page. One listener at the
  // log container avoids per-pill wiring.
  if (pre) {
    pre.addEventListener("click", handlePillClick);
  }

  // ----------------------------------------------------------------
  // Phase 4 — "↩ from <workflow>" badge driven by ?from= URL param
  // ----------------------------------------------------------------

  function renderChainedFromBadge() {
    if (!chainedFromEl) return;
    var params = new URLSearchParams(window.location.search);
    var fromName = params.get("from");
    if (!fromName) return;
    // Strip any unexpected characters; we only want a workflow name.
    if (!/^[a-z][a-z0-9-]+$/.test(fromName)) return;
    while (chainedFromEl.firstChild) chainedFromEl.removeChild(chainedFromEl.firstChild);
    chainedFromEl.appendChild(document.createTextNode("↩ from "));
    var code = document.createElement("code");
    code.textContent = fromName;
    chainedFromEl.appendChild(code);
    chainedFromEl.hidden = false;
  }

  renderChainedFromBadge();

  // ----------------------------------------------------------------
  // Phase 3 — recent-runs strip at the top of the run-view page
  // ----------------------------------------------------------------
  //
  // Uses the shared helper exposed by runner.js's window.__attuneRunner.
  // run_view.html loads runner.js before this script so the helper is
  // available; if it's missing we no-op (history is best-effort).
  var runner = (typeof window !== "undefined") ? window.__attuneRunner : null;
  if (runner && typeof runner.setupRecentRuns === "function") {
    document
      .querySelectorAll("[data-recent-runs]")
      .forEach(runner.setupRecentRuns);
  }

  // Expose internals for tests.
  if (typeof window !== "undefined") {
    window.__attuneRunView = {
      handlePillClick: handlePillClick,
      renderChainedFromBadge: renderChainedFromBadge,
      pillTargetFromEvent: pillTargetFromEvent,
      DATA: DATA
    };
  }
})();
