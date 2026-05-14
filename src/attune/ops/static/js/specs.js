// Specs tab: click-to-edit status pills.
//
// Read mode: compact pill (dot + 3-letter code) with full status in
// title attribute. Click swaps in a <select> for editing; on change
// or blur, PUT to /api/specs/.../status and swap back to a pill with
// the new value. Optimistic UI with rollback on server error.
(function () {
  "use strict";

  var EDITABLE_OPTIONS = ["draft", "in-review", "approved", "complete"];

  function statusCode(status) {
    var s = (status || "").toLowerCase().trim();
    if (s === "draft") return "drf";
    if (s === "in-review" || s === "review") return "rvw";
    if (s === "approved") return "apv";
    if (s === "complete" || s === "completed" || s === "done") return "cpl";
    if (s.length > 8) return s.substring(0, 8) + "…";
    return s;
  }

  function chipClassFor(status) {
    var s = (status || "").toLowerCase().trim();
    if (
      s === "approved" ||
      s === "complete" ||
      s === "completed" ||
      s === "done"
    ) {
      return "chip-ok";
    }
    if (s === "in-review" || s === "review") return "chip-warn";
    if (s === "draft") return "chip-muted";
    return "chip-custom";
  }

  function isCustom(status) {
    var s = (status || "").toLowerCase().trim();
    if (!s) return false;
    return [
      "draft",
      "in-review",
      "review",
      "approved",
      "complete",
      "completed",
      "done",
    ].indexOf(s) === -1;
  }

  function escapeHTML(s) {
    return String(s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  function flash(el, ok) {
    el.classList.add(ok ? "flash-ok" : "flash-err");
    setTimeout(function () {
      el.classList.remove("flash-ok", "flash-err");
    }, 1200);
  }

  function applyPillState(pill, status) {
    pill.classList.remove("chip-ok", "chip-warn", "chip-muted", "chip-custom");
    pill.classList.add(chipClassFor(status));
    if (isCustom(status)) {
      pill.classList.add("status-pill-custom");
    } else {
      pill.classList.remove("status-pill-custom");
    }
    pill.dataset.original = status;
    pill.setAttribute("data-tooltip", status || "(no status)");
    pill.setAttribute(
      "aria-label",
      "Status for " +
        pill.dataset.phase +
        " of " +
        pill.dataset.slug +
        ": " +
        (status || "no status") +
        ". Click to edit."
    );
    var code = statusCode(status) || "(none)";
    pill.innerHTML =
      '<span class="status-dot" aria-hidden="true"></span>' +
      '<span class="status-code">' +
      escapeHTML(code) +
      "</span>";
  }

  async function submitChange(pill, prev, next) {
    var slug = pill.dataset.slug;
    var phase = pill.dataset.phase;
    try {
      var resp = await fetch(
        "/api/specs/" +
          encodeURIComponent(slug) +
          "/" +
          encodeURIComponent(phase) +
          "/status",
        {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ status: next }),
        }
      );
      if (!resp.ok) {
        var body = await resp.text();
        console.error("status flip failed:", resp.status, body);
        applyPillState(pill, prev);
        flash(pill, false);
        pill.setAttribute("data-tooltip", "Failed: " + resp.status + " " + body);
        return false;
      }
      applyPillState(pill, next);
      flash(pill, true);
      return true;
    } catch (err) {
      console.error("status flip exception:", err);
      applyPillState(pill, prev);
      flash(pill, false);
      pill.setAttribute("data-tooltip", "Network error: " + err);
      return false;
    }
  }

  function enterEditMode(pill) {
    if (pill.dataset.editing === "1") return;
    pill.dataset.editing = "1";

    var prev = pill.dataset.original || "";
    var pillDisplay = pill.style.display;
    pill.style.display = "none";

    var select = document.createElement("select");
    select.className = "status-edit-select";
    select.setAttribute("aria-label", pill.getAttribute("aria-label") || "");

    var seen = false;
    EDITABLE_OPTIONS.forEach(function (opt) {
      var o = document.createElement("option");
      o.value = opt;
      o.textContent = opt;
      if (prev.toLowerCase() === opt) {
        o.selected = true;
        seen = true;
      }
      select.appendChild(o);
    });
    if (!seen && prev) {
      var custom = document.createElement("option");
      custom.value = prev;
      custom.textContent = prev + " (current)";
      custom.selected = true;
      select.appendChild(custom);
    }

    pill.parentNode.insertBefore(select, pill);

    var done = false;
    async function finish(commit) {
      if (done) return;
      done = true;
      var next = select.value;
      select.remove();
      pill.style.display = pillDisplay;
      pill.dataset.editing = "";
      if (commit && next !== prev) {
        await submitChange(pill, prev, next);
      }
      pill.focus();
    }

    select.addEventListener("change", function () {
      finish(true);
    });
    select.addEventListener("blur", function () {
      finish(true);
    });
    select.addEventListener("keydown", function (e) {
      if (e.key === "Escape") {
        finish(false);
      }
    });

    select.focus();
    if (typeof select.showPicker === "function") {
      try {
        select.showPicker();
      } catch (_) {
        /* fall back to focus only */
      }
    }
  }

  function attach(pill) {
    pill.addEventListener("click", function () {
      enterEditMode(pill);
    });
    pill.addEventListener("keydown", function (e) {
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        enterEditMode(pill);
      }
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    document.querySelectorAll(".status-pill-editable").forEach(attach);
  });
})();
