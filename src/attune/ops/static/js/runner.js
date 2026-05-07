// Minimal SSE-driven workflow runner UI.
// No frameworks. Wires the per-row Run button to POST /workflows/<name>/run,
// then attaches an EventSource to /runs/<id>/stream.
(function () {
  "use strict";

  function findRow(name) {
    return document.querySelector('tr[data-workflow="' + CSS.escape(name) + '"]');
  }

  function setStatus(row, status) {
    var el = row.querySelector("[data-status]");
    if (el) el.textContent = status;
  }

  function appendLine(row, line) {
    var pre = row.querySelector("[data-log]");
    if (!pre) return;
    pre.textContent += line + "\n";
    pre.scrollTop = pre.scrollHeight;
  }

  function showLogPane(row) {
    var pane = row.querySelector("[data-log-pane]");
    if (pane) pane.hidden = false;
    var pre = row.querySelector("[data-log]");
    if (pre) pre.textContent = "";
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

  function attach(button) {
    button.addEventListener("click", async function () {
      var name = button.dataset.workflow;
      var row = findRow(name);
      if (!row) return;
      button.disabled = true;
      setStatus(row, "starting…");
      showLogPane(row);
      var stopTick = null;
      try {
        var resp = await fetch("/workflows/" + encodeURIComponent(name) + "/run", {
          method: "POST",
        });
        if (!resp.ok) {
          var detail = await resp.text();
          appendLine(row, "[error] " + resp.status + " " + detail);
          setStatus(row, "error");
          button.disabled = false;
          return;
        }
        var body = await resp.json();
        stopTick = startTick(row, "running");
        var es = new EventSource(body.stream_url);
        es.addEventListener("line", function (ev) {
          appendLine(row, JSON.parse(ev.data));
        });
        es.addEventListener("done", function (ev) {
          var info = JSON.parse(ev.data);
          if (stopTick) stopTick();
          setStatus(row, info.status + " (exit " + info.exit_code + ")");
          es.close();
          button.disabled = false;
        });
        es.addEventListener("error", function () {
          if (stopTick) stopTick();
          setStatus(row, "stream error");
          es.close();
          button.disabled = false;
        });
      } catch (err) {
        if (stopTick) stopTick();
        appendLine(row, "[error] " + err);
        setStatus(row, "error");
        button.disabled = false;
      }
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    document.querySelectorAll("[data-run-button]").forEach(attach);
  });
})();
