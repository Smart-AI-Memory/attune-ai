// Per-phase status-flip handler for the Specs tab.
// Optimistic UI with rollback on server error. Mirrors runner.js's pattern.
(function () {
  "use strict";

  function chipClassForStatus(status) {
    var s = (status || "").toLowerCase();
    if (s === "approved" || s === "complete" || s === "completed" || s === "done") {
      return "chip-ok";
    }
    if (s === "in-review" || s === "review") {
      return "chip-warn";
    }
    if (s === "draft") {
      return "chip-muted";
    }
    return "chip";
  }

  function applyChipClass(select, status) {
    var classes = ["status-select", chipClassForStatus(status)];
    select.className = classes.join(" ");
  }

  function flash(select, ok) {
    select.classList.add(ok ? "flash-ok" : "flash-err");
    setTimeout(function () {
      select.classList.remove("flash-ok", "flash-err");
    }, 1200);
  }

  function attach(select) {
    select.addEventListener("change", async function () {
      var slug = select.dataset.slug;
      var phase = select.dataset.phase;
      var prev = select.dataset.original || "";
      var next = select.value;
      if (next === prev) return;
      select.disabled = true;
      applyChipClass(select, next);
      try {
        var resp = await fetch(
          "/api/specs/" + encodeURIComponent(slug) +
          "/" + encodeURIComponent(phase) + "/status",
          {
            method: "PUT",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ status: next }),
          }
        );
        if (!resp.ok) {
          var body = await resp.text();
          console.error("status flip failed:", resp.status, body);
          // Revert to original on failure.
          select.value = prev;
          applyChipClass(select, prev);
          flash(select, false);
          select.title = "Failed: " + resp.status + " " + body;
        } else {
          select.dataset.original = next;
          flash(select, true);
          select.title = "";
        }
      } catch (err) {
        console.error("status flip exception:", err);
        select.value = prev;
        applyChipClass(select, prev);
        flash(select, false);
        select.title = "Network error: " + err;
      } finally {
        select.disabled = false;
      }
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    document.querySelectorAll(".status-select").forEach(attach);
  });
})();
