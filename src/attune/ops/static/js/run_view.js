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
  var RUN_ID = DATA.run_id || "";
  var SOURCE_WORKFLOW = DATA.workflow || "";
  var SOURCE_PATH = DATA.path == null ? null : DATA.path;
  var ALLOW_RUN = DATA.allow_run === true;

  // Suggestion-chip parsing patterns. Declared up top (not in the
  // suggestion-chips section below) because the disk-loaded branch
  // calls renderSuggestionChipsFromLog SYNCHRONOUSLY during IIFE
  // evaluation — with the assignments further down, the hoisted vars
  // would still be undefined at that call and the page init would
  // die on _NEXT_STEP_RE.exec. Lines look like:
  //   I'd run `attune workflow run security-audit` next — Your spec ...
  // The backtick-wrapped workflow name is the parsable signal.
  var _NEXT_STEP_RE = /attune workflow run\s+([a-z][a-z0-9-]+)/i;
  var _VALID_WORKFLOW_NAME_RE = /^[a-z][a-z0-9-]+$/;

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

  // Accumulates raw log content for the post-run error-token scan.
  // We append to the DOM (textNode) for display AND to a plain string
  // so the "done" handler can heuristically detect uncaught exceptions
  // hidden inside an exit-0 run (P0-2 of the 2026-05-14 punch list).
  var logBuffer = "";
  var LOG_BUFFER_MAX = 256 * 1024; // 256 KB cap — enough for typical runs

  function appendLine(line) {
    if (!pre) return;
    pre.appendChild(document.createTextNode(line + "\n"));
    pre.scrollTop = pre.scrollHeight;
    // Keep the buffer bounded — for very long-running workflows we
    // only need recent content to detect failure-leak patterns. The
    // common patterns (Traceback, NameError, etc.) appear near the
    // point of failure, which is usually near the end of the log.
    if (logBuffer.length < LOG_BUFFER_MAX) {
      logBuffer += line + "\n";
    }
  }

  // Returns the first matching error-leak token found in ``content``,
  // or null if none. Used to detect runs that exited 0 (so the CLI
  // didn't propagate the failure) but emitted an uncaught exception
  // or workflow-acknowledged error. Patterns are intentionally
  // conservative — they only match strong, unambiguous signals so
  // we don't false-positive on docstrings or success-state output
  // that happens to discuss errors.
  function detectLogErrorLeak(content) {
    if (!content) return null;
    // 1. Python traceback header — a definitive uncaught-exception
    //    marker. Never appears in well-behaved workflow output.
    if (content.indexOf("Traceback (most recent call last):") !== -1) {
      return "Python traceback";
    }
    // 2. Workflow-emitted "What Went Wrong" section header.
    //    The voice-layer formatter emits this when WorkflowResult
    //    .success is False — but the SDK swallows the upstream
    //    Exception and the run still exits 0 (P0-2 root cause).
    if (
      content.indexOf("What Went Wrong") !== -1 ||
      content.indexOf("This one didn't go as planned") !== -1
    ) {
      return "workflow reported failure";
    }
    // 3. Line-anchored Python exception class. Match against lines
    //    starting with PascalCase + ``Error:`` or ``Exception:`` —
    //    catches ``ValueError: foo``, ``RuntimeError: bar``, etc.
    //    A plain regex over the buffer (no /m flag) anchors with
    //    explicit "\n".
    if (/(?:^|\n)[A-Z][A-Za-z0-9_]*(?:Error|Exception): /.test(content)) {
      return "uncaught exception";
    }
    return null;
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
      var line = JSON.parse(ev.data);
      appendLine(line);
      // Phase 3.3 — extract sweep source progress events from
      // ATTUNE_DS lines. parseSweepEventLine returns null for
      // non-matching lines, so we pay only a cheap startsWith check
      // on the hot path.
      if (typeof line === "string" && line.indexOf("ATTUNE_DS ") === 0) {
        var event = parseSweepEventLine(line);
        if (event) updateSweepProgress(event);
      }
    });

    es.addEventListener("done", function (ev) {
      var info = JSON.parse(ev.data);
      stopTicker();

      // Defense in depth for P0-2: a run that exits 0 but emitted an
      // uncaught Python exception, a workflow-reported failure block,
      // or a similar error-leak signal should not render with a green
      // "completed" chip. Two layers, in order:
      //
      //   1. Phase 4.3 typed-kind path — when the workflow has been
      //      migrated to the sdk-error-message-fidelity flow and the
      //      SDK actually failed, the side-channel writes
      //      ``sdk_error_kind`` onto the run record. Use that directly
      //      instead of regex-scanning the log buffer. Typed, fast,
      //      and survives log-output formatting changes.
      //
      //   2. Log-scan fallback — for unmigrated workflows (Phase 5
      //      hasn't reached them yet) or runs whose CLI exited 0
      //      after a workflow-reported failure, the regex heuristic
      //      still catches Python tracebacks / voice-layer "What Went
      //      Wrong" blocks. Removed once all workflows are migrated.
      var typedKind = info.status === "completed" && info.exit_code === 0
        ? info.sdk_error_kind || null
        : null;
      var leak = !typedKind && info.status === "completed" && info.exit_code === 0
        ? detectLogErrorLeak(logBuffer)
        : null;

      if (typedKind) {
        setStatus("completed with errors (" + typedKind + ")");
        setStatusClass("chip-warn");
        if (statusEl) {
          statusEl.setAttribute(
            "data-tooltip",
            "The run exited 0 but the SDK subprocess reported a " +
            typedKind + " failure. See the 'Raw stderr from claude CLI' " +
            "section below for the underlying message."
          );
        }
      } else if (leak) {
        setStatus("completed with errors (" + leak + ")");
        setStatusClass("chip-warn");
        if (statusEl) {
          statusEl.setAttribute(
            "data-tooltip",
            "The run exited 0 but the log contains a " + leak + ". " +
            "The underlying CLI may have swallowed an exception. " +
            "See P0-2 in docs/specs/ops-dashboard-qa-2026-05-14/punch-list.md."
          );
        }
      } else {
        setStatus(info.status + " (exit " + info.exit_code + ")");
        setStatusClass(
          info.status === "completed" ? "chip-ok" :
          info.status === "failed" ? "chip-danger" :
          "chip-muted"
        );
      }
      // Scan the captured log for "What I'd Do Next" suggestions and
      // render each as a clickable chip alongside any ATTUNE_REC cards.
      // The marker pattern is stable across all SDK-native workflows
      // (defined in attune.voice.personality.HEADER_NEXT_STEPS).
      renderSuggestionChipsFromLog(logBuffer);
      // T6 — when the run carried a structured WorkflowReport, fetch
      // it and render the report panel above the (now collapsing) log.
      if (info.has_report) fetchAndRenderReport();
      es.close();
    });

    es.addEventListener("recommendation", function (ev) {
      // Phase 5 — structured action cards. The server validated the
      // payload before broadcasting; we trust it here but still apply
      // a final client-side url-scheme check before window.open to
      // defend against any future server bypass.
      try {
        var payload = JSON.parse(ev.data);
        renderRecommendationCard(payload);
      } catch (e) {
        // INTENTIONAL: a malformed payload in the stream should not
        // kill the page. Log and move on.
        console.warn("attune-ops: recommendation parse failed", e);
      }
    });

    es.addEventListener("error", function () {
      stopTicker();
      setStatus("stream error");
      setStatusClass("chip-danger");
      es.close();
    });
  } else {
    // Disk-loaded terminal run — no SSE. The log is already rendered
    // server-side in the <pre data-log>; we just style the status chip
    // (the SSE-attached branch sets the chip class on terminal events).
    setStatusClass(
      INITIAL_STATUS === "completed" ? "chip-ok" :
      INITIAL_STATUS === "failed" ? "chip-danger" :
      "chip-muted"
    );
    // Same suggestion-chip pass as the SSE "done" handler — disk-loaded
    // runs should still surface "What I'd Do Next" suggestions from
    // their pre-rendered <pre data-log> content.
    var preEl = document.querySelector("[data-log]");
    if (preEl) {
      renderSuggestionChipsFromLog(preEl.textContent || "");
    }
    // T6 — disk-loaded runs may carry a persisted structured report;
    // a 404 from the report route just means "no panel".
    fetchAndRenderReport();
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

  // Phase 6.1 — fire-and-forget UI counter helper. Delegates to
  // runner.js's recordInteraction if available; no-op otherwise so
  // counter wiring never blocks the pill/rec-card user flow.
  function recordInteraction(event, target) {
    var runner = (typeof window !== "undefined") ? window.__attuneRunner : null;
    if (runner && typeof runner.recordInteraction === "function") {
      runner.recordInteraction(event, target);
    }
  }

  function handlePillClick(ev) {
    var pill = pillTargetFromEvent(ev);
    if (!pill) return;
    ev.preventDefault();
    var target = (pill.textContent || "").trim();
    if (!target) return;
    recordInteraction("pill_click", target);
    if (!ALLOW_RUN) {
      showInlineError(
        "Read-only mode — restart attune ops without --read-only to chain runs."
      );
      return;
    }
    // Chain pills are next-workflow recommendations — stamp the run's
    // provenance so its record carries trigger=attune-rec (RC-3).
    var body = { trigger: "attune-rec" };
    if (SOURCE_PATH) body.path = SOURCE_PATH;
    // Disable the pill to deduplicate double-clicks while the POST is
    // in flight.
    pill.classList.add("pill-disabled");
    fetch("/workflows/" + encodeURIComponent(target) + "/run", {
      method: "POST",
      headers: attuneClientHeaders({ "Content-Type": "application/json", Accept: "application/json" }),
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

  // ----------------------------------------------------------------
  // Phase 3.3 — live sweep progress (ATTUNE_DS line parser)
  // ----------------------------------------------------------------

  // Parse a single ATTUNE_DS event line into a normalized object, or
  // null if the line isn't a per-source event (e.g. version line,
  // final JSON line, malformed). The wire format is space-separated
  // ``ATTUNE_DS <event> <source> ts=<iso> [key=value ...]`` per
  // ds_stdout.py. We accept anything reasonable rather than hard-fail
  // — the engine's emitter is the source of truth, but a forward-
  // compat parser is cheap insurance.
  function parseSweepEventLine(line) {
    if (typeof line !== "string") return null;
    var parts = line.trim().split(/\s+/);
    if (parts.length < 3) return null;
    if (parts[0] !== "ATTUNE_DS") return null;
    var event = parts[1];
    if (event !== "source_started" && event !== "source_finished" && event !== "source_failed") {
      return null;
    }
    var source = parts[2];
    var meta = {};
    for (var i = 3; i < parts.length; i++) {
      var pair = parts[i];
      var eq = pair.indexOf("=");
      if (eq <= 0) continue;
      meta[pair.slice(0, eq)] = pair.slice(eq + 1);
    }
    return { event: event, source: source, meta: meta };
  }

  // Reveal the progress panel on first event and flip the matching
  // <li>'s state. The DOM order is fixed at server-render time so we
  // never reflow the list; we only change ``data-state`` (CSS owns
  // the glyph/color) and update the detail text.
  function updateSweepProgress(event) {
    var panel = document.querySelector("[data-sweep-progress]");
    if (!panel) return;
    panel.hidden = false;
    var item = panel.querySelector('[data-source="' + cssEscape(event.source) + '"]');
    if (!item) return;
    var glyph = item.querySelector(".sweep-progress-glyph");
    var detail = item.querySelector("[data-source-detail]");
    var state = "pending";
    var glyphChar = "⌛";
    var detailText = "";
    if (event.event === "source_started") {
      state = "running";
      glyphChar = "⏳";
      detailText = "running…";
    } else if (event.event === "source_finished") {
      state = "finished";
      glyphChar = "✓";
      var count = event.meta && event.meta.findings;
      detailText = count != null ? count + " finding(s)" : "done";
    } else if (event.event === "source_failed") {
      state = "failed";
      glyphChar = "✗";
      detailText = (event.meta && event.meta.error) || "failed";
    }
    item.setAttribute("data-state", state);
    if (glyph) glyph.textContent = glyphChar;
    if (detail) detail.textContent = detailText;
  }

  // CSS.escape() is widely supported but not universal; fall back to
  // a minimal escape that handles the source names the engine emits
  // (lowercase letters and hyphens only) so this works in older
  // browser environments and headless test harnesses.
  function cssEscape(value) {
    if (typeof CSS !== "undefined" && typeof CSS.escape === "function") {
      return CSS.escape(value);
    }
    return String(value).replace(/[^a-zA-Z0-9_-]/g, "\\$&");
  }

  // ------------------------------------------------------------------
  // Phase 5 — recommendation cards
  // ------------------------------------------------------------------

  // Client-side defense in depth: even though the server validates the
  // url scheme, re-check before window.open in case a future server
  // bypass slips through.
  function isSafeUrl(url) {
    return typeof url === "string" &&
      (url.indexOf("http://") === 0 || url.indexOf("https://") === 0);
  }

  function renderRecommendationCard(payload) {
    if (!payload || typeof payload !== "object") return;
    var slot = document.querySelector("[data-recommendations]");
    if (!slot) return;
    var kind = payload.kind;
    if (kind !== "next-workflow" && kind !== "open-url") return;

    var card = document.createElement("div");
    card.className = "recommendation-card";
    if (payload.severity) {
      card.setAttribute("data-severity", String(payload.severity));
    }

    // Body text: prefer the explicit label; fall back to a sensible
    // default that names the action.
    var labelText = payload.label;
    if (!labelText) {
      labelText = kind === "next-workflow"
        ? "Run " + (payload.name || "")
        : "Open link";
    }
    var body = document.createElement("span");
    body.className = "recommendation-card-body";
    body.textContent = labelText;
    card.appendChild(body);

    var action = document.createElement("button");
    action.className = "btn btn-rec";
    action.type = "button";
    action.textContent = kind === "next-workflow" ? "Run" : "Open";
    action.addEventListener("click", function () {
      recordInteraction("rec_card_click", kind);
      action.disabled = true;
      if (kind === "next-workflow") {
        var name = payload.name;
        if (!name) { action.disabled = false; return; }
        // Rec-card runs are recommendation-launched (RC-3 provenance).
        var body_json = { trigger: "attune-rec" };
        if (payload.args && typeof payload.args.path === "string") {
          body_json.path = payload.args.path;
        }
        fetch("/workflows/" + encodeURIComponent(name) + "/run", {
          method: "POST",
          headers: attuneClientHeaders({"Content-Type": "application/json"}),
          body: JSON.stringify(body_json)
        }).then(function (resp) {
          if (resp.status === 201) {
            return resp.json().then(function (data) {
              window.location.href = "/runs/" + data.run_id +
                "/view?from=" + encodeURIComponent(DATA.workflow || "");
            });
          }
          if (resp.status === 409) {
            return resp.json().then(function (data) {
              showInlineError(
                "Cannot start " + name + " — run " + data.detail.current_run_id +
                " is still active."
              );
              action.disabled = false;
            });
          }
          showInlineError("Could not start " + name + " (HTTP " + resp.status + ")");
          action.disabled = false;
        }).catch(function (err) {
          showInlineError("Could not start " + name + ": " + err);
          action.disabled = false;
        });
      } else {
        // open-url
        if (isSafeUrl(payload.url)) {
          window.open(payload.url, "_blank", "noopener,noreferrer");
        }
        action.disabled = false;
      }
    });
    card.appendChild(action);

    slot.appendChild(card);
    slot.hidden = false;
  }

  // ------------------------------------------------------------------
  // Suggestion chips parsed from "What I'd Do Next" log lines
  // ------------------------------------------------------------------

  // Pattern vars (_NEXT_STEP_RE / _VALID_WORKFLOW_NAME_RE) are declared
  // at the top of the IIFE — see the comment there for why. Free-form
  // explanation after the em-dash is kept as the chip's tooltip text.

  function parseSuggestions(logText) {
    if (!logText || typeof logText !== "string") return [];
    var lines = logText.split(/\r?\n/);
    var inNextSteps = false;
    var out = [];
    var seen = {};
    for (var i = 0; i < lines.length; i++) {
      var raw = lines[i];
      var line = raw.trim();
      if (!line) continue;
      // The voice layer emits the header literally as "What I'd Do Next".
      if (line === "What I'd Do Next") {
        inNextSteps = true;
        continue;
      }
      if (!inNextSteps) continue;
      // Other section headers end the block (e.g. "Cost & Time" appears
      // BEFORE NextSteps, but a future workflow might emit another
      // markdown heading after — guard defensively).
      if (line.charAt(0) === "#") break;
      var m = _NEXT_STEP_RE.exec(line);
      if (!m) continue;
      var name = m[1];
      if (!_VALID_WORKFLOW_NAME_RE.test(name)) continue;
      if (seen[name]) continue;
      seen[name] = true;
      // Tooltip: everything after the em-dash if present, else the
      // whole line trimmed of the "I'd run … next —" preamble.
      var emIdx = line.indexOf("—");
      var tooltip = emIdx >= 0
        ? line.substring(emIdx + 1).trim()
        : line.replace(/^I'd run\s+`[^`]+`\s+next\s*—?\s*/i, "");
      out.push({ name: name, tooltip: tooltip });
    }
    return out;
  }

  function renderSuggestionChipsFromLog(logText) {
    var suggestions = parseSuggestions(logText);
    if (!suggestions.length) return;
    var slot = document.querySelector("[data-recommendations]");
    if (!slot) return;
    // Render under a single header so multi-suggestion runs feel like
    // one group rather than N standalone cards.
    var existing = slot.querySelector("[data-suggestion-row]");
    if (existing) existing.remove();
    var row = document.createElement("div");
    row.className = "suggestion-row";
    row.setAttribute("data-suggestion-row", "");
    var label = document.createElement("span");
    label.className = "suggestion-row-label";
    label.textContent = "What I'd do next:";
    row.appendChild(label);
    for (var i = 0; i < suggestions.length; i++) {
      row.appendChild(buildSuggestionChip(suggestions[i]));
    }
    slot.appendChild(row);
    slot.hidden = false;
  }

  // ``learn-<workflow>`` is emitted by attune.workflows.suggestions
  // ._help_template_suggestions as an *informational* pointer at the
  // matching help-template, not a runnable workflow — there is no
  // workflow registered under that slug. Detect the prefix so we
  // render a non-clickable info chip instead of a Run button that
  // would 404. Matches the f"learn-{workflow_name}" emission site.
  var _INFO_PREFIX_RE = /^learn-/;

  function buildSuggestionChip(suggestion) {
    if (_INFO_PREFIX_RE.test(suggestion.name)) {
      return buildInfoChip(suggestion);
    }
    var chip = document.createElement("button");
    chip.className = "suggestion-chip";
    chip.type = "button";
    chip.setAttribute("data-suggestion-chip", suggestion.name);
    chip.textContent = suggestion.name;
    if (suggestion.tooltip) {
      chip.setAttribute("data-tooltip", suggestion.tooltip);
      chip.setAttribute("aria-label", "Run " + suggestion.name + " — " + suggestion.tooltip);
    } else {
      chip.setAttribute("aria-label", "Run " + suggestion.name);
    }
    chip.addEventListener("click", function () {
      chip.disabled = true;
      // Suggestion chips are next-workflow recommendations (RC-3).
      var body = { trigger: "attune-rec" };
      if (DATA && typeof DATA.path === "string" && DATA.path) {
        body.path = DATA.path;
      }
      fetch("/workflows/" + encodeURIComponent(suggestion.name) + "/run", {
        method: "POST",
        headers: attuneClientHeaders({"Content-Type": "application/json"}),
        body: JSON.stringify(body)
      }).then(function (resp) {
        if (resp.status === 201) {
          return resp.json().then(function (data) {
            window.location.href = "/runs/" + data.run_id +
              "/view?from=" + encodeURIComponent(DATA.workflow || "");
          });
        }
        if (resp.status === 409) {
          return resp.json().then(function (data) {
            showInlineError(
              "Cannot start " + suggestion.name + " — run " +
              data.detail.current_run_id + " is still active."
            );
            chip.disabled = false;
          });
        }
        showInlineError("Could not start " + suggestion.name +
          " (HTTP " + resp.status + ")");
        chip.disabled = false;
      }).catch(function (err) {
        showInlineError("Could not start " + suggestion.name + ": " + err);
        chip.disabled = false;
      });
    });
    return chip;
  }

  function buildInfoChip(suggestion) {
    // Informational sibling of buildSuggestionChip — same DOM hook for
    // tests (data-suggestion-chip) so the renderer drift-guard still
    // catches the chip, but rendered as a <span> with no Run button.
    // CSS variant ``.suggestion-chip-info`` removes the dotted border /
    // pointer cursor so users don't expect clickability.
    var chip = document.createElement("span");
    chip.className = "suggestion-chip suggestion-chip-info";
    chip.setAttribute("data-suggestion-chip", suggestion.name);
    chip.setAttribute("data-suggestion-kind", "info");
    chip.textContent = suggestion.name;
    if (suggestion.tooltip) {
      chip.setAttribute("data-tooltip", suggestion.tooltip);
      chip.setAttribute("aria-label", suggestion.name + " — " + suggestion.tooltip);
    } else {
      chip.setAttribute("aria-label", suggestion.name);
    }
    return chip;
  }

  // ------------------------------------------------------------------
  // T6 (workflow-result-formatting) — structured report panel
  // ------------------------------------------------------------------
  //
  // The runner stashes the workflow's serialized WorkflowReport (sent
  // over the ATTUNE_RUN_META report_b64 side-channel) and the server
  // renders its summary markdown via the canonical Python renderer.
  // This module fetches /runs/<id>/report once the run is terminal,
  // converts that CONSTRAINED markdown subset to HTML (headings,
  // tables, lists, blockquote callouts, fenced code, inline bold/code,
  // and the renderer's literal <details> wrappers), and renders Run
  // chips for next-step actions whose command is a runnable
  // `attune workflow run <name>`. The terminal log collapses into a
  // "Process log" <details> so the report is the primary content.

  function escapeHtml(text) {
    return String(text)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  // Inline transforms applied AFTER escaping: **bold**, `code`,
  // *emphasis*. Escaping first means the regexes only ever see
  // entity-encoded text, so no raw HTML can sneak through.
  function mdInline(text) {
    var s = escapeHtml(text);
    s = s.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
    s = s.replace(/`([^`]+)`/g, "<code>$1</code>");
    s = s.replace(/(^|[\s(])\*([^*\s][^*]*)\*/g, "$1<em>$2</em>");
    return s;
  }

  // Convert the report renderer's markdown subset to HTML. This is NOT
  // a general markdown parser — it handles exactly what
  // attune.voice.report_renderer emits (see that module's docstring).
  // Anything unrecognized renders as an escaped paragraph, so renderer
  // drift degrades to ugly-but-safe text rather than broken markup.
  function mdToHtml(md) {
    var lines = String(md).split(/\r?\n/);
    var out = [];
    var para = [];
    var i, line;

    function flushPara() {
      if (!para.length) return;
      out.push("<p>" + mdInline(para.join(" ")) + "</p>");
      para = [];
    }

    for (i = 0; i < lines.length; i++) {
      line = lines[i];
      var trimmed = line.trim();

      if (!trimmed) { flushPara(); continue; }

      // Renderer-emitted <details> wrappers pass through as real tags
      // (title re-escaped). Everything else angle-bracketed is escaped.
      var dm = /^<details><summary>(.*)<\/summary>$/.exec(trimmed);
      if (dm) {
        flushPara();
        out.push("<details><summary>" + mdInline(dm[1]) + "</summary>");
        continue;
      }
      if (trimmed === "</details>") {
        flushPara();
        out.push("</details>");
        continue;
      }

      // Fenced code block — consume until the closing fence. The
      // renderer indents command fences under their bullet; strip that
      // shared indent so the <pre> doesn't render leading whitespace.
      if (/^```/.test(trimmed)) {
        flushPara();
        var fenceIndent = line.length - line.replace(/^\s+/, "").length;
        var code = [];
        i++;
        while (i < lines.length && !/^\s*```/.test(lines[i])) {
          code.push(lines[i].slice(fenceIndent));
          i++;
        }
        out.push("<pre><code>" + escapeHtml(code.join("\n")) + "</code></pre>");
        continue;
      }

      // Headings — demoted one level (the page owns <h1>).
      var hm = /^(#{1,3})\s+(.*)$/.exec(trimmed);
      if (hm) {
        flushPara();
        var level = hm[1].length + 1;
        out.push("<h" + level + ">" + mdInline(hm[2]) + "</h" + level + ">");
        continue;
      }

      // Pipe table — consume contiguous | lines; row 2 is the ---
      // separator the renderer always emits.
      if (trimmed.charAt(0) === "|") {
        flushPara();
        var rows = [];
        while (i < lines.length && lines[i].trim().charAt(0) === "|") {
          rows.push(lines[i].trim());
          i++;
        }
        i--;
        out.push(mdTable(rows));
        continue;
      }

      // Unordered list — consume contiguous "- " lines. Commands under
      // a bullet arrive as indented fenced blocks and are handled by
      // the fence branch above because the renderer separates them
      // with blank lines.
      if (/^- /.test(trimmed)) {
        flushPara();
        var items = [];
        while (i < lines.length && /^- /.test(lines[i].trim())) {
          items.push("<li>" + mdInline(lines[i].trim().slice(2)) + "</li>");
          i++;
        }
        i--;
        out.push("<ul>" + items.join("") + "</ul>");
        continue;
      }

      // Blockquote callout — consume contiguous "> " lines.
      if (trimmed.charAt(0) === ">") {
        flushPara();
        var quoted = [];
        while (i < lines.length && lines[i].trim().charAt(0) === ">") {
          quoted.push(lines[i].trim().replace(/^>\s?/, ""));
          i++;
        }
        i--;
        out.push(
          "<blockquote>" +
          quoted.filter(function (q) { return q !== ""; })
            .map(function (q) { return "<p>" + mdInline(q) + "</p>"; })
            .join("") +
          "</blockquote>"
        );
        continue;
      }

      para.push(trimmed);
    }
    flushPara();
    return out.join("\n");
  }

  function mdTable(rows) {
    function cells(row) {
      // "| a | b |" → ["a", "b"]. Manual scan (no regex lookbehind —
      // it's a parse error on older Safari) honoring the renderer's
      // escaped \| cells.
      var inner = row.replace(/^\|/, "").replace(/\|$/, "");
      var parts = [];
      var cur = "";
      for (var k = 0; k < inner.length; k++) {
        var ch = inner.charAt(k);
        if (ch === "\\" && inner.charAt(k + 1) === "|") { cur += "|"; k++; continue; }
        if (ch === "|") { parts.push(cur.trim()); cur = ""; continue; }
        cur += ch;
      }
      parts.push(cur.trim());
      return parts;
    }
    var head = cells(rows[0]);
    var html = ["<table><thead><tr>"];
    head.forEach(function (c) { html.push("<th>" + mdInline(c) + "</th>"); });
    html.push("</tr></thead><tbody>");
    // rows[1] is the --- separator; body starts at 2.
    for (var r = 2; r < rows.length; r++) {
      html.push("<tr>");
      cells(rows[r]).forEach(function (c) { html.push("<td>" + mdInline(c) + "</td>"); });
      html.push("</tr>");
    }
    html.push("</tbody></table>");
    return html.join("");
  }

  // Extract runnable next-step actions from the report dict: items in
  // any kind === "next-steps" section whose command parses as
  // `attune workflow run <name>` (same grammar the log-scrape chips
  // use). Other commands stay as fenced code in the markdown.
  function runnableNextActions(report) {
    var out = [];
    var sections = (report && report.sections) || [];
    for (var i = 0; i < sections.length; i++) {
      var s = sections[i];
      if (!s || s.kind !== "next-steps" || !s.items) continue;
      for (var j = 0; j < s.items.length; j++) {
        var item = s.items[j];
        if (!item || typeof item.command !== "string") continue;
        var m = _NEXT_STEP_RE.exec(item.command);
        if (!m || !_VALID_WORKFLOW_NAME_RE.test(m[1])) continue;
        out.push({ name: m[1], tooltip: item.text || "" });
      }
    }
    return out;
  }

  function renderReportPanel(data) {
    var panel = document.querySelector("[data-report-panel]");
    if (!panel || !data || typeof data.markdown !== "string") return;
    while (panel.firstChild) panel.removeChild(panel.firstChild);

    var body = document.createElement("div");
    body.className = "run-report-body";
    body.innerHTML = mdToHtml(data.markdown);
    panel.appendChild(body);

    // One-click Run chips for runnable next-step commands — reuses the
    // suggestion-chip POST flow (and its busy/read-only handling).
    var actions = runnableNextActions(data.report);
    if (actions.length) {
      var row = document.createElement("div");
      row.className = "suggestion-row run-report-actions";
      var label = document.createElement("span");
      label.className = "suggestion-row-label";
      label.textContent = "Run next:";
      row.appendChild(label);
      for (var i = 0; i < actions.length; i++) {
        row.appendChild(buildSuggestionChip(actions[i]));
      }
      panel.appendChild(row);
    }

    panel.hidden = false;
    // The report is now the page's primary content; tuck the raw
    // terminal output away as a collapsed process log.
    var logDetails = document.querySelector("[data-log-details]");
    if (logDetails) logDetails.open = false;
  }

  function fetchAndRenderReport() {
    if (!RUN_ID) return;
    fetch("/runs/" + encodeURIComponent(RUN_ID) + "/report", {
      headers: { Accept: "application/json" }
    })
      .then(function (resp) {
        if (!resp.ok) return null; // 404 = no structured report; fine.
        return resp.json();
      })
      .then(function (data) {
        if (data) renderReportPanel(data);
      })
      .catch(function (err) {
        // INTENTIONAL: the panel is progressive enhancement — a fetch
        // failure leaves the classic log view fully usable.
        console.warn("attune-ops: report fetch failed", err);
      });
  }

  // ------------------------------------------------------------------
  // Copy report — clipboard handler for the [data-copy-report] button
  // ------------------------------------------------------------------

  function readReportText() {
    var preEl = document.querySelector("[data-log]");
    return preEl ? (preEl.textContent || "") : "";
  }

  function flashCopyState(btn, message, ok) {
    var label = btn.querySelector(".btn-copy-report-label");
    if (!label) return;
    var prev = label.textContent;
    label.textContent = message;
    btn.classList.toggle("is-copied", !!ok);
    btn.classList.toggle("is-failed", !ok);
    setTimeout(function () {
      label.textContent = prev;
      btn.classList.remove("is-copied");
      btn.classList.remove("is-failed");
    }, 1500);
  }

  function copyReportToClipboard(btn) {
    var text = readReportText();
    if (!text) {
      flashCopyState(btn, "Nothing to copy", false);
      return Promise.resolve(false);
    }
    if (!navigator.clipboard || !navigator.clipboard.writeText) {
      // Graceful fallback for old browsers / insecure contexts:
      // surface the error so the user knows to retry over HTTPS or
      // in a modern browser. We don't attempt the legacy
      // execCommand("copy") path because it requires document.execCommand
      // which is itself deprecated and security-conscious users have
      // disabled clipboard JS API for a reason.
      flashCopyState(btn, "Clipboard unavailable", false);
      return Promise.resolve(false);
    }
    return navigator.clipboard.writeText(text).then(
      function () {
        flashCopyState(btn, "Copied ✓", true);
        return true;
      },
      function () {
        flashCopyState(btn, "Copy failed", false);
        return false;
      }
    );
  }

  function wireCopyReportButton() {
    var btn = document.querySelector("[data-copy-report]");
    if (!btn) return;
    btn.addEventListener("click", function () {
      copyReportToClipboard(btn);
    });
  }

  if (typeof document !== "undefined") {
    if (document.readyState === "loading") {
      document.addEventListener("DOMContentLoaded", wireCopyReportButton);
    } else {
      wireCopyReportButton();
    }
  }

  // --- "Why did this fail?" — on-demand diagnosis (adv-debugging T5).
  // Renders ONLY for terminal FAILED runs on an explicit user click;
  // nothing here auto-starts a diagnosis on page load or run ingestion.
  function renderDiagnosedChip(diagnosisId) {
    if (!statusEl || !statusEl.parentNode) return;
    if (document.querySelector("[data-diagnosed-chip]")) return;
    var chip = document.createElement("span");
    chip.className = "chip chip-muted";
    chip.setAttribute("data-diagnosed-chip", diagnosisId);
    chip.textContent = "diagnosed: " + diagnosisId;
    statusEl.parentNode.insertBefore(chip, statusEl.nextSibling);
  }

  function renderDiagnoseButton() {
    if (!statusEl || !statusEl.parentNode) return;
    if (document.querySelector("[data-diagnose-btn]")) return;
    var btn = document.createElement("button");
    btn.className = "btn btn-rec";
    btn.type = "button";
    btn.setAttribute("data-diagnose-btn", "1");
    btn.textContent = "Why did this fail?";
    btn.addEventListener("click", function () {
      btn.disabled = true;
      fetch("/runs/" + encodeURIComponent(RUN_ID) + "/diagnose", {
        method: "POST",
        headers: attuneClientHeaders({ Accept: "application/json" })
      }).then(function (resp) {
        return resp.json().then(function (data) {
          return { status: resp.status, data: data };
        });
      }).then(function (result) {
        if (result.status === 201 && result.data.run_id) {
          window.location.assign(
            "/runs/" + encodeURIComponent(result.data.run_id) +
            "/view?from=" + encodeURIComponent(SOURCE_WORKFLOW)
          );
          return;
        }
        if (result.status === 200 && result.data.existing) {
          btn.remove();
          renderDiagnosedChip(result.data.diagnosis_id);
          return;
        }
        btn.disabled = false;
        if (result.status === 409) {
          showInlineError(
            "Cannot diagnose — run " + result.data.detail.current_run_id +
            " is still active."
          );
          return;
        }
        showInlineError("Diagnosis request failed (" + result.status + ").");
      }).catch(function () {
        btn.disabled = false;
        showInlineError("Diagnosis request failed.");
      });
    });
    statusEl.parentNode.insertBefore(btn, statusEl.nextSibling);
  }

  function initDiagnose(status) {
    if (!RUN_ID || !ALLOW_RUN) return;
    if (DATA.trigger === "attune-heal") return;  // no self-diagnosis
    var existing = DATA.diagnosis_ids || [];
    if (existing.length) {
      renderDiagnosedChip(existing[existing.length - 1]);
      return;
    }
    if (status !== "failed") return;
    renderDiagnoseButton();
  }

  initDiagnose(INITIAL_STATUS);
  // A live run that fails after page load grows the button on "done".
  if (typeof es !== "undefined" && es) {
    es.addEventListener("done", function (ev) {
      try {
        initDiagnose(JSON.parse(ev.data).status);
      } catch (e) { /* malformed done payload — no button */ }
    });
  }

  // Expose internals for tests.
  if (typeof window !== "undefined") {
    window.__attuneRunView = {
      handlePillClick: handlePillClick,
      renderChainedFromBadge: renderChainedFromBadge,
      pillTargetFromEvent: pillTargetFromEvent,
      parseSweepEventLine: parseSweepEventLine,
      updateSweepProgress: updateSweepProgress,
      renderRecommendationCard: renderRecommendationCard,
      isSafeUrl: isSafeUrl,
      parseSuggestions: parseSuggestions,
      renderSuggestionChipsFromLog: renderSuggestionChipsFromLog,
      buildSuggestionChip: buildSuggestionChip,
      buildInfoChip: buildInfoChip,
      readReportText: readReportText,
      copyReportToClipboard: copyReportToClipboard,
      wireCopyReportButton: wireCopyReportButton,
      escapeHtml: escapeHtml,
      mdInline: mdInline,
      mdToHtml: mdToHtml,
      runnableNextActions: runnableNextActions,
      renderReportPanel: renderReportPanel,
      fetchAndRenderReport: fetchAndRenderReport,
      DATA: DATA
    };
  }
})();
