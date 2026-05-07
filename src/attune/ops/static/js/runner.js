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

  function attach(button) {
    button.addEventListener("click", async function () {
      var name = button.dataset.workflow;
      var row = findRow(name);
      if (!row) return;
      button.disabled = true;
      setStatus(row, "starting…");
      showLogPane(row);
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
        setStatus(row, "running");
        var es = new EventSource(body.stream_url);
        es.addEventListener("line", function (ev) {
          appendLine(row, JSON.parse(ev.data));
        });
        es.addEventListener("done", function (ev) {
          var info = JSON.parse(ev.data);
          setStatus(row, info.status + " (exit " + info.exit_code + ")");
          es.close();
          button.disabled = false;
        });
        es.addEventListener("error", function () {
          setStatus(row, "stream error");
          es.close();
          button.disabled = false;
        });
      } catch (err) {
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
